from glob import glob
from pathlib import Path
from typing import Union

import click
import yaml
from loguru import logger
from lxml import etree

from cioos_metadata_conversion.cioos import (
    get_records_from_firebase,
    cioos_firebase_to_cioos_schema,
)
from cioos_metadata_conversion import acdd
from cioos_metadata_conversion.utils import drop_empty_values


def _generate_dataset_xml(global_attributes: dict, multilingual_fields: dict = None) -> str:
    output = ["<addAttributes>"]
    for key, value in global_attributes.items():
        output += [f"    <att name='{key}'>{value}</att>"]
        if multilingual_fields and key in multilingual_fields:
            for lang, lang_value in multilingual_fields[key].items():
                if lang_value:
                    output += [
                        f"    <att name='{key}' xml:lang='{lang}'>{lang_value}</att>"
                    ]
    output += ["</addAttributes>"]
    return "\n".join(output)


def global_attributes(
    record,
    output: str = "xml",
    language: str = "en",
    metadata_link: str = None,
    multilingual: str = None,
    **kwargs,
) -> str:
    """Generate an ERDDAP dataset.xml global attributes from a metadata record
    which follows the ACDD 1.3 conventions.

    Args:
        record (dict): A metadata record.
        output (str, optional): The output format. Defaults to "xml".
        language (str, optional): The language to use. Defaults to "en".
        multilingual (str, optional): The method to use for multilingual fields. Defaults to None
            - "suffix": fieldname_en, fieldname_fr
            - "nested": fieldname: "(en) {value}; (fr) {value}"
            - "xml": fieldname: <addAttribute xml:lang="en">{value}</addAttribute>
            - "dict": fieldname: {"multilingual_fields": {"fieldname": {"en": value, "fr": value}}}
        **kwargs: Additional attributes to add to the global attributes.
    """
    global_attributes = acdd.acdd(
        record,
        output=output if output != "xml" else None,
        language=language,
        metadata_link=metadata_link,
        multilingual=multilingual if multilingual in ["suffix", "nested"] else None,
        **kwargs,
    )
    global_attributes = drop_empty_values(global_attributes)

    if not output or output not in ("xml", "dict"):
        logger.debug("Returning global attributes as dict")
        return global_attributes
    
    multilingual_fields = {}
    if multilingual in ("xml", "dict"):
        multilingual_fields = {
            "title": {
                "en": record["identification"]["title"].get("en"),
                "fr": record["identification"]["title"].get("fr"),
            },
            "summary": {
                "en": record["identification"]["abstract"].get("en"),
                "fr": record["identification"]["abstract"].get("fr"),
            },
            "comment": {
                "en": acdd.generate_comment(record, "en"),
                "fr": acdd.generate_comment(record, "fr"),
            },
        }
    if output == "xml":
        logger.debug("Generating dataset XML")
        return _generate_dataset_xml(global_attributes, multilingual_fields)
    else:
        logger.debug("Returning global attributes as dict with multilingual fields")
        global_attributes.update({"multilingual_fields": multilingual_fields})
        return global_attributes


@logger.catch(reraise=True)
def update_dataset_id(tree, dataset_id: str, global_attributes: dict):
    # Retrive dataset
    matching_dataset = tree.xpath(f"//dataset[@datasetID='{dataset_id}']")
    if not matching_dataset:
        return tree

    # No duplicate dataset IDs allowed
    if len(matching_dataset) > 1:
        raise ValueError(f"Duplicate dataset ID {dataset_id} found in XML.")
    dataset = matching_dataset[0]

    for name, value in global_attributes.items():
        # Check if the attribute already exists
        matching_attribute = dataset.xpath(f".//addAttributes/att[@name='{name}']")
        if matching_attribute:
            logger.debug(f"Updating attribute {name} with value {value}")
            matching_attribute[0].text = value
        else:
            # Create a new attribute
            logger.debug(f"Adding new attribute {name} with value {value}")
            new_attribute = etree.Element("att")
            new_attribute.text = value
            new_attribute.attrib["name"] = name
            dataset.find(".//addAttributes").append(new_attribute)

    return tree


class ERDDAP:
    def __init__(self, path) -> None:
        self.path = path
        self.tree = None

        self.read()

    def read(self):
        self.tree = etree.parse(self.path)

    def tostring(self, encoding="utf-8") -> str:
        return etree.tostring(self.tree, pretty_print=True).decode(encoding)

    def save(self, output_file=None, encoding="utf-8"):
        with open(output_file or self.path, "w") as f:
            f.write(self.tostring(encoding))

    def has_dataset_id(self, dataset_id) -> bool:
        return bool(self.tree.xpath(f"//dataset[@datasetID='{dataset_id}']"))

    def update(self, dataset_id: str, global_attributes: dict):

        def _get_attribute(name: str, value: str, lang: str = None):
            new_attribute = etree.Element("att")
            new_attribute.text = value
            new_attribute.attrib["name"] = name
            if lang:
                # Use the XML namespace for the xml:lang attribute to avoid lxml errors
                new_attribute.set("{http://www.w3.org/XML/1998/namespace}lang", lang)
            return new_attribute
        
        # Remove multilingual fields from global attributes
        multilingual_fields = global_attributes.pop("multilingual_fields", {})

        # Retrieve dataset
        matching_dataset = self.tree.xpath(f"//dataset[@datasetID='{dataset_id}']")
        if not matching_dataset:
            return

        # No duplicate dataset IDs allowed
        if len(matching_dataset) > 1:
            raise ValueError(f"Duplicate dataset ID {dataset_id} found in XML.")
        dataset = matching_dataset[0]
        
        added_multilingual_fields = set()
        for name, value in global_attributes.items():
            # Check if the attribute already exists
            matching_attribute = dataset.xpath(f".//addAttributes/att[@name='{name}']")
            if matching_attribute:
                logger.debug(f"Updating attribute {name} with value {value}")
                matching_attribute[0].text = value
            else:
                # Create a new attribute
                logger.debug(f"Adding new attribute {name} with value {value}")
                dataset.find(".//addAttributes").append(_get_attribute(name, value))

            if name in multilingual_fields:
                added_multilingual_fields.add(name)
                for lang in multilingual_fields[name]:
                    if not multilingual_fields[name][lang]:
                        continue
                    dataset.find(".//addAttributes").append(_get_attribute(name, multilingual_fields[name][lang], lang))


        # Add multilingual fields that were not added yet
        missing_multilingual_fields = set(multilingual_fields.keys()) - added_multilingual_fields
        if missing_multilingual_fields:
            logger.debug(f"Processing multilingual fields for dataset {dataset_id}")
            for name in missing_multilingual_fields:
                for lang, lang_value in multilingual_fields[name].items():
                    if not lang_value:
                        continue
                    dataset.find(".//addAttributes").append(_get_attribute(name, lang_value, lang))
        return


def _get_dataset_id_from_record(record, erddap_url, multilingual: bool = True):
    """Get the dataset ID from a metadata record.
    
    Ignore links to subsets of datasets.

    """
    dataset_ids = [
        ressource["url"].split("/")[-1].replace(".html", "")
        for ressource in record["distribution"]
        if erddap_url in ressource["url"] and not "?" in ressource["url"]
    ]

    if not dataset_ids:
        return []
    attrs  = global_attributes(record, output="dict", multilingual="dict" if multilingual else None)
    return [(dataset_id, attrs) for dataset_id in dataset_ids]


def update_dataset_xml(
    datasets_xml: str,
    records: Union[str, list],
    erddap_url: str,
    output_dir: str = None,
    multilingual: bool = False,
):
    """Update an ERDDAP dataset.xml with new global attributes."""

    # Find dataset xml
    if isinstance(records, str):
        record_files = glob(records, recursive=True)
        records = [
            yaml.safe_load(Path(record_file).read_text())
            for record_file in record_files
        ]
        if not records:
            raise ValueError(f"No records found in {records}")
        logger.info(f"Found {len(records)} records to process.")

    # Find dataset xml
    erddap_files = glob(datasets_xml)
    if not erddap_files:
        assert ValueError(f"No files found in {datasets_xml}")

    datasets = [
        dataset
        for record in records
        for dataset in _get_dataset_id_from_record(record, erddap_url, multilingual=multilingual)
        if dataset
    ]
    dataset_ids = [dataset_id for dataset_id, _ in datasets]
    updated = []
    for file in erddap_files:
        erddap = ERDDAP(file)
        for dataset_id, attrs in datasets:
            if not dataset_id:
                continue
            if erddap.has_dataset_id(dataset_id):
                # Update the XML
                erddap.update(dataset_id, attrs)
                updated += [dataset_id]
        file_output = Path(output_dir) / Path(file).name if output_dir else file
        logger.debug("Writing updated XML to {}", file_output)
        erddap.save(file_output or file)

    if missing_datasets := [
        dataset_id for dataset_id in dataset_ids if dataset_id not in updated
    ]:
        logger.warning(f"Dataset ID {missing_datasets} not found in {datasets_xml}.")
    return updated


@click.command()
@click.option("--datasets-xml", "-d", required=True, help="ERDDAP dataset.xml file.")
@click.option("--records", "-r", help="Metadata records.")
@click.option("--erddap-url", "-u", required=True, help="ERDDAP base URL.")
@click.option("--output-dir", "-o", help="Output directory.")
@click.option(
    "--record-status", "-s", default="published", help="Record submission status."
)
@click.option("--firebase-auth-key", "-k", help="Firebase auth key.")
@click.option("--region", "-r", help="Region to fetch records for.")
@click.option("--database-url", "-b", help="Firebase database URL.")
@click.option("--multilingual", "-m", is_flag=True, help="Enable multilingual support.", default=False)
def update(
    datasets_xml,
    records,
    erddap_url,
    output_dir,
    record_status,
    firebase_auth_key,
    region,
    database_url,
    multilingual,
):
    """Update ERDDAP dataset xml with metadata records."""

    if not records and firebase_auth_key and region and database_url:
        logger.info(
            "Fetching records from Firebase for region: {}, status: {}, database URL: {}",
            region,
            record_status,
            database_url,
        )

        records = get_records_from_firebase(
            region,
            firebase_auth_key,
            None,
            record_status.split(","),
            database_url,
        )
        # Convert firebase records to CIOOS schema
        logger.info("Retrieved {} records", len(records))
        if not records:
            return
        records = [
            cioos_firebase_to_cioos_schema(record)
            if isinstance(record, dict)
            else record
            for record in records
        ]
    logger.info("Updating ERDDAP dataset xml: {}", datasets_xml)
    logger.info("Enable multilingual support: {}", multilingual)
    update_dataset_xml(datasets_xml, records, erddap_url, output_dir, multilingual)

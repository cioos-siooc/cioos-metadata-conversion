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

    if not output or output != "xml":
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
                "en": "\n\n".join(acdd.generate_comment(record, "en")),
                "fr": "\n\n".join(acdd.generate_comment(record, "fr")),
            },
        }
    if output == "xml":
        return _generate_dataset_xml(global_attributes, multilingual_fields)
    else:
        return drop_empty_values(global_attributes.update({"multilingual_fields": multilingual_fields}))


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


# Function to update XML
@logger.catch(reraise=True)
def _update_xml(xml_file, dataset_id, updates, encoding="utf-8") -> str:
    # Parse the XML with comments
    tree = etree.parse(xml_file)
    tree = update_dataset_id(tree, dataset_id, updates)
    # Write back to the same file (or use a different file name to save a new version.
    return etree.tostring(tree, pretty_print=True).decode(encoding)


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

        # Remove multilingual fields from global attributes
        multilingual_fields = global_attributes.pop("multilingual_fields", None)

        # Retrieve dataset
        matching_dataset = self.tree.xpath(f"//dataset[@datasetID='{dataset_id}']")
        if not matching_dataset:
            return

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

        # Add multilingual fields if any
        if multilingual_fields:
            logger.debug(f"Processing multilingual fields for dataset {dataset_id}")
            for name, lang_values in multilingual_fields.items():
                for lang, lang_value in lang_values.items():
                    if not lang_value:
                        continue
                    matching_attribute = dataset.xpath(
                        f".//addAttributes/att[@name='{name}' and @xml:lang='{lang}']"
                    )
                    if matching_attribute:
                        logger.debug(f"Updating attribute {name} ({lang}) with value {lang_value}")
                        matching_attribute[0].text = lang_value
                    else:
                        # Create a new attribute
                        logger.debug(f"Adding new attribute {name} ({lang}) with value {lang_value}")
                        new_attribute = etree.Element("att")
                        new_attribute.text = lang_value
                        new_attribute.attrib["name"] = name
                        new_attribute.attrib["xml:lang"] = lang
                        dataset.find(".//addAttributes").append(new_attribute)
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
    attrs  = global_attributes(record, output=None, multilingual="dict" if multilingual else None)
    return [(dataset_id, attrs) for dataset_id in dataset_ids]


def update_dataset_xml(
    datasets_xml: str,
    records: Union[str, list],
    erddap_url: str,
    output_dir: str = None,
    multilingual: bool = True,
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
    erddap_files = glob(datasets_xml, recursive=True)
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
@click.option("--not-multilingual", "-m", is_flag=True, help="Disable multilingual support.")
def update(
    datasets_xml,
    records,
    erddap_url,
    output_dir,
    record_status,
    firebase_auth_key,
    region,
    database_url,
    not_multilingual,
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
    logger.info("Disable multilingual support: {}", not_multilingual)
    update_dataset_xml(datasets_xml, records, erddap_url, output_dir, not not_multilingual)

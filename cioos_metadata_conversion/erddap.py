from glob import glob
from pathlib import Path
from typing import Union

import click
import yaml
from loguru import logger
from lxml import etree

from cioos_metadata_conversion.utils import drop_empty_values
from cioos_metadata_conversion.acdd import global_attributes


def generate_dataset_xml(global_attributes: dict):
    output = ["<addAttributes>"]
    for key, value in global_attributes.items():
        output += [f"    <att name='{key}'>{value}</att>"]
    output += ["</addAttributes>"]
    return "\n".join(output)



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


def _get_dataset_id_from_record(record, erddap_url):
    for ressource in record["distribution"]:
        if erddap_url in ressource["url"]:
            return ressource["url"].split("/")[-1].replace(
                ".html", ""
            ), global_attributes(record, output=None)
    return None, None


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

        # Retrive dataset
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

        return


def update_dataset_xml(
    datasets_xml: str,
    records: Union[str, list],
    erddap_url: str,
    output_dir: str = None,
):
    """Update an ERDDAP dataset.xml with new global attributes."""

    # Find dataset xml
    if isinstance(records, str):
        record_files = glob(records, recursive=True)
        records = [
            yaml.safe_load(Path(record_file).read_text())
            for record_file in record_files
        ]

    # Find dataset xml
    erddap_files = glob(datasets_xml, recursive=True)
    if not erddap_files:
        assert ValueError(f"No files found in {datasets_xml}")

    datasets = [_get_dataset_id_from_record(record, erddap_url) for record in records]
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
@click.option("--records", "-r", required=True, help="Metadata records.")
@click.option("--erddap-url", "-u", required=True, help="ERDDAP base URL.")
@click.option("--output-dir", "-o", help="Output directory.")
def update(datasets_xml, records, erddap_url, output_dir):
    """Update ERDDAP dataset xml with metadata records."""
    update_dataset_xml(datasets_xml, records, erddap_url, output_dir)

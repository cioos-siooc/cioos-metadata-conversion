from glob import glob
from pathlib import Path

import yaml
from jinja2 import Template
from loguru import logger
from lxml import etree

KEYWORDS_PREFIX_MAPPING = {
    "default": {
        "prefix": "",
        "label": None,
    },
    "eov": {
        "prefix": "CIOOS:",
        "label": "CIOOS Essential Ocean Variables Vocabulary",
    },
    "taxa": {
        "prefix": "GBIF:",
        "label": "GBIF Taxonomy Vocabulary",
    },
}


def generate_dataset_xml(global_attributes: dict):
    output = ["<addAttributes>"]
    for key, value in global_attributes.items():
        output += [f"    <att name='{key}'>{value}</att>"]
    output += ["</addAttributes>"]
    return "\n".join(output)


def _get_contact(contact: dict, role: str) -> dict:
    """Generate a CFF contact from a metadata contact."""
    if "individual" in contact:
        attrs = {
            f"{role}_name": contact["individual"].get("name"),
            f"{role}_email": contact["individual"].get("email"),
            f"{role}_orcid": contact["individual"].get("orcid"),
            f"{role}_type": "person",
        }
    else:
        attrs = {
            f"{role}_name": contact["organization"]["name"],
            f"{role}_email": contact["organization"].get("email"),
            f"{role}_type": "institution",
        }

    if not contact.get("organization"):
        logger.warning(f"No organization found for {role} contact.")
        return attrs

    return {
        **attrs,
        f"{role}_institution": contact["organization"].get("name"),
        f"{role}_address": contact["organization"].get("address"),
        f"{role}_city": contact["organization"].get("city"),
        f"{role}_country": contact["organization"].get("country"),
        f"{role}_url": contact["organization"].get("url"),
        f"{role}_ror": contact["organization"].get("ror"),
    }


def _get_contributors(contacts: list, separator=";") -> dict:
    """Generate a list of CFF contributors from a list of metadata contacts."""
    return {
        "contributor_name": separator.join(
            [
                (
                    contact["individual"]["name"]
                    if ("individual" in contact and contact["individual"].get("name"))
                    else contact["organization"]["name"]
                )
                for contact in contacts
            ]
        ),
        "contributor_role": separator.join(
            [",".join(contact["roles"]) for contact in contacts]
        ),
    }


def generate_history(record, language="en"):
    """Generate a history string from a metadata record."""
    history = record["metadata"].get("history")
    if not history:
        return None
    if isinstance(history, dict):
        return record["metadata"]["history"][language]
    elif isinstance(history, list):
        return "Metadata record history:\n" + yaml.dump(history)
    else:
        logger.warning("Invalid history format.")


def global_attributes(
    record, output="xml", language="en", base_url="https://catalogue.hakai.org"
) -> str:
    """Generate an ERDDAP dataset.xml global attributes from a metadata record
    which follows the ACDD 1.3 conventions.
    """
    creator = [contact for contact in record["contact"] if "owner" in contact["roles"]]
    publisher = [
        contact for contact in record["contact"] if "publisher" in contact["roles"]
    ]

    if len(creator) > 1:
        logger.warning("Multiple creators found, using the first one.")

    if len(publisher) > 1:
        logger.warning("Multiple publishers found, using the first one.")

    comment = []
    if record["metadata"]["use_constraints"].get("limitations", {}).get(language):
        comment += [
            "##Limitations:\n"
            + record["metadata"]["use_constraints"]["limitations"][language]
        ]
    translation_comment = (
        record["metadata"]["use_constraints"]
        .get("limitations", {})
        .get("translations", {})
        .get(language)
    )
    if not translation_comment:
        pass
    elif isinstance(translation_comment, str):
        comment += [
            "##Translation:\n"
            + record["metadata"]["use_constraints"]["limitations"]["translations"].get(
                language
            )
        ]
    elif isinstance(translation_comment, dict) and "message" in translation_comment:
        comment += ["##Translation:\n" + translation_comment["message"]]
    else:
        logger.warning("Invalid translation comment format: {}", translation_comment)

    metadata_link = (
        base_url
        + record["metadata"]["naming_authority"].replace(".", "-")
        + "_"
        + record["metadata"]["identifier"]
    )

    global_attributes = {
        "title": record["identification"]["title"][language],
        "summary": record["identification"]["abstract"][language],
        "project": ",".join(record["identification"].get("project", [])),
        "comment": "\n\n".join(comment),
        "progress": record["identification"][
            "progress_code"
        ],  # not a standard ACDD attribute
        "keywords": ",".join(
            [
                KEYWORDS_PREFIX_MAPPING.get(group, {}).get("prefix", "") + keyword
                for group, keywords in record["identification"]["keywords"].items()
                for keyword in keywords.get(language, [])
            ]
        ),
        "keywords_vocabulary": ",".join(
            [
                KEYWORDS_PREFIX_MAPPING[group]["prefix"]
                + " "
                + KEYWORDS_PREFIX_MAPPING[group]["label"]
                for group, keywords in record["identification"]["keywords"].items()
                if keywords.get(language)
                and group in KEYWORDS_PREFIX_MAPPING
                and KEYWORDS_PREFIX_MAPPING[group]["label"]
            ]
        ),
        "id": record["metadata"]["identifier"],
        "naming_authority": record["metadata"]["naming_authority"],
        "date_modified": record["metadata"]["dates"].get("revision"),
        "date_created": record["metadata"]["dates"].get("publication"),
        "product_version": record["identification"].get("edition"),
        "history": generate_history(record, language),
        "license": record["metadata"]["use_constraints"].get("licence", {}).get("code"),
        **(_get_contact(creator[0], "creator") if creator else {}),
        **(_get_contact(publisher[0], "publisher") if publisher else {}),
        **_get_contributors(record["contact"]),
        "doi": record["identification"].get("identifier"),
        "metadata_link": metadata_link,
        "infoUrl": metadata_link,
        "metadata_form": record["metadata"]
        .get("maintenance_note", "")
        .replace("Generated from ", ""),
    }
    if not output:
        return global_attributes
    if output == "xml":
        return generate_dataset_xml(global_attributes)


@logger.catch(reraise=True)
def update_dataset_id(tree, dataset_id:str, global_attributes:dict):
    
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
    for ressource in record["metadata"]["resources"]:
        if erddap_url in ressource["url"]:
            return ressource["url"].split("/")[-1]

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
    
    def update(self, dataset_id:str, global_attributes:dict):
        
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
    dataset_xml: str,
    records: list,
    output_dir: str = None,
):
    """Update an ERDDAP dataset.xml with new global attributes."""

    # Find dataset xml
    erddap_files = glob(dataset_xml, recursive=True)
    if not erddap_files:
        assert ValueError(f"No files found in {dataset_xml}")

    datasets = {_get_dataset_id_from_record(record) for record in records}


    updated = []
    for file in erddap_files:
        erddap = ERDDAP(file)
        for dataset_id, attrs in datasets:
            if erddap.has_dataset_id(dataset_id):
                # Update the XML
                erddap.update(dataset_id, attrs)
                updated += [dataset_id]
        file_output = Path(output_dir) / Path(file).name if output_dir else file
        erddap.save(file_output or file)
    
    if missing_datasets := datasets - set(updated):
        logger.warning(f"Dataset ID {missing_datasets} not found in {dataset_xml}.")
    return updated

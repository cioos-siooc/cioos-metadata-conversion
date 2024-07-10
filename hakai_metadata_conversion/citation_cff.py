"""
Module dedicated to the citation file format:
<https://citation-file-format.github.io>
"""

import yaml
from loguru import logger


def get_cff_person(author):
    """Generate a CFF person"""
    return {
        "given-names": author["individual"]["name"].split(", ")[1],
        "family-names": author["individual"]["name"].split(", ")[0],
        "email": author["individual"]["email"],
        "orcid": author["individual"]["orcid"],
        "affiliation": author["organization"]["name"],
        "address": author["organization"]["address"],
        "city": author["organization"]["city"],
        "country": author["organization"]["country"],
        "website": author["organization"]["url"],
        "ror": author["organization"].get("ror"),
    }


def get_cff_entity(entity):
    return {
        "name": entity["organization"]["name"],
        "address": entity["organization"].get("address"),
        "city": entity["organization"].get("city"),
        "country": entity["organization"].get("country"),
        "contact": entity["organization"].get("email"),
        "website": entity["organization"].get("url"),
        "orcid": entity["organization"].get("orcid"),
        "ror": entity["organization"].get("ror"),
    }


def get_cff_contact(contact):
    return (
        get_cff_person(contact)
        if contact.get("individual")
        else get_cff_entity(contact)
    )


def citation_cff(
    record,
    output_format="yaml",
    language: str = "en",
    message="If you use this software, please cite it as below",
    ressource_base_url="https://catalogue.hakai.org/dataset/",
    record_type="dataset",
) -> str:
    """Generate a convention.cff file from a CKAN record.

    This is based on the documentation at:
    <https://github.com/citation-file-format/citation-file-format/blob/main/schema-guide.md#identifiers>
    """
    resource_url = (
        ressource_base_url
        + record["metadata"]["naming_authority"].replace(".", "-")
        + "_"
        + record["metadata"]["identifier"]
    )
    record = {
        "cff-version": "1.2.0",
        "message": message,
        "authors": [
            get_cff_contact(contact)
            for contact in record["contact"]
            if contact["inCitation"]
        ],
        "title": record["identification"]["title"][language],
        "abstract": record["identification"]["abstract"][language],
        "date": record["metadata"]["dates"]["revision"],
        "contact": [
            get_cff_contact(contact)
            for contact in record["contact"]
            if "pointOfContact" in contact["roles"]
        ],
        "identifiers": [
            {
                "description": f"{record['metadata']['naming_authority']} Unique Identifier",
                "type": "other",
                "value": record["metadata"]["identifier"],
            },
            {
                "description": "Hakai Metadata record URL",
                "type": "url",
                "value": resource_url,
            },
            {
                "description": "Hakai Metadata record DOI",
                "type": "doi",
                "value": (
                    record["identification"]["identifier"]
                    if "doi.org" in record["identification"]["identifier"]
                    else None
                ),
            },
            {
                "description": "Hakai Metadata Form used to generate this record",
                "type": "url",
                "value": record["metadata"]["maintenance_note"].replace(
                    "Generated from ", ""
                ),
            },
            # Generate ressources links
            *[
                {
                    "description": f"{distribution['name'].get(language)}: {distribution.get('description',{}).get(language)}",
                    "type": "url",
                    "value": distribution["url"],
                }
                for distribution in record["distribution"]
            ],
        ],
        "keywords": [
            keyword
            for _, group in record["identification"]["keywords"].items()
            for keyword in group[language]
        ],
        "license": record["metadata"]["use_constraints"]["licence"]["code"],
        "license-url": record["metadata"]["use_constraints"]["licence"]["url"],
        "type": record_type,
        "url": resource_url,
        "version": record["identification"]["edition"],
    }

    if output_format == "yaml":
        return yaml.dump(record, default_flow_style=False)
    return record

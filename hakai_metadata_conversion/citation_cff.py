"""
Module dedicated to the citation file format:
<https://citation-file-format.github.io>
"""

import pycountry
import yaml
from loguru import logger

from hakai_metadata_conversion.utils import drop_empty_values


def _get_country_code(country_name):
    if not country_name:
        return None
    try:
        return pycountry.countries.lookup(country_name).alpha_2
    except LookupError:
        logger.warning(f"Country {country_name} not found in pycountry")
        return None


def _fix_url(url):
    return url if url.startswith("http") else f"https://{url}"


def get_cff_person(author):
    """Generate a CFF person"""
    return drop_empty_values(
        {
            "given-names": author["individual"]["name"].split(", ")[1],
            "family-names": author["individual"]["name"].split(", ")[0],
            "email": author["individual"]["email"],
            "orcid": author["individual"]["orcid"],
            "affiliation": author["organization"]["name"],
            "address": author["organization"]["address"],
            "city": author["organization"]["city"],
            "country": _get_country_code(author["organization"]["country"]),
            "website": _fix_url(author["organization"]["url"]),
            # "ror": author["organization"].get("ror"), # not in CFF schema
        }
    )


def get_cff_entity(entity):
    return drop_empty_values(
        {
            "name": entity["organization"]["name"],
            "address": entity["organization"].get("address"),
            "city": entity["organization"].get("city"),
            "country": _get_country_code(entity["organization"].get("country")),
            "email": entity["organization"].get("email"),
            "website": _fix_url(entity["organization"].get("url")),
            "orcid": entity["organization"].get("orcid"),
            # "ror": entity["organization"].get("ror"), # not in CFF schema
        }
    )


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
        "date-released": record["metadata"]["dates"]["revision"].split("T")[0],
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
                    record["identification"]["identifier"].replace(
                        "https://doi.org/", ""
                    )
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
    record = drop_empty_values(record)

    if output_format == "yaml":
        return yaml.dump(record, default_flow_style=False)
    return record

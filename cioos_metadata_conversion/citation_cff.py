"""
Module dedicated to the citation file format:
<https://citation-file-format.github.io>
"""

import pycountry
import yaml
from loguru import logger

from cioos_metadata_conversion.utils import drop_empty_values


def _get_placeholder(language):
    if language == "en":
        return "Not available"
    elif language == "fr":
        return "Non disponible"
    else:
        return "Not available"


def _get_country_code(country_name):
    if not country_name:
        return None
    try:
        return pycountry.countries.lookup(country_name).alpha_2
    except LookupError:
        logger.warning(f"Country {country_name} not found in pycountry")
        return None


def _fix_url(url):
    if not url:
        return None
    return url if url.startswith("http") else f"https://{url}"


def get_cff_person(author):
    """Generate a CFF person"""
    return drop_empty_values(
        {
            "given-names": (
                author["individual"]["name"].split(", ")[1]
                if ", " in author["individual"].get("name", "")
                else ""
            ),
            "family-names": author["individual"].get("name", "").split(", ")[0],
            "email": author["individual"].get("email"),
            "orcid": author["individual"].get("orcid"),
            "affiliation": author.get("organization", {}).get("name"),
            "address": author.get("organization", {}).get("address"),
            "city": author.get("organization", {}).get("city"),
            "country": _get_country_code(author.get("organization", {}).get("country")),
            "website": _fix_url(author.get("organization", {}).get("url")),
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


def _get_doi(record):
    if not record["identification"].get("identifier", ""):
        return []
    return [
        {
            "description": "DOI",
            "type": "doi",
            "value": (
                record["identification"]["identifier"].replace("https://doi.org/", "")
                if "doi.org" in record["identification"].get("identifier", "")
                else None
            ),
        }
    ]


def _get_ressources(record, language):
    ressources = []
    for distribution in record["distribution"]:
        if not distribution.get("url", "").startswith("http"):
            logger.warning(f"Invalid ressource URL: {distribution.get('url')}")
            continue
        ressources.append(
            {
                "description": ": ".join(
                    [
                        item
                        for item in [
                            distribution.get("name", {}).get(language, ""),
                            distribution.get("description", {}).get(
                                language, _get_placeholder(language)
                            ),
                        ]
                        if item
                    ]
                ),
                "type": "url",
                "value": distribution["url"],
            }
        )
    return ressources


def _get_unique_authors(record):
    authors = []
    for author in record["contact"]:
        contact = get_cff_contact(author)
        if contact not in authors:
            authors.append(contact)
    return authors


def citation_cff(
    record,
    output_format="yaml",
    language: str = "en",
    message="If you use this software, please cite it as below",
    ressource_base_url="https://catalogue.cioos.org/dataset/",
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
        "authors": _get_unique_authors(record),
        "title": record["identification"]["title"].get(language),
        "abstract": record["identification"]["abstract"].get(language),
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
                "description": "Metadata record URL",
                "type": "url",
                "value": resource_url,
            },
            *_get_doi(record),
            {
                "description": "Metadata Form used to generate this record",
                "type": "url",
                "value": record["metadata"]["maintenance_note"].replace(
                    "Generated from ", ""
                ),
            },
            *_get_ressources(record, language=language),
        ],
        "keywords": list(
            set(
                [
                    keyword
                    for _, group in record["identification"]["keywords"].items()
                    for keyword in group.get(language, [])
                ]
            )
        ),
        "license": record["metadata"].get("use_constraints", {}).get("licence", {}).get("code"),
        "license-url": record["metadata"].get("use_constraints", {}).get("licence", {}).get("url"),
        "type": record_type,
        "url": resource_url,
        "version": record["identification"].get("edition"),
    }
    record = drop_empty_values(record)

    if output_format == "yaml":
        return yaml.dump(record, default_flow_style=False)
    return record

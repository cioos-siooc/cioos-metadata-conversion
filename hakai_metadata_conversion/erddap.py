import yaml
from loguru import logger

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

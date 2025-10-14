# ACDD 1.3 Global Attributes

from loguru import logger
import yaml
import json

from cioos_metadata_conversion.utils import drop_empty_values

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


@logger.catch(default={})
def _get_platform(record):
    if not record.get("platform"):
        return {}
    platform = record["platform"]
    return {
        "platform": platform[0]["type"],
        "platform_vocabulary": "http://vocab.nerc.ac.uk/collection/L06/current/",
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


def generate_comment(record, language="en"):
    """Generate a comment string from a metadata record."""
    comments = []
    if (
        record["metadata"]
        .get("use_constraints", {})
        .get("limitations", {})
        .get(language)
    ):
        comments += [
            "##Limitations:\n"
            + record["metadata"]["use_constraints"]["limitations"][language]
        ]
    translation_comment = (
        record["metadata"]
        .get("use_constraints", {})
        .get("limitations", {})
        .get("translations", {})
        .get(language)
    )
    if not translation_comment:
        pass
    elif isinstance(translation_comment, str):
        comments += [
            "##Translation:\n"
            + record["metadata"]
            .get("use_constraints", {})
            .get("limitations", {})
            .get("translations", {})
            .get(language)
        ]
    elif isinstance(translation_comment, dict) and "message" in translation_comment:
        comments += ["##Translation:\n" + translation_comment["message"]]
    else:
        logger.warning("Invalid translation comment format: {}", translation_comment)
    return "\n\n".join(comments) if comments else None


def _generate_multilingual_fields(fields: dict, method: str) -> dict:
    languages = ["en", "fr"]
    if method == "suffix":
        return {
            f"{field}_{lang}": values.get(lang)
            for field, values in fields.items()
            for lang in languages
            if values.get(lang)
        }
    elif method == "nested":
        return {
            field: "; ".join(
                [
                    f"({lang}) {values.get(lang)}"
                    for lang in languages
                    if values.get(lang)
                ]
            )
            for field, values in fields.items()
        }
    else:
        logger.warning(f"Unsupported multilingual method: {method}, skipping.")
        return {}


def acdd(
    record,
    output: str = "xml",
    language: str = "en",
    metadata_link: str = None,
    multilingual: str = None,
    **kwargs,
) -> str:
    """Generate an ACDD global attributes from a metadata record
    which follows the ACDD 1.3 conventions.

    Args:
        record (dict): A metadata record.
        language (str, optional): The language to use. Defaults to "en".
        metadata_link (str, optional): A link to the metadata record. Defaults to None.
        multilingual (str, optional): The method to use for multilingual fields. Defaults to None
            - "suffix": fieldname_en, fieldname_fr
            - "nested": fieldname: "(en) {value}; (fr) {value}"
        **kwargs: Additional attributes to add to the global attributes.
    """
    creator = [contact for contact in record["contact"] if "owner" in contact["roles"]]
    publisher = [
        contact for contact in record["contact"] if "publisher" in contact["roles"]
    ]

    if len(creator) > 1:
        logger.warning("Multiple creators found, using the first one.")

    if len(publisher) > 1:
        logger.warning("Multiple publishers found, using the first one.")

    global_attributes = {
        "institution": (
            creator[0].get("organization", {}).get("name") if creator else ""
        ),
        "title": record["identification"]["title"][language],
        "summary": record["identification"]["abstract"][language],
        "comment": "\n\n".join(generate_comment(record, language)),
        "project": ",".join(record["identification"].get("project", [])),
        "progress": record["identification"][
            "progress_code"
        ],  # not a standard ACDD attribute
        "keywords": ",".join(
            [
                KEYWORDS_PREFIX_MAPPING.get(group, {}).get("prefix", "") + keyword
                for group, keywords in record["identification"]["keywords"].items()
                for keyword in keywords.get(language, [])
                if keyword
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
        "license": record["metadata"]
        .get("use_constraints", {})
        .get("licence", {})
        .get("url"),
        **(_get_contact(creator[0], "creator") if creator else {}),
        **(_get_contact(publisher[0], "publisher") if publisher else {}),
        **_get_contributors(record["contact"]),
        "doi": record["identification"].get("identifier"),
        "metadata_link": record["identification"].get("identifier") or metadata_link,
        "metadata_form": record["metadata"]
        .get("maintenance_note", "")
        .replace("Generated from ", ""),
        **_get_platform(record),
        **kwargs,
    }
    if multilingual:
        multiligual_fields = {
            "title": record["identification"]["title"],
            "summary": record["identification"]["abstract"],
            "comments": {
                "fr": generate_comment(record, "fr"),
                "en": generate_comment(record, "en"),
            },
        }
        global_attributes.update(
            _generate_multilingual_fields(multiligual_fields, multilingual)
        )

    # Remove empty values
    global_attributes = drop_empty_values(global_attributes)

    if output == "json":
        return json.dumps(global_attributes, indent=2)
    elif output == "yaml":
        return yaml.dump(global_attributes, sort_keys=False)
    elif output:
        logger.warning(f"Unsupported output format: {output}, returning dict.")
        return global_attributes
    else:
        return global_attributes

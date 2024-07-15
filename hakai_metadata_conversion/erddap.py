from jinja2 import Template
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


# dataset xml global attributes jinja2 template
dataset_xml_template = Template(
    """
    <addAttributes>
    {% for key, value in global_attributes.items() %}
        <att name="{{ key }}">{{ value }}</att>{% endfor %}
    </addAttributes>
"""
)


def _get_contact(contact: dict, role: str) -> dict:
    """Generate a CFF contact from a metadata contact."""
    if "individual" in contact:
        attrs = {
            f"{role}_name": contact["individual"]["name"],
            f"{role}_email": contact["individual"]["email"],
            f"{role}_orcid": contact["individual"].get("orcid"),
            f"{role}_type": "person",
        }
    else:
        attrs = {
            f"{role}_name": contact["organization"]["name"],
            f"{role}_email": contact["organization"]["email"],
            f"{role}_type": "institution",
        }

    return {
        **attrs,
        f"{role}_institution": contact["organization"]["name"],
        f"{role}_address": contact["organization"]["address"],
        f"{role}_city": contact["organization"]["city"],
        f"{role}_country": contact["organization"]["country"],
        f"{role}_url": contact["organization"]["url"],
        f"{role}_ror": contact["organization"].get("ror"),
    }


def _get_contributors(contacts: list, separator=";") -> dict:
    """Generate a list of CFF contributors from a list of metadata contacts."""
    return {
        "contributor_name": separator.join(
            [
                (
                    contact["individual"]["name"]
                    if "individual" in contact
                    else contact["organization"]["name"]
                )
                for contact in contacts
            ]
        ),
        "contributor_role": separator.join(
            [",".join(contact["roles"]) for contact in contacts]
        ),
    }


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
    if record["metadata"]["use_constraints"]["limitations"]:
        comment += [
            "##Limitations:\n"
            + record["metadata"]["use_constraints"]["limitations"][language]
        ]
    if record["metadata"]["use_constraints"]["limitations"].get("translations").get(
        language
    ):
        comment += [
            "##Translation:\n"
            + record["metadata"]["use_constraints"]["limitations"]["translations"][
                language
            ]
        ]

    metadata_link = (
        base_url
        + record["metadata"]["naming_authority"].replace(".", "-")
        + "_"
        + record["metadata"]["identifier"]
    )

    global_attributes = {
        "title": record["identification"]["title"][language],
        "summary": record["identification"]["abstract"][language],
        "project": ",".join(record["identification"]["project"]),
        "comment": "\n\n".join(comment),
        "progress": record["identification"][
            "progress_code"
        ],  # not a standard ACDD attribute
        "keywords": ",".join(
            [
                KEYWORDS_PREFIX_MAPPING.get(group, {}).get("prefix", "") + keyword
                for group, keywords in record["identification"]["keywords"].items()
                for keyword in keywords[language]
            ]
        ),
        "keywords_vocabulary": ",".join(
            [
                KEYWORDS_PREFIX_MAPPING[group]["prefix"]
                + " "
                + KEYWORDS_PREFIX_MAPPING[group]["label"]
                for group, keywords in record["identification"]["keywords"].items()
                if keywords[language]
                and group in KEYWORDS_PREFIX_MAPPING
                and KEYWORDS_PREFIX_MAPPING[group]["label"]
            ]
        ),
        "id": record["metadata"]["identifier"],
        "naming_authority": record["metadata"]["naming_authority"],
        "date_modified": record["metadata"]["dates"]["revision"],
        "date_created": record["metadata"]["dates"]["publication"],
        "product_version": record["identification"]["edition"],
        "history": record["metadata"]["history"][language],
        "license": record["metadata"]["use_constraints"]["licence"]["code"],
        **(_get_contact(creator[0], "creator") if creator else {}),
        **(_get_contact(publisher[0], "publisher") if publisher else {}),
        **_get_contributors(record["contact"]),
        "doi": record["identification"]["identifier"],
        "metadata_link": metadata_link,
        "infoUrl": metadata_link,
        "metadata_form": record["metadata"]["maintenance_note"].replace(
            "Generated from ", ""
        ),
    }
    if not output:
        return global_attributes
    if output == "xml":
        return dataset_xml_template.render(global_attributes=global_attributes)

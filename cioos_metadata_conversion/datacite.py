# Generate a DataCite record from a CIOOS record
#
# This follows the DataCite schema v4.7 as described in:
# https://schema.datacite.org/meta/kernel-4.7/metadata.xsd
#
# Required fields (per XSD):
#   - identifier (DOI)
#   - creators
#   - titles
#   - publisher
#   - publicationYear
#   - resourceType
#
# All other fields (subjects, contributors, dates, descriptions,
# geoLocations, fundingReferences, rightsList, etc.) are optional.
import json
from datetime import datetime

from datacite import schema45
from loguru import logger

from cioos_metadata_conversion.utils import camel_to_title

CONTRIBUTOR_TYPE_MAPPING_FROM_CIOOS = {
    "pointOfContact": "ContactPerson",
    "distributor": "Distributor",
    "editor": "Editor",
    "rightsHolder": "RightsHolder",
    "sponsor": "Sponsor",
    "processor": "DataCurator",
    "metadataCustodian": "DataCurator",
    "owner": "RightsHolder",
    "funder": "Sponsor",
    "principalInvestigator": "ProjectLeader",
    "collaborator": "ProjectMember",
    "originator": "ProjectMember",
    "contributor": "ProjectMember",
    "author": "Researcher",
    "coAuthor": "Researcher",
    "mediator": "Other",
    "ressourceProvider": "Other",
    "stakeholder": "Other",
    "custodian": "DataCurator"
}


def _get_personal_info(contact) -> dict:
    nameIdentifier = {}
    if "orcid" in contact["individual"]:
        nameIdentifier = {
            "nameIdentifier": contact["individual"]["orcid"],
            "nameIdentifierScheme": "ORCID",
            "schemeUri": "https://orcid.org",
        }

    return {
        "name": contact["individual"].get("name")
        or f"{contact['individual'].get('givenNames', '')} {contact['individual'].get('lastName', '')}".strip(),
        "nameType": "Personal",
        "givenName": contact["individual"].get("givenNames", ""),
        "familyName": contact["individual"].get("lastName", ""),
        "nameIdentifier": nameIdentifier,
    }


def _get_organization_info(contact) -> dict:
    return {
        "name": contact["organization"]["name"],
        "nameType": "Organizational",
        "lang": "en",
    }


def _get_contact_info(contact) -> dict:
    """
    Get the contact information from the Cioos record.
    """
    affiliation = {"name": contact.get("organization", {}).get("name")}
    if "ror" in contact.get("organization", {}):
        affiliation["affiliationIdentifier"] = contact.get("organization", {}).get(
            "ror"
        )
        affiliation["affiliationIdentifierScheme"] = "ROR"
        affiliation["schemeUri"] = "https://ror.org/"
    return {
        **(
            _get_personal_info(contact)
            if "individual" in contact
            else _get_organization_info(contact)
        ),
        "affiliation": [affiliation],
    }


def _get_creators(record) -> list:
    """
    Get the creators from the Cioos record.
    """
    return [
        _get_contact_info(contact)
        for contact in record.get("contact", [])
        if contact.get("inCitation")
    ]


def _get_contributors(record) -> list:
    """
    Get the contributors from the CIOOS record.
    """

    def _get_contributor_type(role):
        """
        Get the contributor type from the Cioos record.
        """
        if role not in CONTRIBUTOR_TYPE_MAPPING_FROM_CIOOS:
            logger.error(f"Unknown contributor type: {role}")
            return "Other"
        return CONTRIBUTOR_TYPE_MAPPING_FROM_CIOOS[role]

    return [
        {
            **_get_contact_info(contact),
            "contributorType": _get_contributor_type(role),
            "lang": "en",
        }
        for contact in record.get("contact", [])
        for role in contact.get("roles", [])
        if role != "publisher"
    ]


def _get_publisher(record) -> dict:
    for contact in record.get("contact", []):
        if "publisher" in contact["roles"]:
            publisher = {
                "name": contact["organization"]["name"],
                "lang": "en",
            }
            if "ror" in contact["organization"]:
                publisher["publisherIdentifier"] = contact["organization"]["ror"]
                publisher["publisherIdentifierScheme"] = "ROR"
                publisher["schemeUri"] = "https://ror.org/"
            return publisher
    logger.warning("No publisher found in the record.")
    return {}


def _get_funding_references(record) -> dict:
    """
    Get the funding references from the Cioos record.
    """

    def _get_funder_ror(contact) -> dict:
        if not contact.get("organization", {}).get("ror"):
            return {}
        return {
            "funderIdentifier": contact["organization"]["ror"],
            "funderIdentifierType": "ROR",
        }

    return {
        "fundingReferences": [
            {
                "funderName": contact.get("organization", {}).get("name"),
                **_get_funder_ror(contact),
            }
            for contact in record.get("contact", [])
            if "funder" in contact.get("roles", [])
        ]
    }


def _get_subject_scheme(group) -> dict:
    """
    Get the subject scheme from the Cioos record.
    """
    if group == "eov":
        return {
            "subjectScheme": "GOOS EOV",
            "schemeUri": "https://www.goosocean.org/eov",
        }
    elif group == "taxa":
        return {
            "subjectScheme": "GBIF",
            "schemeUri": "https://www.gbif.org",
        }
    elif group == "default":
        return {}
    else:
        logger.error(f"Unknown subject group: {group}")
        return {}


def _get_dates(record) -> list:
    """
    Get the dates from the Cioos record. Only includes entries where the date exists.
    """
    dates = []
    created = record.get("identification", {}).get("dates", {}).get("creation")
    if created:
        dates.append({"date": created, "dateType": "Created"})

    revision = record.get("metadata", {}).get("dates", {}).get("revision")
    if revision:
        dates.append({"date": revision, "dateType": "Updated"})

    temporal_begin = record.get("identification", {}).get("temporal_begin")
    temporal_end = record.get("identification", {}).get("temporal_end")
    if temporal_begin or temporal_end:
        dates.append({
            "date": f"{temporal_begin or '*'}/{temporal_end or '*'}",
            "dateType": "Collected",
        })

    return dates


def _get_alternate_identifiers(record) -> dict:
    """
    Get the alternate identifiers from the Cioos record.
    """
    return {"alternateIdentifiers": []}


def _get_related_identifiers(record) -> dict:
    """
    Get the related identifiers from the Cioos record.
    """
    return {"relatedIdentifiers": [
        {
            "relatedIdentifier": item['code'],
            "relatedIdentifierType": item["authority"],
            "relationType": item['association_type'],
        }
        for item in record['identification'].get('associated_resources', [])
    ]}


def _get_related_items(record) -> dict:
    """
    Get the related items from the Cioos record.
    """
    return {"relatedItems": []}


def _get_right_lists(record) -> dict:
    """
    Get the right lists from the Cioos record.
    """
    licence = record.get("metadata", {}).get("use_constraints", {}).get("licence")
    if not licence:
        logger.warning("No use_constraints/licence found in the record.")
        return {}
    return {
        "rights": licence.get("title", {}).get("en", ""),
        "rightsUri": licence.get("url", ""),
        "schemeUri": "https://spdx.org/licenses/",  # TODO confirm
        "rightsIdentifier": licence.get("code", ""),
        "rightsIdentifierScheme": "SPDX",  # TODO confirm
        "lang": "en",
    }


def _get_geo_polygon(record) -> dict:
    """
    Get the polygon from the Cioos record.
    """
    polygon = record.get("spatial", {}).get("polygon")
    if not polygon:
        return {}
    return {
        "geoLocationPolygon": [
            {
                "polygonPoint": {
                    "pointLatitude": float(loc.split(",")[1]),
                    "pointLongitude": float(loc.split(",")[0]),
                }
            }
            for loc in polygon.split(" ")
        ]
    }


def _get_geo_bounding_box(record) -> dict:
    bounding_box = record.get("spatial", {}).get("bounding_box")
    if not bounding_box:
        return {}
    east = bounding_box.get("east")
    west = bounding_box.get("west")
    north = bounding_box.get("north")
    south = bounding_box.get("south")
    if not all(v is not None for v in [east, west, north, south]):
        return {}
    return {
        "geoLocationBoundingBox": {
            "westBoundLongitude": float(west),
            "eastBoundLongitude": float(east),
            "southBoundLatitude": float(south),
            "northBoundLatitude": float(north),
        }
    }


def _get_geo_location_place(record) -> dict:
    description = record.get("spatial", {}).get("description")
    if not description:
        return {}
    return {"geoLocationPlace": description.get("en", "") if isinstance(description, dict) else ""}


def _get_unique_dicts(dict_list: list) -> list:
    unique_dicts = {frozenset(d.items()) for d in dict_list}
    return [dict(items) for items in unique_dicts]


def _get_eov_subjects(record) -> list:
    """
    Get the EOV subjects from the CIOOS record and return a non camelcase list of unique dicts.
    """
    if not record.get("metadata", {}).get("eov"):
        return []
    return _get_unique_dicts(
        [
            {
                "subject": camel_to_title(eov),
                "lang": "en",
                **_get_subject_scheme("eov"),
            }
            for eov in record["metadata"]["eov"]
            if eov
        ]
    )


def _get_keyword_subjects(record) -> list:
    """
    Get the keyword subjects from the CIOOS record.
    """
    if not record.get("metadata", {}).get("keywords"):
        return []
    return _get_unique_dicts(
        [
            {
                "subject": keyword,
                "lang": "en",
                **_get_subject_scheme("default"),
            }
            for keyword in record["metadata"]["keywords"]
            if keyword
        ]
    )


def generate_datacite_record(record, catalogue_url= "http://CATALOGUE_URL.com/dataset/cioos-ca_", doi_prefix=None) -> dict:
    """
    Generate a DataCite record from a Cioos record.
    """

    def _add_optional(field, value):
        """
        Add an optional field to the record.
        """
        if not value:
            logger.debug(f"Optional field {field} is empty")
            return
        optional_fields[field] = value

    optional_fields = {}

    # Set the catalogue URL
    identifier = record["identification"].get("identifier", "")
    existing_doi = identifier.replace("https://doi.org/", "") if identifier else ""

    # If there's an existing DOI, use it; otherwise use the prefix for auto-generation
    if existing_doi:
        _add_optional("doi", existing_doi)
    elif doi_prefix:
        optional_fields["prefix"] = doi_prefix

    # Set the URL
    optional_fields["url"] = catalogue_url + record["metadata"].get("identifier", "")

    # titles — required by DataCite schema
    optional_fields["titles"] = [
        {
            "title": title,
            "lang": lang,
            "titleType": "TranslatedTitle",
        }
        for lang, title in (record["identification"].get("title") or {}).items()
        if lang != "translations" and title
    ] or [{"title": "Untitled", "lang": "en"}]

    # descriptions — optional
    descriptions = [
        {
            "description": abstract,
            "lang": lang,
            "descriptionType": "Abstract",
        }
        for lang, abstract in (record["identification"].get("abstract") or {}).items()
        if lang != "translations" and abstract
    ]
    limitations = record.get("metadata", {}).get("use_constraints", {}).get("limitations")
    if isinstance(limitations, dict):
        descriptions += [
            {
                "description": "limitations: " + description,
                "lang": lang,
                "descriptionType": "Other",
            }
            for lang, description in limitations.items()
            if lang != "translations" and description
        ]

    vertical = record.get("spatial", {}).get("vertical")
    if vertical and len(vertical) == 2:
        vertical_description = f"Vertical extent: {vertical[0]} to {vertical[1]}"
        vertical_positive = record.get("spatial", {}).get("vertical_positive", "")
        if vertical_positive:
            vertical_description += f" ({vertical_positive})"
        descriptions.append(
            {
                "description": vertical_description,
                "descriptionType": "Other",
                "lang": "en",
            }
        )

    _add_optional("descriptions", descriptions)

    # creators — required by DataCite schema
    creators = _get_creators(record)
    optional_fields["creators"] = creators or [{"name": ":unav", "nameType": "Organizational"}]

    # publisher — required by DataCite schema
    publisher = _get_publisher(record)
    optional_fields["publisher"] = publisher or {"name": ":unav", "lang": "en"}

    # contributors
    _add_optional("contributors", _get_contributors(record))

    # publicationYear — use publication date if available, fall back to current year
    # (required by DataCite schema)
    publication_date = record.get("metadata", {}).get("dates", {}).get("publication")
    if publication_date:
        optional_fields["publicationYear"] = str(
            datetime.strptime(publication_date, "%Y-%m-%d").year
        )
    else:
        optional_fields["publicationYear"] = str(datetime.now().year)

    # subjects — only added if keywords exist
    subjects = _get_eov_subjects(record) + _get_keyword_subjects(record)
    if subjects:
        _add_optional(
            "subjects",
            _get_unique_dicts(
                [
                    {
                        "subject": "FOS: Earth and related environmental sciences",
                        "lang": "en",
                        "subjectScheme": "Fields of Science and Technology (FOS)",
                        "schemeUri": "https://www.oecd.org/science/inno/38235147.pdf",
                    }
                ]
                + subjects
            ),
        )

    # dates — only added if dateStart/dateEnd/dateRevised exist
    dates = _get_dates(record)
    _add_optional("dates", dates)

    # geoLocations — only added if all bounds exist
    geo_location = {
        **_get_geo_polygon(record),
        **_get_geo_bounding_box(record),
        **_get_geo_location_place(record),
    }
    _add_optional("geoLocations", [geo_location] if geo_location else [])

    # fundingReferences — only added if funders exist
    funding = _get_funding_references(record)
    _add_optional("fundingReferences", funding.get("fundingReferences"))

    return {
        **optional_fields,
        "language": record.get("metadata", {}).get("language", ""),
        "types": {
            "resourceTypeGeneral": record.get("metadataScope", "Dataset"),
            "resourceType": "",
        },
        **_get_alternate_identifiers(record),
        **_get_related_identifiers(record),
        "version": record["identification"].get("edition", ""),
        "rightsList": [_get_right_lists(record)],
        **_get_related_items(record),
        "schemaVersion": "http://datacite.org/schema/kernel-4",
    }


def to_json(record, output=None) -> str:
    """
    Convert the DataCite record to JSON.
    """
    datacite_record = generate_datacite_record(record)
    datacite_json_record = json.dumps(datacite_record, indent=4)
    if output:
        logger.debug(f"Output file: {output}")
        with open(output, "w") as f:
            f.write(datacite_json_record)
    return datacite_json_record


def to_xml(record, output=None) -> str:
    """
    Convert the DataCite record to XML.
    """
    datacite_record = generate_datacite_record(record)
    xml = schema45.tostring(datacite_record)

    if output:
        logger.debug(f"Output file: {output}")
        with open(output, "w") as f:
            f.write(xml)
    return xml

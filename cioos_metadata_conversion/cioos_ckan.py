# Generate a CKAN record from a CIOOS record
#
# This follows the CIOOS-SIOOC CKAN schema as described in:
# https://github.com/cioos-siooc/cioos-siooc-schema
import json
from datetime import datetime

from loguru import logger


# Map CIOOS roles to CKAN roles
ROLE_MAPPING = {
    "owner": "author",
    "custodian": "custodian",
    "distributor": "distributor",
    "originator": "originator",
    "pointOfContact": "pointOfContact",
    "principalInvestigator": "principalInvestigator",
    "processor": "processor",
    "publisher": "publisher",
    "author": "author",
    "collaborator": "collaborator",
    "contributor": "contributor",
    "coAuthor": "coAuthor",
    "editor": "editor",
    "funder": "funder",
    "mediator": "mediator",
    "resourceProvider": "resourceProvider",
    "rightsHolder": "rightsHolder",
    "sponsor": "sponsor",
    "stakeholder": "stakeholder",
    "user": "user",
}


def _get_individual_name(individual: dict) -> dict:
    """
    Get the individual name fields from the contact.
    """
    result = {}

    # Handle name field
    if "name" in individual:
        result["name"] = individual["name"]

    # Handle ORCID
    if "orcid" in individual:
        orcid = individual["orcid"]
        # Extract just the ID part if it's a full URL
        if orcid.startswith("https://orcid.org/"):
            result["inidividualOrcidId"] = orcid.replace("https://orcid.org/", "")
        else:
            result["inidividualOrcidId"] = orcid

    # Handle position
    if "position" in individual:
        result["position"] = individual["position"]

    return result


def _get_organization_name(organization: dict) -> dict:
    """
    Get the organization name fields from the contact.
    """
    result = {}

    if "name" in organization:
        result["orgName"] = organization["name"]

    # Handle ROR
    if "ror" in organization:
        ror = organization["ror"]
        # Extract just the ID part if it's a full URL
        if ror.startswith("https://ror.org/"):
            result["orgRor"] = ror.replace("https://ror.org/", "")
        else:
            result["orgRor"] = ror

    # Handle contact details
    if "email" in organization:
        result["orgEmail"] = organization["email"]

    if "url" in organization:
        result["onlineResource"] = organization["url"]

    return result


def _build_contact_entry(contact: dict, role: str) -> dict:
    """
    Build a contact entry for CKAN repeating subfields.
    """
    entry = {"role": role}

    # Add individual information if present
    if "individual" in contact:
        entry.update(_get_individual_name(contact["individual"]))

    # Add organization information if present
    if "organization" in contact:
        entry.update(_get_organization_name(contact["organization"]))

    return entry


def _get_metadata_point_of_contact(record: dict) -> list:
    """
    Get metadata point of contact entries (required field).
    """
    contacts = []
    for contact in record.get("contact", []):
        for role in contact.get("roles", []):
            if role == "pointOfContact":
                mapped_role = ROLE_MAPPING.get(role, role)
                contacts.append(_build_contact_entry(contact, mapped_role))

    # Ensure at least one contact exists
    if not contacts:
        logger.warning("No pointOfContact found, using first contact as fallback")
        if record.get("contact"):
            first_contact = record["contact"][0]
            contacts.append(_build_contact_entry(first_contact, "pointOfContact"))

    return contacts


def _get_cited_responsible_party(record: dict) -> list:
    """
    Get cited responsible party entries (required field).
    """
    parties = []
    for contact in record.get("contact", []):
        if contact.get("inCitation", False):
            for role in contact.get("roles", []):
                mapped_role = ROLE_MAPPING.get(role, role)
                parties.append(_build_contact_entry(contact, mapped_role))

    return parties


def _get_distributors(record: dict) -> list:
    """
    Get distributor entries (optional field).
    """
    distributors = []
    for contact in record.get("contact", []):
        for role in contact.get("roles", []):
            if role == "distributor":
                mapped_role = ROLE_MAPPING.get(role, role)
                distributors.append(_build_contact_entry(contact, mapped_role))

    return distributors


def _format_fluent_text(text_dict: dict, include_translations: bool = False) -> dict:
    """
    Format bilingual text for CKAN fluent fields.
    Extracts 'en' and 'fr' keys, optionally includes translation metadata.
    """
    result = {}

    if "en" in text_dict:
        result["en"] = text_dict["en"]
    if "fr" in text_dict:
        result["fr"] = text_dict["fr"]

    # CKAN doesn't typically include translation metadata in the main fields
    # It's handled separately by the fluent plugin

    return result


def _get_keywords(record: dict) -> dict:
    """
    Get keywords in CKAN fluent tags format.
    """
    keywords_obj = record.get("identification", {}).get("keywords", {})

    # Combine all keyword types (default, eov, taxa)
    en_keywords = []
    fr_keywords = []

    for keyword_group in keywords_obj.values():
        if isinstance(keyword_group, dict):
            en_keywords.extend(keyword_group.get("en", []))
            fr_keywords.extend(keyword_group.get("fr", []))

    return {
        "en": en_keywords,
        "fr": fr_keywords
    }


def _get_eov(record: dict) -> list:
    """
    Get Essential Ocean Variables (EOV) from keywords.
    """
    return record.get("identification", {}).get("keywords", {}).get("eov", {}).get("en", [])


def _map_progress_code(progress_code: str) -> str:
    """
    Map CIOOS progress codes to CKAN progress values.
    """
    mapping = {
        "completed": "complete",
        "onGoing": "onGoing",
        "planned": "planned",
        "underDevelopment": "underDevelopment",
    }
    return mapping.get(progress_code, progress_code)


def _get_temporal_extent(record: dict) -> dict:
    """
    Get temporal extent in CKAN format.
    """
    temporal_extent = {}

    temporal_begin = record.get("identification", {}).get("temporal_begin")
    temporal_end = record.get("identification", {}).get("temporal_end")

    if temporal_begin:
        # Convert ISO datetime to just date (yyyy-mm-dd)
        try:
            dt = datetime.fromisoformat(temporal_begin.replace("Z", "+00:00"))
            temporal_extent["begin"] = dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            temporal_extent["begin"] = temporal_begin

    if temporal_end:
        try:
            dt = datetime.fromisoformat(temporal_end.replace("Z", "+00:00"))
            temporal_extent["end"] = dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            temporal_extent["end"] = temporal_end

    return temporal_extent if temporal_extent else None


def _get_vertical_extent(record: dict) -> dict:
    """
    Get vertical extent in CKAN format.
    """
    vertical = record.get("spatial", {}).get("vertical", [])

    if len(vertical) >= 2:
        return {
            "min": vertical[0],
            "max": vertical[1]
        }

    return None


def _get_spatial(record: dict) -> dict:
    """
    Get spatial extent in GeoJSON format for CKAN.
    """
    bbox = record.get("spatial", {}).get("bbox")
    polygon = record.get("spatial", {}).get("polygon")

    if polygon:
        # Convert polygon string to GeoJSON
        coords = []
        for point in polygon.split():
            lon, lat = point.split(",")
            coords.append([float(lon), float(lat)])

        # Ensure polygon is closed
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        return {
            "type": "Polygon",
            "coordinates": [coords]
        }
    elif bbox:
        # Create GeoJSON from bounding box
        west = bbox.get("west")
        east = bbox.get("east")
        south = bbox.get("south")
        north = bbox.get("north")

        if all([west, east, south, north]):
            return {
                "type": "Polygon",
                "coordinates": [[
                    [float(west), float(south)],
                    [float(east), float(south)],
                    [float(east), float(north)],
                    [float(west), float(north)],
                    [float(west), float(south)]
                ]]
            }

    return None


def _get_dataset_reference_dates(record: dict) -> list:
    """
    Get dataset reference dates in CKAN repeating format.
    """
    dates = []

    identification_dates = record.get("identification", {}).get("dates", {})

    # Map CIOOS date types to CKAN date types
    date_type_mapping = {
        "creation": "creation",
        "publication": "publication",
        "revision": "revision"
    }

    for cioos_type, ckan_type in date_type_mapping.items():
        if cioos_type in identification_dates:
            dates.append({
                "type": ckan_type,
                "date": identification_dates[cioos_type]
            })

    return dates


def _get_metadata_reference_dates(record: dict) -> list:
    """
    Get metadata reference dates in CKAN repeating format.
    """
    dates = []

    metadata_dates = record.get("metadata", {}).get("dates", {})

    # Map CIOOS date types to CKAN date types
    date_type_mapping = {
        "creation": "creation",
        "publication": "publication",
        "revision": "revision"
    }

    for cioos_type, ckan_type in date_type_mapping.items():
        if cioos_type in metadata_dates:
            dates.append({
                "type": ckan_type,
                "date": metadata_dates[cioos_type]
            })

    return dates


def _get_license_id(record: dict) -> str:
    """
    Get license ID from CIOOS record.
    """
    license_code = record.get("metadata", {}).get("use_constraints", {}).get("licence", {}).get("code")

    # Map common CIOOS license codes to CKAN license IDs
    license_mapping = {
        "CC-BY-4.0": "cc-by",
        "CC-BY-SA-4.0": "cc-by-sa",
        "CC0-1.0": "cc-zero",
        "OGL-Canada-2.0": "ogl-canada",
    }

    return license_mapping.get(license_code, license_code)


def _get_resources(record: dict) -> list:
    """
    Get resources from distribution section.
    """
    resources = []

    for dist in record.get("distribution", []):
        resource = {
            "url": dist.get("url", "")
        }

        # Add bilingual name
        if "name" in dist:
            resource["name_translated"] = _format_fluent_text(dist["name"])

        # Add bilingual description
        if "description" in dist:
            resource["description_translated"] = _format_fluent_text(dist["description"])

        # Add format if available
        if "url" in dist:
            url = dist["url"]
            # Try to detect format from URL
            if "erddap" in url.lower():
                resource["format"] = "ERDDAP"
            elif url.endswith(".pdf"):
                resource["format"] = "PDF"
            elif url.endswith(".html"):
                resource["format"] = "HTML"

        resources.append(resource)

    return resources


def generate_ckan_record(record: dict) -> dict:
    """
    Generate a CKAN dataset record from a CIOOS record.

    Args:
        record: CIOOS intermediate format record

    Returns:
        Dictionary compatible with CIOOS-SIOOC CKAN schema
    """

    ckan_record = {}

    # Required fields
    # Title (fluent text)
    if "identification" in record and "title" in record["identification"]:
        ckan_record["title_translated"] = _format_fluent_text(record["identification"]["title"])

    # Notes/Description (fluent markdown)
    if "identification" in record and "abstract" in record["identification"]:
        ckan_record["notes_translated"] = _format_fluent_text(record["identification"]["abstract"])

    # Keywords (fluent tags)
    ckan_record["keywords"] = _get_keywords(record)

    # Essential Ocean Variables
    eov = _get_eov(record)
    if eov:
        ckan_record["eov"] = eov

    # Resource type - map from CIOOS to CKAN
    # CKAN expects values like 'dataset', 'series', 'model', etc.
    ckan_record["resource-type"] = "dataset"  # Default value

    # Progress
    progress_code = record.get("identification", {}).get("progress_code")
    if progress_code:
        ckan_record["progress"] = _map_progress_code(progress_code)

    # Frequency of update - would need to be added to CIOOS intermediate format
    # For now, we'll skip it or set a default

    # Metadata point of contact (required repeating)
    ckan_record["metadata-point-of-contact"] = _get_metadata_point_of_contact(record)

    # Cited responsible party (required repeating)
    cited_parties = _get_cited_responsible_party(record)
    if cited_parties:
        ckan_record["cited-responsible-party"] = cited_parties

    # Optional fields

    # Citation (fluent markdown)
    # This would need to be constructed from the record if not present

    # License
    license_id = _get_license_id(record)
    if license_id:
        ckan_record["license_id"] = license_id

    # Version
    edition = record.get("identification", {}).get("edition")
    if edition:
        ckan_record["version"] = edition

    # Projects
    projects = record.get("identification", {}).get("project")
    if projects:
        ckan_record["projects"] = projects

    # Spatial extent
    spatial = _get_spatial(record)
    if spatial:
        ckan_record["spatial"] = json.dumps(spatial)

    # Temporal extent
    temporal = _get_temporal_extent(record)
    if temporal:
        ckan_record["temporal-extent"] = temporal

    # Vertical extent
    vertical = _get_vertical_extent(record)
    if vertical:
        ckan_record["vertical-extent"] = vertical

    # Dataset reference dates
    dataset_dates = _get_dataset_reference_dates(record)
    if dataset_dates:
        ckan_record["dataset-reference-date"] = dataset_dates

    # Metadata reference dates
    metadata_dates = _get_metadata_reference_dates(record)
    if metadata_dates:
        ckan_record["metadata-reference-date"] = metadata_dates

    # Distributors
    distributors = _get_distributors(record)
    if distributors:
        ckan_record["distributor"] = distributors

    # Resources
    resources = _get_resources(record)
    if resources:
        ckan_record["resources"] = resources

    # Metadata language
    language = record.get("metadata", {}).get("language", "en")
    ckan_record["metadata-language"] = language

    # Unique resource identifier
    identifier = record.get("identification", {}).get("identifier")
    if identifier:
        # Extract DOI if it's a URL
        if identifier.startswith("https://doi.org/"):
            doi = identifier.replace("https://doi.org/", "")
            ckan_record["unique-resource-identifier-full"] = [{
                "authority": "DOI",
                "code": doi,
                "codeSpace": "https://doi.org/"
            }]

    # Maintenance note
    maintenance_note = record.get("metadata", {}).get("maintenance_note")
    if maintenance_note:
        ckan_record["maintenance-note"] = maintenance_note

    # Lineage - if history is available
    history = record.get("metadata", {}).get("history")
    if history:
        ckan_record["lineage"] = {
            "statement": _format_fluent_text(history)
        }

    # Name - use metadata identifier as the dataset name
    metadata_identifier = record.get("metadata", {}).get("identifier")
    if metadata_identifier:
        ckan_record["name"] = metadata_identifier

    return ckan_record


def to_json(record: dict, output=None) -> str:
    """
    Convert the CKAN record to JSON.

    Args:
        record: CIOOS intermediate format record
        output: Optional output file path

    Returns:
        JSON string of CKAN record
    """
    ckan_record = generate_ckan_record(record)
    ckan_json_record = json.dumps(ckan_record, indent=4, ensure_ascii=False)

    if output:
        logger.debug(f"Output file: {output}")
        with open(output, "w", encoding="utf-8") as f:
            f.write(ckan_json_record)

    return ckan_json_record

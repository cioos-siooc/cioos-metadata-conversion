"""
Retrieve DOI metadata from DataCite API and map to CIOOS Firebase structure.

This module provides utilities to:
1. Fetch DOI metadata from the DataCite API
2. Map DataCite metadata to the CIOOS Firebase metadata form structure
3. Validate and enhance DOI information

DataCite API Documentation: https://developer.datacite.org/
"""

from attr import attributes
import requests
from typing import Dict, Any, Optional, List
from loguru import logger
from datetime import datetime, timezone
import os

from datacite import DataCiteRESTClient

datacite_client = DataCiteRESTClient(
    username=os.getenv("DATACITE_ACCOUNT_ID"),
    password=os.getenv("DATACITE_PASSWORD"),
    prefix=os.getenv("DATACITE_PREFIX"),
    test_mode=os.getenv("DATACITE_TEST_MODE", "true").lower() == "true",
)


class DOIRetrievalError(Exception):
    """Raised when DOI retrieval or mapping fails."""

    pass


def fetch_doi_metadata(doi: str) -> Dict[str, Any]:
    """
    Fetch metadata for a specific DOI from the DataCite API.

    Args:
        doi: DOI string (e.g., "10.26071/mxtr-gp72" or "https://doi.org/10.26071/mxtr-gp72")

    Returns:
        Dictionary containing the DataCite metadata

    Raises:
        DOIRetrievalError: If the DOI is not found or the API request fails
    """
    try:
        return datacite_client.metadata_get(doi)  # Test if DOI exists
    except Exception as e:
        raise DOIRetrievalError(f"Failed to retrieve DOI {doi} from DataCite: {str(e)}")


def map_datacite_to_firebase(datacite_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map DataCite API response to CIOOS Firebase metadata structure.

    This function transforms the DataCite metadata into the Firebase format used by
    the CIOOS metadata form, focusing on essential fields while preserving the structure.

    Args:
        datacite_data: DataCite metadata dictionary

    Returns:
        Dictionary with Firebase metadata structure

    Raises:
        DOIRetrievalError: If mapping fails due to invalid data
    """

    return {
        # Basic identification
        "datasetIdentifier": datacite_data.get("doi"),
        "identifier": _extract_identifier(datacite_data),
        # Title and description
        "title": _map_title(datacite_data.get("titles", [])),
        "abstract": _map_abstract(datacite_data.get("descriptions", [])),
        # Keywords
        "keywords": _map_keywords(datacite_data.get("keywords", [])),
        # Dates
        "dateStart": _map_date(datacite_data.get("publicationYear")),
        "dateEnd": None,
        # Contacts/Contributors
        "contacts": [
            *_map_contacts(datacite_data.get("creators", [])),
            *_map_contacts(datacite_data.get("contributors", [])),
        ],  # TODO missing publisher
        # Associated resources/related identifiers
        "associated_resources": _map_associated_resources(
            datacite_data.get("relatedIdentifiers", [])
        ),
        # Rights/License
        "license": _map_license(datacite_data.get("rightsList", [])),
        # Resource type
        "resourceType": _map_resource_type(datacite_data.get("types", {})),
        # Publication metadata
        "language": _map_language(datacite_data.get("language", "en")),
        "created": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "metadataScope": "Dataset",
        "doiCreationStatus": datacite_data.get("state", "findable").lower(),
        "progress": "completed",
    }


def _extract_identifier(attributes: Dict[str, Any]) -> str:
    """Generate a unique identifier from DataCite attributes."""
    import uuid

    # Use a combination of DOI and timestamp as identifier
    return str(uuid.uuid4())


def _map_title(titles: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Map titles from DataCite format to Firebase format.

    DataCite format: [{"title": "...", "lang": "en", "titleType": "..."}]
    Firebase format: {"en": "...", "fr": "..."}
    """
    result = {}
    for title_obj in titles:
        title_text = title_obj.get("title", "")
        lang = (title_obj.get("lang") or "en").lower()

        # Skip non-en/fr titles for Firebase structure
        if lang in ["en", "fr"]:
            result[lang] = title_text

    # Ensure we have at least an English title
    if not result:
        result["en"] = titles[0].get("title", "") if titles else ""

    return result


def _map_abstract(descriptions: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Map descriptions/abstracts from DataCite to Firebase format.

    DataCite format: [{"description": "...", "lang": "en", "descriptionType": "Abstract"}]
    Firebase format: {"en": "...", "fr": "..."}
    """
    result = {}

    # Filter for abstracts
    abstracts = [d for d in descriptions if d.get("descriptionType") == "Abstract"]

    if abstracts:
        for abstract_obj in abstracts:
            desc_text = abstract_obj.get("description", "")
            lang = (abstract_obj.get("lang") or "en").lower()

            if lang in ["en", "fr"]:
                result[lang] = desc_text

    return result if result else {"en": ""}


def _map_keywords(keywords: List[str]) -> Dict[str, List[str]]:
    """
    Map keywords from DataCite to Firebase format.

    Returns keywords as English by default, can be enhanced with language detection.
    """
    if not keywords:
        return {}

    # DataCite returns flat list, Firebase expects language-keyed structure
    return {
        "en": keywords,
    }


def _map_date(publication_year: Optional[int]) -> Optional[str]:
    """Map publication year to ISO date format."""
    if publication_year:
        return f"{publication_year}-01-01T00:00:00.000Z"
    return None


def _map_contacts(
    creators: List[Dict[str, Any]], in_citation: bool = False
) -> List[Dict[str, Any]]:
    """
    Map creators/contributors from DataCite to Firebase contacts format.

    DataCite creators: [{"name": "...", "nameType": "Personal/Organizational", ...}]
    Firebase contacts: [{"lastName": "...", "givenNames": "...", "orgName": "...", "role": ["owner"]}]
    """
    contacts = []

    for i, creator in enumerate(creators):
        name_type = creator.get("nameType", "Personal")

        if name_type == "Personal":
            contact = {
                "givenNames": creator.get("givenName", ""),
                "lastName": creator.get("familyName", ""),
                "indEmail": "",
                "indOrcid": _extract_orcid(creator.get("nameIdentifier")),
                "indPosition": "",
                "orgName": _extract_org_name(creator.get("affiliation", [])),
                "orgCity": "",
                "orgCountry": "",
                "orgEmail": "",
                "orgURL": "",
                "orgAdress": "",
                "orgRor": _extract_ror(creator.get("affiliation", [])),
                "inCitation": in_citation,  # First creator in citation
                "role": ["owner"] if i == 0 else ["collaborator"],
            }
        else:  # Organizational
            contact = {
                "givenNames": "",
                "lastName": "",
                "indEmail": "",
                "indOrcid": "",
                "indPosition": "",
                "orgName": creator.get("name", ""),
                "orgCity": "",
                "orgCountry": "",
                "orgEmail": "",
                "orgURL": "",
                "orgAdress": "",
                "orgRor": _extract_ror(creator.get("affiliation", [])),
                "inCitation": in_citation,
                "role": ["publisher"],
            }

        contacts.append(contact)

    return contacts


def _extract_orcid(name_identifier: Any) -> str:
    """Extract ORCID from nameIdentifier field."""
    if isinstance(name_identifier, dict):
        orcid = name_identifier.get("nameIdentifier", "")
        if orcid and not orcid.startswith("https://"):
            return f"https://orcid.org/{orcid}"
        return orcid
    elif isinstance(name_identifier, str):
        if name_identifier.startswith("https://"):
            return name_identifier
        return f"https://orcid.org/{name_identifier}"
    return ""


def _extract_org_name(affiliation: List[Dict[str, Any]]) -> str:
    """Extract organization name from affiliation array."""
    if not affiliation:
        return ""
    elif len(affiliation) > 0 and isinstance(affiliation[0], str):
        return affiliation[0]
    elif affiliation and len(affiliation) > 0:
        return affiliation[0].get("name", "")
    return ""


def _extract_ror(affiliation: List[Dict[str, Any]]) -> str:
    """Extract ROR ID from affiliation array."""
    if not affiliation or isinstance(affiliation[0], str):
        return ""
    if affiliation and len(affiliation) > 0:
        ror = affiliation[0].get("affiliationIdentifier", "")
        if ror and not ror.startswith("https://"):
            return f"https://ror.org/{ror}"
        return ror
    return ""


def _map_associated_resources(
    related_identifiers: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Map related identifiers from DataCite to Firebase associated_resources format.

    DataCite format: [{"relatedIdentifier": "...", "relatedIdentifierType": "DOI", ...}]
    Firebase format: [{"authority": "DOI", "code": "...", "association_type": "...", ...}]
    """
    resources = []

    for rel_id in related_identifiers:
        resource = {
            "authority": rel_id.get("relatedIdentifierType", "URL"),
            "code": rel_id.get("relatedIdentifier", ""),
            "association_type": _map_relation_type(rel_id.get("relationType")),
            "association_type_iso": "crossReference",
            "title": {
                "en": rel_id.get("title", "") or rel_id.get("relatedIdentifier", ""),
                "fr": rel_id.get("title", "") or rel_id.get("relatedIdentifier", ""),
            },
        }
        resources.append(resource)

    return resources


def _map_relation_type(datacite_relation_type: Optional[str]) -> str:
    """
    Map DataCite relation types to Firebase association_type values.

    DataCite types: Cites, IsCitedBy, IsReferencedBy, References, IsVersionOf, HasVersion, etc.
    Firebase types: Similar to DataCite but may need custom mapping
    """
    if not datacite_relation_type:
        return "References"

    type_mapping = {
        "Cites": "Cites",
        "IsCitedBy": "IsCitedBy",
        "IsReferencedBy": "IsReferencedBy",
        "References": "References",
        "IsVersionOf": "IsVersionOf",
        "HasVersion": "HasVersion",
        "IsPartOf": "IsPartOf",
        "HasPart": "HasPart",
        "IsSupplementTo": "IsSupplementTo",
        "IsSupplementedBy": "IsSupplementedBy",
        "IsContinuedBy": "IsContinuedBy",
        "Continues": "Continues",
        "IsNewVersionOf": "IsNewVersionOf",
        "IsPreviousVersionOf": "IsPreviousVersionOf",
    }

    return type_mapping.get(datacite_relation_type, "References")


def _map_license(rights_list: List[Dict[str, Any]]) -> str:
    """
    Extract license from rights list.

    DataCite format: [{"rights": "CC-BY-4.0", "rightsUri": "https://..."}]
    """
    if rights_list and len(rights_list) > 0:
        rights = rights_list[0].get("rights", "")
        return rights
    return ""


def _map_resource_type(types: Dict[str, Any]) -> List[str]:
    """
    Map resource type from DataCite to Firebase format.

    DataCite: {"resourceType": "Dataset", "resourceTypeGeneral": "Dataset"}
    Firebase: ["biological"] or ["physical"] etc.
    """
    resource_type_general = types.get("resourceTypeGeneral", "Dataset").lower()

    type_mapping = {
        "dataset": "dataset",
        "text": "text",
        "image": "image",
        "software": "software",
        "model": "model",
        "service": "service",
    }

    mapped_type = type_mapping.get(resource_type_general, "dataset")
    return [mapped_type]


def _map_language(language: Optional[str]) -> str:
    """Map language code to Firebase format."""
    if not language:
        return "en"

    lang_code = language.lower().split("-")[0]  # Get primary language code
    return "fr" if lang_code == "fr" else "en"


def retrieve_doi_as_firebase_record(doi: str) -> Dict[str, Any]:
    """
    Convenience function to fetch a DOI and return it as a Firebase record.

    Args:
        doi: DOI string (e.g., "10.26071/mxtr-gp72" or "https://doi.org/10.26071/mxtr-gp72")

    Returns:
        Firebase metadata record dictionary

    Raises:
        DOIRetrievalError: If retrieval or mapping fails
    """
    logger.info(f"Retrieving DOI metadata: {doi}")
    datacite_data = fetch_doi_metadata(doi)
    logger.debug(f"Successfully retrieved DataCite metadata for {doi}")

    firebase_record = map_datacite_to_firebase(datacite_data, doi)
    logger.info(f"Successfully mapped DataCite metadata to Firebase format for {doi}")

    return firebase_record

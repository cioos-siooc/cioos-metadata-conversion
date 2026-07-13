"""
Retrieve Polar Data Catalogue (PDC) ISO 19139 metadata records and map them
to the CIOOS Firebase structure.

This module provides utilities to:
1. Fetch ISO metadata records from the Polar Data Catalogue by CCIN reference number
2. Parse PDC ISO 19139 XML records
3. Map PDC metadata to the CIOOS Firebase metadata form structure

Vendored and adapted from
https://github.com/cioos-siooc/pdc-metadata-conversion (pdc/iso.py).
The translation features of the original package are intentionally excluded;
translations are handled elsewhere.

Polar Data Catalogue: https://www.polardata.ca/
"""

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union

import requests
import yaml
from loguru import logger
from lxml import etree as ET

PDC_ISO_XML_URL = "https://polardata.ca/pdcsearch/xml/iso/{ccin}_iso.xml"

# Define the namespaces
namespaces = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
    "gml": "http://www.opengis.net/gml",
}

MAP_ISO_LANGUAGE = {
    "eng; CAN": "en",
    "fra; CAN": "fr",
}
MAP_ISO_STATUS = {
    "underDevelopment": "underDevelopment",
    "ongoing": "onGoing",
    "completed": "completed",
    "planned": "planned",
}

NAMES_MAPPING = {
    "Polar Data Catalogue": ["Polar Data Catalogue", ""],
}

ROLES_MAPPING = {
    "Originator": "originator",
    "Collaborator": "collaborator",
    "Author": "author",
    "coAuthor": "coauthor",
    "pointOfContact": "pointOfContact",
    "principalInvestigator": "principalInvestigator",
}

DEFAULT_DOI_PREFIXES = ["10.21963"]

EOV_TO_KEYWORDS = yaml.safe_load(
    (Path(__file__).parent.parent / "resources" / "eov_to_keywords.yaml").read_text(
        encoding="utf-8"
    )
)


class PDCRetrievalError(Exception):
    """Raised when PDC record retrieval or mapping fails."""

    pass


def fetch_pdc_metadata(ccin: Union[str, int]) -> str:
    """
    Fetch the ISO 19139 metadata record for a CCIN reference number from the
    Polar Data Catalogue.

    Args:
        ccin: CCIN reference number (e.g., "13172")

    Returns:
        The ISO XML record as text

    Raises:
        PDCRetrievalError: If the record is not found or the request fails
    """
    url = PDC_ISO_XML_URL.format(ccin=ccin)
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        raise PDCRetrievalError(
            f"Failed to retrieve PDC record {ccin} from {url}: {e}"
        ) from e
    return response.text


def _parse_date(date: str) -> Optional[str]:
    """Parse a date."""
    if not date or date == "Undefined":
        return
    elif not re.match(r"\d{4}-\d{2}-\d{2}", date):
        logger.warning("Invalid date: {}", date)
        return date
    return (
        datetime.strptime(date, "%Y-%m-%d")
        .replace(tzinfo=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _apply_role_mapping(role: str) -> Optional[str]:
    """Apply a mapping to a role."""
    result = ROLES_MAPPING.get(role)

    if result is None and role in ROLES_MAPPING.values():
        return role
    elif result is None:
        logger.warning("Mapping not found for role: {}", role)
        return None
    return result


def _apply_mapping(mapping: dict, value: str) -> Optional[str]:
    """Apply a mapping to a value."""
    result = mapping.get(value)
    if result is None:
        logger.warning("Mapping not found for value: {}[{}]", mapping, value)
        return None
    return result


def _contact_name(author_text: str, name_mapping: dict = NAMES_MAPPING) -> list[str]:
    """Get the name of a contact.

    Attempt to split the name into given and last names.
    If the name is in the mapping, return the mapped name.
    If the name has more than two parts, log a warning.

    """
    if author_text is None:
        logger.debug("No contact name found")
        return [""]
    if ":" in author_text:
        author_text = author_text.split(":")[-1].strip()

    if "," in author_text:
        author_text = " ".join(author_text.split(",")[::-1])

    names = re.split(r"\s+", author_text)
    names = [name for name in names if name]
    if " ".join(names) in name_mapping:
        names = name_mapping[" ".join(names)]
    elif len(names) > 2:
        logger.warning("Name has more than two parts: {}", names)
    else:
        logger.debug("Name has two parts: {}", names)
    return names


class PDC_ISO:
    """Parser for Polar Data Catalogue ISO 19139 metadata records."""

    def __init__(self, source, name_mapping: dict = NAMES_MAPPING):
        """
        Args:
            source: Path to an ISO XML file, a file-like object, or the raw
                XML record as a string or bytes.
            name_mapping: Mapping used to fix contact names that cannot be
                split into given and last names.
        """
        self.file = source
        if isinstance(source, bytes):
            self.tree = ET.fromstring(source).getroottree()
        elif isinstance(source, str) and source.lstrip().startswith("<"):
            self.tree = ET.fromstring(source.encode("utf-8")).getroottree()
        else:
            self.tree = ET.parse(source)
        self.name_mapping = name_mapping

    def _create_contact(
        self,
        contact,
        in_citation: bool,
        role: list[str] = None,
    ) -> dict:
        """Add a contact to the metadata record."""
        logger.debug("Creating contact: {}", contact)
        names = _contact_name(
            self.get(".//gmd:individualName/gco:CharacterString", contact),
            self.name_mapping,
        )

        return {
            "givenNames": " ".join(names[:-1]),
            "lastName": names[-1],
            "inCitation": in_citation,
            "indEmail": self.get(
                ".//gmd:electronicMailAddress/gco:CharacterString", contact
            ),
            "indName": " ".join(names),
            "indOrcid": "",
            "orgAddress": self.get(
                ".//gmd:deliveryPoint/gco:CharacterString", contact
            ),
            "orgCity": self.get(".//gmd:city/gco:CharacterString", contact),
            "orgCountry": self.get(".//gmd:country/gco:CharacterString", contact),
            "orgEmail": self.get(
                ".//gmd:electronicMailAddress/gco:CharacterString", contact
            ),
            "orgName": self.get(
                ".//gmd:organisationName/gco:CharacterString", contact
            ),
            "orgRor": "",
            "orgURL": "",
            "role": role
            or [_apply_role_mapping(self.get(".//gmd:CI_RoleCode", contact))],
        }

    def get(self, tag, item=None, default=None, level="DEBUG") -> Optional[str]:
        """Extract specific tag element within item."""
        result = (item if item is not None else self.tree).find(
            tag, namespaces=namespaces
        )
        if result is None:
            logger.log(level, "Item {} not found", tag)
            return default
        return result.text

    def get_places(self) -> list[str]:
        """Extract the places from the metadata record."""
        places = []
        for kw in self.tree.findall(
            ".//gmd:descriptiveKeywords", namespaces=namespaces
        ):
            if (
                kw.find(".//gmd:MD_KeywordTypeCode", namespaces=namespaces).text
                == "place"
            ):
                places.append(
                    kw.find(
                        ".//gmd:keyword/gco:CharacterString", namespaces=namespaces
                    ).text
                )
        return places

    def _get_suggested_citation_contacts(self) -> tuple[list[dict], str]:
        """Extract the contacts from the citation."""
        contacts = []
        citation = self.tree.findall(
            ".//gmd:citation/gmd:CI_Citation/gmd:otherCitationDetails/gco:CharacterString",
            namespaces=namespaces,
        )
        citation = citation[0].text if citation else None
        if not citation or citation.lower() in ("unpublished data", "unpublished"):
            return contacts, citation
        coauthors = re.split(r"\(|\d{4}\.", citation)
        if not len(coauthors) > 1:
            if "et al." in citation:
                logger.info("No coauthors listed in citation: {}", citation)
            else:
                logger.warning("No coauthors found in citation: {}", citation)
            return contacts, citation

        coauthors = re.sub(r"\s+\&\s+|\s+and\s+", "", coauthors[0])

        potential_coauthors = []
        coauthors_items = coauthors.split(",")
        for index, item in enumerate(coauthors_items):
            item = item.strip()
            if not item:
                continue
            if re.match(r"\w\.", item) and potential_coauthors and index > 0:
                # If the item is a name with initials, add it to the last contact
                potential_coauthors[-1]["givenNames"] = item
            else:
                # Add as coauthor
                potential_coauthors.append(
                    {
                        "lastName": item,
                        "role": ["coauthor"],
                        "inCitation": True,
                    }
                )
        return potential_coauthors, citation

    def _combine_contacts(self, contacts) -> list[dict]:
        """Combine matching contacts and join roles"""
        new_contacts = []
        new_contacts_roles = []
        for contact in contacts:
            roles = contact.pop("role")
            if contact not in new_contacts:
                new_contacts += [contact]
                new_contacts_roles += [roles]
            else:
                contact_id = new_contacts.index(contact)
                if roles:
                    new_contacts_roles[contact_id] += roles

        # Add back roles
        for i, new_contact in enumerate(new_contacts):
            new_contact["role"] = new_contacts_roles[i]
        return new_contacts

    def _get_keywords(self) -> list[str]:
        """Retrieve theme type keywords."""
        keywords = []
        for kw in self.tree.findall(
            ".//gmd:descriptiveKeywords", namespaces=namespaces
        ):
            if (
                kw.find(".//gmd:MD_KeywordTypeCode", namespaces=namespaces).text
                == "theme"
            ):
                keywords += [
                    item.text
                    for item in kw.findall(
                        ".//gmd:keyword/gco:CharacterString", namespaces=namespaces
                    )
                ]
        if not keywords:
            logger.warning("No keywords found in metadata")
        return keywords

    def _get_eov_from_keywords(self) -> list[str]:
        """Extract EOV from keywords."""

        def _has_keyword(keyword):
            """Return the eovs that have the keyword."""
            return [
                eov
                for eov, keywords in EOV_TO_KEYWORDS.items()
                if keywords and keyword in keywords
            ]

        keywords = self._get_keywords()
        eovs = []
        for keyword in keywords:
            eovs += _has_keyword(keyword)
        if not eovs:
            logger.warning("No EOV found in keywords: {}", keywords)
            eovs = ["other"]
        return list(set(eovs))

    def _get_doi(self, ccin, doi_prefixes: list = None) -> str:
        """Resolve the DOI associated with a CCIN reference number, if any."""
        if not ccin:
            return ""
        if not doi_prefixes:
            doi_prefixes = DEFAULT_DOI_PREFIXES

        for prefix in doi_prefixes:
            doi_url = f"https://doi.org/{prefix}/{ccin}"
            response = requests.get(doi_url)
            if response.status_code == 200:
                return doi_url
        return ""

    def to_firebase(
        self,
        userID: str = "",
        filename: str = "",
        recordID: str = "",
        status: str = "",
        license: str = "",
        region: str = "",
        projects: list[str] = None,
        resourceType: list[str] = None,
        shares: list[str] = None,
        distribution: list[dict] = None,
        eov: list[str] = None,
        identifier: uuid.UUID = None,
        doiCreationStatus: str = "findable",
        doi_prefixes: list[str] = None,
    ) -> dict:
        """Convert a Polar Data Catalogue ISO metadata record to the CIOOS
        Firebase metadata structure."""

        if identifier is None:
            identifier = uuid.uuid4()

        # Verify if contacts match the suggested citation
        citation_contacts, citation = self._get_suggested_citation_contacts()
        responsible_parties = [
            self._create_contact(contact, in_citation=True)
            for contact in self.tree.findall(
                ".//gmd:CI_Citation/gmd:citedResponsibleParty",
                namespaces=namespaces,
            )
        ]
        if (
            len(citation_contacts) > len(responsible_parties)
            and "et al." not in citation
        ):
            logger.warning(
                "file={} Citation contacts ({} contacts) do not match the responsible parties ({} contacts): citation={}",
                self.file,
                len(citation_contacts),
                len(responsible_parties),
                citation,
            )

        return {
            "userID": userID,
            "title": {
                "en": self.get(".//gmd:title/gco:CharacterString"),
            },
            "abstract": {"en": self.get(".//gmd:abstract/gco:CharacterString")},
            "category": "dataset",
            "limitations": "",
            "contacts": self._combine_contacts(
                [
                    self._create_contact(
                        self.tree.find(".//gmd:pointOfContact", namespaces=namespaces),
                        False,
                        ["pointOfContact"],
                    ),
                    self._create_contact(
                        self.tree.find(
                            ".//gmd:metadataMaintenance", namespaces=namespaces
                        ),
                        False,
                        ["custodian"],
                    ),
                    self._create_contact(
                        self.tree.find(".//gmd:distributor", namespaces=namespaces),
                        False,
                        ["distributor"],
                    ),
                    *responsible_parties,
                ]
            ),
            "created": _parse_date(self.get(".//gmd:dateStamp/gco:Date")),
            "datasetIdentifier": self._get_doi(
                self.get(".//gmd:dataSetURI/gco:CharacterString").split("=")[-1],
                doi_prefixes,
            ),
            "dateStart": _parse_date(self.get(".//gml:beginPosition")),
            "dateEnd": _parse_date(self.get(".//gml:endPosition")),
            "datePublished": _parse_date(self.get(".//gmd:dateStamp/gco:Date")),
            "dateRevised": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "distribution": distribution or [],
            "doiCreationStatus": doiCreationStatus,
            "edition": self.get(".//gmd:version") or "1.0",
            "eov": eov or self._get_eov_from_keywords(),
            "filename": filename,
            "history": [],  # Related to Lineage
            "identifier": "ccin-" + str(identifier),
            "keywords": {
                "en": list(
                    set(
                        item.strip()
                        for kw in self.tree.findall(
                            ".//gmd:keyword/gco:CharacterString",
                            namespaces=namespaces,
                        )
                        for item in kw.text.split(",")
                    )
                ),
                "fr": [],
            },
            "language": _apply_mapping(
                MAP_ISO_LANGUAGE, self.get(".//gmd:language/gco:CharacterString")
            ),
            "lastEditedBy": {"displayName": "", "email": ""},
            "license": license,  # eg "CC-BY-4.0"
            "comments": {
                "en": (
                    "## Purpose: "
                    + self.get(".//gmd:purpose/gco:CharacterString")
                    + "\n\n## Supplemental Information: "
                    + self.get(".//gmd:supplementalInformation/gco:CharacterString")
                ),
            },
            "map": {
                "description": {
                    "en": " - ".join(self.get_places()),
                },
                "north": self.get(".//gmd:northBoundLatitude/gco:Decimal"),
                "south": self.get(".//gmd:southBoundLatitude/gco:Decimal"),
                "east": self.get(".//gmd:eastBoundLongitude/gco:Decimal"),
                "west": self.get(".//gmd:westBoundLongitude/gco:Decimal"),
                "polygon": "",
            },
            "metadataScope": "Dataset",
            "noPlatform": True,
            "platforms": [],
            "noTaxa": True,
            "progress": _apply_mapping(
                MAP_ISO_STATUS, self.get(".//gmd:status/gmd:MD_ProgressCode")
            ),
            "projects": projects or [],
            "recordID": recordID,
            "region": region,
            "resourceType": resourceType or [],
            "sharedWith": {person: True for person in shares or []},
            "status": status,
            "timeFirstPublished": _parse_date(self.get(".//gmd:dateStamp/gco:Date")),
            "vertical": {},
            "noVerticalExtent": True,
            "verticalExtentDirection": "depthPositive",
            "verticalExtentMax": None,  # unavailable in PDC metadata
            "verticalExtentMin": None,  # unavailable in PDC metadata
            "associated_resources": [
                {
                    "association_type": "IsIdenticalTo",
                    "association_type_iso": "crossReference",
                    "authority": "URL",
                    "code": self.get(".//gmd:dataSetURI/gco:CharacterString"),
                    "title": {
                        "en": "Polar Data Catalogue equivalent record",
                        "fr": "Enregistrement équivalent du Catalogue de données polaires",
                    },
                }
            ],
        }


def retrieve_pdc_as_firebase_record(source: Union[str, int], **kwargs) -> dict:
    """
    Convenience function to fetch a PDC record and return it as a Firebase record.

    Args:
        source: A CCIN reference number (e.g., "13172"), a polardata.ca ISO XML
            URL, or a path to a local ISO XML file.
        **kwargs: Extra arguments passed to PDC_ISO.to_firebase (userID, status,
            license, region, projects, resourceType, shares, distribution, eov,
            identifier, doiCreationStatus, doi_prefixes).

    Returns:
        Firebase metadata record dictionary

    Raises:
        PDCRetrievalError: If retrieval or mapping fails
    """
    source = str(source)
    logger.info("Retrieving PDC metadata: {}", source)

    ccin = None
    if source.isdigit():
        ccin = source
        record = PDC_ISO(fetch_pdc_metadata(ccin))
    elif source.startswith(("http://", "https://")):
        match = re.search(r"(\d+)_iso\.xml", source)
        ccin = match.group(1) if match else None
        try:
            response = requests.get(source)
            response.raise_for_status()
        except requests.RequestException as e:
            raise PDCRetrievalError(
                f"Failed to retrieve PDC record from {source}: {e}"
            ) from e
        record = PDC_ISO(response.text)
    else:
        match = re.search(r"(\d+)_iso\.xml", source)
        ccin = match.group(1) if match else None
        try:
            record = PDC_ISO(source)
        except (OSError, ET.XMLSyntaxError) as e:
            raise PDCRetrievalError(f"Failed to parse PDC record {source}: {e}") from e

    kwargs.setdefault("filename", f"ccin-{ccin}" if ccin else "")
    kwargs.setdefault("recordID", f"ccin-{ccin}" if ccin else "")

    firebase_record = record.to_firebase(**kwargs)
    logger.info("Successfully mapped PDC metadata to Firebase format for {}", source)

    return firebase_record

# Generate a DataCite record from a Cioos record
# 
# This follow the DataCite schema v4.6 as described in:
# https://datacite-metadata-schema.readthedocs.io/en/4.6/properties/overview/

from loguru import logger

# TODO map cioos roles to datacite contributor roles
CONTRIBUTOR_TYPE_MAPPING_FROM_CIOOS = {
    "ContactPerson": "ContactPerson",
    "DataCollector": "DataCollector",
    "DataCurator": "DataCurator",
    "DataManager": "DataManager",
    "Distributor": "Distributor",
    "Editor": "Editor",
    "HostingInstitution": "HostingInstitution",
    "Producer": "Producer",
    "ProjectLeader": "ProjectLeader",
    "ProjectManager": "ProjectManager",
    "ProjectMember": "ProjectMember",
    "RegistrationAgency": "RegistrationAgency",
    "RegistrationAuthority": "RegistrationAuthority",
    "RelatedPerson": "RelatedPerson",
    "Researcher": "Researcher",
    "ResearchGroup": "ResearchGroup",
    "RightsHolder": "RightsHolder",
    "Sponsor": "Sponsor",
    "Supervisor": "Supervisor",
    "Translator": "Translator",
    "WorkPackageLeader": "WorkPackageLeader",
    "Other": "Other",
}

def _get_personal_info(contact) -> dict:
    return {
        "name": contact["name"],
        "nameType": "Personal",
        "givenName": contact["givenName"],
        "familyName": contact["familyName"],"
        "nameIdentifier":{
            "nameIdentifier": contact["orcid"],
            "nameIdentifierScheme": "ORCID",
            "schemeUri": "https://orcid.org",
        }
    }
def _get_organization_info(contact) -> dict:
    return {
        "name": contact["organization"],
        "nameType": "Organizational",
        "lang": "en",
    }

def _get_contact_info(contact) -> dict:
    """
    Get the contact information from the Cioos record.
    """
    return {
        **(_get_personal_info(contact) if contact["givenName"]else _get_organization_info(contact)),
        "affiliation": [
        {
            "affiliationIdentifier": contact["organization"],
            "affiliationIdentifierScheme": "ROR",
            "name": contact["organization"],
            "schemeUri": "https://ror.org/"
        }
        ],
    }

def _get_creators(record) -> list:
    """
    Get the creators from the Cioos record.
    """
    return [
        _get_contact_info(contact)
        for contact in record["contacts"]
        if "creator" in contact["roles"]
    ]


def _get_contributors(record) -> list:
    """
    Get the contributors from the CIOOS record.
    """
    return [
        {
            **_get_contact_info(contact),
            "contributorType": CONTRIBUTOR_TYPE_MAPPING_FROM_CIOOS.get(
                contact["roles"][0], "Other"
            ),
        }
        for contact in record["contacts"]
        if any(role in contact["roles"] for role in ["contributor", "editor"])
    ]

def _get_publisher(record) -> dict:
    for contact in record["contacts"]:
        if "publisher" in contact["roles"]:
            return {
                "name": contact["organization"],
                "publisherIdentifier": contact["ror"],
                "publisherIdentifierScheme":"ROR",
                "schemeUri": "https://ror.org/",
                "lang": "en"
            }
    logger.warning("No publisher found in the record.")

def generate_record(record) -> dict:
    """
    Generate a DataCite record from a Cioos record.
    """
    return {
        "identifier": {
            "doi": record["doi"],
        },
        "titles": [
            {
                "title": record["title_translated"]["en"],
                "lang": "en",
            },
            {
                "title": record["title_translated"]["fr"],
                "lang": "fr",
            }
        ],
        "creators": _get_creators(record),
        "publisher": _get_publisher(record),
        "contributors": _get_contributors(record),
        "publicationYear": record["publicationYear"],
        "subjects": [
            {
                "subject": subject,
                "lang": "en",
            }
            for subject in record["keywords"]
        ],
        "dates":[],
        "language": record["language"],
        "resourceType": {
            "resourceTypeGeneral": record["resourceTypeGeneral"],
            "resourceType": record["resourceType"],
        },
        "alternatedIdentifiers": [],
        "relatedIdentifiers": [],
        "sizes": [],
        "formats": [],
        "version": record["version"],
        "rightsList": [
            {
                "rights": record["license"],
                "lang": "en",
            }
        ],
        "descriptions": [
            {
                "description": record["description_translated"]["en"],
                "lang": "en",
            },
            {
                "description": record["description_translated"]["fr"],
                "lang": "fr",
            }
        ],
        "geoLocations": [],
        "fundingReferences": [],
        "relatedItems": [],
    }

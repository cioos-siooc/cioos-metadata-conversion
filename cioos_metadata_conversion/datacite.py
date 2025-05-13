# Generate a DataCite record from a Cioos record
# 
# This follow the DataCite schema v4.6 as described in:
# https://datacite-metadata-schema.readthedocs.io/en/4.6/properties/overview/

from loguru import logger
from datetime import datetime

# TODO map cioos roles to datacite contributor roles
CONTRIBUTOR_TYPE_MAPPING_FROM_CIOOS = {
    "pointOfContact": "ContactPerson",
    "DataCollector": "DataCollector",
    "custodian": "DataCurator",
    "DataManager": "DataManager",
    "distributor": "Distributor",
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
    "processor": "Other",
}

def _get_personal_info(contact) -> dict:
    nameIdentifier = {}
    if "orcid" in contact['individual']:
        nameIdentifier = {
            "nameIdentifier": contact['individual']["orcid"],
            "nameIdentifierScheme": "ORCID",
            "schemeUri": "https://orcid.org",
        }

    return {
        "name": contact['individual']["name"],
        "nameType": "Personal",
        "givenName": contact['individual'].get("givenNames",""),
        "familyName": contact['individual'].get("lastName",""),
        "nameIdentifier": nameIdentifier,
    }
def _get_organization_info(contact) -> dict:
    return {
        "name": contact["organization"]['name'],
        "nameType": "Organizational",
        "lang": "en",
    }

def _get_contact_info(contact) -> dict:
    """
    Get the contact information from the Cioos record.
    """
    affiliation = {"name": contact["organization"]['name']}
    if "ror" in contact["organization"]:
        affiliation["affiliationIdentifier"] = contact["organization"]['ror']
        affiliation["affiliationIdentifierScheme"] = "ROR"
        affiliation["schemeUri"] = "https://ror.org/"    
    return {
        **(_get_personal_info(contact) if "individual" in contact else _get_organization_info(contact)),
        "affiliation": [affiliation],
    }

def _get_creators(record) -> list:
    """
    Get the creators from the Cioos record.
    """
    return [
        _get_contact_info(contact)
        for contact in record["contact"]
        if "owner" in contact["roles"]
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
        for contact in record["contact"]
        for role in contact["roles"]
        if role not in {"owner", "publisher", "funder"}
    ]

def _get_publisher(record) -> dict:
    for contact in record["contact"]:
        if "publisher" in contact["roles"]:
            publisher = {
                "name": contact["organization"]['name'],
                "lang": "en",
            }
            if "ror" in contact["organization"]:
                publisher["publisherIdentifier"] = contact["organization"]['ror']
                publisher["publisherIdentifierScheme"] = "ROR"
                publisher["schemeUri"] = "https://ror.org/"
            return publisher
        
    logger.warning("No publisher found in the record.")

def _get_funding_references(record) -> dict:
    """
    Get the funding references from the Cioos record.
    """
    def _get_funder_ror(contact) -> dict:
        if not contact["organization"].get('ror'):
            return {}
        return{
            "funderIdentifier": contact["organization"]['ror'],
            "funderIdentifierType": "ROR",
        }

    return {
        "fundingReferences": [
            {
                "funderName": contact["organization"]['name'],
                **_get_funder_ror(contact),
            }
            for contact in record["contact"]
            if "funder" in contact["roles"]
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
        return {
            
        }

DATES_MAPPING = {
    "creation": "Created",
    "publication": "Issued",
    "revision": "Updated",
}
def _get_dates(record) -> list:
    """
    Get the dates from the Cioos record.
    """
    def _get_date(name, date):
        """
        Get the date from the Cioos record.
        """
        if name not in DATES_MAPPING:
            logger.error(f"Unknown date type: {name}")
            return {
                "date": date,
                "dateInformation": name,
                "type": "Other",
            }
        return {
            "date": date,
            "dateType": DATES_MAPPING[name],
        }

    return (
        [_get_date(name, date)
        for name, date in record['identification']["dates"].items()] +
        [_get_date(name,date)
         for name, date in record['metadata']["dates"].items()] +
        [{
            "date": f"{record['identification'].get('temporal_begin','*')}/{record['identification'].get('temporal_end', '*')}",
            "dateType": "Collected",
        }]
    )

def _get_alternate_identifiers(record) -> dict:
    """
    Get the alternate identifiers from the Cioos record.
    """
    return {"alternateIdentifiers":[
    ]}

def _get_related_identifiers(record) -> dict:
    """
    Get the related identifiers from the Cioos record.
    """
    return {"relatedIdentifiers":[
    ]}

def _get_related_items(record) -> dict:
    """
    Get the related items from the Cioos record.
    """
    return {"relatedItems":[
    ]}


def generate_record(record) -> dict:
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
    _add_optional("doi", record["identification"].get("identifier","").replace("https://doi.org/",""))

    return {
        "titles": [
            {
                "title": title,
                "lang": lang,
            }
            for lang, title in record['identification']["title"].items()
            if lang != "translations"
        ],
        **optional_fields,
        "creators": _get_creators(record),
        "publisher": _get_publisher(record),
        "contributors": _get_contributors(record),
        # parse iso date and return year from record['identification']["dates"]["created"]
        "publicationYear": str(datetime.strptime(
            record['metadata']["dates"]["publication"], "%Y-%m-%d"
        ).year),
        "subjects": [
            {
                "subject": keyword,
                "lang": lang,
                **_get_subject_scheme(group),
            }
            for group, group_keywords in record['identification']["keywords"].items()
            for lang, keywords in group_keywords.items()
            for keyword in keywords
        ],
        "dates":_get_dates(record),
        "language": record['metadata']["language"],
        "types": {
            "resourceTypeGeneral": "Dataset", # TODO revise with latest version of cioos
            "resourceType": "CIOOS Dataset Record", # TODO revise with latest version of cioos
        },
        **_get_alternate_identifiers(record),
        **_get_related_identifiers(record),
        # "sizes": [],
        # "formats": [],
        "version": record["identification"]["edition"],
        "rightsList": [
            {
                "rights": record["metadata"]['use_constraints']['licence']['title']['en'],
                "rightsUri": record["metadata"]['use_constraints']['licence']['url'],
                "schemeUri": "https://spdx.org/licenses/", # TODO confirm
                "rightsIdentifier": record["metadata"]['use_constraints']['licence']['code'],
                "rightsIdentifierScheme": "SPDX", # TODO confirm 
                "lang": "en", 
            }
        ],
        "descriptions": [
            {
                "description": abstract,
                "lang": lang,
                "descriptionType": "Abstract",
            }
            for lang, abstract in record["identification"]["abstract"].items()
            if lang != "translations"
        ] + [
            {
                "description": "limitations: " + description,
                "lang": lang,
                "descriptionType": "Other",
            }
            for lang, description in record["metadata"]["use_constraints"]['limitations'].items()
            if lang != "translations"
        ],
        "geoLocations": [
            {"geoLocationPolygon":[
                {"polygonPoint": {
                    "pointLatitude": float(loc.split(',')[1]),
                    "pointLongitude": float(loc.split(',')[0]),
                }}
                for loc in record["spatial"]["polygon"].split(" ")
            ]}
        ],
        **_get_funding_references(record),
        **_get_related_items(record),
        "schemaVersion": "http://datacite.org/schema/kernel-4",
    }

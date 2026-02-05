import requests
from loguru import logger

OBIS_API_BASE = "https://api.obis.org/v3/dataset"


def add_fr(text):
    outtext = {}
    outtext["en"] = text
    outtext["fr"] = "Traduction française actuellement indisponible"
    outtext["translations"] = {
        "fr": {
            "message": "text translations coming soon / Traductions de textes à venir",
            "verified": False,
        }
    }
    return outtext


def parse_extent_to_map(extent_wkt):
    """
    Parse OBIS extent POLYGON to CIOOS map format.
    Returns dict with north, south, east, west, polygon, description.
    """
    if not extent_wkt:
        return {}

    try:
        # Extract coordinates from POLYGON((lon lat, lon lat, ...))
        # Handle potential variations in WKT format if necessary,
        # but this simple split assumes POLYGON((...)) standard format
        coords_str = extent_wkt.split("POLYGON((")[1].split("))")[0]
        coord_pairs = coords_str.split(",")

        lons = []
        lats = []

        polygon = ""
        for pair in coord_pairs:
            pair = pair.strip()
            if not pair:
                continue
            parts = pair.split()
            if len(parts) >= 2:
                lon = float(parts[0])
                lat = float(parts[1])
                lons.append(lon)
                lats.append(lat)
                polygon += f"{lon},{lat} "

        if not lons or not lats:
            return {
                "polygon": extent_wkt,
                "description": {"en": ""},
            }

        return {
            "north": str(max(lats)),
            "south": str(min(lats)),
            "east": str(max(lons)),
            "west": str(min(lons)),
            "polygon": polygon.strip(),
            "description": {"en": "Spatial extent from OBIS"},
        }
    except (IndexError, ValueError) as e:
        logger.warning(f"Failed to parse extent WKT: {extent_wkt}. Error: {e}")
        # If parsing fails, return empty map but keep original polygon if possible
        return {
            "polygon": extent_wkt,  # Keep the original even if we can't parse it
            "description": {"en": ""},
        }


def convert_contacts(obis_contacts):
    cioos_contacts = []
    if not obis_contacts:
        return cioos_contacts

    for contact in obis_contacts:
        given_name = contact.get("givenname", "")
        last_name = contact.get("surname", "")

        # Build full name
        full_name = ""
        if given_name and last_name:
            full_name = f"{given_name} {last_name}"
        elif given_name:
            full_name = given_name
        elif last_name:
            full_name = last_name

        cioos_contact = {
            "givenNames": given_name,
            "lastName": last_name,
            "indName": full_name,
            "indOrcid": "",
            "inCitation": True,  # Default to true for creators/authors
            "role": [contact.get("type", "")],  # role is an array in CIOOS
            "orgName": contact.get("organization", ""),
            "orgAddress": "",
            "orgCity": "",
            "orgCountry": "",
            "orgRor": "",
            "orgURL": contact.get("url", ""),
        }

        # For contacts with email, add it with different field name
        if contact.get("email"):
            cioos_contact["indEmail"] = contact.get("email")

        # Add position if available
        if contact.get("position"):
            cioos_contact["position"] = contact.get("position")

        cioos_contacts.append(cioos_contact)

    return cioos_contacts


def map_obis_to_cioos(obis_data):
    cioos_data = {}
    cioos_data["abstract"] = add_fr(obis_data.get("abstract", ""))
    cioos_data["datasetIdentifier"] = obis_data.get("id")
    cioos_data["title"] = add_fr(obis_data.get("title", ""))
    cioos_data["license"] = obis_data.get("intellectualrights", "")
    cioos_data["category"] = "dataset"
    cioos_data["comment"] = ""

    # Keywords
    keywords = []
    if obis_data.get("keywords"):
        for keyword in obis_data["keywords"]:
            if isinstance(keyword, dict):
                keywords.append(keyword.get("keyword"))
            elif isinstance(keyword, str):
                keywords.append(keyword)

    cioos_data["keywords"] = {"en": keywords, "fr": []}

    # Associated resources
    associated_resources = []

    # Primary dataset URL
    if obis_data.get("url"):
        associated_resources.append(
            {
                "association_type": "IsIdenticalTo",
                "association_type_iso": "crossReference",
                "authority": "URL",
                "code": obis_data["url"],
                "title": "Primary dataset URL",
            }
        )

    # Archive URL
    if obis_data.get("archive") and obis_data["archive"] != obis_data.get("url"):
        associated_resources.append(
            {
                "association_type": "IsIdenticalTo",
                "association_type_iso": "crossReference",
                "authority": "URL",
                "code": obis_data["archive"],
                "title": "Dataset archive",
            }
        )

    # Metadata feed
    if obis_data.get("feed") and obis_data["feed"].get("url"):
        associated_resources.append(
            {
                "association_type": "IsIdenticalTo",
                "association_type_iso": "crossReference",
                "authority": "URL",
                "code": obis_data["feed"]["url"],
                "title": "Metadata feed source",
            }
        )

    # Tags (e.g., vocabulary terms)
    if obis_data.get("tags"):
        for tag in obis_data["tags"]:
            associated_resources.append(
                {
                    "association_type": "IsDescribedBy",
                    "association_type_iso": "crossReference",
                    "authority": "URL",
                    "code": tag,
                    "title": "OBIS Dataset Type vocabulary term",
                }
            )

    cioos_data["associated_resources"] = associated_resources
    cioos_data["contacts"] = convert_contacts(obis_data.get("contacts"))

    created_date = obis_data.get("created")
    if created_date:
        cioos_data["created"] = created_date.split(".")[0] + "Z"
    else:
        cioos_data["created"] = ""

    # Temporal extent of data collection (not available in OBIS metadata)
    cioos_data["dateStart"] = ""
    cioos_data["dateEnd"] = ""

    # Dataset publication
    published_date = obis_data.get("published", "")
    if published_date:
        cioos_data["datePublished"] = published_date.split(".")[0] + "Z"
    else:
        cioos_data["datePublished"] = ""

    # Last revision / update
    updated_date = obis_data.get("updated", "")
    if updated_date:
        cioos_data["dateRevised"] = updated_date.split(".")[0] + "Z"
    else:
        cioos_data["dateRevised"] = ""

    # Spatial extent
    cioos_data["map"] = parse_extent_to_map(obis_data.get("extent"))

    # Distribution - data access information
    distribution = []
    if obis_data.get("archive"):
        distribution.append(
            {
                "name": add_fr("Darwin Core Archive"),
                "url": obis_data["archive"],
                "description": add_fr(
                    "Download the complete Darwin Core Archive dataset"
                ),
            }
        )
    if obis_data.get("url") and obis_data.get("url") != obis_data.get("archive"):
        distribution.append(
            {
                "name": add_fr("IPT Resource Page"),
                "url": obis_data["url"],
                "description": add_fr(
                    "View dataset metadata and access options via the Integrated Publishing Toolkit"
                ),
            }
        )
    cioos_data["distribution"] = distribution

    # Constant fields - all OBIS records are datasets
    cioos_data["metadataScope"] = "Dataset"
    cioos_data["resourceType"] = "Dataset"
    cioos_data["doiCreationStatus"] = ""
    cioos_data["edition"] = ""
    cioos_data["filename"] = ""
    cioos_data["identifier"] = ""
    cioos_data["noPlatform"] = ""
    cioos_data["progress"] = ""
    cioos_data["recordID"] = ""
    cioos_data["status"] = ""
    cioos_data["userID"] = ""
    cioos_data["lastEditedBy"] = {"displayName": "", "email": ""}
    cioos_data["language"] = "en"

    # Additional CIOOS fields not available in OBIS
    cioos_data["limitations"] = add_fr("")  # Usage limitations/constraints
    cioos_data["noTaxa"] = True  # OBIS metadata doesn't include taxon lists
    cioos_data["noVerticalExtent"] = True  # Vertical extent not in OBIS metadata
    cioos_data["verticalExtentDirection"] = ""  # e.g., "depthPositive"
    cioos_data["timeFirstPublished"] = cioos_data[
        "datePublished"
    ]  # Use same as datePublished
    cioos_data["eov"] = []  # Essential Ocean Variables - can't map from OBIS
    cioos_data["platforms"] = []  # Platform information not available
    cioos_data["projects"] = []  # Project information not available
    cioos_data["region"] = ""  # Geographic region classification

    return cioos_data


def retrieve_obis_metadata(dataset_id: str):
    """
    Retrieve metadata for an OBIS dataset by ID.
    """
    url = f"{OBIS_API_BASE}/{dataset_id}"
    logger.info(f"Retrieving OBIS metadata from: {url}")

    response = requests.get(url)
    response.raise_for_status()

    obis_data = response.json()

    # OBIS API returns a dict with "results" list
    if "results" in obis_data:
        if not obis_data["results"]:
            raise ValueError(f"No OBIS dataset found with ID: {dataset_id}")
        obis_data = obis_data["results"][0]
    elif isinstance(obis_data, list):
        if not obis_data:
            raise ValueError(f"No OBIS dataset found with ID: {dataset_id}")
        obis_data = obis_data[0]

    return map_obis_to_cioos(obis_data)

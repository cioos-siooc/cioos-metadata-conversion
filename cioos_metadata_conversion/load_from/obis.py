import requests
from loguru import logger

OBIS_API_BASE = "https://api.obis.org/v3/dataset"
OBIS_FACET_URL = "https://api.obis.org/v3/facet"

# Mapping from OBIS taxonomic class names to CIOOS Essential Ocean Variables.
# Built from the OBIS /v3/facet?facets=class endpoint values and the CIOOS
# EOV choices in cioos-siooc_schema.json.
TAXON_CLASS_TO_EOV = {
    # Fish — fishAbundanceAndDistribution
    "Actinopterygii": "fishAbundanceAndDistribution",
    "Teleostei": "fishAbundanceAndDistribution",
    "Elasmobranchii": "fishAbundanceAndDistribution",
    "Chondrichthyes": "fishAbundanceAndDistribution",
    "Myxini": "fishAbundanceAndDistribution",
    "Petromyzonti": "fishAbundanceAndDistribution",
    "Holocephali": "fishAbundanceAndDistribution",
    "Chondrostei": "fishAbundanceAndDistribution",
    "Ichthyostraca": "fishAbundanceAndDistribution",
    # Marine turtles, birds, mammals
    "Mammalia": "marineTurtlesBirdsMammalsAbundanceAndDistribution",
    "Aves": "marineTurtlesBirdsMammalsAbundanceAndDistribution",
    "Reptilia": "marineTurtlesBirdsMammalsAbundanceAndDistribution",
    # Phytoplankton
    "Bacillariophyceae": "phytoplanktonBiomassAndDiversity",
    "Dinophyceae": "phytoplanktonBiomassAndDiversity",
    "Coscinodiscophyceae": "phytoplanktonBiomassAndDiversity",
    "Mediophyceae": "phytoplanktonBiomassAndDiversity",
    "Fragilariophyceae": "phytoplanktonBiomassAndDiversity",
    "Cyanophyceae": "phytoplanktonBiomassAndDiversity",
    "Prymnesiophyceae": "phytoplanktonBiomassAndDiversity",
    "Coccolithophyceae": "phytoplanktonBiomassAndDiversity",
    "Chrysophyceae": "phytoplanktonBiomassAndDiversity",
    "Cryptophyceae": "phytoplanktonBiomassAndDiversity",
    "Prasinophyceae": "phytoplanktonBiomassAndDiversity",
    "Raphidophyceae": "phytoplanktonBiomassAndDiversity",
    "Dictyochophyceae": "phytoplanktonBiomassAndDiversity",
    "Euglenoidea": "phytoplanktonBiomassAndDiversity",
    "Euglenophyceae": "phytoplanktonBiomassAndDiversity",
    "Xanthophyceae": "phytoplanktonBiomassAndDiversity",
    "Chlorophyceae": "phytoplanktonBiomassAndDiversity",
    "Chlorodendrophyceae": "phytoplanktonBiomassAndDiversity",
    "Trebouxiophyceae": "phytoplanktonBiomassAndDiversity",
    "Zygnematophyceae": "phytoplanktonBiomassAndDiversity",
    # Zooplankton (includes many protist microzooplankton & foraminifera groups)
    "Hexanauplia": "zooplanktonBiomassAndDiversity",
    "Copepoda": "zooplanktonBiomassAndDiversity",
    "Branchiopoda": "zooplanktonBiomassAndDiversity",
    "Ostracoda": "zooplanktonBiomassAndDiversity",
    "Scyphozoa": "zooplanktonBiomassAndDiversity",
    "Hydrozoa": "zooplanktonBiomassAndDiversity",
    "Appendicularia": "zooplanktonBiomassAndDiversity",
    "Thaliacea": "zooplanktonBiomassAndDiversity",
    "Sagittoidea": "zooplanktonBiomassAndDiversity",
    "Choanoflagellatea": "zooplanktonBiomassAndDiversity",
    "Oligotrichea": "zooplanktonBiomassAndDiversity",
    "Heterotrichea": "zooplanktonBiomassAndDiversity",
    "Prostomatea": "zooplanktonBiomassAndDiversity",
    "Oligohymenophorea": "zooplanktonBiomassAndDiversity",
    "Globothalamea": "zooplanktonBiomassAndDiversity",
    "Tubothalamea": "zooplanktonBiomassAndDiversity",
    "Nodosariata": "zooplanktonBiomassAndDiversity",
    "Monothalamea": "zooplanktonBiomassAndDiversity",
    "Tubulinea": "zooplanktonBiomassAndDiversity",
    "Foraminifera incertae sedis": "zooplanktonBiomassAndDiversity",
    # Microbes
    "Alphaproteobacteria": "microbeBiomassAndDiversity",
    "Betaproteobacteria": "microbeBiomassAndDiversity",
    "Gammaproteobacteria": "microbeBiomassAndDiversity",
    "Deltaproteobacteria": "microbeBiomassAndDiversity",
    "Epsilonproteobacteria": "microbeBiomassAndDiversity",
    "Flavobacteria": "microbeBiomassAndDiversity",
    "Actinobacteria": "microbeBiomassAndDiversity",
    "Bacilli": "microbeBiomassAndDiversity",
    "Bacili": "microbeBiomassAndDiversity",
    "Cytophagia": "microbeBiomassAndDiversity",
    "Sphingobacteria": "microbeBiomassAndDiversity",
    "Gemmatimonadetes(class)": "microbeBiomassAndDiversity",
    "Aquificae": "microbeBiomassAndDiversity",
    "Methanomicrobia": "microbeBiomassAndDiversity",
    # Macroalgae
    "Phaeophyceae": "macroalgalCanopyCoverAndComposition",
    "Florideophyceae": "macroalgalCanopyCoverAndComposition",
    "Ulvophyceae": "macroalgalCanopyCoverAndComposition",
    "Bangiophyceae": "macroalgalCanopyCoverAndComposition",
    "Compsopogonophyceae": "macroalgalCanopyCoverAndComposition",
    # Hard coral
    "Anthozoa": "hardCoralCoverAndComposition",
    "Hexacorallia": "hardCoralCoverAndComposition",
    "Octocorallia": "hardCoralCoverAndComposition",
    # Invertebrates (catch-all for many marine invertebrate classes)
    "Gastropoda": "invertebrateAbundanceAndDistribution",
    "Bivalvia": "invertebrateAbundanceAndDistribution",
    "Cephalopoda": "invertebrateAbundanceAndDistribution",
    "Polychaeta": "invertebrateAbundanceAndDistribution",
    "Clitellata": "invertebrateAbundanceAndDistribution",
    "Echinoidea": "invertebrateAbundanceAndDistribution",
    "Asteroidea": "invertebrateAbundanceAndDistribution",
    "Ophiuroidea": "invertebrateAbundanceAndDistribution",
    "Holothuroidea": "invertebrateAbundanceAndDistribution",
    "Crinoidea": "invertebrateAbundanceAndDistribution",
    "Malacostraca": "invertebrateAbundanceAndDistribution",
    "Thecostraca": "invertebrateAbundanceAndDistribution",
    "Demospongiae": "invertebrateAbundanceAndDistribution",
    "Calcarea": "invertebrateAbundanceAndDistribution",
    "Hexactinellida": "invertebrateAbundanceAndDistribution",
    "Ascidiacea": "invertebrateAbundanceAndDistribution",
    "Tentaculata": "invertebrateAbundanceAndDistribution",
    "Gymnolaemata": "invertebrateAbundanceAndDistribution",
    "Stenolaemata": "invertebrateAbundanceAndDistribution",
    "Polyplacophora": "invertebrateAbundanceAndDistribution",
    "Scaphopoda": "invertebrateAbundanceAndDistribution",
    "Sipunculidea": "invertebrateAbundanceAndDistribution",
    "Pycnogonida": "invertebrateAbundanceAndDistribution",
    "Hexapoda": "invertebrateAbundanceAndDistribution",
    "Arachnida": "invertebrateAbundanceAndDistribution",
    "Turbellaria": "invertebrateAbundanceAndDistribution",
    "Chromadorea": "invertebrateAbundanceAndDistribution",
    "Monogenea": "invertebrateAbundanceAndDistribution",
    "Hoplonemertea": "invertebrateAbundanceAndDistribution",
    # Seagrass — Magnoliopsida covers most seagrasses (Zostera, Posidonia, etc.)
    "Magnoliopsida": "seagrassCoverAndComposition",
    "Liliopsida": "seagrassCoverAndComposition",
    # Other
    "Amphibia": "other",
}


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


# Valid CIOOS/ISO 19115 role codes (from cioos-siooc_schema.json)
CIOOS_ROLE_CODES = {
    "author", "custodian", "distributor", "originator", "owner",
    "pointOfContact", "principalInvestigator", "processor", "publisher",
    "resourceProvider", "user", "sponsor", "coAuthor", "collaborator",
    "editor", "mediator", "rightsHolder", "contributor", "funder",
    "stakeholder",
}

# Mapping from OBIS EML construct types to CIOOS role codes.
# OBIS uses EML element names (creator, contact, metadataProvider, etc.)
# as the contact "type" field. These don't exist in the ISO role codelist
# that CIOOS uses, so we map them to the closest CIOOS equivalent.
# See: https://manual.obis.org/eml.html
# See: https://github.com/cioos-siooc/metadata-xml
OBIS_TO_CIOOS_ROLE = {
    "creator": "author",
    "contact": "pointOfContact",
    "metadataProvider": "custodian",
    "metadataprovider": "custodian",
    "associatedParty": "contributor",
    "associatedparty": "contributor",
    "personnel": "contributor",
}


def fetch_eovs_from_taxonomy(dataset_id):
    """Fetch taxonomic classes for an OBIS dataset and map them to CIOOS EOVs.

    Calls the OBIS facet API to get class-level taxonomy, then maps each class
    to a CIOOS Essential Ocean Variable using TAXON_CLASS_TO_EOV.
    Returns a deduplicated list of EOV codes.
    """
    if not dataset_id:
        return []

    try:
        response = requests.get(
            OBIS_FACET_URL,
            params={"datasetid": dataset_id, "facets": "class"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as e:
        logger.warning(f"Failed to fetch taxonomy facets for {dataset_id}: {e}")
        return []

    classes = data.get("results", {}).get("class", [])
    if not classes:
        logger.info(f"No taxonomic classes found for dataset {dataset_id}")
        return []

    eovs = set()
    unmapped = []
    for entry in classes:
        taxon_class = entry.get("key", "")
        eov = TAXON_CLASS_TO_EOV.get(taxon_class)
        if eov:
            eovs.add(eov)
        else:
            unmapped.append(taxon_class)

    if unmapped:
        logger.info(
            f"Dataset {dataset_id}: unmapped taxonomic classes: {unmapped}"
        )

    # CIOOS requires at least one EOV; if we can't map any taxonomy classes
    # (or if a dataset only contains odd/terrestrial classes), fall back to "other".
    if not eovs:
        logger.warning(
            f"Dataset {dataset_id}: no EOVs mapped from taxonomy; falling back to ['other']"
        )
        return ["other"]

    return sorted(eovs)


def map_obis_role_to_cioos(obis_role):
    """Map an OBIS EML role/type to a valid CIOOS ISO 19115 role code.

    Checks in order:
    1. If the role is already a valid CIOOS role code, use it as-is.
    2. If it matches a known OBIS EML construct, map it.
    3. Otherwise fall back to 'contributor'.
    """
    if not obis_role:
        return "contributor"

    # Already a valid CIOOS role code (e.g. from associatedParty/role)
    if obis_role in CIOOS_ROLE_CODES:
        return obis_role

    # Known OBIS EML construct mapping
    mapped = OBIS_TO_CIOOS_ROLE.get(obis_role)
    if mapped:
        return mapped

    # Case-insensitive fallback check
    lower = obis_role.lower()
    for code in CIOOS_ROLE_CODES:
        if lower == code.lower():
            return code

    mapped = OBIS_TO_CIOOS_ROLE.get(lower)
    if mapped:
        return mapped

    logger.warning(f"Unknown OBIS role '{obis_role}', falling back to 'contributor'")
    return "contributor"


def convert_contacts(obis_contacts):
    cioos_contacts = []
    if not obis_contacts:
        return cioos_contacts

    for contact in obis_contacts:
        given_name = contact.get("givenname", "")
        last_name = contact.get("surname", "")
        org_name = contact.get("organization", "")

        # Skip contacts with no usable identity — they would produce empty
        # individual/organization dicts that crash the XML template after
        # scrub_dict removes all the empty values.
        if not given_name and not last_name and not org_name:
            logger.debug(f"Skipping contact with no name or organization: {contact}")
            continue

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
            "role": [map_obis_role_to_cioos(contact.get("type", ""))],
            "orgName": org_name,
            "orgAddress": "",
            "orgCity": "",
            "orgCountry": "",
            "orgRor": "",
            "orgURL": contact.get("url", ""),
        }

        if contact.get("email"):
            cioos_contact["indEmail"] = contact.get("email")

        # indPosition is the field name firebase_to_cioos expects
        if contact.get("position"):
            cioos_contact["indPosition"] = contact.get("position")

        cioos_contacts.append(cioos_contact)

    return cioos_contacts


def map_obis_to_cioos(obis_data):
    cioos_data = {}
    cioos_data["abstract"] = add_fr(obis_data.get("abstract", ""))
    # Only set datasetIdentifier when the dataset has a real DOI.
    # The metadata-xml template emits a bare cit:identifier (no mcc:authority)
    # and the CKAN harvester defaults unqualified identifiers to doi.org,
    # producing broken links like doi.org/<UUID> for datasets without DOIs.
    cioos_data["datasetIdentifier"] = obis_data.get("doi", "") or ""
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

    # OBIS only provides English keywords. Use them as French placeholders
    # since many are scientific terms or proper nouns that don't change.
    cioos_data["keywords"] = {"en": keywords, "fr": keywords}

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

    # The metadata-xml template only emits mdb:contact (required by ISO 19115-3)
    # for contacts with the "custodian" role.  When the OBIS metadataProvider
    # entry has no name/org it gets dropped by convert_contacts(), leaving no
    # custodian.  Promote the first available contact so the XML stays valid.
    has_custodian = any(
        "custodian" in c.get("role", []) for c in cioos_data["contacts"]
    )
    if not has_custodian and cioos_data["contacts"]:
        cioos_data["contacts"][0]["role"].append("custodian")
        logger.info(
            "No custodian contact found; promoted first contact to custodian"
        )

    # Dates — the metadata-xml template requires metadata.dates to survive
    # scrub_dict (which strips empty values).  When created or published are
    # missing we fall back to updated so at least one date is always present.
    updated_date = obis_data.get("updated", "")
    updated_clean = updated_date.split(".")[0] + "Z" if updated_date else ""

    created_date = obis_data.get("created") or updated_date
    if created_date:
        cioos_data["created"] = created_date.split(".")[0] + "Z"
    else:
        cioos_data["created"] = ""

    # Temporal extent of data collection (not available in OBIS metadata)
    cioos_data["dateStart"] = ""
    cioos_data["dateEnd"] = ""

    # Dataset publication
    published_date = obis_data.get("published", "") or updated_date
    if published_date:
        cioos_data["datePublished"] = published_date.split(".")[0] + "Z"
    else:
        cioos_data["datePublished"] = ""

    # Last revision / update
    cioos_data["dateRevised"] = updated_clean

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
    # Derive EOVs from OBIS taxonomy via the facet API
    dataset_id = obis_data.get("id")
    cioos_data["eov"] = fetch_eovs_from_taxonomy(dataset_id)
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

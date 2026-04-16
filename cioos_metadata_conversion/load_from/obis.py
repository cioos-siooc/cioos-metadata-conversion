import re

import requests
from loguru import logger

OBIS_API_BASE = "https://api.obis.org/v3/dataset"
OBIS_FACET_URL = "https://api.obis.org/v3/facet"
OBIS_OCCURRENCE_URL = "https://api.obis.org/v3/occurrence"

# Mapping from OBIS taxonomic class names to CIOOS Essential Ocean Variables.
# Built from the OBIS /v3/facet?facets=class endpoint values and the CIOOS
# EOV choices in cioos-siooc_schema.json.
TAXON_CLASS_TO_EOV = {
    # ── Fish — fishAbundanceAndDistribution ──
    "Actinopterygii": "fishAbundanceAndDistribution",
    "Teleostei": "fishAbundanceAndDistribution",
    "Elasmobranchii": "fishAbundanceAndDistribution",
    "Chondrichthyes": "fishAbundanceAndDistribution",
    "Myxini": "fishAbundanceAndDistribution",
    "Petromyzonti": "fishAbundanceAndDistribution",
    "Holocephali": "fishAbundanceAndDistribution",
    "Chondrostei": "fishAbundanceAndDistribution",
    "Ichthyostraca": "fishAbundanceAndDistribution",
    "Holostei": "fishAbundanceAndDistribution",
    "Coelacanthi": "fishAbundanceAndDistribution",
    "Dipneusti": "fishAbundanceAndDistribution",
    # ── Marine turtles, birds, mammals ──
    "Mammalia": "marineTurtlesBirdsMammalsAbundanceAndDistribution",
    "Aves": "marineTurtlesBirdsMammalsAbundanceAndDistribution",
    "Reptilia": "marineTurtlesBirdsMammalsAbundanceAndDistribution",
    # ── Phytoplankton — photosynthetic algae & cyanobacteria ──
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
    # New phytoplankton additions (from OBIS facet data)
    "Pyramimonadophyceae": "phytoplanktonBiomassAndDiversity",
    "Mamiellophyceae": "phytoplanktonBiomassAndDiversity",
    "Cryptophyta incertae sedis": "phytoplanktonBiomassAndDiversity",
    "Pelagophyceae": "phytoplanktonBiomassAndDiversity",
    "Eustigmatophyceae": "phytoplanktonBiomassAndDiversity",
    "Bolidophyceae": "phytoplanktonBiomassAndDiversity",
    "Pavlovophyceae": "phytoplanktonBiomassAndDiversity",
    "Prasinodermatophyceae": "phytoplanktonBiomassAndDiversity",
    "Nephroselmidophyceae": "phytoplanktonBiomassAndDiversity",
    "Pinguiophyceae": "phytoplanktonBiomassAndDiversity",
    "Synurophyceae": "phytoplanktonBiomassAndDiversity",
    "Haptophyta incertae sedis": "phytoplanktonBiomassAndDiversity",
    "Dinoflagellata incertae sedis": "phytoplanktonBiomassAndDiversity",
    "Chlorarachnea": "phytoplanktonBiomassAndDiversity",
    "Chlorarachniophyceae": "phytoplanktonBiomassAndDiversity",
    "Glaucophyceae": "phytoplanktonBiomassAndDiversity",
    "Charophyceae": "phytoplanktonBiomassAndDiversity",
    # ── Zooplankton — planktonic heterotrophs, ciliates, rotifers, jellyfish ──
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
    # New zooplankton additions (from OBIS facet data)
    "Polycystina": "zooplanktonBiomassAndDiversity",     # Radiolaria
    "Litostomatea": "zooplanktonBiomassAndDiversity",     # Ciliates
    "Spirotrichea": "zooplanktonBiomassAndDiversity",     # Ciliates (tintinnids etc.)
    "Acantharia": "zooplanktonBiomassAndDiversity",       # Planktonic protists
    "Eurotatoria": "zooplanktonBiomassAndDiversity",      # Rotifers
    "Phyllopharyngea": "zooplanktonBiomassAndDiversity",  # Ciliates
    "Nassophorea": "zooplanktonBiomassAndDiversity",      # Ciliates
    "Telonemea": "zooplanktonBiomassAndDiversity",        # Heterotrophic flagellates
    "Maxillopoda": "zooplanktonBiomassAndDiversity",      # Crustaceans (planktonic)
    "Colpodea": "zooplanktonBiomassAndDiversity",         # Ciliates
    "Karyorelictea": "zooplanktonBiomassAndDiversity",    # Ciliates
    "Nuda": "zooplanktonBiomassAndDiversity",             # Ctenophores (comb jellies)
    "Cubozoa": "zooplanktonBiomassAndDiversity",          # Box jellyfish
    "Staurozoa": "zooplanktonBiomassAndDiversity",        # Stalked jellyfish
    "Thecofilosea": "zooplanktonBiomassAndDiversity",     # Amoeboid protists (protozooplankton)
    "Discosea": "zooplanktonBiomassAndDiversity",         # Amoebae (protozooplankton)
    "Sarcomonadea": "zooplanktonBiomassAndDiversity",     # Heterotrophic flagellates
    "Plagiopylea": "zooplanktonBiomassAndDiversity",      # Ciliates
    "Imbricatea": "zooplanktonBiomassAndDiversity",       # Cercozoan protists
    # ── Microbes — bacteria, archaea, fungi, parasitic & heterotrophic protists ──
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
    # New bacteria additions
    "Verrucomicrobiae": "microbeBiomassAndDiversity",
    "Opitutae": "microbeBiomassAndDiversity",
    "Planctomycetacia": "microbeBiomassAndDiversity",
    "Phycisphaerae": "microbeBiomassAndDiversity",
    "Clostridia": "microbeBiomassAndDiversity",
    "Bacteroidia": "microbeBiomassAndDiversity",
    "Anaerolineae": "microbeBiomassAndDiversity",
    "Planctomycetia": "microbeBiomassAndDiversity",
    "Holophagae": "microbeBiomassAndDiversity",
    "Deinococci": "microbeBiomassAndDiversity",
    "Caldilineae": "microbeBiomassAndDiversity",
    "Negativicutes": "microbeBiomassAndDiversity",
    "Erysipelotrichi": "microbeBiomassAndDiversity",
    "Nitrospira": "microbeBiomassAndDiversity",
    "Zetaproteobacteria": "microbeBiomassAndDiversity",
    "Synergistia": "microbeBiomassAndDiversity",
    "Chloroflexi": "microbeBiomassAndDiversity",
    "Mollicutes": "microbeBiomassAndDiversity",
    "Chlamydiia": "microbeBiomassAndDiversity",
    "Fusobacteria": "microbeBiomassAndDiversity",
    "Acidobacteria": "microbeBiomassAndDiversity",
    "Fibrobacteres(class)": "microbeBiomassAndDiversity",
    "Spirochaetes(Class)": "microbeBiomassAndDiversity",
    "Thermomicrobia": "microbeBiomassAndDiversity",
    "Bacteroidetes incertae sedis": "microbeBiomassAndDiversity",
    # New archaea additions
    "Thermoplasmata": "microbeBiomassAndDiversity",
    "Thaumarchaeota incertae sedis": "microbeBiomassAndDiversity",
    "Halobacteria": "microbeBiomassAndDiversity",
    "Thermococci": "microbeBiomassAndDiversity",
    "Thermoprotei": "microbeBiomassAndDiversity",
    "Methanobacteria": "microbeBiomassAndDiversity",
    "Nanoarchaeia": "microbeBiomassAndDiversity",
    "Archaeoglobi": "microbeBiomassAndDiversity",
    "Methanococci": "microbeBiomassAndDiversity",
    # Fungi — marine fungi are microbes per NOAA/NIH/GOOS definitions
    "Dothideomycetes": "microbeBiomassAndDiversity",
    "Agaricomycetes": "microbeBiomassAndDiversity",
    "Sordariomycetes": "microbeBiomassAndDiversity",
    "Eurotiomycetes": "microbeBiomassAndDiversity",
    "Tremellomycetes": "microbeBiomassAndDiversity",
    "Saccharomycetes": "microbeBiomassAndDiversity",
    "Leotiomycetes": "microbeBiomassAndDiversity",
    "Microbotryomycetes": "microbeBiomassAndDiversity",
    "Lecanoromycetes": "microbeBiomassAndDiversity",
    "Chytridiomycetes": "microbeBiomassAndDiversity",
    "Cystobasidiomycetes": "microbeBiomassAndDiversity",
    "Glomeromycetes": "microbeBiomassAndDiversity",
    "Taphrinomycetes": "microbeBiomassAndDiversity",
    "Pezizomycetes": "microbeBiomassAndDiversity",
    "Orbiliomycetes": "microbeBiomassAndDiversity",
    "Wallemiomycetes": "microbeBiomassAndDiversity",
    "Ustilaginomycetes": "microbeBiomassAndDiversity",
    "Agaricostilbomycetes": "microbeBiomassAndDiversity",
    # Heterotrophic / parasitic protists — eukaryotic microbes
    "Labyrinthulea": "microbeBiomassAndDiversity",        # Thraustochytrids (decomposers)
    "Conoidasida": "microbeBiomassAndDiversity",           # Apicomplexa parasites
    "Perkinsea": "microbeBiomassAndDiversity",             # Parasitic protists (mollusc pathogens)
    "Kinetoplastea": "microbeBiomassAndDiversity",         # Flagellates (incl. parasites)
    "Diplonemea": "microbeBiomassAndDiversity",            # Heterotrophic flagellates
    "Peronosporea": "microbeBiomassAndDiversity",          # Oomycetes
    # ── Macroalgae ──
    "Phaeophyceae": "macroalgalCanopyCoverAndComposition",
    "Florideophyceae": "macroalgalCanopyCoverAndComposition",
    "Ulvophyceae": "macroalgalCanopyCoverAndComposition",
    "Bangiophyceae": "macroalgalCanopyCoverAndComposition",
    "Compsopogonophyceae": "macroalgalCanopyCoverAndComposition",
    # ── Hard coral ──
    "Anthozoa": "hardCoralCoverAndComposition",
    "Hexacorallia": "hardCoralCoverAndComposition",
    "Octocorallia": "hardCoralCoverAndComposition",
    # ── Invertebrates — benthic & other marine invertebrates ──
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
    # New invertebrate additions
    "Enoplea": "invertebrateAbundanceAndDistribution",         # Nematodes
    "Caudofoveata": "invertebrateAbundanceAndDistribution",    # Shell-less molluscs
    "Pilidiophora": "invertebrateAbundanceAndDistribution",    # Nemerteans (ribbon worms)
    "Palaeonemertea": "invertebrateAbundanceAndDistribution",  # Nemerteans
    "Leptocardii": "invertebrateAbundanceAndDistribution",     # Lancelets
    "Enteropneusta": "invertebrateAbundanceAndDistribution",   # Acorn worms
    "Merostomata": "invertebrateAbundanceAndDistribution",     # Horseshoe crabs
    "Solenogastres": "invertebrateAbundanceAndDistribution",   # Shell-less molluscs
    "Homoscleromorpha": "invertebrateAbundanceAndDistribution",# Sponges
    "Trematoda": "invertebrateAbundanceAndDistribution",       # Flukes
    # ── Seagrass ──
    "Magnoliopsida": "seagrassCoverAndComposition",
    "Liliopsida": "seagrassCoverAndComposition",
    # ── Other — organisms not fitting any current GOOS EOV ──
    "Amphibia": "other",
    "Crocodylia": "other",  # Not covered by any GOOS EOV (sea turtles EOV is turtles only)
}


# Mapping from BODC NERC P01 parameter codes to CIOOS Essential Ocean Variables.
# measurementTypeID in OBIS eMoF records is typically a URI like
# http://vocab.nerc.ac.uk/collection/P01/current/TEMPPR01/ — the 8-char tail
# is the P01 code we match on. Reference: https://vocab.nerc.ac.uk/collection/P01/current/
MEASUREMENT_P01_TO_EOV = {
    # Temperature
    "TEMPPR01": "subSurfaceTemperature",   # Sea water temperature (CTD)
    "TEMPST01": "seaSurfaceTemperature",   # Sea surface temperature
    "TEMPET01": "subSurfaceTemperature",   # Temperature of water by electronic thermometer
    # Salinity
    "PSALST01": "seaSurfaceSalinity",      # Practical salinity at surface
    "PSALPR01": "subSurfaceSalinity",      # Practical salinity (CTD)
    "PSLTZZ01": "subSurfaceSalinity",      # Practical salinity of water body
    # Oxygen
    "DOXYZZXX": "oxygen",
    "DOXMZZXX": "oxygen",
    "OXYSZZ01": "oxygen",
    # Nutrients
    "NTRAZZXX": "nutrients",               # Nitrate
    "NTRIZZXX": "nutrients",               # Nitrite
    "NTRZAAZX": "nutrients",               # Nitrate+nitrite
    "AMONAAZX": "nutrients",               # Ammonium
    "PHOSZZXX": "nutrients",               # Phosphate
    "SLCAAAZX": "nutrients",               # Silicate
    # Inorganic carbon chemistry
    "PHXXZZXX": "inorganicCarbon",         # pH
    "PCO2XXXX": "inorganicCarbon",         # pCO2
    "ALKYAAZX": "inorganicCarbon",         # Total alkalinity
    "TCO2AAZX": "inorganicCarbon",         # Dissolved inorganic carbon
    # Organic carbon
    "CORGZZZX": "dissolvedOrganicCarbon",
    "CORGPM01": "particulateMatter",       # Particulate organic carbon
    # Chlorophyll → ocean colour proxy (no separate chlorophyll EOV)
    "CPHLZZXX": "oceanColour",
    "CPHLPR01": "oceanColour",
    "CPHLMOD2": "oceanColour",             # Chlorophyll fluorescence (modelled)
    # Turbidity / suspended matter
    "TURBXXXX": "particulateMatter",
    "TSEDZZ01": "particulateMatter",
    # Wind → ocean surface stress proxy
    "EWSBZZ01": "oceanSurfaceStress",      # Wind speed
    "EWDAZZ01": "oceanSurfaceStress",      # Wind direction
    # Sea state — Beaufort wind force is the classic sea-state proxy
    "WMOCWFBF": "seaState",                # Beaufort wind force
    "WMOCSSXX": "seaState",                # Beaufort wind force / sea state
}


# Fallback mapping by free-text measurementType, case-insensitive substring match.
# Used when measurementTypeID is blank (common in older OBIS records). Order
# matters: more specific keys should precede broader ones. Surface-vs-subsurface
# for temperature/salinity is handled separately in _map_measurement_pair.
MEASUREMENT_TEXT_TO_EOV = {
    # Temperature / salinity — surface vs subsurface disambiguation below
    "temperature": "subSurfaceTemperature",
    "salinity": "subSurfaceSalinity",
    # Oxygen
    "dissolved oxygen": "oxygen",
    "oxygen": "oxygen",
    # Nutrients
    "nitrate": "nutrients",
    "nitrite": "nutrients",
    "ammonium": "nutrients",
    "phosphate": "nutrients",
    "silicate": "nutrients",
    "total nitrogen": "nutrients",
    "total phosphorus": "nutrients",
    # Inorganic carbon chemistry
    "ph": "inorganicCarbon",
    "pco2": "inorganicCarbon",
    "alkalinity": "inorganicCarbon",
    "dic": "inorganicCarbon",
    # Organic carbon
    "dissolved organic carbon": "dissolvedOrganicCarbon",
    "doc": "dissolvedOrganicCarbon",
    "particulate organic carbon": "particulateMatter",
    "poc": "particulateMatter",
    # Chlorophyll / ocean colour
    "chlorophyll": "oceanColour",
    # Particulates / turbidity
    "turbidity": "particulateMatter",
    "suspended": "particulateMatter",
    # Currents — default subsurface, surface rule below upgrades "surface current"
    "current velocity": "subSurfaceCurrents",
    "current speed": "subSurfaceCurrents",
    "current direction": "subSurfaceCurrents",
    "current strength": "subSurfaceCurrents",
    "tidal current": "surfaceCurrents",
    # Sea state — must precede wind keys so "Beaufort wind force (sea state)"
    # matches "beaufort" / "sea state" before falling through to "wind force".
    "sea state": "seaState",
    "beaufort": "seaState",
    "wave height": "seaState",
    "wave observation": "seaState",
    "wave exposure": "seaState",
    # Wind → ocean surface stress
    "wind speed": "oceanSurfaceStress",
    "wind direction": "oceanSurfaceStress",
    "wind force": "oceanSurfaceStress",
    # Sea ice
    "sea ice": "seaIce",
    "ice cover": "seaIce",
    "ice observation": "seaIce",
    # Ocean sound — acoustic detection / hydrophone data
    "hydrophone": "oceanSound",
    "acoustic detection": "oceanSound",
    "vocalization": "oceanSound",
    "call detected": "oceanSound",
    # Marine debris
    "marine debris": "marineDebris",
    "microplastic": "marineDebris",
    "plastic debris": "marineDebris",
    # Stable carbon isotopes
    "delta 13c": "stableCarbonIsotopes",
    "delta13c": "stableCarbonIsotopes",
    "d13c": "stableCarbonIsotopes",
    "δ13c": "stableCarbonIsotopes",
    # Nitrous oxide
    "nitrous oxide": "nitrousOxide",
    "n2o": "nitrousOxide",
    # Transient tracers
    "cfc-11": "transientTracers",
    "cfc-12": "transientTracers",
    "sf6": "transientTracers",
    "tritium": "transientTracers",
}


_P01_CODE_RE = re.compile(r"/([A-Z0-9]{8})/?$")


def _map_measurement_pair(m_type, m_type_id):
    """Map one OBIS eMoF (measurementType, measurementTypeID) pair to a CIOOS EOV.

    Priority:
      1. P01 code extracted from measurementTypeID URI (authoritative).
      2. Case-insensitive substring match on measurementType free text.
    Returns None when nothing matches. Temperature/salinity disambiguate
    between surface and subsurface based on whether 'surface' appears in
    the free text.
    """
    if m_type_id:
        match = _P01_CODE_RE.search(m_type_id)
        if match:
            eov = MEASUREMENT_P01_TO_EOV.get(match.group(1))
            if eov:
                return eov

    if not m_type:
        return None

    text = m_type.lower()
    has_surface = "surface" in text
    for key, eov in MEASUREMENT_TEXT_TO_EOV.items():
        # Word-boundary match — "ph" must not match "chlorophyll", "doc" must
        # not match "doctor", etc. Multi-word keys like "dissolved oxygen"
        # also need boundaries on either end of the phrase.
        if re.search(rf"\b{re.escape(key)}\b", text):
            if has_surface and eov == "subSurfaceTemperature":
                return "seaSurfaceTemperature"
            if has_surface and eov == "subSurfaceSalinity":
                return "seaSurfaceSalinity"
            if has_surface and eov == "subSurfaceCurrents":
                return "surfaceCurrents"
            return eov
    return None


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


def _has_emof_extension(extensions):
    """Return True if the dataset declares a MeasurementOrFact extension."""
    if not extensions:
        return False
    for ext in extensions:
        if not ext:
            continue
        if "measurementorfact" in str(ext).lower():
            return True
    return False


def fetch_eovs_from_measurements(dataset_id, extensions=None, sample_size=100):
    """Fetch OBIS eMoF measurements for a dataset and map them to CIOOS EOVs.

    Short-circuits when `extensions` is provided and does not list any
    MeasurementOrFact variant — the majority of OBIS datasets are pure
    occurrence records, so this keeps the extra HTTP call out of the hot path.
    Otherwise fetches a bounded sample of occurrences with mof=true and maps
    the distinct (measurementType, measurementTypeID) pairs via
    _map_measurement_pair.

    Args:
        dataset_id: OBIS dataset UUID.
        extensions: optional list from obis_data['extensions']. Used as a
            cheap gate to skip datasets without eMoF.
        sample_size: max occurrences to fetch. Each occurrence can carry
            several measurements, so 100 is usually enough to cover every
            distinct measurement type in a CTD-paired dataset.

    Returns:
        Sorted list of unique CIOOS EOV codes. [] on error, no MoF extension,
        or nothing mapped.
    """
    if not dataset_id:
        return []

    if extensions is not None and not _has_emof_extension(extensions):
        logger.debug(
            f"Dataset {dataset_id}: no MeasurementOrFact extension; skipping eMoF fetch"
        )
        return []

    try:
        response = requests.get(
            OBIS_OCCURRENCE_URL,
            params={
                "datasetid": dataset_id,
                "mof": "true",
                "size": sample_size,
                "fields": "measurementType,measurementTypeID",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as e:
        logger.warning(
            f"Failed to fetch eMoF measurements for {dataset_id}: {e}"
        )
        return []

    pairs = set()
    for occ in data.get("results", []) or []:
        for mof in occ.get("mof", []) or []:
            pairs.add((mof.get("measurementType", ""), mof.get("measurementTypeID", "")))

    eovs = set()
    unmapped = []
    for m_type, m_type_id in pairs:
        eov = _map_measurement_pair(m_type, m_type_id)
        if eov:
            eovs.add(eov)
        elif m_type or m_type_id:
            unmapped.append((m_type, m_type_id))

    if unmapped:
        logger.debug(
            f"Dataset {dataset_id}: unmapped eMoF measurements: {unmapped}"
        )

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
    # Derive EOVs from OBIS taxonomy (biology) and eMoF measurements
    # (physical/biogeochemical). The measurement path short-circuits on
    # datasets that don't declare a MeasurementOrFact extension.
    dataset_id = obis_data.get("id")
    extensions = obis_data.get("extensions") or []
    taxonomy_eovs = fetch_eovs_from_taxonomy(dataset_id)
    measurement_eovs = fetch_eovs_from_measurements(dataset_id, extensions=extensions)

    merged = set(taxonomy_eovs) | set(measurement_eovs)
    # When measurement EOVs landed, drop the taxonomy "other" fallback so
    # we don't emit misleading pairs like ["other", "seaSurfaceTemperature"].
    if measurement_eovs:
        merged.discard("other")
    cioos_data["eov"] = sorted(merged) if merged else ["other"]
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

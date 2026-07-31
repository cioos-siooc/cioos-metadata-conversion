import copy
import json
import re
from pathlib import Path

import requests
import yaml
from loguru import logger
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    import duckdb
except ImportError:  # pragma: no cover - duckdb is a declared dependency
    duckdb = None

OBIS_API_BASE = "https://api.obis.org/v3/dataset"
OBIS_FACET_URL = "https://api.obis.org/v3/facet"
OBIS_OCCURRENCE_URL = "https://api.obis.org/v3/occurrence"

# OBIS publishes one anonymous GeoParquet file per dataset. Reading the class /
# samplingProtocol / eMoF signals directly from this file is much faster and
# more accurate (full-dataset, not a sample) than the live API, which we keep
# as a fallback for datasets not yet present in the parquet store.
OBIS_PARQUET_URL_TEMPLATE = (
    "https://obis-open-data.s3.amazonaws.com/occurrence/{dataset_id}.parquet"
)
# Key of the ExtendedMeasurementOrFact extension inside the per-dataset
# occurrence parquet's `extensions` struct (a list of eMoF structs).
OBIS_EMOF_PARQUET_KEY = "http://rs.iobis.org/obis/terms/ExtendedMeasurementOrFact"

# Shared HTTP settings for every live OBIS API call (fallbacks + metadata).
_HTTP_USER_AGENT = "CIOOS-OBIS-Harvester/1.0 (+https://cioos.ca)"
_HTTP_TIMEOUT = 30

_SESSION = None
_DUCKDB_CON = None


def _get_session():
    """Return a shared requests.Session with retry/backoff and a User-Agent.

    Retries transient connection errors and 5xx responses so a momentary OBIS
    hiccup doesn't fail the harvest. A single session is reused across calls to
    benefit from connection pooling.
    """
    global _SESSION
    if _SESSION is None:
        session = requests.Session()
        retry = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=1.0,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({"User-Agent": _HTTP_USER_AGENT})
        _SESSION = session
    return _SESSION


def _get_duckdb_connection():
    """Return a lazily-created duckdb connection with httpfs loaded, or None.

    Returns None when duckdb is unavailable so callers cleanly fall back to the
    OBIS API.
    """
    global _DUCKDB_CON
    if duckdb is None:
        return None
    if _DUCKDB_CON is None:
        try:
            con = duckdb.connect()
            con.execute("INSTALL httpfs; LOAD httpfs;")
            _DUCKDB_CON = con
        except Exception as e:  # pragma: no cover - environment/setup failure
            logger.debug(f"duckdb/httpfs unavailable: {e}; using OBIS API")
            return None
    return _DUCKDB_CON


def _obis_parquet_url(dataset_id):
    return OBIS_PARQUET_URL_TEMPLATE.format(dataset_id=dataset_id)


def _read_parquet_class_counts(dataset_id):
    """Read class-level record counts from the per-dataset OBIS parquet.

    Returns a list of {"key": <class>, "records": <count>} dicts mirroring the
    /v3/facet?facets=class response shape, or None to signal the caller to fall
    back to the API (parquet missing/404, network error, missing column, or
    duckdb unavailable).
    """
    con = _get_duckdb_connection()
    if con is None:
        return None
    url = _obis_parquet_url(dataset_id)
    try:
        rows = con.execute(
            'SELECT interpreted."class" AS key, count(*) AS records '
            "FROM read_parquet(?) "
            'WHERE interpreted."class" IS NOT NULL '
            'GROUP BY interpreted."class"',
            [url],
        ).fetchall()
    except Exception as e:
        logger.debug(
            f"Parquet class read failed for {dataset_id}: {e}; falling back to API"
        )
        return None
    return [{"key": key, "records": records} for key, records in rows]


def _read_parquet_sampling_protocols(dataset_id):
    """Read the distinct samplingProtocol strings from the per-dataset parquet.

    Returns a set of samplingProtocol strings (full dataset, unioning the
    interpreted and source values), or None to signal a fall back to the API.
    """
    con = _get_duckdb_connection()
    if con is None:
        return None
    url = _obis_parquet_url(dataset_id)
    try:
        rows = con.execute(
            "SELECT DISTINCT interpreted.samplingProtocol AS ip, "
            "source.samplingProtocol AS sp "
            "FROM read_parquet(?)",
            [url],
        ).fetchall()
    except Exception as e:
        logger.debug(
            f"Parquet samplingProtocol read failed for {dataset_id}: {e}; "
            f"falling back to API"
        )
        return None
    protocols = set()
    for interpreted_proto, source_proto in rows:
        for proto in (interpreted_proto, source_proto):
            if proto:
                protocols.add(proto)
    return protocols


def _read_parquet_measurement_pairs(dataset_id):
    """Read distinct eMoF (measurementType, measurementTypeID) pairs.

    Extracts the pairs from the nested ExtendedMeasurementOrFact extension in
    the per-dataset parquet. Returns a set of (measurementType,
    measurementTypeID) string tuples (missing values normalised to "" to match
    the API path), or None to signal a fall back to the API.
    """
    con = _get_duckdb_connection()
    if con is None:
        return None
    url = _obis_parquet_url(dataset_id)
    try:
        rows = con.execute(
            "WITH e AS ("
            '  SELECT unnest(extensions."' + OBIS_EMOF_PARQUET_KEY + '") AS m '
            "  FROM read_parquet(?) "
            '  WHERE extensions."' + OBIS_EMOF_PARQUET_KEY + '" IS NOT NULL '
            '    AND len(extensions."' + OBIS_EMOF_PARQUET_KEY + '") > 0'
            ") "
            "SELECT DISTINCT "
            "  COALESCE(m.source.measurementType, '') AS mtype, "
            "  COALESCE(m.source.measurementTypeID, '') AS mtypeid "
            "FROM e",
            [url],
        ).fetchall()
    except Exception as e:
        logger.debug(
            f"Parquet eMoF read failed for {dataset_id}: {e}; falling back to API"
        )
        return None
    return {(mtype, mtypeid) for mtype, mtypeid in rows}

# ── Mapping data ────────────────────────────────────────────────────────────
# Every value this loader emits — the EOV vocabularies, the platform keyword
# table, the guard patterns, the audit-derived thresholds, the per-field record
# map and every literal string — lives in resources/obis_mapping.yaml. Only
# control flow lives in this module. See that file's header for editing rules.
#
# The derived names below are defined in ONE contiguous block on purpose. They
# have statement-order dependencies (the compiled platform patterns must come
# from the same expression as the table they mirror, and the keyword table is
# read further down at import time), and splitting them invites a stale half.

_MAPPING_PATH = Path(__file__).parent.parent / "resources" / "obis_mapping.yaml"

# Use libyaml where it is available: this module is imported on every CLI
# invocation and at pytest collection, and the pure-Python parser is an order of
# magnitude slower on a file this size. Our pyyaml pin does not guarantee the C
# extension on source-built platforms, hence the getattr.
_YamlBase = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


class ObisMappingError(RuntimeError):
    """resources/obis_mapping.yaml is missing, unparseable or inconsistent."""


class _UniqueKeyLoader(_YamlBase):
    """SafeLoader that rejects duplicate mapping keys.

    PyYAML silently keeps the last of a repeated key. The taxon table is 190
    hand-editable lines, which is exactly where a duplicated class name would
    hide, and there is no ruff step in CI to catch the equivalent in Python.
    """

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    None, None, f"duplicate key {key!r}", key_node.start_mark
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def _mapping_error(message):
    return ObisMappingError(f"{_MAPPING_PATH.resolve()}: {message}")


_REGEX_METACHARACTERS = set(r"\.^$*+?()[]{}|")

_RE_FLAGS = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "DOTALL": re.DOTALL,
    "VERBOSE": re.VERBOSE,
}


def _validate_obis_mapping(mapping):
    """Check the invariants the matching code relies on but cannot enforce.

    Cross-*file* vocabulary checks (every EOV present in eov.json, every
    platform label in platforms.json) deliberately live in the test suite
    instead: this module is imported at pytest collection, so raising here
    would turn a vocabulary drift into a collection error for every test file.
    """
    for path in (
        ("version",),
        ("fields",),
        ("templates", "associated_resources"),
        ("templates", "distribution"),
        ("contacts", "field_map"),
        ("eov", "from_taxon_class"),
        ("eov", "from_p01_code"),
        ("eov", "from_measurement_text"),
        ("eov", "guards"),
        ("eov", "gates"),
        ("platforms", "keywords"),
        ("roles", "obis_to_cioos"),
        ("roles", "valid_cioos_codes"),
    ):
        node = mapping
        for key in path:
            if not isinstance(node, dict) or key not in node:
                raise _mapping_error(f"missing required section {'.'.join(path)}")
            node = node[key]

    eov = mapping["eov"]

    # Taxon classes are matched exact-case against the OBIS facet values.
    for taxon_class in eov["from_taxon_class"]:
        if not taxon_class[:1].isupper():
            raise _mapping_error(
                f"taxon class {taxon_class!r} must keep its original capitalisation "
                f"— lookup is exact-case against the OBIS facet values"
            )

    # P01 codes are the 8-character upper-case tail of a NERC vocabulary URI.
    for code in eov["from_p01_code"]:
        if len(code) != 8 or not code.isupper():
            raise _mapping_error(
                f"P01 code {code!r} must be exactly 8 upper-case characters"
            )

    # Terms are lower-cased plain text: the matcher lowers the input and
    # re.escape()s the term, so an upper-case letter can never match and a
    # backslash would be escaped into a literal rather than acting as a regex.
    for entry in eov["from_measurement_text"]:
        term = entry["term"]
        if term != term.lower():
            raise _mapping_error(
                f"measurement term {term!r} must be lower-case — the matcher "
                f"lowers the input before comparing"
            )
        if _REGEX_METACHARACTERS & set(term):
            raise _mapping_error(
                f"measurement term {term!r} must be plain text, not a regex — "
                f"the matcher re.escape()s it and wraps it in word boundaries"
            )

    # Both gates index the taxon table, so a class named in one and missing
    # from the other silently disables that gate.
    gates = eov["gates"]
    taxon = eov["from_taxon_class"]
    missing = sorted(set(gates["benthic_indicator_classes"]) - set(taxon))
    if missing:
        raise _mapping_error(
            f"benthic indicator classes absent from from_taxon_class: {missing}"
        )
    mistyped = sorted(
        c
        for c in gates["zooplankton"]["core_classes"]
        if taxon.get(c) != "zooplanktonBiomassAndDiversity"
    )
    if mistyped:
        raise _mapping_error(
            f"core zooplankton classes that do not map to "
            f"zooplanktonBiomassAndDiversity: {mistyped}"
        )
    for name in ("cover", "zooplankton"):
        key = "min_fraction" if name == "cover" else "min_core_fraction"
        fraction = gates[name][key]
        if not isinstance(fraction, float) or not 0 < fraction < 1:
            raise _mapping_error(
                f"gates.{name}.{key} must be a fraction between 0 and 1, got {fraction!r}"
            )

    # map_obis_role_to_cioos iterates the codes for a case-insensitive retry
    # and returns the first hit, so two codes differing only by case would make
    # the result depend on set ordering.
    codes = mapping["roles"]["valid_cioos_codes"]
    if len({c.lower() for c in codes}) != len(codes):
        raise _mapping_error("roles.valid_cioos_codes contains case-duplicates")

    return mapping


def _load_obis_mapping():
    """Parse and validate resources/obis_mapping.yaml.

    Hard-fails rather than degrading. Without this file the loader cannot
    produce correct records, and a silent fallback would publish wrong metadata
    for every OBIS dataset. This matches the other resource loaders
    (pdc.py, firebase_to_cioos.py), which also raise.
    """
    try:
        with open(_MAPPING_PATH, encoding="utf-8") as fh:
            mapping = yaml.load(fh, Loader=_UniqueKeyLoader)
    except (OSError, yaml.YAMLError) as e:
        raise ObisMappingError(
            f"Could not load the OBIS mapping from {_MAPPING_PATH.resolve()}: {e}"
        ) from e
    if not isinstance(mapping, dict):
        raise _mapping_error("expected a mapping at the top level")
    return _validate_obis_mapping(mapping)


_MAPPING = _load_obis_mapping()

_EOV = _MAPPING["eov"]

# OBIS taxonomic class name -> CIOOS EOV. Exact-key, exact-case lookup, so the
# order of the file's entries does not matter here.
TAXON_CLASS_TO_EOV = _EOV["from_taxon_class"]

# BODC NERC P01 parameter code -> CIOOS EOV.
MEASUREMENT_P01_TO_EOV = _EOV["from_p01_code"]

# Free-text measurementType -> CIOOS EOV, used when measurementTypeID is blank.
# ORDER IS SEMANTIC: _map_measurement_pair scans in insertion order and returns
# on the first word-boundary match, which is why this is built from the file's
# ordered sequence and must never be sourced from a mapping.
MEASUREMENT_TEXT_TO_EOV = {
    entry["term"]: entry["eov"] for entry in _EOV["from_measurement_text"]
}

_GUARDS = _EOV["guards"]


def _compile_guard(name):
    """Compile a guard pattern with only the flags the file asks for.

    Flags are explicit per pattern and default to none so that an omission
    fails closed rather than silently widening a match.
    """
    spec = _GUARDS[name]
    flags = 0
    for flag in spec.get("flags") or []:
        if flag not in _RE_FLAGS:
            raise _mapping_error(f"unknown regex flag {flag!r} on guard {name!r}")
        flags |= _RE_FLAGS[flag]
    try:
        return re.compile(spec["pattern"], flags)
    except re.error as e:
        raise _mapping_error(f"guard {name!r} has an invalid pattern: {e}") from e


# Air/atmospheric temperature has no CIOOS EOV; these tokens suppress the
# temperature terms. Note _map_measurement_pair skips the hit and KEEPS
# SCANNING, so "Air temperature and salinity" still yields subSurfaceSalinity.
_ATMOSPHERIC_RE = _compile_guard("atmospheric")
_TEMPERATURE_EOVS = set(_GUARDS["atmospheric"]["suppresses"])

# Flow-cytometry "per cell" carbon metrics, not bulk water-column particulates.
_PER_CELL_RE = _compile_guard("per_cell")
_PER_CELL_P01 = set(_GUARDS["per_cell"]["p01_codes"])

# A non-pH carbonate parameter, which is what lifts a dataset into
# inorganicCarbon; see the aggregation in fetch_eovs_from_measurements.
_STRONG_IC_TEXT_RE = _compile_guard("strong_inorganic_carbon")
_STRONG_IC_P01 = set(_GUARDS["strong_inorganic_carbon"]["p01_codes"])

# Promotes the default subsurface mapping when the free text says "surface".
_SURFACE_UPGRADES = _GUARDS["surface_upgrades"]

# Parses the 8-char code out of a measurementTypeID URI. Stays in code because
# it is a parser rather than a mapping, and it is deliberately upper-case-only
# and flagless — a blanket IGNORECASE would let lower-case tails through.
_P01_CODE_RE = re.compile(r"/([A-Z0-9]{8})/?$")

# False-positive gates. Applied in fetch_eovs_from_taxonomy in this order:
# per-class cover fraction, then the zooplankton core gate, then the
# benthic-indicator gate — which can retract an EOV an earlier gate added.
_GATES = _EOV["gates"]
COVER_EOVS = set(_GATES["cover"]["eovs"])
COVER_EOV_MIN_FRACTION = _GATES["cover"]["min_fraction"]
CORE_ZOOPLANKTON_CLASSES = set(_GATES["zooplankton"]["core_classes"])
ZOO_MIN_CORE_FRACTION = _GATES["zooplankton"]["min_core_fraction"]
BENTHIC_INDICATOR_CLASSES = set(_GATES["benthic_indicator_classes"])

_ROLES = _MAPPING["roles"]
CIOOS_ROLE_CODES = set(_ROLES["valid_cioos_codes"])
OBIS_TO_CIOOS_ROLE = _ROLES["obis_to_cioos"]
_ROLE_FALLBACK = _ROLES["fallback"]

_PLATFORMS = _MAPPING["platforms"]

# ORDER IS SEMANTIC: _match_platform_keywords collects hits in table order and
# fetch_platforms_from_obis numbers them obis-platform-1, -2, … so reordering
# the file renames the emitted platform ids. Overlap between a generic and a
# specific pattern is resolved by _PLATFORM_SPECIFICITY, not by order.
_PLATFORM_KEYWORD_TABLE = [
    (entry["pattern"], entry["label"]) for entry in _PLATFORMS["keywords"]
]

# Derived from the same expression as the table above so the two cannot drift:
# this is what runtime matching reads, while the guardrail test reads the table.
_PLATFORM_KEYWORDS_COMPILED = [
    (re.compile(pattern, re.IGNORECASE), label)
    for pattern, label in _PLATFORM_KEYWORD_TABLE
]

# When the key label is matched, drop these labels from the result set.
_PLATFORM_SPECIFICITY = {
    label: set(drops) for label, drops in _PLATFORMS["specificity"].items()
}

_PLATFORM_RESOURCE_PATH = (
    Path(__file__).parent.parent / "resources" / _PLATFORMS["vocabulary_file"]
)


def _load_platform_vocab():
    """Return the set of valid CIOOS platform label_en strings.

    Hard-fails, like every other resource loader in the package. The previous
    soft fallback rebuilt the labels from _PLATFORM_KEYWORD_TABLE, which now
    comes from the mapping file — so on a packaging failure it would have
    validated the table against itself (vacuously true) while silently
    narrowing the vocabulary from 81 labels to 23, and that set filters real
    output in fetch_platforms_from_obis.
    """
    try:
        with open(_PLATFORM_RESOURCE_PATH, encoding="utf-8") as fh:
            return {entry["label_en"] for entry in json.load(fh)}
    except (OSError, json.JSONDecodeError, KeyError) as e:
        raise ObisMappingError(
            f"Could not load the CIOOS platform vocabulary from "
            f"{_PLATFORM_RESOURCE_PATH.resolve()}: {e}"
        ) from e


VALID_PLATFORM_LABELS = _load_platform_vocab()


def _is_strong_inorganic_carbon(m_type, m_type_id):
    """True when an eMoF pair measures a non-pH carbonate parameter."""
    if m_type_id:
        match = _P01_CODE_RE.search(m_type_id)
        if match and match.group(1) in _STRONG_IC_P01:
            return True
    if m_type and _STRONG_IC_TEXT_RE.search(m_type):
        return True
    return False


def _map_measurement_pair(m_type, m_type_id):
    """Map one OBIS eMoF (measurementType, measurementTypeID) pair to a CIOOS EOV.

    Priority:
      1. P01 code extracted from measurementTypeID URI (authoritative).
      2. Case-insensitive substring match on measurementType free text.
    Returns None when nothing matches. Temperature/salinity disambiguate
    between surface and subsurface based on whether 'surface' appears in
    the free text. Atmospheric/air temperature is suppressed.
    """
    # Flow-cytometry "per cell" metrics describe phytoplankton carbon
    # content per individual, not bulk particulates. Suppress before any
    # mapping attempt so both the P01 and text paths skip these.
    p01_code = None
    if m_type_id:
        match = _P01_CODE_RE.search(m_type_id)
        if match:
            p01_code = match.group(1)
    is_per_cell = (p01_code in _PER_CELL_P01) or (
        bool(m_type) and bool(_PER_CELL_RE.search(m_type))
    )
    if is_per_cell:
        return None

    if p01_code:
        eov = MEASUREMENT_P01_TO_EOV.get(p01_code)
        if eov:
            return eov

    if not m_type:
        return None

    text = m_type.lower()
    has_surface = "surface" in text
    is_atmospheric = bool(_ATMOSPHERIC_RE.search(text))
    # Insertion order is the file's order and it is semantic: first match wins,
    # so specific terms precede broader ones.
    for term, eov in MEASUREMENT_TEXT_TO_EOV.items():
        # Word-boundary match — "ph" must not match "chlorophyll", "doc" must
        # not match "doctor", etc. Multi-word terms like "dissolved oxygen"
        # also need boundaries on either end of the phrase.
        if re.search(rf"\b{re.escape(term)}\b", text):
            if is_atmospheric and eov in _TEMPERATURE_EOVS:
                # Air temperature — no matching CIOOS EOV. `continue`, not
                # `return`: a later term may still apply, which is why
                # "Air temperature and salinity" yields subSurfaceSalinity.
                continue
            if has_surface and eov in _SURFACE_UPGRADES:
                return _SURFACE_UPGRADES[eov]
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



def fetch_eovs_from_taxonomy(dataset_id):
    """Fetch taxonomic classes for an OBIS dataset and map them to CIOOS EOVs.

    Calls the OBIS facet API to get class-level taxonomy, then maps each class
    to a CIOOS Essential Ocean Variable using TAXON_CLASS_TO_EOV.
    Returns a deduplicated list of EOV codes. Cover-type EOVs are subject to
    a record-fraction threshold to suppress by-catch false positives.
    """
    if not dataset_id:
        return []

    # Parquet-first: read full-dataset class counts locally. On any miss/error
    # fall back to the live OBIS facet API. The mapping/gating below is
    # identical regardless of the acquisition source.
    classes = _read_parquet_class_counts(dataset_id)
    if classes is None:
        try:
            response = _get_session().get(
                OBIS_FACET_URL,
                params={"datasetid": dataset_id, "facets": "class"},
                timeout=_HTTP_TIMEOUT,
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

    total_records = sum(entry.get("records", 0) or 0 for entry in classes)
    eovs = set()
    unmapped = []
    for entry in classes:
        taxon_class = entry.get("key", "")
        eov = TAXON_CLASS_TO_EOV.get(taxon_class)
        if not eov:
            unmapped.append(taxon_class)
            continue
        records = entry.get("records", 0) or 0
        if (
            eov in COVER_EOVS
            and total_records > 0
            and records / total_records < COVER_EOV_MIN_FRACTION
        ):
            logger.debug(
                f"Dataset {dataset_id}: class {taxon_class} "
                f"({records}/{total_records} = {records / total_records:.2%}) "
                f"below cover-EOV threshold {COVER_EOV_MIN_FRACTION:.0%}; "
                f"skipping {eov}"
            )
            continue
        eovs.add(eov)

    if unmapped:
        logger.info(
            f"Dataset {dataset_id}: unmapped taxonomic classes: {unmapped}"
        )

    # Zooplankton gate: require core planktonic classes (Copepoda, Ostracoda,
    # Sagittoidea, etc.) to clear ZOO_MIN_CORE_FRACTION. Gelatinous bycatch
    # alone (Scyphozoa, Hydrozoa) is not enough.
    if "zooplanktonBiomassAndDiversity" in eovs and total_records > 0:
        core_records = sum(
            (entry.get("records", 0) or 0)
            for entry in classes
            if entry.get("key") in CORE_ZOOPLANKTON_CLASSES
        )
        if core_records / total_records < ZOO_MIN_CORE_FRACTION:
            logger.debug(
                f"Dataset {dataset_id}: core zooplankton classes "
                f"({core_records}/{total_records} = "
                f"{core_records / total_records:.2%}) below threshold "
                f"{ZOO_MIN_CORE_FRACTION:.0%}; dropping "
                f"zooplanktonBiomassAndDiversity"
            )
            eovs.discard("zooplanktonBiomassAndDiversity")

    # Invertebrate gate (plankton-net refinement): if zooplankton is emitted,
    # require a benthic-indicator class for invertebrate to also emit. In a
    # plankton net, Malacostraca/Gastropoda/Polychaeta/Bivalvia/Cephalopoda
    # are usually larval or pelagic forms already captured under zooplankton,
    # not a separate benthic community. A visible benthic-sessile class
    # (echinoderm, sponge, ascidian, barnacle, etc.) is what lifts the
    # dataset into "also sampled epifauna" territory.
    if (
        "zooplanktonBiomassAndDiversity" in eovs
        and "invertebrateAbundanceAndDistribution" in eovs
    ):
        has_benthic = any(
            entry.get("key") in BENTHIC_INDICATOR_CLASSES
            and (entry.get("records", 0) or 0) > 0
            for entry in classes
        )
        if not has_benthic:
            logger.debug(
                f"Dataset {dataset_id}: zooplankton emitted but no benthic "
                f"indicator class present; dropping "
                f"invertebrateAbundanceAndDistribution"
            )
            eovs.discard("invertebrateAbundanceAndDistribution")

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

    # Parquet-first: the eMoF extension is present in the per-dataset parquet,
    # so extract distinct (measurementType, measurementTypeID) pairs locally.
    # On any miss/error fall back to the live occurrence API. The mapping below
    # is identical regardless of the acquisition source.
    pairs = _read_parquet_measurement_pairs(dataset_id)
    if pairs is None:
        try:
            response = _get_session().get(
                OBIS_OCCURRENCE_URL,
                params={
                    "datasetid": dataset_id,
                    "mof": "true",
                    "size": sample_size,
                    "fields": "measurementType,measurementTypeID",
                },
                timeout=_HTTP_TIMEOUT,
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
    has_strong_inorganic_carbon = False
    for m_type, m_type_id in pairs:
        eov = _map_measurement_pair(m_type, m_type_id)
        if eov:
            eovs.add(eov)
        elif m_type or m_type_id:
            unmapped.append((m_type, m_type_id))
        if _is_strong_inorganic_carbon(m_type, m_type_id):
            has_strong_inorganic_carbon = True

    # Drop inorganicCarbon when only pH was measured — CIOOS curator
    # convention treats lone pH as water quality, not carbonate chemistry.
    if "inorganicCarbon" in eovs and not has_strong_inorganic_carbon:
        eovs.discard("inorganicCarbon")
        logger.debug(
            f"Dataset {dataset_id}: dropping inorganicCarbon (pH-only, no "
            f"alkalinity/DIC/pCO2)"
        )

    if unmapped:
        logger.debug(
            f"Dataset {dataset_id}: unmapped eMoF measurements: {unmapped}"
        )

    return sorted(eovs)


# ── Platform inference ──────────────────────────────────────────────────────
# OBIS exposes no structured platform field; DwC samplingProtocol (free text on
# occurrence records) is the only reliable signal. We read the distinct protocol
# strings, match them against the keyword table in obis_mapping.yaml, and emit
# values from the CIOOS form vocabulary. Conservative on purpose: when nothing
# matches we emit no platform and the loader sets noPlatform=True.


def _match_platform_keywords(text):
    """Return CIOOS platform label_en values matched in text.

    Case-insensitive. Deduplicated. Applies the specificity overrides so
    generic labels are dropped when a more specific label also hit.
    """
    if not text:
        return []
    hits = []
    for regex, label in _PLATFORM_KEYWORDS_COMPILED:
        if label in hits:
            continue
        if regex.search(text):
            hits.append(label)

    drop = set()
    for specific, generics in _PLATFORM_SPECIFICITY.items():
        if specific in hits:
            drop.update(generics)

    return [h for h in hits if h not in drop]


def fetch_platforms_from_obis(dataset_id, sample_size=100):
    """Sample OBIS occurrences and infer CIOOS platform types.

    Reads samplingProtocol from a bounded slice of /v3/occurrence records,
    matches it against _PLATFORM_KEYWORD_TABLE, and returns a list of
    {"id", "type", "description"} dicts whose "type" is a label_en from
    the bundled CIOOS platform vocabulary. Returns [] when nothing was
    sampled, no samplingProtocol carried recognisable keywords, or the
    API call failed — callers should then set noPlatform=True.

    Args:
        dataset_id: OBIS dataset UUID.
        sample_size: max occurrences to fetch. 100 is usually enough to
            cover the distinct samplingProtocol strings used in a dataset.
    """
    if not dataset_id:
        return []

    # Parquet-first: read the distinct samplingProtocol strings from the full
    # dataset. On any miss/error fall back to the live occurrence API sample.
    # The keyword matching below is identical regardless of the source.
    protocols = _read_parquet_sampling_protocols(dataset_id)
    if protocols is None:
        try:
            response = _get_session().get(
                OBIS_OCCURRENCE_URL,
                params={
                    "datasetid": dataset_id,
                    "size": sample_size,
                    "fields": "samplingProtocol,basisOfRecord",
                },
                timeout=_HTTP_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as e:
            logger.warning(
                f"Failed to fetch occurrences for platform inference {dataset_id}: {e}"
            )
            return []

        protocols = set()
        for occ in data.get("results", []) or []:
            proto = occ.get("samplingProtocol")
            if proto:
                protocols.add(proto)

    matched_labels = []
    for proto in protocols:
        for label in _match_platform_keywords(proto):
            if label in matched_labels:
                continue
            if label not in VALID_PLATFORM_LABELS:
                # Belt-and-braces: the keyword table is authored against the
                # vendored vocab, but flag drift instead of emitting garbage.
                logger.warning(
                    f"Platform label '{label}' is not in the CIOOS "
                    f"vocabulary; skipping (dataset {dataset_id})"
                )
                continue
            matched_labels.append(label)

    return [
        {
            "id": f"obis-platform-{i + 1}",
            "type": label,
            "description": {"en": "", "fr": ""},
        }
        for i, label in enumerate(matched_labels)
    ]


def map_obis_role_to_cioos(obis_role):
    """Map an OBIS EML role/type to a valid CIOOS ISO 19115 role code.

    Checks in order:
    1. If the role is already a valid CIOOS role code, use it as-is.
    2. If it matches a known OBIS EML construct, map it.
    3. Otherwise fall back to the configured default.
    """
    if not obis_role:
        return _ROLE_FALLBACK

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

    logger.warning(
        f"Unknown OBIS role '{obis_role}', falling back to '{_ROLE_FALLBACK}'"
    )
    return _ROLE_FALLBACK


def convert_contacts(obis_contacts):
    """Map OBIS contact entries to CIOOS contacts using the `contacts` section."""
    cioos_contacts = []
    if not obis_contacts:
        return cioos_contacts

    spec = _MAPPING["contacts"]
    field_map = spec["field_map"]
    optional_field_map = spec.get("optional_field_map") or {}

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

        # Assembled in the emitted key order rather than by iterating field_map,
        # because several downstream consumers read the record positionally when
        # serialising it.
        cioos_contact = {
            field_map["givenname"]: given_name,
            field_map["surname"]: last_name,
            "indName": full_name,
            "indOrcid": spec["constants"]["indOrcid"],
            "inCitation": spec["constants"]["inCitation"],
            "role": [map_obis_role_to_cioos(contact.get("type", ""))],
            field_map["organization"]: org_name,
            "orgAddress": spec["constants"]["orgAddress"],
            "orgCity": spec["constants"]["orgCity"],
            "orgCountry": spec["constants"]["orgCountry"],
            "orgRor": spec["constants"]["orgRor"],
            field_map["url"]: contact.get("url", ""),
        }

        # Emitted only when OBIS actually supplied them, so scrub_dict does not
        # have to strip an empty key back out.
        for obis_field, cioos_field in optional_field_map.items():
            if contact.get(obis_field):
                cioos_contact[cioos_field] = contact.get(obis_field)

        cioos_contacts.append(cioos_contact)

    return cioos_contacts


# ── Record assembly ─────────────────────────────────────────────────────────
# map_obis_to_cioos walks the `fields` section of obis_mapping.yaml in file
# order — which is also the emitted key order — and dispatches each entry to
# one of three kinds: a constant, a `source` read (optionally through a named
# transform), or a named handler that owns some real control flow.
#
# The handlers below hold the conditionals, fallback chains and network calls.
# They take their literal strings from the file's `templates` section, so the
# file stays the single place to look for "where does this value come from"
# without pretending to be executable logic.


def _trim_date(value):
    """OBIS timestamp -> `…Z`, dropping fractional seconds.

    Empty in, empty out: without the guard an absent date would become the
    literal string "Z", which survives scrub_dict and reaches the XML.
    """
    return value.split(".")[0] + "Z" if value else ""


def _get_path(data, path):
    """Read a dotted path (`feed.url`), returning None if any hop is missing."""
    node = data
    for key in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


_TRANSFORMS = {
    "add_fr": add_fr,
    "iso_date": _trim_date,
}


def _h_dataset_identifier(obis_data, spec, record):
    """`doi`, falling back to `citation_id` only when that is itself a DOI."""
    doi = obis_data.get("doi") or ""
    if not doi:
        citation_id = obis_data.get("citation_id") or ""
        if "doi.org/" in citation_id or citation_id.startswith("10."):
            doi = citation_id
    return doi


def _h_first_present(obis_data, spec, record):
    """First non-empty of `source`, through the transform if one is named."""
    transform = _TRANSFORMS[spec["transform"]] if spec.get("transform") else None
    value = ""
    for key in spec["source"]:
        value = obis_data.get(key) or ""
        if value:
            break
    return transform(value) if transform else value


def _h_keywords(obis_data, spec, record):
    """OBIS keywords may be dicts with a `keyword` key, or bare strings."""
    keywords = []
    for keyword in obis_data.get(spec["source"]) or []:
        if isinstance(keyword, dict):
            keywords.append(keyword.get("keyword"))
        elif isinstance(keyword, str):
            keywords.append(keyword)
    # OBIS only provides English keywords. Reused as the French placeholders
    # since most are scientific terms or proper nouns that don't change.
    return {"en": keywords, "fr": keywords}


def _template_values(obis_data, entry):
    """Resolve one template entry's `when` condition to the values it emits."""
    when = entry["when"]
    if when == "url":
        return [obis_data["url"]] if obis_data.get("url") else []
    if when == "archive_differs_from_url":
        archive = obis_data.get("archive")
        return [archive] if archive and archive != obis_data.get("url") else []
    if when == "url_differs_from_archive":
        url = obis_data.get("url")
        return [url] if url and url != obis_data.get("archive") else []
    if when == "archive":
        return [obis_data["archive"]] if obis_data.get("archive") else []
    if when == "feed_url":
        feed_url = _get_path(obis_data, entry["source"])
        return [feed_url] if feed_url else []
    if when == "each_tag":
        return list(obis_data.get(entry["source"]) or [])
    raise _mapping_error(f"unknown template condition {when!r}")


def _h_associated_resources(obis_data, spec, record):
    template = _MAPPING["templates"]["associated_resources"]
    defaults = template["defaults"]
    resources = []
    for entry in template["entries"]:
        for value in _template_values(obis_data, entry):
            resources.append(
                {
                    "association_type": entry["association_type"],
                    "association_type_iso": defaults["association_type_iso"],
                    "authority": defaults["authority"],
                    "code": value,
                    "title": entry["title"],
                }
            )
    return resources


def _h_distribution(obis_data, spec, record):
    template = _MAPPING["templates"]["distribution"]
    wrapped = set(template.get("add_fr_fields") or [])
    distribution = []
    for entry in template["entries"]:
        for value in _template_values(obis_data, entry):
            distribution.append(
                {
                    "name": add_fr(entry["name"]) if "name" in wrapped else entry["name"],
                    "url": value,
                    "description": (
                        add_fr(entry["description"])
                        if "description" in wrapped
                        else entry["description"]
                    ),
                }
            )
    return distribution


def _h_contacts(obis_data, spec, record):
    contacts = convert_contacts(obis_data.get(spec["source"]))

    # The metadata-xml template only emits mdb:contact (required by ISO 19115-3)
    # for contacts with the "custodian" role.  When the OBIS metadataProvider
    # entry has no name/org it gets dropped by convert_contacts(), leaving no
    # custodian.  Promote the first available contact so the XML stays valid.
    if _MAPPING["contacts"].get("promote_custodian"):
        has_custodian = any("custodian" in c.get("role", []) for c in contacts)
        if not has_custodian and contacts:
            contacts[0]["role"].append("custodian")
            logger.info(
                "No custodian contact found; promoted first contact to custodian"
            )
    return contacts


def _h_extent_to_map(obis_data, spec, record):
    return parse_extent_to_map(obis_data.get(spec["source"]))


def _h_eov_from_signals(obis_data, spec, record):
    """Merge the taxonomy and eMoF EOV signals.

    Both paths use controlled-vocabulary signals only — taxonomy class names and
    eMoF P01 codes / parameter labels.  Abstract / title / keyword NLP is
    intentionally out of scope here; a separate AI-backed tool handles
    abstract-based EOV inference, and mixing the two produces inconsistent
    tagging.
    """
    dataset_id = obis_data.get("id")
    extensions = obis_data.get("extensions") or []
    taxonomy_eovs = fetch_eovs_from_taxonomy(dataset_id)
    measurement_eovs = fetch_eovs_from_measurements(dataset_id, extensions=extensions)

    merged = set(taxonomy_eovs) | set(measurement_eovs)
    # When measurement EOVs landed, drop the taxonomy "other" fallback so
    # we don't emit misleading pairs like ["other", "seaSurfaceTemperature"].
    if measurement_eovs:
        merged.discard("other")
    return sorted(merged) if merged else ["other"]


def _h_platforms(obis_data, spec, record):
    return fetch_platforms_from_obis(obis_data.get(spec["source"]))


def _h_no_platform(obis_data, spec, record):
    """True when nothing matched, so firebase_to_cioos skips the platform path
    and the XML omits the section.  Kept a real bool."""
    return not record["platforms"]


def _h_same_as_date_published(obis_data, spec, record):
    return record["datePublished"]


_HANDLERS = {
    "dataset_identifier": _h_dataset_identifier,
    "first_present": _h_first_present,
    "keywords": _h_keywords,
    "associated_resources": _h_associated_resources,
    "distribution": _h_distribution,
    "contacts": _h_contacts,
    "extent_to_map": _h_extent_to_map,
    "eov_from_signals": _h_eov_from_signals,
    "platforms": _h_platforms,
    "no_platform": _h_no_platform,
    "same_as_date_published": _h_same_as_date_published,
}


def _validate_field_specs():
    """Check every `fields` entry is well-formed and names something real.

    Runs at import, once the registries above exist, so a renamed transform or
    handler fails loudly at startup instead of silently emitting a wrong value.
    """
    for name, spec in _MAPPING["fields"].items():
        if not isinstance(spec, dict):
            raise _mapping_error(f"fields.{name} must be a mapping, got {spec!r}")
        kinds = {"constant", "source", "handler"} & set(spec)
        if not kinds:
            raise _mapping_error(
                f"fields.{name} needs one of constant / source / handler"
            )
        transform = spec.get("transform")
        if transform is not None and transform not in _TRANSFORMS:
            raise _mapping_error(
                f"fields.{name} names unknown transform {transform!r}; "
                f"known: {sorted(_TRANSFORMS)}"
            )
        handler = spec.get("handler")
        if handler is not None and handler not in _HANDLERS:
            raise _mapping_error(
                f"fields.{name} names unknown handler {handler!r}; "
                f"known: {sorted(_HANDLERS)}"
            )


_validate_field_specs()


def map_obis_to_cioos(obis_data):
    """Build a CIOOS (firebase-shaped) record from one OBIS dataset response.

    Driven by the `fields` section of obis_mapping.yaml: that file is where the
    provenance of every emitted key lives, and its order is the emitted key
    order.  See the module comment above for the three entry kinds.
    """
    cioos_data = {}
    for name, spec in _MAPPING["fields"].items():
        if "handler" in spec:
            cioos_data[name] = _HANDLERS[spec["handler"]](obis_data, spec, cioos_data)
            continue

        if "constant" in spec:
            value = spec["constant"]
            # Copy so a caller mutating a list/dict value can't corrupt the
            # mapping for every subsequent record.
            if isinstance(value, (list, dict)):
                value = copy.deepcopy(value)
        else:
            value = obis_data.get(spec["source"], spec.get("default", ""))

        transform = spec.get("transform")
        cioos_data[name] = _TRANSFORMS[transform](value) if transform else value

    return cioos_data


def retrieve_obis_metadata(dataset_id: str):
    """
    Retrieve metadata for an OBIS dataset by ID.
    """
    url = f"{OBIS_API_BASE}/{dataset_id}"
    logger.info(f"Retrieving OBIS metadata from: {url}")

    response = _get_session().get(url, timeout=_HTTP_TIMEOUT)
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

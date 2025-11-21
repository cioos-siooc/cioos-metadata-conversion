# CIOOS Form to CIOOS Intermediate Format Mapping

This document describes how metadata fields from the CIOOS Form (Firebase-based) are transformed into the CIOOS intermediate format, which serves as the canonical representation for all subsequent conversions (ISO 19115-3, DataCite, ERDDAP/ACDD, etc.).

## Overview

The CIOOS Form is a web-based metadata entry interface that stores data in Firebase. The conversion to the intermediate CIOOS format is handled by the `record_json_to_yaml()` function in [firebase_to_cioos.py](cioos_metadata_conversion/firebase_to_cioos.py:143).

### Transformation Purpose

The CIOOS intermediate format:
- Provides a clean, consistent structure for metadata
- Removes empty values and normalizes data types
- Performs coordinate transformations and data enrichment
- Serves as the source for all output format conversions

### Key Processing Steps

1. **Field Restructuring**: Flatten and reorganize Firebase structure
2. **Data Enrichment**: Resolve license codes, translate EOVs, format taxa
3. **Coordinate Transformation**: Convert lat,long to long,lat format
4. **Date Normalization**: Extract dates from datetime strings
5. **Contact Processing**: Restructure contact information and add missing distributors
6. **Empty Value Removal**: Scrub all empty strings, nulls, and empty objects

## Top-Level Structure

The CIOOS intermediate format has four main sections:

```yaml
metadata:      # Metadata about the metadata
spatial:       # Geographic and vertical extent
identification: # Resource identification and description
contact:       # Responsible parties
distribution:  # Distribution/access information
platform:      # Platform and instrument information (optional)
instruments:   # Standalone instruments (optional)
```

## Field Mappings

### Metadata Section

#### metadata.naming_authority
**CIOOS Form Source**: N/A
**Value**: "ca.cioos"
**Processing**: Hardcoded value
**Description**: Authority responsible for creating the identifier

#### metadata.identifier
**CIOOS Form Source**: `identifier`
**Type**: String (UUID)
**Example**: "9d1a8fe4-2675-4e34-8b65-16459736535a"
**Description**: Unique identifier for the metadata record

#### metadata.language
**CIOOS Form Source**: `language`
**Type**: String
**Values**: "en" | "fr"
**Description**: Primary language of the metadata

#### metadata.language_alternate
**CIOOS Form Source**: Derived (opposite of `language`)
**Processing**: Not explicitly set but inferred
**Description**: Alternate language for bilingual metadata

#### metadata.maintenance_note
**CIOOS Form Source**: Constructed from `userID`, `recordID`, `language`, `region`
**Format**: "Generated from https://cioos-siooc.github.io/metadata-entry-form#/{language}/{region}/{userID}/{recordID}"
**Example**: "Generated from https://cioos-siooc.github.io/metadata-entry-form#/fr/stlaurent/Ea7wMTBNmvWBD2n1oSc8X0KQi9z1/-OTS9E-8LKZrL_Yuggg0"
**Description**: Link back to the form where metadata was created

#### metadata.use_constraints
**CIOOS Form Source**: Multiple sources
**Structure**:
```yaml
use_constraints:
  limitations:
    en: "..."
    fr: "..."
  licence:
    title:
      en: "..."
    url: "..."
    code: "..."
```

##### metadata.use_constraints.limitations
**CIOOS Form Source**: `limitations`
**Type**: Bilingual text or string
**Default**: "None" if not provided

##### metadata.use_constraints.licence
**CIOOS Form Source**: `license` (code like "CC-BY-4.0")
**Processing**: Resolved via `licenses.json` lookup
**Structure**:
- `title.en`: Full license name
- `url`: License URL
- `code`: License code
**Example**:
```yaml
licence:
  title:
    en: "Creative Commons Attribution 4.0 Attribution"
  url: "https://creativecommons.org/licenses/by/4.0"
  code: "CC-BY-4.0"
```

#### metadata.comment
**CIOOS Form Source**: `comment`
**Type**: Bilingual text or string

#### metadata.history
**CIOOS Form Source**: `history` array
**Type**: Array of lineage objects
**Structure**: Each history item includes:
- `statement`: Bilingual text
- `scope`: Scope code (e.g., "Dataset")
- `scopeIso`: ISO scope code
- `additionalDocumentation`: Array of citation objects
- `source`: Array of source objects
- `processingStep`: Array of processing step objects

**Passed through**: Structure preserved from form

#### metadata.dates
**CIOOS Form Source**: Multiple date fields
**Structure**:
```yaml
dates:
  revision: "2025-06-25T17:24:48.469Z"
  publication: "2025-01-01"
```

##### metadata.dates.revision
**CIOOS Form Source**: `created`
**Type**: ISO 8601 datetime string
**Description**: Last modification timestamp

##### metadata.dates.publication
**CIOOS Form Source**: `timeFirstPublished`
**Processing**: `date_from_datetime_str()` - extracts date part (first 10 characters)
**Format**: "YYYY-MM-DD" or empty
**Description**: First publication date

#### metadata.scope
**CIOOS Form Source**: `metadataScopeIso` OR `metadataScope`
**Type**: String
**Values**: "dataset", "series", "service", etc.
**Description**: Type of resource being described

### Spatial Section

#### spatial.bbox
**CIOOS Form Source**: `map.west`, `map.south`, `map.east`, `map.north`
**Type**: Array of 4 floats `[west, south, east, north]`
**Condition**: Only if `map.polygon` is NOT present
**Processing**: Convert string values to floats
**Example**: `[-66.97, 49.91, -66.77, 50.04]`

#### spatial.polygon
**CIOOS Form Source**: `map.polygon`
**Type**: String (space-separated coordinate pairs)
**Processing**: `fix_lat_long_polygon()` - transforms from "lat,long" to "long,lat"
**Format**: "long1,lat1 long2,lat2 long3,lat3 ..."
**Example Input**: "50.03,-66.84 50.01,-66.93 49.97,-66.97"
**Example Output**: "-66.84,50.03 -66.93,50.01 -66.97,49.97"
**Note**: Polygon takes precedence over bbox if both exist

#### spatial.vertical
**CIOOS Form Source**: `verticalExtentMin`, `verticalExtentMax`, `noVerticalExtent`
**Type**: Array of 2 floats `[min, max]`
**Processing**:
- If `noVerticalExtent` is true: `[0, 0]`
- Otherwise: `[float(verticalExtentMin), float(verticalExtentMax)]`

#### spatial.vertical_positive
**CIOOS Form Source**: `verticalExtentDirection` or `noVerticalExtent`
**Type**: String
**Values**: "heightPositive" | "depthPositive"
**Default**: "heightPositive" if `noVerticalExtent` is true

#### spatial.vertical_epsg
**CIOOS Form Source**: `verticalExtentEPSG` or `noVerticalExtent`
**Processing**: Resolved via `epsg.json` lookup
**Default**: EPSG 5829 if `noVerticalExtent` is true
**Structure**: Full EPSG definition object

#### spatial.description
**CIOOS Form Source**: `map.description`
**Type**: Bilingual text
**Example**:
```yaml
description:
  en: "Port-Cartier"
  fr: "Port-Cartier"
```

#### spatial.descriptionIdentifier
**CIOOS Form Source**: `map.descriptionIdentifier`
**Type**: String (UUID)
**Description**: Unique identifier for the geographic description

### Identification Section

#### identification.title
**CIOOS Form Source**: `title`
**Type**: Bilingual text
**Example**:
```yaml
title:
  en: "DCBA"
  fr: "ABCD"
  translations:
    en:
      message: "text translated using..."
      verified: false
```

#### identification.identifier
**CIOOS Form Source**: `datasetIdentifier`
**Type**: String (usually DOI)
**Example**: "https://doi.org/10.26071/mxtr-gp72"
**Description**: Persistent identifier for the dataset

#### identification.abstract
**CIOOS Form Source**: `abstract`
**Type**: Bilingual text
**Example**:
```yaml
abstract:
  en: "Zyxwvutsrqponmi kjihgfedcba..."
  fr: "Abcdefghijk lmnopqrstuvwxyz..."
```

#### identification.associated_resources
**CIOOS Form Source**: `associated_resources`
**Type**: Array of resource objects
**Structure**: Each resource includes:
- `association_type`: DataCite-style type (e.g., "IsReferencedBy", "IsCitedBy")
- `association_type_iso`: ISO-style type (e.g., "crossReference")
- `authority`: Authority type ("DOI", "URL")
- `code`: The identifier/URL
- `title`: Bilingual title
**Passed through**: Structure preserved from form

#### identification.dates
**CIOOS Form Source**: Multiple date fields
**Structure**:
```yaml
dates:
  creation: "2025-01-01"
  publication: "2025-01-01"
  revision: "2025-01-01"
```

##### identification.dates.creation
**CIOOS Form Source**: `dateStart`
**Processing**: `date_from_datetime_str()` - extracts date part
**Description**: Dataset creation date

##### identification.dates.publication
**CIOOS Form Source**: `datePublished`
**Processing**: `date_from_datetime_str()` - extracts date part
**Description**: Dataset publication date

##### identification.dates.revision
**CIOOS Form Source**: `dateRevised`
**Processing**: `date_from_datetime_str()` - extracts date part
**Description**: Dataset revision date

#### identification.keywords
**CIOOS Form Source**: `keywords`, `eov`, `taxa`
**Structure**:
```yaml
keywords:
  default:
    en: ["keyword1", "keyword2"]
    fr: ["mot-clé1", "mot-clé2"]
  eov:
    en: ["oxygen", "nutrients"]
    fr: ["Oxygène", "Nutriments"]
  taxa:
    en: ["Animalia", "Mollusca"]
    fr: ["Animalia", "Mollusca"]
```

##### identification.keywords.default
**CIOOS Form Source**: `keywords.en` and `keywords.fr`
**Processing**: `strip_keywords()` - removes leading/trailing whitespace
**Type**: Bilingual keyword lists

##### identification.keywords.eov
**CIOOS Form Source**: `eov` array
**Processing**:
- English: Direct from form
- French: `eovs_to_fr()` - translates using `eov.json` lookup
**Example**: "invertebrateAbundanceAndDistribution" → "Abondance et distribution d'invertébrés"

##### identification.keywords.taxa
**CIOOS Form Source**: `taxa` array (GBIF taxonomy objects)
**Processing**: `format_taxa()` - flattens taxonomic hierarchy
**Logic**:
- Extracts: kingdom, phylum, class, order, family, genus, species
- Joins non-null values with commas
- Splits back into array of individual taxa names
**Example Input**:
```json
{
  "kingdom": "Animalia",
  "phylum": "Mollusca",
  "class": "Gastropoda"
}
```
**Example Output**: `["Animalia", "Mollusca", "Gastropoda"]`

**Removal**: If `noTaxa` is true, the entire `taxa` key is removed

#### identification.temporal_begin
**CIOOS Form Source**: `dateStart`
**Type**: ISO 8601 datetime string
**Description**: Start of temporal coverage

#### identification.temporal_end
**CIOOS Form Source**: `dateEnd`
**Type**: ISO 8601 datetime string
**Description**: End of temporal coverage

#### identification.status
**CIOOS Form Source**: `status`
**Type**: String
**Description**: Dataset status (often used for publication workflow)

#### identification.project
**CIOOS Form Source**: `projects`
**Type**: Array of strings
**Example**: `["Coastal Environmental Baseline Program"]`

#### identification.progress_code
**CIOOS Form Source**: `progress`
**Type**: String
**Values**: "completed", "onGoing", "planned", "obsolete", etc.
**Example**: "completed"

#### identification.edition
**CIOOS Form Source**: `edition`
**Type**: String
**Description**: Version or edition of the dataset

### Contact Section

**CIOOS Form Source**: `contacts` array
**Type**: Array of contact objects
**Processing**: Restructures each contact, adds automatic distributor

#### Contact Structure

Each contact in the CIOOS format:
```yaml
- roles: ["owner", "funder"]
  organization:
    name: "Organization Name"
    url: "https://example.org"
    address: "123 Street"
    city: "City"
    country: "Country"
    email: "org@example.org"
    ror: "https://ror.org/..."
  individual:
    name: "LastName, FirstName"
    position: "Position Title"
    email: "person@example.org"
    orcid: "https://orcid.org/..."
  inCitation: true
```

#### Contact Field Mappings

##### roles
**CIOOS Form Source**: `contact.role`
**Type**: Array of strings
**Direct mapping**: Roles passed through as-is

##### organization.name
**CIOOS Form Source**: `contact.orgName`

##### organization.url
**CIOOS Form Source**: `contact.orgURL`

##### organization.address
**CIOOS Form Source**: `contact.orgAdress`
**Note**: Typo in form field name preserved

##### organization.city
**CIOOS Form Source**: `contact.orgCity`

##### organization.country
**CIOOS Form Source**: `contact.orgCountry`

##### organization.email
**CIOOS Form Source**: `contact.orgEmail`

##### organization.ror
**CIOOS Form Source**: `contact.orgRor`
**Description**: Research Organization Registry identifier

##### individual.name
**CIOOS Form Source**: `contact.lastName`, `contact.givenNames`
**Processing**: Concatenates as "LastName, FirstName"
**Logic**: `", ".join([lastName, givenNames])` with None removal

##### individual.position
**CIOOS Form Source**: `contact.indPosition`

##### individual.email
**CIOOS Form Source**: `contact.indEmail`

##### individual.orcid
**CIOOS Form Source**: `contact.indOrcid`
**Format**: "https://orcid.org/0000-0000-0000-0000"

##### inCitation
**CIOOS Form Source**: `contact.inCitation`
**Type**: Boolean
**Description**: Whether this contact should appear in dataset citations

#### Special Contact Processing

##### 1. Automatic Distributor Assignment

**Logic** (lines 296-303):
```python
# If there's no distributor set, set it to the data contact (owner)
all_roles = [contact["role"] for contact in record["contacts"]]
all_roles_flat = [j for sub in all_roles for j in sub]

if "distributor" not in all_roles_flat:
    for contact in record["contacts"]:
        if "owner" in contact["role"]:
            contact["role"] += ["distributor"]
```

**Effect**: If no contact has "distributor" role, it's automatically added to all "owner" contacts

##### 2. Organization Contact Prepending

**CIOOS Form Source**: `organization` (top-level field)
**Logic** (lines 305-313):
```python
if organization:
    organization = {
        "roles": ["owner"],
        "organization": {"name": record.get("organization")},
    }
    record_yaml["contact"] = [organization] + record_yaml["contact"]
```

**Effect**: If a top-level `organization` field exists, creates a new contact and prepends it to the contact list

### Distribution Section

**CIOOS Form Source**: `distribution` array
**Type**: Array of distribution objects
**Structure Preserved**: Each distribution object passed through with minimal processing

#### Distribution Structure

```yaml
distribution:
  - url: "https://example.org/data"
    name:
      en: "ERDDAP Dataset"
      fr: "Jeu de données ERDDAP"
    description:
      en: "Complete dataset..."
      fr: "Ensemble de données complet..."
```

##### url
**CIOOS Form Source**: `distribution[].url`
**Type**: String (URL)

##### name
**CIOOS Form Source**: `distribution[].name`
**Type**: Bilingual text

##### description
**CIOOS Form Source**: `distribution[].description`
**Type**: Bilingual text

### Platform and Instruments Section

**Condition**: Behavior depends on `noPlatform` flag

#### Case 1: No Platform (`noPlatform` = true)

**Result**: `instruments` array at root level
**CIOOS Form Source**: `instruments`
**Structure**: Array passed through as-is

```yaml
instruments:
  - id: "inst-1"
    type: "Sensor"
    description: "..."
```

#### Case 2: Single Platform

**Condition**: `platforms` array has exactly 1 element
**Result**: `platform` array with instruments nested
**Processing**:
```python
record["platforms"][0]["instruments"] = instrumentsList
record_yaml["platform"] = record["platforms"]
```

**Structure**:
```yaml
platform:
  - id: "plat-1"
    name: "Platform Name"
    type: "coastal structure"
    instruments:
      - id: "inst-1"
        type: "Sensor"
      - id: "inst-2"
        type: "Profiler"
```

#### Case 3: Multiple Platforms

**Condition**: `platforms` array has > 1 element
**Result**: `platform` array with instruments matched by platform ID
**Processing**: Each instrument's `platform` field matched to platform `id`

```python
for platform in platformList:
    instruments = []
    for instrument in instrumentsList:
        if instrument["platform"] == platform["id"]:
            instruments.append(instrument)
    if len(instruments) > 0:
        platform["instruments"] = instruments
```

**Structure**:
```yaml
platform:
  - id: "plat-1"
    name: "Platform 1"
    instruments:
      - id: "inst-1"
  - id: "plat-2"
    name: "Platform 2"
    instruments:
      - id: "inst-2"
      - id: "inst-3"
```

## Data Processing Functions

### scrub_dict(d_in)
**Purpose**: Recursively remove empty strings, None values, and empty objects
**Applied**: To entire output structure
**Effect**: Clean, minimal output without null pollution

### scrub_list(d_in)
**Purpose**: Scrub dictionaries within lists
**Applied**: To all array values

### strip_keywords(keywords)
**Purpose**: Remove leading/trailing whitespace from keywords
**Input**: `{"en": ["keyword "], "fr": [" mot-clé"]}`
**Output**: `{"en": ["keyword"], "fr": ["mot-clé"]}`

### date_from_datetime_str(datetime_str)
**Purpose**: Extract date from datetime string
**Input**: "2025-01-01T17:00:00.000Z"
**Output**: "2025-01-01"
**Logic**: Returns first 10 characters

### fix_lat_long_polygon(polygon)
**Purpose**: Transform coordinate order from lat,long to long,lat
**Input**: "50.03,-66.84 50.01,-66.93"
**Output**: "-66.84,50.03 -66.93,50.01"
**Steps**:
1. Replace ", " with "," (clean spacing)
2. Split by spaces into coordinate pairs
3. For each pair, split by comma into [lat, long]
4. Rejoin as [long, lat]

### format_taxa(taxa)
**Purpose**: Flatten GBIF taxonomy objects to keyword list
**Input**: Array of taxonomy objects with hierarchical structure
**Output**: Flat array of taxonomic names
**Logic**:
- Extract: kingdom, phylum, class, order, family, genus, species
- Filter out None/null values
- Join with commas, then split back to array
**Effect**: Converts complex taxonomy to simple keyword list

### eovs_to_fr(eovs_en)
**Purpose**: Translate EOV codes from English to French
**Input**: `["oxygen", "nutrients"]`
**Output**: `["Oxygène", "Nutriments"]`
**Data Source**: `eov.json` lookup table
**Fallback**: Empty string for missing translations

## Resource Files

### licenses.json
**Purpose**: License code to full license information
**Structure**:
```json
{
  "CC-BY-4.0": {
    "title": {"en": "Creative Commons Attribution 4.0 Attribution"},
    "url": "https://creativecommons.org/licenses/by/4.0",
    "code": "CC-BY-4.0"
  }
}
```
**Supported Licenses**: CC-BY-4.0, CC-BY-SA-4.0, CC-BY-ND-4.0, CC-BY-NC-4.0, CC-BY-NC-SA-4.0, CC-BY-NC-ND-4.0, CC0, and others

### eov.json
**Purpose**: EOV translations and metadata
**Structure**:
```json
[
  {
    "category": "Biogeochemical",
    "value": "oxygen",
    "label EN": "Oxygen",
    "label FR": "Oxygène",
    "definition EN": "The amount of dissolved oxygen in seawater.",
    "definition FR": "Concentration d'oxygène dissous dans l'eau de mer",
    "icon": "dissolved-oxygen.svg",
    "url": "https://www.goosocean.org/..."
  }
]
```

### epsg.json
**Purpose**: EPSG coordinate reference system definitions
**Structure**: Array of EPSG code objects indexed by code
**Usage**: Vertical extent reference system lookup

## Fields Not Mapped

The following CIOOS Form fields are **NOT** included in the CIOOS intermediate format:

- `category` - Internal categorization
- `doiCreationStatus` - DOI workflow status
- `filename` - Internal file tracking
- `lastEditedBy` - Editor information
- `recordID` - Firebase record ID (used only for maintenance_note URL)
- `region` - Regional classification (used only for maintenance_note URL)
- `resourceType` - Resource type classification
- `status` - Mapped but often empty/unused
- `userID` - User identifier (used only for maintenance_note URL)
- `noVerticalExtent` - Flag only, values default to 0
- `noTaxa` - Flag only, causes taxa removal
- `noPlatform` - Flag only, affects platform/instrument structure

## Validation and Quality Control

The transformation includes several quality control measures:

1. **Empty Value Removal**: All empty strings, nulls, and empty objects removed
2. **Type Conversion**: String numbers converted to floats for coordinates/extents
3. **Coordinate Validation**: Lat/long order corrected for standards compliance
4. **Date Extraction**: Datetime strings normalized to date-only format where needed
5. **Whitespace Trimming**: Keywords cleaned of leading/trailing spaces
6. **None Filtering**: None values removed from concatenations

## Usage Example

```python
from cioos_metadata_conversion.firebase_to_cioos import record_json_to_yaml

# Load CIOOS Form data from Firebase
firebase_record = {...}  # JSON from Firebase

# Transform to CIOOS intermediate format
cioos_record = record_json_to_yaml(firebase_record)

# Result is ready for any output conversion
# - ISO 19115-3 XML
# - DataCite JSON/XML
# - ERDDAP/ACDD attributes
# - Citation.cff
```

## File References

- **Transformation code**: [firebase_to_cioos.py](cioos_metadata_conversion/firebase_to_cioos.py)
- **Resource files**: [cioos_metadata_conversion/resources/](cioos_metadata_conversion/resources/)
  - [licenses.json](cioos_metadata_conversion/resources/licenses.json)
  - [eov.json](cioos_metadata_conversion/resources/eov.json)
  - [epsg.json](cioos_metadata_conversion/resources/epsg.json)
- **Test data**: [tests/records/firebase/test-dataset-record.json](tests/records/firebase/test-dataset-record.json)
- **Test YAML output**: [tests/records/test_record1.yaml](tests/records/test_record1.yaml)

## Standards Compliance

The CIOOS intermediate format is designed to support:
- **ISO 19115-3**: Geographic information metadata
- **DataCite 4.5**: Research data citation
- **ACDD 1.3**: Attribute Convention for Data Discovery
- **Schema.org**: Structured data for web discovery
- **CIOOS Metadata Profile**: Canadian ocean data requirements

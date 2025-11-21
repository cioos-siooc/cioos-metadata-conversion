# CIOOS Form to DataCite Schema Mapping

This document describes how metadata fields from the CIOOS Form are mapped to the DataCite Metadata Schema v4.5.

## Overview

The conversion process follows two steps:
1. **CIOOS Form to CIOOS**: CIOOS Form data is converted to an intermediate CIOOS format ([firebase_to_cioos.py](cioos_metadata_conversion/firebase_to_cioos.py))
2. **CIOOS to DataCite**: The CIOOS format is then mapped to DataCite schema ([datacite.py](cioos_metadata_conversion/datacite.py))

## Field Mappings

### Required Fields

#### 1. Identifier (DOI)
**DataCite**: `identifier` (identifierType="DOI")
**CIOOS Source**: `record['identification']['identifier']`
**CIOOS Form Source**: `datasetIdentifier`
**Notes**:
- DOI prefix "https://doi.org/" is stripped
- Can be optionally generated if `doi_prefix` parameter is provided

#### 2. Creators
**DataCite**: `creators`
**CIOOS Source**: `record['contact']` where `inCitation = true`
**CIOOS Form Source**: `contacts` array
**Mapping Logic**:
- Filters contacts where `inCitation` is `true`
- Personal creators:
  - `creatorName`: `individual.name` or concatenation of `givenNames` + `lastName`
  - `nameType`: "Personal"
  - `givenName`: `individual.givenNames`
  - `familyName`: `individual.lastName`
  - `nameIdentifier`: `individual.orcid` (if present)
    - `nameIdentifierScheme`: "ORCID"
    - `schemeUri`: "https://orcid.org"
- Organization creators:
  - `creatorName`: `organization.name`
  - `nameType`: "Organizational"
  - `lang`: "en"
- Affiliation (both types):
  - `affiliation.name`: `organization.name`
  - `affiliationIdentifier`: `organization.ror` (if present)
  - `affiliationIdentifierScheme`: "ROR"
  - `schemeUri`: "https://ror.org/"

#### 3. Titles
**DataCite**: `titles`
**CIOOS Source**: `record['identification']['title']`
**CIOOS Form Source**: `title` (multilingual object with `en`, `fr` keys)
**Mapping Logic**:
- Each language becomes a separate title entry
- `titleType`: "TranslatedTitle"
- `lang`: Language code
- Excludes "translations" metadata key

#### 4. Publisher
**DataCite**: `publisher`
**CIOOS Source**: `record['contact']` where `'publisher' in roles`
**CIOOS Form Source**: `contacts` array with `role` containing "publisher"
**Mapping Logic**:
- Uses organization name from first contact with publisher role
- Falls back to "CIOOS" if no publisher found
- `publisherIdentifier`: `organization.ror` (if present)
- `publisherIdentifierScheme`: "ROR"
- `schemeUri`: "https://ror.org/"
- `lang`: "en"

#### 5. Publication Year
**DataCite**: `publicationYear`
**CIOOS Source**: `record['metadata']['dates']['publication']`
**CIOOS Form Source**: `timeFirstPublished`
**Mapping Logic**:
- Extracts year from ISO date string
- Falls back to current year if not available

#### 6. Resource Type
**DataCite**: `types.resourceTypeGeneral`
**CIOOS Source**: `record.get('metadataScope', 'Dataset')`
**CIOOS Form Source**: `metadataScope` or `metadataScopeIso`
**Default**: "Dataset"

### Recommended/Optional Fields

#### 7. Subjects
**DataCite**: `subjects`
**Sources**: Multiple
**Mapping Logic**:
- **Fixed Subject**: Always includes "FOS: Earth and related environmental sciences"
  - `subjectScheme`: "Fields of Science and Technology (FOS)"
  - `schemeUri`: "https://www.oecd.org/science/inno/38235147.pdf"

- **EOV (Essential Ocean Variables)**:
  - **CIOOS Source**: `record['metadata']['eov']`
  - **CIOOS Form Source**: `eov` array
  - Converted from camelCase to Title Case
  - `subjectScheme`: "GOOS EOV"
  - `schemeUri`: "https://www.goosocean.org/eov"

- **Keywords**:
  - **CIOOS Source**: `record['metadata']['keywords']`
  - **CIOOS Form Source**: `keywords.en` and `keywords.fr`
  - No specific scheme assigned

#### 8. Contributors
**DataCite**: `contributors`
**CIOOS Source**: `record['contact']`
**CIOOS Form Source**: `contacts` array
**Mapping Logic**:
- All contacts except those with role "publisher"
- Same personal/organization structure as creators
- **Role Mapping** (`CONTRIBUTOR_TYPE_MAPPING_FROM_CIOOS`):

| CIOOS Form Role | DataCite Contributor Type |
|---------------------|---------------------------|
| pointOfContact | ContactPerson |
| distributor | Distributor |
| editor | Editor |
| rightsHolder | RightsHolder |
| sponsor | Sponsor |
| processor | DataCurator |
| metadataCustodian | DataCurator |
| custodian | DataCurator |
| owner | RightsHolder |
| funder | Sponsor |
| principalInvestigator | ProjectLeader |
| collaborator | ProjectMember |
| originator | ProjectMember |
| contributor | ProjectMember |
| author | Researcher |
| coAuthor | Researcher |
| mediator | Other |
| ressourceProvider | Other |
| stakeholder | Other |

**Note**: If no distributor is found in contacts, the system automatically adds the distributor role to the "owner" contact

#### 9. Dates
**DataCite**: `dates`
**Mapping**:

| Date Type | CIOOS Source | CIOOS Form Source |
|-----------|--------------|-----------------|
| Created | `record['identification']['dates']['created']` | Not directly mapped |
| Updated | `record['metadata']['dates']['revision']` | `created` (timestamp) |
| Collected | `record['identification']['temporal_begin']` to `record['identification']['temporal_end']` | `dateStart` to `dateEnd` |

**Format**: ISO 8601 date or date range (e.g., "2025-01-01/2025-03-01")

#### 10. Language
**DataCite**: `language`
**CIOOS Source**: `record['metadata']['language']`
**CIOOS Form Source**: `language`

#### 11. Alternate Identifiers
**DataCite**: `alternateIdentifiers`
**Status**: Currently empty array (placeholder)

#### 12. Related Identifiers
**DataCite**: `relatedIdentifiers`
**CIOOS Source**: `record['identification']['associated_resources']`
**CIOOS Form Source**: `associated_resources` array
**Mapping**:
- `relatedIdentifier`: `code` (URL or DOI)
- `relatedIdentifierType`: `authority` (e.g., "DOI", "URL")
- `relationType`: `association_type` (e.g., "IsReferencedBy", "IsCitedBy")

#### 13. Version
**DataCite**: `version`
**CIOOS Source**: `record['identification']['edition']`
**CIOOS Form Source**: `edition`

#### 14. Rights List
**DataCite**: `rightsList`
**CIOOS Source**: `record['metadata']['use_constraints']['licence']`
**CIOOS Form Source**: `license` (code, e.g., "CC-BY-4.0") resolved via `licenses.json`
**Mapping**:
- `rights`: License title in English
- `rightsUri`: License URL
- `rightsIdentifier`: License code (e.g., "CC-BY-4.0")
- `rightsIdentifierScheme`: "SPDX"
- `schemeUri`: "https://spdx.org/licenses/"
- `lang`: "en"

#### 15. Descriptions
**DataCite**: `descriptions`
**Sources**:

1. **Abstract**:
   - **CIOOS Source**: `record['identification']['abstract']`
   - **CIOOS Form Source**: `abstract` (multilingual with `en`, `fr`)
   - `descriptionType`: "Abstract"

2. **Limitations** (if present):
   - **CIOOS Source**: `record['metadata']['use_constraints']['limitations']`
   - **CIOOS Form Source**: `limitations`
   - `descriptionType`: "Other"
   - Prefixed with "limitations: "

#### 16. Geo Locations
**DataCite**: `geoLocations`
**Components**:

1. **Bounding Box**:
   - **CIOOS Source**: `record['spatial']['bounding_box']`
   - **CIOOS Form Source**: `map.west`, `map.east`, `map.north`, `map.south`
   - Fields: `westBoundLongitude`, `eastBoundLongitude`, `northBoundLatitude`, `southBoundLatitude`

2. **Polygon** (if present):
   - **CIOOS Source**: `record['spatial']['polygon']`
   - **CIOOS Form Source**: `map.polygon`
   - Format: Space-separated coordinate pairs "lon,lat"
   - Converted to array of `polygonPoint` with `pointLongitude`, `pointLatitude`

3. **Location Place**:
   - **CIOOS Source**: `record['spatial']['description']['en']`
   - **CIOOS Form Source**: `map.description.en`
   - Plain text place name

#### 17. Funding References
**DataCite**: `fundingReferences`
**CIOOS Source**: `record['contact']` where `'funder' in roles`
**CIOOS Form Source**: `contacts` with `role` containing "funder"
**Mapping**:
- `funderName`: `organization.name`
- `funderIdentifier`: `organization.ror` (if present)
- `funderIdentifierType`: "ROR"

#### 18. Related Items
**DataCite**: `relatedItems`
**Status**: Currently empty array (placeholder)

### Additional Metadata in CIOOS (Not Mapped to DataCite)

The following fields are present in the CIOOS intermediate format but are not currently mapped to DataCite:

- **Spatial Information**:
  - Vertical extent (min, max, direction, EPSG code)
  - Spatial description identifier

- **Identification**:
  - Project information
  - Progress code
  - Status

- **Metadata**:
  - Naming authority
  - Maintenance note
  - Comment
  - History/Lineage information

- **Platform and Instruments**:
  - Platform details
  - Instrument information

- **Distribution**:
  - Download URLs
  - Distribution descriptions

## Special Processing

### 1. Coordinate Transformation
Polygon coordinates are transformed from "lat,long" (CIOOS Form) to "long,lat" (CIOOS/DataCite standard).

### 2. EOV Translation
EOV values are converted from camelCase to Title Case using the `camel_to_title()` utility function.

### 3. Taxa Formatting
Taxa information is flattened from taxonomic hierarchy to a comma-separated list of taxonomic levels.

### 4. Empty Field Handling
The conversion process includes scrubbing functions to remove empty strings, null values, and empty objects.

### 5. Deduplication
Subjects and other repeating fields are deduplicated using the `_get_unique_dicts()` function.

## File References

- **Main conversion code**: [datacite.py](cioos_metadata_conversion/datacite.py)
- **CIOOS Form to CIOOS transformation**: [firebase_to_cioos.py](cioos_metadata_conversion/firebase_to_cioos.py)
- **Test data**: [test-dataset-record.json](tests/records/firebase/test-dataset-record.json)
- **Example output**: [test-dataset-record-datacite.xml](test-dataset-record-datacite.xml)
- **Unit tests**: [test_datacite.py](tests/test_datacite.py)

## Schema Version

The implementation follows **DataCite Metadata Schema v4.5** as documented at:
https://datacite-metadata-schema.readthedocs.io/en/4.6/properties/overview/

Schema version is specified in output as: `http://datacite.org/schema/kernel-4`

# CIOOS Form to ERDDAP/ACDD Mapping

This document describes how metadata fields from the CIOOS Form are mapped to ERDDAP dataset.xml global attributes following the ACDD 1.3 (Attribute Convention for Data Discovery) conventions.

## Overview

The conversion process follows two steps:
1. **CIOOS Form to CIOOS**: CIOOS Form data is converted to an intermediate CIOOS format ([firebase_to_cioos.py](cioos_metadata_conversion/firebase_to_cioos.py))
2. **CIOOS to ACDD/ERDDAP**: The CIOOS format is then mapped to ACDD 1.3 global attributes for use in ERDDAP ([acdd.py](cioos_metadata_conversion/acdd.py) and [erddap.py](cioos_metadata_conversion/erddap.py))

## What is ACDD?

ACDD (Attribute Convention for Data Discovery) is a standard set of global attributes designed to enhance data discovery and interoperability in earth science datasets. ERDDAP uses these attributes to provide rich metadata for datasets.

## Multilingual Support

The conversion supports three methods for handling multilingual content:

1. **suffix**: Creates separate attributes for each language (e.g., `title_en`, `title_fr`)
2. **nested**: Combines languages in one attribute with language tags (e.g., `title: "(en) Title; (fr) Titre"`)
3. **xml**: Uses XML `xml:lang` attributes (e.g., `<att name="title" xml:lang="en">Title</att>`)

## Field Mappings

### Core Identification Fields

#### 1. ID
**ACDD/ERDDAP Attribute**: `id`
**CIOOS Source**: `record['metadata']['identifier']`
**CIOOS Form Source**: `identifier`
**Description**: Unique identifier for the dataset
**Required**: Yes

#### 2. Naming Authority
**ACDD/ERDDAP Attribute**: `naming_authority`
**CIOOS Source**: `record['metadata']['naming_authority']`
**CIOOS Form Source**: Hardcoded as "ca.cioos" in transformation
**Description**: Organization responsible for the naming convention
**Required**: Yes
**Default**: "ca.cioos"

#### 3. Title
**ACDD/ERDDAP Attribute**: `title`
**CIOOS Source**: `record['identification']['title'][language]`
**CIOOS Form Source**: `title.en` or `title.fr`
**Description**: A descriptive title for the dataset
**Required**: Yes
**Multilingual**: Yes (with `title_en`, `title_fr` when using suffix method)

#### 4. Summary
**ACDD/ERDDAP Attribute**: `summary`
**CIOOS Source**: `record['identification']['abstract'][language]`
**CIOOS Form Source**: `abstract.en` or `abstract.fr`
**Description**: A paragraph describing the dataset
**Required**: Yes
**Multilingual**: Yes (with `summary_en`, `summary_fr` when using suffix method)

### Contact and Attribution

#### 5. Institution
**ACDD/ERDDAP Attribute**: `institution`
**CIOOS Source**: `record['contact']` where `'owner' in roles` → `organization.name`
**CIOOS Form Source**: `contacts` with role "owner" → `orgName`
**Description**: Institution responsible for the dataset (typically the data owner)
**Note**: Uses the first owner if multiple are found

#### 6. Creator Information
**ACDD/ERDDAP Attributes**:
- `creator_name`
- `creator_email`
- `creator_orcid`
- `creator_type` (person or institution)
- `creator_institution`
- `creator_address`
- `creator_city`
- `creator_country`
- `creator_url`
- `creator_ror`

**CIOOS Source**: `record['contact']` where `'owner' in roles`
**CIOOS Form Source**: `contacts` with role "owner"
**Mapping Logic**:
- If contact has `individual`:
  - `creator_name`: `indName` (from `lastName`, `givenNames`)
  - `creator_email`: `indEmail`
  - `creator_orcid`: `indOrcid`
  - `creator_type`: "person"
- If contact has only organization:
  - `creator_name`: `orgName`
  - `creator_email`: `orgEmail`
  - `creator_type`: "institution"
- Organization details (both cases):
  - `creator_institution`: `orgName`
  - `creator_address`: `orgAdress`
  - `creator_city`: `orgCity`
  - `creator_country`: `orgCountry`
  - `creator_url`: `orgURL`
  - `creator_ror`: `orgRor`

#### 7. Publisher Information
**ACDD/ERDDAP Attributes**:
- `publisher_name`
- `publisher_email`
- `publisher_type` (person or institution)
- `publisher_institution`
- `publisher_address`
- `publisher_city`
- `publisher_country`
- `publisher_url`
- `publisher_ror`

**CIOOS Source**: `record['contact']` where `'publisher' in roles`
**CIOOS Form Source**: `contacts` with role "publisher"
**Mapping Logic**: Same structure as creator information

#### 8. Contributor Information
**ACDD/ERDDAP Attributes**:
- `contributor_name`
- `contributor_role`

**CIOOS Source**: `record['contact']` (all contacts)
**CIOOS Form Source**: `contacts` array
**Format**: Semicolon-separated lists
- `contributor_name`: Names of all contacts (individual or organization)
- `contributor_role`: Comma-separated roles for each contact, separated by semicolons

**Example**:
```
contributor_name: "John Doe;ACME Organization;Jane Smith"
contributor_role: "owner,pointOfContact;publisher;distributor,editor"
```

### Temporal Information

#### 9. Date Modified
**ACDD/ERDDAP Attribute**: `date_modified`
**CIOOS Source**: `record['metadata']['dates']['revision']`
**CIOOS Form Source**: `created` (timestamp of last modification)
**Description**: Date of last metadata revision
**Format**: ISO 8601 date string

#### 10. Date Created
**ACDD/ERDDAP Attribute**: `date_created`
**CIOOS Source**: `record['metadata']['dates']['publication']`
**CIOOS Form Source**: `timeFirstPublished`
**Description**: Date when the dataset was first published
**Format**: ISO 8601 date (extracted from datetime string)

### Scientific Information

#### 11. Keywords
**ACDD/ERDDAP Attribute**: `keywords`
**CIOOS Source**: `record['identification']['keywords']`
**CIOOS Form Source**: `keywords.en`, `keywords.fr`, `eov`, `taxa`
**Format**: Comma-separated list with prefixes
**Mapping Logic**:
- Default keywords: No prefix (e.g., "ocean temperature,salinity")
- EOV keywords: "CIOOS:" prefix (e.g., "CIOOS:oxygen,CIOOS:seaSurfaceTemperature")
- Taxa keywords: "GBIF:" prefix (e.g., "GBIF:Animalia,GBIF:Mollusca")

**Prefix Mapping**:
| Keyword Group | Prefix | Label |
|---------------|--------|-------|
| default | (none) | null |
| eov | CIOOS: | CIOOS Essential Ocean Variables Vocabulary |
| taxa | GBIF: | GBIF Taxonomy Vocabulary |

#### 12. Keywords Vocabulary
**ACDD/ERDDAP Attribute**: `keywords_vocabulary`
**CIOOS Source**: Derived from keyword groups present
**Format**: Comma-separated list of vocabulary labels with their prefixes
**Example**: "CIOOS: CIOOS Essential Ocean Variables Vocabulary,GBIF: GBIF Taxonomy Vocabulary"

#### 13. Project
**ACDD/ERDDAP Attribute**: `project`
**CIOOS Source**: `record['identification']['project']`
**CIOOS Form Source**: `projects` array
**Format**: Comma-separated list
**Example**: "Oceanography,Coastal Environmental Baseline Program"

#### 14. Progress
**ACDD/ERDDAP Attribute**: `progress`
**CIOOS Source**: `record['identification']['progress_code']`
**CIOOS Form Source**: `progress`
**Description**: Current status of the dataset
**Note**: This is not a standard ACDD attribute but is included for CIOOS-specific needs
**Possible Values**: "completed", "onGoing", "planned", etc.

### Platform and Instruments

#### 15. Platform
**ACDD/ERDDAP Attribute**: `platform`
**CIOOS Source**: `record['platform'][0]['type']`
**CIOOS Form Source**: `platforms[0].type`
**Description**: Type of platform used for data collection
**Example**: "coastal structure", "land/onshore structure"

#### 16. Platform Vocabulary
**ACDD/ERDDAP Attribute**: `platform_vocabulary`
**CIOOS Source**: Hardcoded
**Value**: "http://vocab.nerc.ac.uk/collection/L06/current/"
**Description**: URL to the NERC vocabulary for platform types

### Version and History

#### 17. Product Version
**ACDD/ERDDAP Attribute**: `product_version`
**CIOOS Source**: `record['identification']['edition']`
**CIOOS Form Source**: `edition`
**Description**: Version number or identifier for the dataset

#### 18. History
**ACDD/ERDDAP Attribute**: `history`
**CIOOS Source**: `record['metadata']['history']`
**CIOOS Form Source**: `history` array
**Description**: Provides an audit trail for modifications to the dataset
**Format**:
- If string: Uses directly
- If list: Formatted as YAML with "Metadata record history:\n" prefix
- Multilingual: Uses appropriate language version

### Legal and Usage Constraints

#### 19. License
**ACDD/ERDDAP Attribute**: `license`
**CIOOS Source**: `record['metadata']['use_constraints']['licence']['url']`
**CIOOS Form Source**: `license` code (e.g., "CC-BY-4.0") resolved via `licenses.json`
**Description**: URL to the license governing the use of the dataset
**Example**: "https://creativecommons.org/licenses/by/4.0"

#### 20. Comment
**ACDD/ERDDAP Attribute**: `comment`
**CIOOS Source**: `record['metadata']['use_constraints']['limitations']` + translation info
**CIOOS Form Source**: `limitations`
**Description**: Miscellaneous information about the dataset
**Multilingual**: Yes (with `comment_en`, `comment_fr` when using suffix method)

**Format**:
```
##Limitations:
[limitation text]

##Translation:
[translation message if applicable]
```

### References and Links

#### 21. DOI
**ACDD/ERDDAP Attribute**: `doi`
**CIOOS Source**: `record['identification']['identifier']`
**CIOOS Form Source**: `datasetIdentifier`
**Description**: Digital Object Identifier for the dataset
**Example**: "https://doi.org/10.26071/mxtr-gp72"

#### 22. Metadata Link
**ACDD/ERDDAP Attribute**: `metadata_link`
**CIOOS Source**: `record['identification']['identifier']` or provided parameter
**CIOOS Form Source**: `datasetIdentifier`
**Description**: URL to the complete metadata record
**Fallback**: Can be provided as a parameter if not in the record

#### 23. Metadata Form
**ACDD/ERDDAP Attribute**: `metadata_form`
**CIOOS Source**: `record['metadata']['maintenance_note']` (with "Generated from " removed)
**CIOOS Form Source**: Derived from form URL
**Description**: Link to the form used to create this metadata
**Example**: "https://cioos-siooc.github.io/metadata-entry-form#/en/stlaurent/..."

## ERDDAP-Specific Processing

### Dataset Identification

The system matches CIOOS metadata records to ERDDAP datasets by:
1. Looking for distribution URLs that contain the ERDDAP URL
2. Extracting the dataset ID from the URL (last segment before `.html`)
3. Ignoring subset URLs (those containing `?`)

### XML Generation

The ERDDAP module generates XML in the following format:
```xml
<addAttributes>
    <att name='id'>fb5c9e1e-a911-46b7-8c1d-e34215a105ed</att>
    <att name='naming_authority'>ca.cioos</att>
    <att name='title'>Dataset Title</att>
    <att name='title' xml:lang='en'>Dataset Title</att>
    <att name='title' xml:lang='fr'>Titre du jeu de données</att>
</addAttributes>
```

### Updating Existing Datasets

The ERDDAP update process:
1. Parses existing ERDDAP `datasets.xml` files
2. Finds datasets by `datasetID` attribute
3. Updates existing `<att>` elements or creates new ones
4. Preserves multilingual attributes using `xml:lang`
5. Maintains all other dataset configuration (data variables, source URLs, etc.)

## Special Processing

### 1. Contact Role Handling

The system automatically adds the "distributor" role to any contact with the "owner" role if no distributor is explicitly defined.

### 2. Multiple Creators/Publishers

If multiple contacts have the "owner" or "publisher" role, the system uses the first one and logs a warning.

### 3. Keyword Prefix Generation

Keywords are automatically prefixed based on their source:
- Standard keywords: No prefix
- EOV (Essential Ocean Variables): "CIOOS:" prefix
- Taxa (from GBIF): "GBIF:" prefix

### 4. Empty Value Removal

All empty strings, null values, and empty objects are removed from the final output using the `drop_empty_values()` utility function.

### 5. Multilingual Field Generation

Depending on the multilingual method selected:
- **suffix**: `title` → `title_en`, `title_fr`
- **nested**: `title` → `title: "(en) Title; (fr) Titre"`
- **xml**: Uses XML namespace attributes for language specification

## Output Formats

The ACDD module supports multiple output formats:
1. **dict** (default): Python dictionary
2. **json**: JSON string
3. **yaml**: YAML string
4. **xml**: ERDDAP-compatible XML (via erddap module)

## ACDD Version

This implementation follows **ACDD 1.3** (Attribute Convention for Data Discovery version 1.3).

Reference: http://wiki.esipfed.org/index.php/Attribute_Convention_for_Data_Discovery_1-3

## Additional CIOOS-Specific Attributes

The following attributes are not part of standard ACDD but are included for CIOOS needs:

- `progress`: Dataset completion status
- `metadata_form`: Link to the metadata entry form
- Platform-related attributes for research platforms

## Fields Not Mapped

The following CIOOS/CIOOS Form fields are not currently mapped to ACDD/ERDDAP:

- **Spatial Information**:
  - Bounding box coordinates
  - Polygon geometry
  - Vertical extent
  - Spatial description and identifiers

- **Temporal Coverage**:
  - Start and end dates for data collection (distinct from metadata dates)

- **Associated Resources**:
  - Related publications
  - Related datasets

- **Distribution**:
  - Download URLs (except ERDDAP URL for matching)
  - Distribution format information

- **Instruments**:
  - Detailed instrument specifications
  - Instrument-platform relationships

- **Quality Assurance**:
  - Quality control procedures
  - Processing steps

## File References

- **ACDD conversion code**: [acdd.py](cioos_metadata_conversion/acdd.py)
- **ERDDAP integration code**: [erddap.py](cioos_metadata_conversion/erddap.py)
- **CIOOS Form to CIOOS transformation**: [firebase_to_cioos.py](cioos_metadata_conversion/firebase_to_cioos.py)
- **Test ERDDAP XML**: [test_datasets.xml](tests/erddap_xmls/test_datasets.xml)
- **Unit tests**: [test_acdd.py](tests/test_acdd.py), [test_erddap.py](tests/test_erddap.py)

## Usage Examples

### Generate ACDD attributes as dictionary
```python
from cioos_metadata_conversion import acdd

attributes = acdd.acdd(record, language="en")
```

### Generate ACDD attributes with multilingual support (suffix method)
```python
attributes = acdd.acdd(record, language="en", multilingual="suffix")
# Result includes: title_en, title_fr, summary_en, summary_fr
```

### Generate ERDDAP XML with multilingual support
```python
from cioos_metadata_conversion import erddap

xml = erddap.global_attributes(record, output="xml", multilingual="xml")
```

### Update existing ERDDAP datasets.xml
```python
from cioos_metadata_conversion.erddap import update_dataset_xml

update_dataset_xml(
    datasets_xml="path/to/datasets.xml",
    records=[record1, record2],
    erddap_url="https://data.example.org/erddap",
    multilingual=True
)
```

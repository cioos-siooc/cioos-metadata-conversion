# CIOOS Form to ISO 19115-3 XML Mapping

This document describes how metadata fields from the CIOOS Form are mapped to ISO 19115-3 XML format following the CIOOS metadata profile.

## Overview

The conversion process follows two steps:
1. **CIOOS Form to CIOOS**: CIOOS Form data is converted to an intermediate CIOOS format ([firebase_to_cioos.py](cioos_metadata_conversion/firebase_to_cioos.py))
2. **CIOOS to ISO 19115-3**: The CIOOS format is then transformed to ISO 19115-3 XML using the `metadata-xml` package (Jinja2 templates)

The XML generation is handled by the external [metadata-xml](https://github.com/cioos-siooc/metadata-xml) package, which uses Jinja2 templates to render ISO 19115-3 compliant XML.

## What is ISO 19115-3?

ISO 19115-3:2016 is an international standard for geospatial metadata. It defines an XML schema for describing geographic information and services. The CIOOS implementation follows a specific profile of ISO 19115-3 designed for ocean data discovery.

## Multilingual Support

ISO 19115-3 has built-in support for multilingual content using:
- `PT_FreeText` elements for bilingual text fields
- `LocalisedCharacterString` with `locale` attributes
- Primary language in `defaultLocale`, alternate language in `otherLocale`

## Field Mappings

### Metadata Information

#### 1. Metadata Identifier
**ISO Path**: `mdb:metadataIdentifier/mcc:MD_Identifier/mcc:code`
**CIOOS Source**: `record['metadata']['identifier']`
**CIOOS Form Source**: `identifier`
**Required**: Yes (CIOOS core mandatory)
**Description**: Unique identifier for the metadata record

#### 2. Naming Authority
**ISO Path**: `mdb:metadataIdentifier/mcc:MD_Identifier/mcc:authority/cit:CI_Citation/cit:title`
**CIOOS Source**: `record['metadata']['naming_authority']`
**CIOOS Form Source**: Hardcoded as "ca.cioos"
**Description**: Organization responsible for the naming convention

#### 3. Default Locale (Language)
**ISO Path**: `mdb:defaultLocale/lan:PT_Locale/lan:language/lan:LanguageCode`
**CIOOS Source**: `record['metadata']['language']`
**CIOOS Form Source**: `language`
**Required**: Yes (CIOOS core mandatory)
**Values**: "eng" (English) or "fra" (French) - ISO 639-2 codes
**Notes**:
- Country code is hardcoded as "CAN" (ISO 3166-1)
- Character encoding is hardcoded as "utf8"

#### 4. Other Locale (Alternate Language)
**ISO Path**: `mdb:otherLocale/lan:PT_Locale/lan:language/lan:LanguageCode`
**CIOOS Source**: Derived from all language keys in record
**Description**: Lists all alternate languages used in the metadata

#### 5. Metadata Scope
**ISO Path**: `mdb:metadataScope/mdb:MD_MetadataScope/mdb:resourceScope/mcc:MD_ScopeCode`
**CIOOS Source**: `record['metadata']['scope']`
**CIOOS Form Source**: `metadataScope` or `metadataScopeIso`
**Required**: Yes (CIOOS core mandatory)
**Default**: "dataset"

#### 6. Metadata Contact
**ISO Path**: `mdb:contact`
**CIOOS Source**: `record['contact']` where NOT `inCitation` OR `'custodian' in roles`
**CIOOS Form Source**: `contacts` with same criteria
**Required**: Yes (CIOOS core mandatory)
**Description**: Contacts responsible for the metadata (not the resource itself)

#### 7. Metadata Dates
**ISO Path**: `mdb:dateInfo/cit:CI_Date`
**CIOOS Source**: `record['metadata']['dates']`
**CIOOS Form Source**:
- `created` → revision date
- `timeFirstPublished` → publication date
**Format**: ISO 8601 date or datetime
**Notes**: Multiple date types supported (publication, revision, creation)

#### 8. Metadata Standard
**ISO Path**: `mdb:metadataStandard/cit:CI_Citation`
**Value**: "ISO 19115-1 Geographic information - Metadata"
**Edition**: "First Edition 2014-04-01"
**Hardcoded**: Yes

#### 9. Metadata Maintenance
**ISO Path**: `mdb:metadataMaintenance/mmi:MD_MaintenanceInformation`
**Value**: maintenanceAndUpdateFrequency = "asNeeded"
**Hardcoded**: Yes
**Description**: Refers to maintenance of the metadata itself

### Identification Information

#### 10. Resource Title
**ISO Path**: `mdb:identificationInfo/mri:MD_DataIdentification/mri:citation/cit:CI_Citation/cit:title`
**CIOOS Source**: `record['identification']['title']`
**CIOOS Form Source**: `title.en` and `title.fr`
**Required**: Yes (CIOOS core mandatory)
**Multilingual**: Yes (PT_FreeText)

#### 11. Resource Dates
**ISO Path**: `mdb:identificationInfo/.../mri:citation/cit:CI_Citation/cit:date/cit:CI_Date`
**CIOOS Source**: `record['identification']['dates']`
**CIOOS Form Source**:
- `dateStart` → creation date
- `datePublished` → publication date
- `dateRevised` → revision date
**Format**: ISO 8601 date or datetime

#### 12. Resource Edition
**ISO Path**: `mdb:identificationInfo/.../mri:citation/cit:CI_Citation/cit:edition`
**CIOOS Source**: `record['identification']['edition']`
**CIOOS Form Source**: `edition`

#### 13. Resource Identifier (DOI)
**ISO Path**: `mdb:identificationInfo/.../mri:citation/cit:CI_Citation/cit:identifier/mcc:MD_Identifier/mcc:code`
**CIOOS Source**: `record['identification']['identifier']`
**CIOOS Form Source**: `datasetIdentifier`
**Example**: "https://doi.org/10.21966/kace-2d24"

#### 14. Cited Responsible Parties
**ISO Path**: `mdb:identificationInfo/.../mri:citation/cit:CI_Citation/cit:citedResponsibleParty`
**CIOOS Source**: `record['contact']` where `inCitation = true`
**CIOOS Form Source**: `contacts` with `inCitation = true`
**Description**: Contacts to be included in dataset citation

#### 15. Abstract
**ISO Path**: `mdb:identificationInfo/mri:MD_DataIdentification/mri:abstract`
**CIOOS Source**: `record['identification']['abstract']`
**CIOOS Form Source**: `abstract.en` and `abstract.fr`
**Required**: Yes (CIOOS core mandatory)
**Multilingual**: Yes (PT_FreeText)

#### 16. Credit/Acknowledgement
**ISO Path**: `mdb:identificationInfo/mri:MD_DataIdentification/mri:credit`
**CIOOS Source**: `record['identification']['acknowledgement']`
**CIOOS Form Source**: Not directly mapped (optional field)
**Multilingual**: Yes (PT_FreeText)

#### 17. Status (Progress Code)
**ISO Path**: `mdb:identificationInfo/mri:MD_DataIdentification/mri:status/mcc:MD_ProgressCode`
**CIOOS Source**: `record['identification']['progress_code']`
**CIOOS Form Source**: `progress`
**Required**: Yes (CIOOS core mandatory)
**Default**: "onGoing"
**Values**: completed, onGoing, planned, obsolete, etc.

#### 18. Temporal Resolution
**ISO Path**: `mdb:identificationInfo/mri:MD_DataIdentification/mri:temporalResolution`
**CIOOS Source**: `record['identification']['time_coverage_resolution']`
**CIOOS Form Source**: Not directly mapped
**Format**: ISO 8601 duration (e.g., "P1D" for one day)

#### 19. Topic Category
**ISO Path**: `mdb:identificationInfo/mri:MD_DataIdentification/mri:topicCategory/mri:MD_TopicCategoryCode`
**CIOOS Source**: `record['identification']['topic_category']`
**Default**: "oceans"
**Required**: Yes
**Values**: ISO 19115 topic categories (oceans, environment, climatologyMeteorologyAtmosphere, etc.)

### Geographic Extent

#### 20. Bounding Box
**ISO Path**: `mdb:identificationInfo/.../mri:extent/gex:EX_Extent/gex:geographicElement/gex:EX_GeographicBoundingBox`
**CIOOS Source**: `record['spatial']['bbox']` (array of 4 values)
**CIOOS Form Source**: `map.west`, `map.south`, `map.east`, `map.north`
**Required**: Yes (CIOOS core mandatory if not using polygon)
**Structure**:
- `gex:westBoundLongitude`: bbox[0]
- `gex:southBoundLatitude`: bbox[1]
- `gex:eastBoundLongitude`: bbox[2]
- `gex:northBoundLatitude`: bbox[3]

#### 21. Bounding Polygon
**ISO Path**: `mdb:identificationInfo/.../mri:extent/gex:EX_Extent/gex:geographicElement/gex:EX_BoundingPolygon`
**CIOOS Source**: `record['spatial']['polygon']`
**CIOOS Form Source**: `map.polygon`
**Required**: Yes (CIOOS core mandatory if not using bounding box)
**Format**: Space-separated coordinate pairs "long,lat"
**Notes**: Coordinates transformed from lat,long to long,lat during CIOOS Form conversion

#### 22. Geographic Description
**ISO Path**: `mdb:identificationInfo/.../mri:extent/gex:EX_Extent/gex:geographicElement/gex:EX_GeographicDescription`
**CIOOS Source**: `record['spatial']['description']`
**CIOOS Form Source**: `map.description.en` and `map.description.fr`
**Required**: Yes (CIOOS core mandatory for biological datasets)
**Identifier**: `record['spatial']['descriptionIdentifier']`
**Code Space**: "ca.cioos"

#### 23. Vertical Extent
**ISO Path**: `mdb:identificationInfo/.../mri:extent/gex:EX_Extent/gex:verticalElement/gex:EX_VerticalExtent`
**CIOOS Source**: `record['spatial']['vertical']` (array of 2 values)
**CIOOS Form Source**:
- `verticalExtentMin` → minimumValue
- `verticalExtentMax` → maximumValue
**Additional Fields**:
- `vertical_positive`: `verticalExtentDirection`
- `vertical_epsg`: Reference system

#### 24. Temporal Extent
**ISO Path**: `mdb:identificationInfo/.../mri:extent/gex:EX_Extent/gex:temporalElement/gex:EX_TemporalExtent`
**CIOOS Source**:
- `record['identification']['temporal_begin']`
- `record['identification']['temporal_end']`
**CIOOS Form Source**: `dateStart` and `dateEnd`
**Format**: ISO 8601 datetime
**Optional**: `temporal_duration` field

### Keywords and Descriptive Information

#### 25. Keywords
**ISO Path**: `mdb:identificationInfo/.../mri:descriptiveKeywords/mri:MD_Keywords`
**CIOOS Source**: `record['identification']['keywords']`
**Structure**: Multiple keyword groups:

1. **Government of Canada Core Subject Thesaurus**:
   - Hardcoded keyword: "Oceans"
   - Thesaurus: "Government of Canada Core Subject Thesaurus"
   - Date: 2016-10-13

2. **Default Keywords**:
   - **CIOOS Source**: `record['identification']['keywords']['default']`
   - **CIOOS Form Source**: `keywords.en` and `keywords.fr`
   - Thesaurus name: "default"

3. **EOV Keywords**:
   - **CIOOS Source**: `record['identification']['keywords']['eov']`
   - **CIOOS Form Source**: `eov` array
   - Thesaurus name: "eov"

4. **Taxa Keywords**:
   - **CIOOS Source**: `record['identification']['keywords']['taxa']`
   - **CIOOS Form Source**: `taxa` (formatted from taxonomic hierarchy)
   - Thesaurus name: "taxa"

5. **Custom Thesauri**:
   - Any keyword group with a URL as the key becomes a thesaurus with online resource

**Multilingual**: Yes - each keyword can have en/fr versions

#### 26. Project Keywords
**ISO Path**: `mdb:identificationInfo/.../mri:descriptiveKeywords/mri:MD_Keywords`
**CIOOS Source**: `record['identification']['project']`
**CIOOS Form Source**: `projects` array
**Type**: MD_KeywordTypeCode = "project"
**Multilingual**: Yes

### Resource Constraints

#### 27. License (Legal Constraints)
**ISO Path**: `mdb:identificationInfo/.../mri:resourceConstraints/mco:MD_LegalConstraints`
**CIOOS Source**: `record['metadata']['use_constraints']['licence']`
**CIOOS Form Source**: `license` code resolved via `licenses.json`
**Default**: Creative Commons Attribution 4.0 (CC-BY-4.0)
**Structure**:
- `mco:reference/cit:CI_Citation/cit:title`: License title
- `mco:reference/cit:CI_Citation/cit:identifier`: License code
- `mco:reference/cit:CI_Citation/cit:onlineResource`: License URL
- `mco:useConstraints/mco:MD_RestrictionCode`: "licence"

#### 28. Use Limitations
**ISO Path**: `mdb:identificationInfo/.../mri:resourceConstraints/mco:MD_Constraints/mco:useLimitation`
**CIOOS Source**: `record['metadata']['use_constraints']['limitations']`
**CIOOS Form Source**: `limitations`
**Required**: Yes (CIOOS core mandatory)
**Multilingual**: Yes (PT_FreeText)

#### 29. Associated Resources
**ISO Path**: `mdb:identificationInfo/.../mri:associatedResource/mri:MD_AssociatedResource`
**CIOOS Source**: `record['identification']['associated_resources']`
**CIOOS Form Source**: `associated_resources` array
**Structure**:
- `mri:name/cit:CI_Citation/cit:title`: Resource title
- `mri:name/cit:CI_Citation/cit:identifier/mcc:authority`: Authority (e.g., "DOI", "URL")
- `mri:name/cit:CI_Citation/cit:identifier/mcc:code`: Resource code/URL
- `mri:associationType/mri:DS_AssociationTypeCode`: Association type (e.g., "crossReference")
- `mri:initiativeType/mri:DS_InitiativeTypeCode`: Initiative type (optional)

**Association Types**: IsReferencedBy, IsCitedBy, crossReference, etc.

#### 30. Supplemental Information (Comment)
**ISO Path**: `mdb:identificationInfo/.../mri:supplementalInformation`
**CIOOS Source**: `record['metadata']['comment']`
**CIOOS Form Source**: `comment`
**Multilingual**: Yes (PT_FreeText)

### Resource Maintenance

#### 31. Resource Maintenance
**ISO Path**: `mdb:identificationInfo/.../mri:resourceMaintenance/mmi:MD_MaintenanceInformation`
**CIOOS Source**: `record['metadata']['maintenance_note']`
**CIOOS Form Source**: Derived from form URL
**Fixed Values**:
- `mmi:maintenanceAndUpdateFrequency`: "asNeeded"
**Notes**: Refers to maintenance of the data resource itself

### Distribution Information

#### 32. Distributor Contact
**ISO Path**: `mdb:distributionInfo/mrd:MD_Distribution/mrd:distributor/mrd:MD_Distributor/mrd:distributorContact`
**CIOOS Source**: `record['contact']` where `'distributor' in roles`
**CIOOS Form Source**: `contacts` with role "distributor"
**Required**: Yes (CIOOS core mandatory)

#### 33. Transfer Options (Distribution URLs)
**ISO Path**: `mdb:distributionInfo/mrd:MD_Distribution/mrd:transferOptions/mrd:MD_DigitalTransferOptions/mrd:onLine/cit:CI_OnlineResource`
**CIOOS Source**: `record['distribution']`
**CIOOS Form Source**: `distribution` array
**Structure**:
- `cit:linkage`: Distribution URL
- `cit:protocol`: "WWW:LINK"
- `cit:name`: Distribution name (auto-detects "ERDDAP" for ERDDAP URLs)
- `cit:description`: Distribution description

### Lineage/History Information

#### 34. Resource Lineage
**ISO Path**: `mdb:resourceLineage/mrl:LI_Lineage`
**CIOOS Source**: `record['metadata']['history']`
**CIOOS Form Source**: `history` array
**Structure**:

Each lineage step includes:

1. **Statement**:
   - **ISO Path**: `mrl:statement`
   - **CIOOS Source**: `history[].statement`
   - **Multilingual**: Yes

2. **Scope**:
   - **ISO Path**: `mrl:scope/mcc:MD_Scope/mcc:level/mcc:MD_ScopeCode`
   - **CIOOS Source**: `history[].scopeIso`
   - **CIOOS Form Source**: `history[].scope`

3. **Additional Documentation**:
   - **ISO Path**: `mrl:additionalDocumentation/cit:CI_Citation`
   - **CIOOS Source**: `history[].additionalDocumentation[]`
   - **CIOOS Form Source**: `history[].additionalDocumentation[]`
   - Includes title, code/URL, and online resource link

4. **Source**:
   - **ISO Path**: `mrl:source/mrl:LI_Source`
   - **CIOOS Source**: `history[].source[]`
   - Includes description, title, code, and citation

5. **Processing Step**:
   - **ISO Path**: `mrl:processStep/mrl:LI_ProcessStep`
   - **CIOOS Source**: `history[].processingStep[]`
   - Includes description, title, code, and reference

### Platform and Instruments (Acquisition Information)

#### 35. Platform
**ISO Path**: `mdb:acquisitionInformation/mac:MI_AcquisitionInformation/mac:platform/mac:MI_Platform`
**CIOOS Source**: `record['platform']`
**CIOOS Form Source**: `platforms` array
**Required**: Recommended
**Structure**:
- `mac:identifier/mcc:MD_Identifier/mcc:code`: Platform ID
- `mac:identifier/mcc:MD_Identifier/mcc:authority/cit:CI_Citation/cit:title`: Platform name
- `mac:description`: Platform description
- Authority includes role="originator" and party name

#### 36. Instruments
**ISO Path**: `mdb:acquisitionInformation/.../mac:platform/mac:MI_Platform/mac:instrument/mac:MI_Instrument`
**CIOOS Source**: `record['platform'][].instruments[]`
**CIOOS Form Source**: `instruments` array (associated with platforms)
**Structure**:
- `mac:identifier/mcc:MD_Identifier/mcc:code`: Instrument ID
- `mac:type`: Instrument type
- `mac:description`: Instrument description

## Contact/Responsible Party Structure

Contacts in ISO 19115-3 are represented by `cit:CI_Responsibility` elements with the following structure:

### Personal Contact
**CIOOS Source**: Contact with `individual` field
- `cit:role/cit:CI_RoleCode`: Role from CIOOS Form
- `cit:party/cit:CI_Individual`:
  - `cit:name`: Individual name
  - `cit:positionName`: Position
  - `cit:contactInfo/cit:CI_Contact`:
    - `cit:address/cit:CI_Address/cit:electronicMailAddress`: Email
    - `cit:onlineResource/cit:CI_OnlineResource/cit:linkage`: ORCID (if present)

### Organizational Contact
**CIOOS Source**: Contact without `individual` field
- `cit:role/cit:CI_RoleCode`: Role from CIOOS Form
- `cit:party/cit:CI_Organisation`:
  - `cit:name`: Organization name
  - `cit:contactInfo/cit:CI_Contact`:
    - `cit:address/cit:CI_Address`: Address, city, country, email
    - `cit:onlineResource`: Organization URL, ROR (if present)

### Role Code Mapping

CIOOS Form roles map directly to ISO 19115 CI_RoleCode values:
- resourceProvider, custodian, owner, user, distributor, originator
- pointOfContact, principalInvestigator, processor, publisher, author
- sponsor, coAuthor, collaborator, editor, mediator, rightsHolder
- contributor, funder, stakeholder

## Special Processing

### 1. Bilingual Text Handling

Bilingual fields use the `PT_FreeText` pattern:
```xml
<cit:title>
  <gco:CharacterString>Title in default language</gco:CharacterString>
  <lan:PT_FreeText>
    <lan:textGroup>
      <lan:LocalisedCharacterString locale="#en">English Title</lan:LocalisedCharacterString>
    </lan:textGroup>
    <lan:textGroup>
      <lan:LocalisedCharacterString locale="#fr">Titre français</lan:LocalisedCharacterString>
    </lan:textGroup>
  </lan:PT_FreeText>
</cit:title>
```

### 2. Date Normalization

Dates are normalized to ISO 8601 format:
- Full datetime: `YYYY-MM-DDTHH:MM:SSZ` → `gco:DateTime`
- Date only: `YYYY-MM-DD` → `gco:Date`
- Year only: `YYYY` → `gco:Date`
- Times ending in `T00:00:00Z` are converted to date-only format

### 3. URL Validation

URLs in online resources and identifiers are validated and escaped for XML safety.

### 4. Coordinate System

- **Geographic**: WGS84 (implied)
- **Vertical**: Specified by EPSG code in `vertical_epsg` field
- **Coordinate Order**: longitude, latitude (as per ISO 19115-3)

### 5. Language Code Conversion

Two-letter language codes are converted to three-letter ISO 639-2 codes:
- "en" → "eng"
- "fr" → "fra"

## CIOOS Metadata Profile Extensions

The CIOOS metadata profile adds specific requirements beyond base ISO 19115-3:

1. **Bilingual Support**: Mandatory for title and abstract
2. **CIOOS Core Elements**: Marked with comments in templates
3. **Specific Codelists**: CIOOS-specific vocabularies for EOV, taxa
4. **Distribution Requirements**: ERDDAP URL auto-detection
5. **Platform/Instrument**: Enhanced acquisition information structure

## Standards and References

- **ISO 19115-1:2014**: Geographic information - Metadata - Part 1: Fundamentals
- **ISO 19115-3:2016**: Geographic information - Metadata - Part 3: XML schema implementation
- **CIOOS Metadata Profile**: https://cioos-siooc.github.io/metadata-profile/
- **XML Schema Location**: http://standards.iso.org/iso/19115/-3/mdb/2.0

## File References

- **XML generation module**: [xml.py](cioos_metadata_conversion/xml.py)
- **External template package**: [metadata-xml](https://github.com/cioos-siooc/metadata-xml)
- **Main Jinja2 template**: `metadata-xml/metadata_xml/iso19115-cioos-template/main.j2`
- **Contact template**: `metadata-xml/metadata_xml/iso19115-cioos-template/contact.j2`
- **Bilingual template**: `metadata-xml/metadata_xml/iso19115-cioos-template/bilingual.j2`
- **CIOOS Form to CIOOS transformation**: [firebase_to_cioos.py](cioos_metadata_conversion/firebase_to_cioos.py)
- **Test records**: [tests/records/](tests/records/)
- **Unit tests**: [test_xml.py](tests/test_xml.py)

## Usage Example

```python
from cioos_metadata_conversion import xml

# record is a CIOOS-formatted dictionary
iso_xml = xml.xml(record)

# Or using the Record class
from cioos_metadata_conversion.record import Record

record = Record(source="path/to/record.yaml", schema="CIOOS")
record.load()
iso_xml = record.convert_to("iso19115-3_xml")
```

## Validation

The generated XML should validate against:
- ISO 19115-3 XML schemas (https://schemas.isotc211.org/)
- CIOOS metadata profile requirements
- Canadian government metadata standards (where applicable)

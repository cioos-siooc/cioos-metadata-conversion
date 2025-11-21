# CIOOS Form Schema

The CIOOS Form is a web-based metadata entry interface built on Firebase that allows researchers and data managers to create standardized metadata records for ocean datasets. This document describes the structure and fields of the CIOOS Form schema.

## Overview

The CIOOS Form (also called the CIOOS Metadata Entry Form) is:

- **Web-based**: Accessible at https://cioos-siooc.github.io/metadata-entry-form
- **Bilingual**: Supports English and French metadata entry
- **Firebase-backed**: Data stored in Firebase Realtime Database
- **Standards-aligned**: Designed to capture data for multiple metadata standards

## Form URL Structure

```
https://cioos-siooc.github.io/metadata-entry-form#/{language}/{region}/{userID}/{recordID}
```

- `language`: `en` or `fr`
- `region`: Regional identifier (e.g., `stlaurent`, `pacific`, `atlantic`)
- `userID`: Firebase user identifier
- `recordID`: Unique record identifier

## Schema Structure

### Top-Level Fields

The CIOOS Form schema is a flat JSON structure with the following main sections:

```json
{
  "identifier": "uuid",
  "recordID": "firebase-record-id",
  "userID": "firebase-user-id",
  "region": "stlaurent",
  "language": "en",
  "created": "2025-06-25T17:24:48.469Z",
  "title": {...},
  "abstract": {...},
  "contacts": [...],
  "map": {...},
  "keywords": {...},
  "eov": [...],
  "taxa": [...],
  "distribution": [...],
  "history": [...],
  "projects": [...],
  ...
}
```

## Field Reference

### Identifiers and Metadata

#### identifier
**Type**: String (UUID)
**Required**: Yes
**Description**: Unique identifier for the metadata record
**Example**: `"9d1a8fe4-2675-4e34-8b65-16459736535a"`

#### datasetIdentifier
**Type**: String (DOI URL)
**Required**: No
**Description**: Persistent identifier for the dataset (usually a DOI)
**Example**: `"https://doi.org/10.26071/mxtr-gp72"`

#### recordID
**Type**: String
**Description**: Firebase record ID
**Example**: `"-OTS9E-8LKZrL_Yuggg0"`

#### userID
**Type**: String
**Description**: Firebase user ID of record creator
**Example**: `"Ea7wMTBNmvWBD2n1oSc8X0KQi9z1"`

#### region
**Type**: String
**Values**: `"stlaurent"`, `"pacific"`, `"atlantic"`, `"hakai"`
**Description**: CIOOS regional node

#### language
**Type**: String
**Values**: `"en"` or `"fr"`
**Description**: Primary language of the metadata

#### created
**Type**: String (ISO 8601 datetime)
**Description**: Last modification timestamp
**Example**: `"2025-06-25T17:24:48.469Z"`

### Descriptive Metadata

#### title
**Type**: Bilingual object
**Required**: Yes
**Structure**:
```json
{
  "title": {
    "en": "English Title",
    "fr": "Titre français",
    "translations": {
      "en": {
        "message": "translation note",
        "verified": false
      }
    }
  }
}
```

#### abstract
**Type**: Bilingual object
**Required**: Yes
**Description**: Dataset description/summary
**Structure**: Same as title with `en` and `fr` keys
**Supports**: Markdown formatting

#### edition
**Type**: String
**Description**: Version or edition of the dataset
**Example**: `"1.0.0"`

#### comment
**Type**: Bilingual object or String
**Description**: Additional comments about the dataset

#### limitations
**Type**: Bilingual object or String
**Description**: Limitations or constraints on data use

### Contacts

#### contacts
**Type**: Array of contact objects
**Required**: Yes (at least one)
**Structure**:
```json
{
  "contacts": [
    {
      "role": ["owner", "pointOfContact"],
      "inCitation": true,
      "givenNames": "FirstName",
      "lastName": "LastName",
      "indPosition": "Position Title",
      "indEmail": "person@example.org",
      "indOrcid": "https://orcid.org/0000-0000-0000-0000",
      "orgName": "Organization Name",
      "orgEmail": "org@example.org",
      "orgURL": "https://example.org",
      "orgAdress": "123 Street",
      "orgCity": "City",
      "orgCountry": "Canada",
      "orgRor": "https://ror.org/..."
    }
  ]
}
```

**Contact Roles**:
- `owner`: Data owner
- `pointOfContact`: Point of contact
- `custodian`: Metadata custodian
- `distributor`: Data distributor
- `publisher`: Publisher
- `principalInvestigator`: Principal investigator
- `processor`: Data processor
- `originator`: Originator
- `author`: Author
- `coAuthor`: Co-author
- `collaborator`: Collaborator
- `contributor`: Contributor
- `editor`: Editor
- `funder`: Funder
- `sponsor`: Sponsor
- `rightsHolder`: Rights holder
- `stakeholder`: Stakeholder
- `mediator`: Mediator
- `resourceProvider`: Resource provider

#### organization
**Type**: String
**Description**: Optional top-level organization name
**Note**: If provided, creates an additional contact with `owner` role

### Geographic Extent

#### map
**Type**: Object
**Required**: Yes
**Structure**:
```json
{
  "map": {
    "west": "-125.0",
    "east": "-124.0",
    "south": "48.0",
    "north": "49.0",
    "polygon": "48.0,-125.0 48.0,-124.0 49.0,-124.0 49.0,-125.0",
    "description": {
      "en": "Geographic area name",
      "fr": "Nom de la zone géographique"
    },
    "descriptionIdentifier": "uuid"
  }
}
```

**Note**: Either bounding box (west/east/south/north) OR polygon is required
**Coordinate Format**: Strings, polygon in "lat,long" format (transformed during conversion)

### Vertical Extent

#### verticalExtentMin
**Type**: String (numeric)
**Description**: Minimum depth/height
**Example**: `"0"`

#### verticalExtentMax
**Type**: String (numeric)
**Description**: Maximum depth/height
**Example**: `"100"`

#### verticalExtentDirection
**Type**: String
**Values**: `"heightPositive"` or `"depthPositive"`
**Description**: Vertical coordinate direction

#### verticalExtentEPSG
**Type**: String
**Description**: EPSG code for vertical reference system
**Example**: `"5829"`

#### noVerticalExtent
**Type**: Boolean
**Description**: Flag indicating no vertical extent applies

### Temporal Coverage

#### dateStart
**Type**: String (ISO 8601 datetime)
**Description**: Start of temporal coverage
**Example**: `"2025-01-01T17:00:00.000Z"`

#### dateEnd
**Type**: String (ISO 8601 datetime)
**Description**: End of temporal coverage
**Example**: `"2025-03-01T17:00:00.000Z"`

#### timeFirstPublished
**Type**: String (ISO 8601 datetime)
**Description**: Date dataset was first published

#### datePublished
**Type**: String (ISO 8601 datetime)
**Description**: Publication date

#### dateRevised
**Type**: String (ISO 8601 datetime)
**Description**: Last revision date

### Keywords and Vocabularies

#### keywords
**Type**: Bilingual object with arrays
**Structure**:
```json
{
  "keywords": {
    "en": ["keyword1", "keyword2", "keyword3"],
    "fr": ["mot-clé1", "mot-clé2", "mot-clé3"]
  }
}
```

#### eov
**Type**: Array of strings
**Description**: Essential Ocean Variables (EOV) from GOOS vocabulary
**Values**: Camel-case codes (e.g., `"oxygen"`, `"invertebrateAbundanceAndDistribution"`)
**Example**:
```json
{
  "eov": ["oxygen", "nutrients", "seaSurfaceTemperature"]
}
```

#### taxa
**Type**: Array of GBIF taxonomy objects
**Description**: Taxonomic information from GBIF
**Structure**:
```json
{
  "taxa": [
    {
      "kingdom": "Animalia",
      "phylum": "Mollusca",
      "class": "Gastropoda",
      "order": "Stylommatophora",
      "family": "Helicidae",
      "genus": "Helix",
      "species": "Helix pomatia",
      "canonicalName": "Helix pomatia",
      "scientificName": "Helix pomatia Linnaeus, 1758",
      "key": 1234567,
      "rank": "SPECIES"
    }
  ]
}
```

#### noTaxa
**Type**: Boolean
**Description**: Flag indicating taxa information is not applicable

### Projects and Status

#### projects
**Type**: Array of strings
**Description**: Associated research projects
**Example**: `["Coastal Environmental Baseline Program", "Ocean Observing Initiative"]`

#### progress
**Type**: String
**Values**: `"completed"`, `"onGoing"`, `"planned"`, `"obsolete"`, `"historicalArchive"`, etc.
**Description**: Dataset progress/status code

#### status
**Type**: String
**Description**: Publication workflow status

#### metadataScope
**Type**: String
**Values**: `"Dataset"`, `"Series"`, `"Service"`, etc.
**Description**: Type of resource being described

#### metadataScopeIso
**Type**: String
**Description**: ISO version of metadata scope

### Distribution

#### distribution
**Type**: Array of distribution objects
**Structure**:
```json
{
  "distribution": [
    {
      "url": "https://example.org/data",
      "name": {
        "en": "Distribution Name",
        "fr": "Nom de distribution"
      },
      "description": {
        "en": "Description...",
        "fr": "Description..."
      }
    }
  ]
}
```

### License and Constraints

#### license
**Type**: String
**Values**: License code (e.g., `"CC-BY-4.0"`, `"CC-BY-NC-4.0"`, `"CC0"`)
**Description**: Data license code
**Resolved**: To full license information via lookup table

### History and Lineage

#### history
**Type**: Array of history objects
**Description**: Provenance and processing history
**Structure**:
```json
{
  "history": [
    {
      "scope": "Dataset",
      "statement": {
        "en": "History statement...",
        "fr": "Déclaration historique..."
      },
      "additionalDocumentation": [
        {
          "code": "https://example.org/doc",
          "title": {"en": "Doc Title"},
          "authority": "URL"
        }
      ],
      "source": [...],
      "processingStep": [...]
    }
  ]
}
```

### Associated Resources

#### associated_resources
**Type**: Array of resource objects
**Description**: Related datasets, publications, etc.
**Structure**:
```json
{
  "associated_resources": [
    {
      "association_type": "IsReferencedBy",
      "association_type_iso": "crossReference",
      "authority": "DOI",
      "code": "https://doi.org/10.1002/example",
      "title": {
        "en": "Related Publication Title"
      }
    }
  ]
}
```

**Association Types**:
- `IsReferencedBy`: This dataset is referenced by the resource
- `IsCitedBy`: This dataset is cited by the resource
- `IsSupplementTo`: This dataset supplements the resource
- `IsPartOf`: This dataset is part of the resource

### Platforms and Instruments

#### platforms
**Type**: Array of platform objects
**Structure**:
```json
{
  "platforms": [
    {
      "id": "platform-uuid",
      "name": {"en": "Platform Name"},
      "type": "coastal structure",
      "description": {"en": "Platform description"},
      "authority": {"en": "Authority name"},
      "role": "originator"
    }
  ]
}
```

#### instruments
**Type**: Array of instrument objects
**Structure**:
```json
{
  "instruments": [
    {
      "id": "instrument-uuid",
      "type": {"en": "Sensor Type"},
      "description": {"en": "Instrument description"},
      "platform": "platform-uuid"
    }
  ]
}
```

#### noPlatform
**Type**: Boolean
**Description**: Flag indicating no platform information applies

### Workflow Fields

#### doiCreationStatus
**Type**: String
**Values**: `"draft"`, `"published"`
**Description**: DOI creation workflow status

#### filename
**Type**: String
**Description**: Associated filename (if any)

#### lastEditedBy
**Type**: Object
**Structure**:
```json
{
  "lastEditedBy": {
    "displayName": "User Name",
    "email": "user@example.org"
  }
}
```

#### category
**Type**: String
**Description**: Internal categorization

#### resourceType
**Type**: Array of strings
**Description**: Type of resource (e.g., `["biological"]`, `["physical"]`)

## Translation Support

### Translation Object Structure

Bilingual fields can include translation metadata:

```json
{
  "title": {
    "en": "Original English",
    "fr": "Traduction française",
    "translations": {
      "fr": {
        "message": "text translated using the Amazon translate service / texte traduit à l'aide du service de traduction Amazon",
        "verified": false
      }
    }
  }
}
```

- `message`: Note about translation method
- `verified`: Whether translation has been verified by a human

## Validation Rules

### Required Fields

At form submission, the following are typically required:

- `identifier`
- `language`
- `title` (at least one language)
- `abstract` (at least one language)
- `contacts` (at least one with required fields)
- `map` (bounding box or polygon)

### Conditional Requirements

- If `noPlatform` is false, platform information should be provided
- If `noTaxa` is false, taxa information should be provided
- Either bounding box OR polygon is required (not both)
- At least one contact must have `owner` role

## Form Behavior

### Auto-save

The form auto-saves to Firebase as users type, preventing data loss.

### URL-based Routing

The form uses URL hash fragments for navigation:
- Record selection
- Form sections
- Language switching

### Validation

Client-side validation ensures:
- Required fields are filled
- Valid email formats
- Valid URLs (DOI, ORCID, ROR)
- Geographic coordinates in valid ranges

## Export Format

When exported from Firebase, records are JSON objects with the structure described above. These exports can be converted using:

```bash
cioos_metadata_conversion convert \
  --input firebase-export.json \
  --input-schema firebase \
  --output-format iso19115-3_xml
```

## Form Versions

The form schema evolves over time. Key versions:

- **v1**: Initial implementation
- **v2**: Added platform/instrument support
- **v3**: Enhanced lineage/history
- **Current**: See form source code for latest

## See Also

- [CIOOS Form to CIOOS Mapping](mappings/cioos-form-to-cioos.md) - How form data is transformed
- [Input Schemas](input-schemas.md) - Working with Firebase exports
- [CIOOS Metadata Entry Form](https://cioos-siooc.github.io/metadata-entry-form) - Live form
- [Form Source Code](https://github.com/cioos-siooc/metadata-entry-form) - GitHub repository

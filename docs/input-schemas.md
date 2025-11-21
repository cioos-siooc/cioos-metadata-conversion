# Input Schemas

The CIOOS Metadata Conversion tool supports two input schemas: CIOOS intermediate format and Firebase (CIOOS Form) exports.

## CIOOS Intermediate Format

The canonical format used internally by the conversion tool. This is a structured YAML or JSON representation that serves as the source for all output conversions.

### Format: YAML or JSON

Both YAML and JSON representations are supported:

```yaml
# record.yaml
metadata:
  naming_authority: ca.cioos
  identifier: uuid-here
  language: en
identification:
  title:
    en: "Dataset Title"
  abstract:
    en: "Description..."
```

```json
{
  "metadata": {
    "naming_authority": "ca.cioos",
    "identifier": "uuid-here",
    "language": "en"
  },
  "identification": {
    "title": {"en": "Dataset Title"},
    "abstract": {"en": "Description..."}
  }
}
```

### Structure

The CIOOS format has four main sections:

#### metadata
Metadata about the metadata record itself:
- `naming_authority`: Authority for identifiers (typically "ca.cioos")
- `identifier`: Unique metadata record identifier
- `language`: Primary language ("en" or "fr")
- `dates`: Publication and revision dates
- `use_constraints`: License and limitations

#### spatial
Geographic and vertical extent:
- `bbox`: Bounding box `[west, south, east, north]`
- `polygon`: WKT polygon string
- `vertical`: Vertical extent `[min, max]`
- `description`: Geographic description

#### identification
Resource identification and description:
- `title`: Bilingual title
- `identifier`: Dataset identifier (e.g., DOI)
- `abstract`: Bilingual abstract
- `keywords`: Keywords by vocabulary (default, eov, taxa)
- `dates`: Creation, publication, revision dates
- `temporal_begin/end`: Temporal coverage
- `project`: Associated projects
- `progress_code`: Status (completed, onGoing, etc.)

#### contact
Responsible parties:
- `roles`: Array of roles (owner, distributor, etc.)
- `organization`: Organization details
- `individual`: Individual details (optional)
- `inCitation`: Whether to include in citations

See the [CIOOS Form to CIOOS mapping](mappings/cioos-form-to-cioos.md) for complete structure details.

### Usage

```bash
cioos_metadata_conversion convert \
  --input record.yaml \
  --input-schema CIOOS \
  --output-format datacite_xml
```

## Firebase Format

JSON export from the CIOOS metadata entry form. This format is automatically transformed to the CIOOS intermediate format during conversion.

### Format: JSON

Firebase exports are JSON files from the metadata entry form:

```json
{
  "identifier": "uuid",
  "language": "en",
  "title": {
    "en": "Dataset Title",
    "fr": "Titre du jeu de données"
  },
  "abstract": {
    "en": "Description...",
    "fr": "Description..."
  },
  "contacts": [...],
  "map": {
    "west": "-125.0",
    "south": "48.0",
    "east": "-124.0",
    "north": "49.0"
  }
}
```

### Key Differences from CIOOS Format

1. **Flat Structure**: Firebase format is flatter than CIOOS
2. **String Coordinates**: Geographic coordinates are strings, not floats
3. **Different Field Names**: Uses form field names (e.g., `datasetIdentifier` vs `identifier`)
4. **Lat,Long Order**: Polygon coordinates in lat,long order (transformed to long,lat)

### Transformation Process

Firebase format is automatically converted to CIOOS using `firebase_to_cioos.record_json_to_yaml()`:

1. **Restructuring**: Fields reorganized into CIOOS structure
2. **Type Conversion**: Strings → floats for coordinates
3. **Coordinate Transform**: lat,long → long,lat for polygons
4. **Enrichment**: License codes resolved, EOVs translated
5. **Contact Processing**: Contacts restructured, distributor auto-assigned

See the [CIOOS Form to CIOOS mapping](mappings/cioos-form-to-cioos.md) for complete transformation details.

### Usage

```bash
cioos_metadata_conversion convert \
  --input firebase-export.json \
  --input-schema firebase \
  --output-format iso19115-3_xml
```

## Loading from URLs

Both schemas support loading from URLs:

```bash
cioos_metadata_conversion convert \
  --input "https://example.com/metadata.yaml" \
  --input-schema CIOOS \
  --output-format datacite_xml
```

## Schema Selection

### When to Use CIOOS

- Working with already-processed metadata
- Batch processing from a catalog
- Integrating with other CIOOS tools
- Maximum control over field values

### When to Use Firebase

- Direct exports from metadata entry form
- Preserving form structure
- Initial conversion from form to standards
- Working with form backups

## Validation

### CIOOS Format

Required fields:
- `metadata.identifier`
- `metadata.language`
- `identification.title` (with at least one language)
- `identification.abstract` (with at least one language)
- `contact` (at least one)

### Firebase Format

Required fields:
- `identifier`
- `language`
- `title.en` or `title.fr`
- `abstract.en` or `abstract.fr`
- `contacts` (at least one)
- `map` with bounding box or polygon

## Examples

### Minimal CIOOS Record

```yaml
metadata:
  naming_authority: ca.cioos
  identifier: abc-123
  language: en
identification:
  title:
    en: "Minimal Dataset"
  abstract:
    en: "A minimal example"
spatial:
  bbox: [-125.0, 48.0, -124.0, 49.0]
contact:
  - roles: [owner]
    organization:
      name: "Example Org"
```

### Minimal Firebase Record

```json
{
  "identifier": "abc-123",
  "language": "en",
  "title": {"en": "Minimal Dataset"},
  "abstract": {"en": "A minimal example"},
  "map": {
    "west": "-125.0",
    "south": "48.0",
    "east": "-124.0",
    "north": "49.0"
  },
  "contacts": [{
    "role": ["owner"],
    "orgName": "Example Org"
  }]
}
```

## Converting Between Schemas

To convert Firebase to CIOOS format:

```bash
cioos_metadata_conversion convert \
  --input firebase-export.json \
  --input-schema firebase \
  --output-format yaml \
  --output-file cioos-record.yaml
```

Then use the CIOOS format for subsequent conversions:

```bash
cioos_metadata_conversion convert \
  --input cioos-record.yaml \
  --input-schema CIOOS \
  --output-format datacite_xml
```

## See Also

- [CIOOS Form to CIOOS Mapping](mappings/cioos-form-to-cioos.md) - Detailed field mappings
- [Usage Guide](usage.md) - Examples using both schemas
- [CLI Reference](cli.md) - Command-line options

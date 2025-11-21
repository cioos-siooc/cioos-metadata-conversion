# Usage Guide

This guide provides detailed examples and workflows for using the CIOOS Metadata Conversion tool.

## Understanding the Conversion Pipeline

The tool uses a two-stage conversion pipeline:

```
Input Format → CIOOS Intermediate Format → Output Format
```

This architecture ensures consistency and makes it easy to add new formats.

## Input Schemas

### CIOOS Intermediate Format

The canonical format used internally. It's a structured representation (YAML or JSON) optimized for conversion.

**Example structure**:
```yaml
metadata:
  naming_authority: ca.cioos
  identifier: uuid-here
  language: en
identification:
  title:
    en: "Dataset Title"
    fr: "Titre du jeu de données"
  abstract:
    en: "Dataset description..."
spatial:
  bbox: [-125.0, 48.0, -124.0, 49.0]
contact:
  - roles: [owner, distributor]
    organization:
      name: "Organization Name"
```

### Firebase Format

JSON export from the CIOOS metadata entry form. This is automatically converted to CIOOS intermediate format.

## CLI Usage Patterns

### Single File Conversion

Convert one file to one output:

```bash
cioos_metadata_conversion convert \
  --input record.yaml \
  --input-schema CIOOS \
  --output-format iso19115-3_xml \
  --output-file record.xml
```

### Batch Conversion

Convert multiple files with glob patterns:

```bash
# All YAML files in a directory
cioos_metadata_conversion convert \
  --input "records/*.yaml" \
  --input-schema CIOOS \
  --output-format datacite_json \
  --output-dir ./datacite

# Recursive processing
cioos_metadata_conversion convert \
  --input "data/**/*.yaml" \
  --recursive \
  --input-schema CIOOS \
  --output-format iso19115-3_xml \
  --output-dir ./xml-output
```

### Format Conversion Chain

Convert between formats:

```bash
# Firebase → CIOOS intermediate format
cioos_metadata_conversion convert \
  -i firebase-export.json \
  --input-schema firebase \
  -f yaml \
  -o cioos-record.yaml

# CIOOS intermediate format → ISO 19115-3 XML
cioos_metadata_conversion convert \
  -i cioos-record.yaml \
  --input-schema CIOOS \
  -f iso19115-3_xml \
  -o record.xml
```

## Python API Usage

### Basic Workflow

```python
from cioos_metadata_conversion.record import Record

# Load and convert
record = Record(source="record.yaml", schema="CIOOS")
record.load().convert_to_cioos_schema()

# Generate different outputs
iso_xml = record.convert_to("iso19115-3_xml")
datacite = record.convert_to("datacite_json")
acdd = record.convert_to("acdd_yaml")

# Save to files
with open("record.xml", "w") as f:
    f.write(iso_xml)
```

### Working with Firebase Data

```python
from cioos_metadata_conversion import firebase_to_cioos
from cioos_metadata_conversion.record import Record
import json

# Load Firebase export
with open("firebase-export.json") as f:
    firebase_data = json.load(f)

# Convert to CIOOS format
cioos_data = firebase_to_cioos.record_json_to_yaml(firebase_data)

# Use with Record for further conversions
record = Record(source=cioos_data, schema="CIOOS")
xml = record.convert_to("iso19115-3_xml")
```

### Batch Processing in Python

```python
from pathlib import Path
from cioos_metadata_conversion.record import Record

input_dir = Path("records")
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

for yaml_file in input_dir.glob("*.yaml"):
    try:
        # Load record
        record = Record(source=str(yaml_file), schema="CIOOS")
        record.load().convert_to_cioos_schema()

        # Convert to DataCite XML
        datacite_xml = record.convert_to("datacite_xml")

        # Save output
        output_file = output_dir / f"{yaml_file.stem}.xml"
        output_file.write_text(datacite_xml)

        print(f"✓ Converted {yaml_file.name}")
    except Exception as e:
        print(f"✗ Failed {yaml_file.name}: {e}")
```

### Error Handling

```python
from cioos_metadata_conversion.record import Record
from loguru import logger

try:
    record = Record(source="record.yaml", schema="CIOOS")
    record.load().convert_to_cioos_schema()

    if not record.metadata:
        raise ValueError("No metadata found in record")

    xml = record.convert_to("iso19115-3_xml")

except FileNotFoundError:
    logger.error("Input file not found")
except ValueError as e:
    logger.error(f"Invalid record: {e}")
except Exception as e:
    logger.exception("Conversion failed")
```

## Specific Format Examples

### ISO 19115-3 XML

Generate standards-compliant geospatial metadata:

```bash
cioos_metadata_conversion convert \
  -i record.yaml \
  --input-schema CIOOS \
  -f iso19115-3_xml \
  -o record.xml
```

**Use cases**:
- Catalog harvesting (OGC CSW)
- Geospatial metadata portals
- Standards compliance

### DataCite

Generate metadata for DOI registration:

```bash
# XML format (for DataCite API)
cioos_metadata_conversion convert \
  -i record.yaml \
  --input-schema CIOOS \
  -f datacite_xml \
  -o datacite.xml

# JSON format (for programmatic use)
cioos_metadata_conversion convert \
  -i record.yaml \
  --input-schema CIOOS \
  -f datacite_json \
  -o datacite.json
```

**Use cases**:
- DOI registration
- Data citation
- Repository integration

### ERDDAP/ACDD

Generate attributes for ERDDAP server or NetCDF files:

```bash
# YAML format (human-readable)
cioos_metadata_conversion convert \
  -i record.yaml \
  --input-schema CIOOS \
  -f acdd_yaml \
  -o attributes.yaml

# JSON format (programmatic)
cioos_metadata_conversion convert \
  -i record.yaml \
  --input-schema CIOOS \
  -f acdd_json \
  -o attributes.json
```

**Use cases**:
- ERDDAP dataset configuration
- NetCDF global attributes
- ACDD compliance

### Citation File Format

Generate citation files for datasets:

```bash
cioos_metadata_conversion convert \
  -i record.yaml \
  --input-schema CIOOS \
  -f cff \
  -o CITATION.cff
```

**Use cases**:
- Dataset citation
- Software repositories
- GitHub integration

## ERDDAP Integration

### Update ERDDAP datasets.xml

Automatically update ERDDAP configuration with CIOOS metadata:

```bash
cioos_metadata_conversion erddap-update \
  --datasets-xml /path/to/datasets.xml \
  --records "records/*.yaml" \
  --erddap-url "https://data.example.org/erddap" \
  --multilingual \
  --backup
```

**What it does**:
1. Matches CIOOS records to ERDDAP datasets by URL
2. Generates ACDD-compliant global attributes
3. Updates the datasets.xml file
4. Preserves existing configuration
5. Optionally creates backup

### Workflow Example

```bash
# 1. Export CIOOS metadata
cioos_metadata_conversion convert \
  -i cioos-records/*.yaml \
  --input-schema CIOOS \
  -f acdd_yaml \
  -p ./acdd-attributes

# 2. Review generated attributes
cat acdd-attributes/dataset1.acdd_yaml

# 3. Update ERDDAP configuration
cioos_metadata_conversion erddap-update \
  -d /opt/erddap/datasets.xml \
  -r cioos-records/*.yaml \
  -u "https://data.example.org/erddap" \
  --backup \
  --multilingual

# 4. Reload ERDDAP
# (ERDDAP-specific reload procedure)
```

## Advanced Workflows

### Quality Control Pipeline

```bash
#!/bin/bash
# validate-and-convert.sh

INPUT_DIR="source-records"
OUTPUT_DIR="validated-output"
ERROR_LOG="errors.log"

mkdir -p "$OUTPUT_DIR"

for record in "$INPUT_DIR"/*.yaml; do
    echo "Processing $record..."

    # Convert to ISO 19115-3 XML
    if cioos_metadata_conversion convert \
        -i "$record" \
        --input-schema CIOOS \
        -f iso19115-3_xml \
        -o "$OUTPUT_DIR/$(basename "$record" .yaml).xml" \
        2>> "$ERROR_LOG"; then
        echo "✓ Success"
    else
        echo "✗ Failed - check $ERROR_LOG"
    fi
done
```

### Multi-Format Export

Generate all formats for a record:

```bash
#!/bin/bash
# export-all-formats.sh

INPUT="record.yaml"
OUTPUT_DIR="exports"

mkdir -p "$OUTPUT_DIR"

formats=("iso19115-3_xml" "datacite_xml" "datacite_json" "acdd_yaml" "cff")

for format in "${formats[@]}"; do
    echo "Generating $format..."
    cioos_metadata_conversion convert \
        -i "$INPUT" \
        --input-schema CIOOS \
        -f "$format" \
        -p "$OUTPUT_DIR"
done

echo "All formats exported to $OUTPUT_DIR"
```

### Integration with CI/CD

```yaml
# .github/workflows/convert-metadata.yml
name: Convert Metadata

on:
  push:
    paths:
      - 'metadata/*.yaml'

jobs:
  convert:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install converter
        run: |
          pip install git+https://github.com/cioos-siooc/cioos-metadata-conversion.git

      - name: Convert to ISO 19115-3
        run: |
          cioos_metadata_conversion convert \
            -i "metadata/*.yaml" \
            --input-schema CIOOS \
            -f iso19115-3_xml \
            -p xml-output

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: xml-metadata
          path: xml-output/
```

## Tips and Best Practices

### 1. Validate Input Data

Ensure your CIOOS records have required fields:
- `metadata.identifier`
- `metadata.language`
- `identification.title`
- `identification.abstract`
- `contact` (at least one)

### 2. Use Appropriate Formats

- **ISO 19115-3 XML**: Geospatial catalogs, long-term archival
- **DataCite**: DOI registration, citation
- **ACDD**: ERDDAP, NetCDF, CF-compliant datasets
- **CFF**: Citation, GitHub repositories

### 3. Bilingual Metadata

Ensure bilingual fields have both English and French:

```yaml
title:
  en: "English Title"
  fr: "Titre français"
abstract:
  en: "English abstract..."
  fr: "Résumé français..."
```

### 4. Testing Conversions

Always test on a single record before batch processing:

```bash
# Test first
cioos_metadata_conversion convert -i test-record.yaml ...

# Then batch
cioos_metadata_conversion convert -i "all-records/*.yaml" ...
```

### 5. Backup Original Data

Keep backups before bulk conversions or ERDDAP updates:

```bash
# Backup
cp -r records/ records-backup/

# Convert
cioos_metadata_conversion convert ...
```

## Troubleshooting

### Empty Output

If conversion produces empty or minimal output:
- Check that required fields are present
- Verify input schema is correct
- Review logs for warnings

### Encoding Issues

Specify encoding if you have special characters:

```bash
cioos_metadata_conversion convert \
  --encoding utf-8 \
  --output-encoding utf-8 \
  ...
```

### Large Batch Processing

For very large batches, process in chunks:

```bash
# Process 100 files at a time
find records/ -name "*.yaml" | xargs -n 100 \
  cioos_metadata_conversion convert \
    --input-schema CIOOS \
    -f datacite_xml \
    -p output/
```

## Next Steps

- [CLI Reference](cli.md) - Complete CLI documentation
- [Input Schemas](input-schemas.md) - Understanding input formats
- [Output Formats](output-formats.md) - Details on output formats
- [Mappings](mappings/index.md) - Field mapping documentation

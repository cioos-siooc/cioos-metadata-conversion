# Quick Start

Get started with CIOOS Metadata Conversion in just a few minutes.

## Installation

```bash
pip install git+https://github.com/cioos-siooc/cioos-metadata-conversion.git
```

For more installation options, see the [Installation Guide](installation.md).

## Basic Workflow

### 1. Prepare Your Metadata

Ensure you have a metadata record in either:

- **CIOOS intermediate format** (YAML or JSON)
- **Firebase export** (JSON from CIOOS metadata entry form)

### 2. Convert to Target Format

```bash
cioos_metadata_conversion convert \
  --input your-record.yaml \
  --input-schema CIOOS \
  --output-format iso19115-3_xml \
  --output-file output.xml
```

### 3. Verify Output

Check the generated file:

```bash
cat output.xml
```

## Common Use Cases

### Convert to ISO 19115-3 XML

For catalog harvesting and standards compliance:

```bash
cioos_metadata_conversion convert \
  -i record.yaml \
  --input-schema CIOOS \
  -f iso19115-3_xml \
  -o record.xml
```

### Generate DataCite Metadata

For DOI registration:

```bash
cioos_metadata_conversion convert \
  -i record.yaml \
  --input-schema CIOOS \
  -f datacite_xml \
  -o datacite.xml
```

### Create ERDDAP Attributes

For ERDDAP server configuration:

```bash
cioos_metadata_conversion convert \
  -i record.yaml \
  --input-schema CIOOS \
  -f acdd_yaml \
  -o attributes.yaml
```

### Batch Processing

Convert multiple files at once:

```bash
cioos_metadata_conversion convert \
  -i "records/*.yaml" \
  --input-schema CIOOS \
  -f datacite_json \
  -p ./output
```

## Python API Quick Start

### Basic Conversion

```python
from cioos_metadata_conversion.record import Record

# Load a record
record = Record(source="record.yaml", schema="CIOOS")
record.load().convert_to_cioos_schema()

# Convert to different formats
iso_xml = record.convert_to("iso19115-3_xml")
datacite_json = record.convert_to("datacite_json")

print(iso_xml)
```

### Load from URL

```python
from cioos_metadata_conversion.record import Record

record = Record(
    source="https://example.com/metadata.yaml",
    schema="CIOOS"
)
record.load().convert_to_cioos_schema()

output = record.convert_to("datacite_xml")
```

### Convert Firebase to CIOOS

```python
from cioos_metadata_conversion import firebase_to_cioos

# Load Firebase export
with open("firebase-export.json") as f:
    firebase_data = json.load(f)

# Convert to CIOOS format
cioos_record = firebase_to_cioos.record_json_to_yaml(firebase_data)

# Now use with Record
record = Record(source=cioos_record, schema="CIOOS")
xml = record.convert_to("iso19115-3_xml")
```

## Next Steps

- [Full CLI Reference](cli.md) - All CLI commands and options
- [Usage Guide](usage.md) - Detailed examples and workflows
- [Mappings](mappings/index.md) - Understand field mappings
- [API Reference](api/record.md) - Python API documentation

## Getting Help

If you encounter issues:

1. Check the [Installation Guide](installation.md) for troubleshooting
2. Review the [CLI Reference](cli.md) for correct syntax
3. See the [Usage Guide](usage.md) for detailed examples
4. Open an issue on [GitHub](https://github.com/cioos-siooc/cioos-metadata-conversion/issues)

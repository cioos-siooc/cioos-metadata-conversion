# Output Formats

The CIOOS Metadata Conversion tool supports multiple output formats for different use cases and metadata standards.

## Available Formats

| Format | Extension | Description | Use Case |
|--------|-----------|-------------|----------|
| `iso19115-3_xml` | `.xml` | ISO 19115-3:2016 XML | Geospatial catalogs, standards compliance |
| `datacite_xml` | `.xml` | DataCite 4.5 XML | DOI registration, research data citation |
| `datacite_json` | `.json` | DataCite 4.5 JSON | Programmatic DOI management |
| `acdd_yaml` | `.yaml` | ACDD 1.3 attributes (YAML) | ERDDAP config, NetCDF metadata |
| `acdd_json` | `.json` | ACDD 1.3 attributes (JSON) | Programmatic ACDD metadata |
| `erddap` | `.xml` | ERDDAP datasets.xml | ERDDAP server integration |
| `cff` | `.cff` | Citation File Format | Dataset citation, GitHub |
| `yaml` | `.yaml` | CIOOS intermediate format | Data exchange, archival |
| `json` | `.json` | CIOOS intermediate format | Programmatic processing |

## ISO 19115-3 XML

### Description
Geographic Information - Metadata standard (ISO 19115-3:2016)

### Standard
- **Version**: ISO 19115-3:2016
- **Schema**: http://standards.iso.org/iso/19115/-3/mdb/2.0

### Features
- Complete geospatial metadata
- Bilingual support (PT_FreeText)
- Platform and instrument details
- Resource lineage
- Responsible parties with full contact info

### Use Cases
- Geospatial data catalogs
- OGC Catalog Service for the Web (CSW)
- Long-term metadata archival
- GEOSS Portal, GCMD

### Example

```bash
cioos_metadata_conversion convert \
  -i record.yaml \
  --input-schema CIOOS \
  -f iso19115-3_xml \
  -o record.xml
```

### Documentation
- [CIOOS to ISO 19115-3 Mapping](mappings/cioos-to-iso19115-3.md)
- [ISO 19115-3 Standard](http://standards.iso.org/iso/19115/)

## DataCite XML

### Description
Research data citation metadata (DataCite Schema 4.5)

### Standard
- **Version**: DataCite Metadata Schema 4.5
- **Schema**: http://schema.datacite.org/meta/kernel-4.5/

### Features
- DOI-focused metadata
- Creator and contributor details
- Funding information
- Related identifiers
- Geographic locations

### Use Cases
- DOI registration
- Research data repositories
- Data citation
- Open data portals

### Example

```bash
cioos_metadata_conversion convert \
  -i record.yaml \
  --input-schema CIOOS \
  -f datacite_xml \
  -o datacite.xml
```

### Documentation
- [CIOOS to DataCite Mapping](mappings/cioos-to-datacite.md)
- [DataCite Metadata Schema](https://schema.datacite.org/)

## DataCite JSON

### Description
Same as DataCite XML but in JSON format

### Standard
- **Version**: DataCite Metadata Schema 4.5

### Features
- Same metadata as XML version
- Easier programmatic access
- Direct API integration

### Example

```bash
cioos_metadata_conversion convert \
  -i record.yaml \
  --input-schema CIOOS \
  -f datacite_json \
  -o datacite.json
```

### Python Usage

```python
import json
from cioos_metadata_conversion.record import Record

record = Record("record.yaml", "CIOOS")
record.load().convert_to_cioos_schema()

datacite_json = json.loads(record.convert_to("datacite_json"))
print(datacite_json["identifier"])
```

## ACDD YAML

### Description
Attribute Convention for Data Discovery (ACDD 1.3) global attributes

### Standard
- **Version**: ACDD 1.3
- **Reference**: http://wiki.esipfed.org/index.php/ACDD_1-3

### Features
- ACDD-compliant global attributes
- CF conventions support
- Platform and instrument metadata
- Contact information as attributes
- Vocabulary-based keywords

### Use Cases
- ERDDAP dataset configuration
- NetCDF global attributes
- CF-compliant datasets
- THREDDS catalogs

### Example

```bash
cioos_metadata_conversion convert \
  -i record.yaml \
  --input-schema CIOOS \
  -f acdd_yaml \
  -o attributes.yaml
```

### Documentation
- [CIOOS to ERDDAP/ACDD Mapping](mappings/cioos-to-erddap-acdd.md)
- [ACDD Standard](http://wiki.esipfed.org/index.php/ACDD_1-3)

## ACDD JSON

### Description
Same as ACDD YAML but in JSON format

### Features
- Programmatic access to ACDD attributes
- Direct integration with data services
- JSON API compatibility

### Example

```python
import json
from cioos_metadata_conversion.record import Record

record = Record("record.yaml", "CIOOS")
record.load().convert_to_cioos_schema()

acdd = json.loads(record.convert_to("acdd_json"))
print(acdd["title"])
print(acdd["keywords"])
```

## ERDDAP

### Description
ERDDAP datasets.xml format with global attributes

### Standard
- **ACDD 1.3**: Attribute conventions
- **CF 1.6+**: Climate and Forecast conventions

### Features
- Direct ERDDAP integration
- Multilingual attribute support (optional)
- XML format matching ERDDAP schema
- Dataset-specific configurations

### Use Cases
- ERDDAP server configuration
- Automated metadata updates
- Dataset catalog management

### Example

```bash
cioos_metadata_conversion erddap-update \
  --datasets-xml /path/to/datasets.xml \
  --records "records/*.yaml" \
  --erddap-url "https://data.example.org/erddap" \
  --multilingual
```

### Documentation
- [CIOOS to ERDDAP/ACDD Mapping](mappings/cioos-to-erddap-acdd.md)
- [ERDDAP Documentation](https://coastwatch.pfeg.noaa.gov/erddap/download/setup.html)

## Citation File Format (CFF)

### Description
Human and machine-readable citation file format

### Standard
- **Version**: CFF 1.2.0
- **Reference**: https://citation-file-format.github.io/

### Features
- Software and dataset citation
- Author and contributor details
- Version information
- References and identifiers

### Use Cases
- Dataset citation
- GitHub repositories
- Software packages
- CITATION files

### Example

```bash
cioos_metadata_conversion convert \
  -i record.yaml \
  --input-schema CIOOS \
  -f cff \
  -o CITATION.cff
```

### Documentation
- [CFF Specification](https://citation-file-format.github.io/)
- [GitHub Citation Integration](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files)

## CIOOS Intermediate Format (YAML)

### Description
CIOOS intermediate format in YAML

### Features
- Human-readable
- Complete metadata structure
- Suitable for version control
- Easy to edit

### Use Cases
- Metadata archival
- Version control (Git)
- Manual editing
- Data exchange

### Example

```bash
# Convert Firebase to CIOOS intermediate format
cioos_metadata_conversion convert \
  -i firebase-export.json \
  --input-schema firebase \
  -f yaml \
  -o cioos-record.yaml
```

## CIOOS Intermediate Format (JSON)

### Description
CIOOS intermediate format in JSON

### Features
- Programmatic access
- API integration
- Compact format
- Easy parsing

### Use Cases
- API responses
- Automated processing
- Database storage
- Web applications

### Example

```python
import json
from cioos_metadata_conversion import firebase_to_cioos

# Convert Firebase to CIOOS intermediate format
with open("firebase-export.json") as f:
    firebase_data = json.load(f)

cioos_data = firebase_to_cioos.record_json_to_yaml(firebase_data)

with open("cioos-record.json", "w") as f:
    json.dump(cioos_data, f, indent=2)
```

## Format Comparison

| Feature | ISO 19115-3 | DataCite | ACDD | CFF |
|---------|-------------|----------|------|-----|
| **Primary Use** | Geospatial catalogs | DOI/Citation | Data servers | Software citation |
| **Bilingual** | Full support | Limited | Optional | Limited |
| **Geographic Detail** | Comprehensive | Basic | Basic | None |
| **Platform/Instruments** | Detailed | Limited | Yes | No |
| **Lineage/History** | Comprehensive | Basic | Limited | No |
| **Contact Detail** | Complete | Structured | Flat attributes | Basic |
| **File Format** | XML | XML/JSON | YAML or JSON | YAML |

## Choosing a Format

### For Geospatial Metadata
→ Use **ISO 19115-3 XML**

### For DOI Registration
→ Use **DataCite XML** or **DataCite JSON**

### For ERDDAP/NetCDF
→ Use **ACDD** (YAML or JSON) or **ERDDAP**

### For Citation
→ Use **CFF** or **DataCite**

### For Data Exchange
→ Use **CIOOS Intermediate Format** (YAML or JSON)

## See Also

- [Usage Guide](usage.md) - Detailed conversion examples
- [CLI Reference](cli.md) - Command-line options
- [Mappings Documentation](mappings/index.md) - Field-level mappings

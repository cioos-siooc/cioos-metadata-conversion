# CLI Reference

The CIOOS Metadata Conversion tool provides a command-line interface (CLI) for converting metadata records between different formats and standards.

## Main Command

```bash
cioos_metadata_conversion [OPTIONS] COMMAND [ARGS]...
```

### Global Options

- `--help`: Show help message and exit

## Commands

### convert

Convert metadata records to different metadata formats or standards.

#### Usage

```bash
cioos_metadata_conversion convert [OPTIONS]
```

#### Options

##### Required Options

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--input` | `-i` | PATH | Input file or URL |
| `--input-schema` | | CHOICE | Input file schema: `CIOOS` or `firebase` |
| `--output-format` | `-f` | CHOICE | Output format (see [Output Formats](#output-formats)) |

##### Optional Options

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--recursive` | `-r` | FLAG | `false` | Process files recursively |
| `--encoding` | | TEXT | `utf-8` | Encoding of the input file |
| `--output-dir` | `-p` | PATH | `.` | Output directory |
| `--output-file` | `-o` | PATH | | Output file (single file only) |
| `--output-encoding` | | TEXT | `utf-8` | Encoding of the output file |

#### Output Formats

Available output format values for `--output-format`:

| Format | Description |
|--------|-------------|
| `json` | CIOOS intermediate format (JSON) |
| `yaml` | CIOOS intermediate format (YAML) |
| `erddap` | ERDDAP datasets.xml attributes |
| `cff` | Citation File Format |
| `xml` | ISO 19115-3 XML (deprecated, use `iso19115-3_xml`) |
| `iso19115_xml` | ISO 19115-3 XML (deprecated, use `iso19115-3_xml`) |
| `iso19115-3_xml` | ISO 19115-3 XML |
| `datacite_json` | DataCite JSON |
| `datacite_xml` | DataCite XML |
| `acdd_json` | ACDD 1.3 attributes (JSON) |
| `acdd_yaml` | ACDD 1.3 attributes (YAML) |

#### Examples

**Convert a single CIOOS intermediate format file to ISO 19115-3 XML**:

```bash
cioos_metadata_conversion convert \
  --input record.yaml \
  --input-schema CIOOS \
  --output-format iso19115-3_xml \
  --output-file record.xml
```

**Convert Firebase JSON to DataCite XML**:

```bash
cioos_metadata_conversion convert \
  --input firebase-export.json \
  --input-schema firebase \
  --output-format datacite_xml \
  --output-dir ./output
```

**Batch convert multiple YAML files**:

```bash
cioos_metadata_conversion convert \
  --input "records/*.yaml" \
  --input-schema CIOOS \
  --output-format datacite_json \
  --output-dir ./datacite-output
```

**Recursive directory processing**:

```bash
cioos_metadata_conversion convert \
  --input "data/**/*.yaml" \
  --recursive \
  --input-schema CIOOS \
  --output-format iso19115-3_xml \
  --output-dir ./xml-output
```

**Convert from URL**:

```bash
cioos_metadata_conversion convert \
  --input "https://example.com/metadata.yaml" \
  --input-schema CIOOS \
  --output-format datacite_xml \
  --output-file output.xml
```

**Specify custom encoding**:

```bash
cioos_metadata_conversion convert \
  --input record.yaml \
  --encoding utf-8 \
  --input-schema CIOOS \
  --output-format iso19115-3_xml \
  --output-file record.xml \
  --output-encoding utf-8
```

### erddap-update

Update ERDDAP datasets.xml files with CIOOS metadata.

This command updates existing ERDDAP dataset configurations with metadata from CIOOS records. It matches datasets by URL and updates the global attributes.

#### Usage

```bash
cioos_metadata_conversion erddap-update [OPTIONS]
```

#### Options

| Option | Short | Type | Required | Description |
|--------|-------|------|----------|-------------|
| `--datasets-xml` | `-d` | PATH | Yes | Path to ERDDAP datasets.xml file |
| `--records` | `-r` | PATH | Yes | Path to CIOOS records (glob pattern) |
| `--erddap-url` | `-u` | TEXT | Yes | Base URL of the ERDDAP server |
| `--output` | `-o` | PATH | No | Output file (default: updates in place) |
| `--backup` | | FLAG | No | Create backup before updating |
| `--multilingual` | | FLAG | No | Include multilingual attributes |

#### Examples

**Update ERDDAP datasets.xml with CIOOS metadata**:

```bash
cioos_metadata_conversion erddap-update \
  --datasets-xml /path/to/datasets.xml \
  --records "records/*.yaml" \
  --erddap-url "https://data.example.org/erddap" \
  --multilingual
```

**Create backup and update**:

```bash
cioos_metadata_conversion erddap-update \
  --datasets-xml /path/to/datasets.xml \
  --records "records/*.yaml" \
  --erddap-url "https://data.example.org/erddap" \
  --backup \
  --output /path/to/updated-datasets.xml
```

**Update from Firebase records**:

```bash
cioos_metadata_conversion erddap-update \
  --datasets-xml /path/to/datasets.xml \
  --records "firebase/*.json" \
  --erddap-url "https://data.example.org/erddap"
```

## Exit Codes

The CLI uses standard exit codes:

- `0`: Success
- `1`: General error (e.g., file not found, conversion failed)
- `2`: Command-line usage error

## Environment Variables

### CIOOS_LOG_LEVEL

Set the logging level:

```bash
export CIOOS_LOG_LEVEL=DEBUG
cioos_metadata_conversion convert --input record.yaml ...
```

Valid values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### CIOOS_ENCODING

Default encoding for input/output files:

```bash
export CIOOS_ENCODING=utf-8
```

## Advanced Usage

### Piping and Redirection

While the CLI doesn't support stdin directly, you can work with files:

```bash
# Convert and view output
cioos_metadata_conversion convert \
  --input record.yaml \
  --input-schema CIOOS \
  --output-format json | jq .

# Chain conversions
cioos_metadata_conversion convert \
  --input record.yaml \
  --input-schema CIOOS \
  --output-format json \
  --output-file temp.json

cioos_metadata_conversion convert \
  --input temp.json \
  --input-schema CIOOS \
  --output-format datacite_xml \
  --output-file final.xml
```

### Globbing Patterns

The CLI supports glob patterns for batch processing:

```bash
# All YAML files in current directory
cioos_metadata_conversion convert --input "*.yaml" ...

# All files recursively
cioos_metadata_conversion convert --input "**/*.yaml" --recursive ...

# Specific pattern
cioos_metadata_conversion convert --input "records/dataset-*.json" ...
```

### Error Handling

The CLI uses loguru for logging. Errors are logged to stderr:

```bash
# Capture errors
cioos_metadata_conversion convert ... 2> errors.log

# Verbose output
cioos_metadata_conversion convert ... 2>&1 | tee output.log
```

## Shell Completion

### Bash

Add to your `~/.bashrc`:

```bash
eval "$(_CIOOS_METADATA_CONVERSION_COMPLETE=bash_source cioos_metadata_conversion)"
```

### Zsh

Add to your `~/.zshrc`:

```bash
eval "$(_CIOOS_METADATA_CONVERSION_COMPLETE=zsh_source cioos_metadata_conversion)"
```

### Fish

Add to your `~/.config/fish/completions/cioos_metadata_conversion.fish`:

```bash
eval (env _CIOOS_METADATA_CONVERSION_COMPLETE=fish_source cioos_metadata_conversion)
```

## Tips and Best Practices

1. **Use Absolute Paths**: When processing multiple files, use absolute paths to avoid confusion
2. **Test First**: Try conversion on a single file before batch processing
3. **Check Encodings**: Ensure input and output encodings match your data
4. **Validate Output**: Always validate generated XML/JSON against schemas
5. **Use Output Directories**: For batch processing, specify an output directory rather than individual files
6. **Backup Originals**: When updating files (like ERDDAP), always create backups first

## See Also

- [Usage Guide](usage.md) - Detailed usage examples and workflows
- [Input Schemas](input-schemas.md) - Understanding input formats
- [Output Formats](output-formats.md) - Details on output formats

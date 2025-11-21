# Installation

This guide will help you install the CIOOS Metadata Conversion package in your environment.

## Requirements

- **Python**: 3.11 or higher
- **Package Manager**: pip or uv (recommended)

## Installation Methods

### Using pip (Standard)

Install directly from GitHub:

```bash
pip install git+https://github.com/cioos-siooc/cioos-metadata-conversion.git
```

### Using uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package installer and resolver. It's recommended for development.

1. **Install uv**:

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   Or on Windows:

   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. **Install the package**:

   ```bash
   uv pip install git+https://github.com/cioos-siooc/cioos-metadata-conversion.git
   ```

### Development Installation

For development or to contribute to the project:

1. **Clone the repository**:

   ```bash
   git clone https://github.com/cioos-siooc/cioos-metadata-conversion.git
   cd cioos-metadata-conversion
   ```

2. **Install with uv** (recommended):

   ```bash
   # Install uv if you haven't already
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Sync dependencies
   uv sync --dev
   ```

   Or **install with pip**:

   ```bash
   pip install -e ".[dev]"
   ```

3. **Verify installation**:

   ```bash
   cioos_metadata_conversion --help
   ```

## Dependencies

The package has the following main dependencies:

### Core Dependencies

- **loguru**: Logging framework
- **requests**: HTTP library
- **cffconvert**: Citation File Format conversion
- **pycountry**: ISO country data
- **pyyaml**: YAML parser
- **lxml**: XML processing
- **click**: CLI framework
- **datacite**: DataCite metadata utilities
- **python-dotenv**: Environment variable management
- **google-auth** & **google-oauth**: Firebase authentication

### External Package

- **metadata-xml**: ISO 19115-3 XML generation (from GitHub)
  - Repository: https://github.com/cioos-siooc/metadata-xml

### Development Dependencies

For development, additional packages are included:

- **pytest**: Testing framework
- **pytest-xdist**: Parallel test execution
- **ruff**: Fast Python linter and formatter
- **mkdocs-material**: Documentation site generation

## Verifying Installation

After installation, verify that the package is working correctly:

### Check CLI Access

```bash
cioos_metadata_conversion --help
```

You should see output showing the available commands:

```
Usage: cioos_metadata_conversion [OPTIONS] COMMAND [ARGS]...

  CIOOS Metadata Conversion CLI.
  Convert metadata records to different metadata formats or standards.

Options:
  --help  Show this message and exit.

Commands:
  convert        Convert metadata records to different metadata formats...
  erddap-update  Update ERDDAP datasets.xml files with CIOOS metadata
```

### Test Basic Conversion

Create a test file and try converting it:

```bash
# Download a sample record (example)
curl -o sample.yaml https://raw.githubusercontent.com/cioos-siooc/cioos-metadata-conversion/main/tests/records/test_record1.yaml

# Convert to ISO 19115-3 XML
cioos_metadata_conversion convert \
  --input sample.yaml \
  --input-schema CIOOS \
  --output-format iso19115-3_xml \
  --output-file output.xml

# Check the output
cat output.xml
```

### Python API Test

Test the Python API:

```python
from cioos_metadata_conversion.record import Record, InputSchemas

# Create a simple test
try:
    record = Record(source={"test": "data"}, schema=InputSchemas.CIOOS)
    print("✓ Package imported successfully")
except ImportError as e:
    print(f"✗ Import failed: {e}")
```

## Troubleshooting

### Common Issues

#### Module Not Found Errors

If you see `ModuleNotFoundError: No module named 'metadata_xml'`:

The `metadata-xml` package is installed from GitHub. Ensure your installation includes it:

```bash
pip install git+https://github.com/cioos-siooc/metadata-xml.git
```

Or reinstall the main package which should pull it in:

```bash
pip install --force-reinstall git+https://github.com/cioos-siooc/cioos-metadata-conversion.git
```

#### Python Version Issues

Ensure you're using Python 3.11 or higher:

```bash
python --version
```

If you have multiple Python versions, use:

```bash
python3.11 -m pip install git+https://github.com/cioos-siooc/cioos-metadata-conversion.git
```

#### Permission Errors

On Unix/Linux systems, if you encounter permission errors, use:

```bash
pip install --user git+https://github.com/cioos-siooc/cioos-metadata-conversion.git
```

Or use a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install git+https://github.com/cioos-siooc/cioos-metadata-conversion.git
```

### Getting Help

If you continue to experience issues:

1. Check the [GitHub Issues](https://github.com/cioos-siooc/cioos-metadata-conversion/issues)
2. Ensure all dependencies are installed
3. Try installing in a fresh virtual environment
4. Open a new issue with details about your environment and the error

## Next Steps

- [Quick Start Guide](quickstart.md) - Start using the tool
- [CLI Reference](cli.md) - Learn about all CLI commands
- [Usage Guide](usage.md) - Detailed usage examples

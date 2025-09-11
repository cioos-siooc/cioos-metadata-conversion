# CIOOS Metadata Conversion

This project provides a tool to generate various metadata formats and standards
from the CIOOS metadata catalogue form schema. It aims to
facilitate the sharing and citation of datasets by converting metadata records into
widely recognized standards.

## Currently Supported Standards

- `citation.cff`: Citation File Format, a human and machine-readable file format
  which provides citation metadata for software.
- `ACDD-1.3`: ACDD-1.3 standard attributes.
- ERDDAP<sup>TM</sup>: XML metadata attributes following the CF1.6 and ACDD 1.3 standards.
- `ISO19115-3` schema: CIOOS standard ISO19115-3 schema.
- `Datacite-xml` and `Datacite-json` schema: Datacite compatible Schema.

## Features

- **Easy Integration**: Seamlessly integrates with existing CKAN instances to
  fetch catalogue records.
- **Extensible**: Designed with extensibility in mind, allowing for adding more metadata standards in the future.
- **User-Friendly**: Provides a simple, intuitive interface for generating
  metadata files.

## Getting Started

To use this tool, follow these steps:

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/your/repository.git
   cd repository
   ```

2. **Install Dependencies:**

   ```bash
   pip install -e .
   ```

3. **Run the Tool:**

   ```bash
   python cioos_metadata_conversion
   ```

   For more information

   ```bash
   python cioos_metadata_conversion --help
   ```

## How to Contribute

We welcome contributions! If you would like to add support for more metadata standards or improve the tool, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature (git checkout -b feature/AmazingFeature).
3. Commit your changes (git commit -m 'Add some AmazingFeature').
4. Push to the branch (git push origin feature/AmazingFeature).
5. Open a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

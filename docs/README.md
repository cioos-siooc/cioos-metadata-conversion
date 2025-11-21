# Documentation

This directory contains the source files for the CIOOS Metadata Conversion documentation website, built with [MkDocs Material](https://squidfunk.github.io/mkdocs-material/).

## Building the Documentation

### Prerequisites

Install the documentation dependencies:

```bash
# Using uv (recommended)
uv sync --dev

# Or using pip
pip install mkdocs mkdocs-material mkdocs-autorefs
```

### Local Development

Serve the documentation locally with auto-reload:

```bash
mkdocs serve
```

Then open http://127.0.0.1:8000 in your browser.

### Building Static Site

Build the static HTML site:

```bash
mkdocs build
```

Output will be in the `site/` directory.

### Deploying to GitHub Pages

Deploy to GitHub Pages:

```bash
mkdocs gh-deploy
```

This will build the site and push to the `gh-pages` branch.

## Documentation Structure

```
docs/
├── index.md                    # Home page
├── installation.md             # Installation guide
├── quickstart.md              # Quick start guide
├── cli.md                     # CLI reference
├── usage.md                   # Detailed usage guide
├── input-schemas.md           # Input format documentation
├── output-formats.md          # Output format documentation
├── contributing.md            # Contributing guide
├── mappings/                  # Field mapping documentation
│   ├── index.md              # Mappings overview
│   ├── cioos-form-to-cioos.md
│   ├── cioos-to-iso19115-3.md
│   ├── cioos-to-datacite.md
│   └── cioos-to-erddap-acdd.md
└── api/                       # API reference (planned)
    └── ...
```

## Writing Documentation

### Markdown Features

The documentation supports:

- **GitHub Flavored Markdown**
- **Code blocks** with syntax highlighting
- **Admonitions** (notes, warnings, tips)
- **Tables**
- **Task lists**
- **Mermaid diagrams**

### Code Blocks

````markdown
```python
from cioos_metadata_conversion.record import Record

record = Record(source="record.yaml", schema="CIOOS")
```
````

### Admonitions

```markdown
!!! note
    This is a note.

!!! warning
    This is a warning.

!!! tip
    This is a tip.
```

### Tables

```markdown
| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
```

### Links

```markdown
[Link text](page.md)
[Link with anchor](page.md#section)
```

## Configuration

The site configuration is in `mkdocs.yml` at the project root. Key settings:

- **theme**: Material theme configuration
- **nav**: Navigation structure
- **plugins**: Enabled plugins (search, autorefs)
- **markdown_extensions**: Enabled Markdown features

## Tips

1. **Preview changes**: Always run `mkdocs serve` to preview changes locally
2. **Check links**: Ensure all internal links work
3. **Update nav**: Add new pages to `nav` section in `mkdocs.yml`
4. **Code examples**: Test all code examples before documenting
5. **Screenshots**: Store in `docs/images/` if needed

## Need Help?

- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [Markdown Guide](https://www.markdownguide.org/)

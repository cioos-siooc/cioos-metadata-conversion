# Building and Deploying Documentation

## Quick Start

```bash
# Install dependencies
uv sync --dev

# Serve locally
mkdocs serve

# Open http://127.0.0.1:8000
```

## Installation

### Install MkDocs Dependencies

Using uv:
```bash
uv sync --dev
```

Using pip:
```bash
pip install mkdocs mkdocs-material mkdocs-autorefs
```

## Local Development

### Serve Documentation

```bash
mkdocs serve
```

This will:
- Start a local server at http://127.0.0.1:8000
- Auto-reload on file changes
- Show warnings for broken links

### Build Static Site

```bash
mkdocs build
```

Output in `site/` directory.

### Clean Build

```bash
rm -rf site/
mkdocs build
```

## Deployment

### GitHub Pages

#### Automatic Deployment

```bash
mkdocs gh-deploy
```

This will:
1. Build the documentation
2. Push to `gh-pages` branch
3. Deploy to GitHub Pages

#### Manual Deployment

```bash
# Build
mkdocs build

# Push to gh-pages branch
git checkout gh-pages
cp -r site/* .
git add .
git commit -m "Update documentation"
git push origin gh-pages
```

### Custom Domain

Add `CNAME` file in `docs/`:

```bash
echo "docs.example.org" > docs/CNAME
```

Then configure DNS:
```
docs.example.org.  CNAME  your-username.github.io.
```

## Configuration

### Site Settings

Edit `mkdocs.yml`:

```yaml
site_name: CIOOS Metadata Conversion
site_url: https://cioos-siooc.github.io/cioos-metadata-conversion/
repo_url: https://github.com/cioos-siooc/cioos-metadata-conversion
```

### Navigation

Add pages to `nav` section:

```yaml
nav:
  - Home: index.md
  - Getting Started:
    - Installation: installation.md
    - Quick Start: quickstart.md
```

### Theme Customization

```yaml
theme:
  name: material
  palette:
    primary: blue
  features:
    - navigation.tabs
    - search.suggest
```

## Validation

### Check Links

```bash
# Build and check for warnings
mkdocs build --strict
```

### Validate Markdown

```bash
# Using markdownlint (if installed)
markdownlint docs/**/*.md
```

## Troubleshooting

### Build Errors

**Problem**: `ModuleNotFoundError: No module named 'mkdocs'`

**Solution**:
```bash
uv sync --dev
# or
pip install mkdocs mkdocs-material
```

**Problem**: Broken links in output

**Solution**: Run `mkdocs build --strict` to see warnings

### Deployment Issues

**Problem**: `gh-deploy` fails with authentication error

**Solution**:
```bash
# Configure Git credentials
git config --global user.name "Your Name"
git config --global user.email "your@email.com"

# Or use SSH instead of HTTPS
git remote set-url origin git@github.com:cioos-siooc/cioos-metadata-conversion.git
```

**Problem**: 404 on GitHub Pages

**Solution**:
- Check repository settings → Pages
- Ensure source is set to `gh-pages` branch
- Wait a few minutes for deployment

## CI/CD Integration

### GitHub Actions

Create `.github/workflows/docs.yml`:

```yaml
name: Deploy Documentation

on:
  push:
    branches:
      - main
    paths:
      - 'docs/**'
      - 'mkdocs.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install mkdocs mkdocs-material mkdocs-autorefs

      - name: Deploy to GitHub Pages
        run: |
          mkdocs gh-deploy --force
```

## Tips

1. **Preview before deploying**: Always run `mkdocs serve` to check changes
2. **Test builds**: Run `mkdocs build --strict` to catch errors
3. **Use relative links**: Link to other docs with `[text](page.md)`
4. **Check mobile view**: Material theme is responsive
5. **Update regularly**: Keep docs in sync with code changes

## See Also

- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [GitHub Pages Documentation](https://docs.github.com/en/pages)

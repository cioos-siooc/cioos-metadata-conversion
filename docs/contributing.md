# Contributing

We welcome contributions to the CIOOS Metadata Conversion project! This guide will help you get started.

## Ways to Contribute

- **Bug Reports**: Report bugs via GitHub Issues
- **Feature Requests**: Suggest new features or improvements
- **Code Contributions**: Submit pull requests with bug fixes or new features
- **Documentation**: Improve or expand documentation
- **Testing**: Help test the tool and report issues

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR-USERNAME/cioos-metadata-conversion.git
cd cioos-metadata-conversion
```

### 2. Install Development Dependencies

Using uv (recommended):

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --dev
```

Or using pip:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### 3. Install Pre-commit Hooks (Optional)

```bash
pip install pre-commit
pre-commit install
```

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Your Changes

- Write clean, documented code
- Follow existing code style
- Add tests for new features
- Update documentation as needed

### 3. Run Tests

```bash
# Run all tests
pytest

# Run tests in parallel
pytest -n auto

# Run specific test file
pytest tests/test_datacite.py
```

### 4. Check Code Style

```bash
# Format code with ruff
ruff format .

# Check for issues
ruff check .
```

### 5. Update Documentation

If your changes affect user-facing functionality:

- Update relevant `.md` files in `docs/`
- Update mapping documentation if field mappings change
- Add examples if introducing new features

Build and preview docs locally:

```bash
mkdocs serve
# Open http://127.0.0.1:8000 in your browser
```

## Pull Request Process

### 1. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature"
# or
git commit -m "fix: resolve issue with..."
```

Use conventional commit messages:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `style:` - Code style changes
- `chore:` - Build/tooling changes

### 2. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 3. Create Pull Request

- Go to the original repository on GitHub
- Click "New Pull Request"
- Select your fork and branch
- Fill out the pull request template
- Link any related issues

### 4. Code Review

- Respond to review comments
- Make requested changes
- Push additional commits to your branch

## Code Style Guidelines

### Python Code

- Follow PEP 8 style guide
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions focused and concise

Example:

```python
def convert_metadata(record: dict, format: str) -> str:
    """Convert metadata record to specified format.

    Args:
        record: Metadata record dictionary
        format: Target format (e.g., 'datacite_xml')

    Returns:
        Converted metadata as string

    Raises:
        ValueError: If format is not supported
    """
    # Implementation
    pass
```

### Documentation

- Use clear, concise language
- Include code examples
- Add links to related documentation
- Keep formatting consistent

## Testing Guidelines

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use descriptive test names

Example:

```python
def test_datacite_conversion_includes_required_fields():
    """Test that DataCite conversion includes all required fields."""
    record = load_test_record()
    result = datacite.to_xml(record)

    assert "<identifier" in result
    assert "<creators>" in result
    assert "<titles>" in result
```

### Test Data

- Use fixtures for reusable test data
- Place test records in `tests/records/`
- Document test data sources

## Adding New Output Formats

To add support for a new metadata standard:

### 1. Create Converter Module

```python
# cioos_metadata_conversion/my_standard.py

def to_my_standard(record: dict) -> str:
    """Convert CIOOS record to My Standard format.

    Args:
        record: CIOOS intermediate format record

    Returns:
        My Standard formatted output
    """
    # Implementation
    pass
```

### 2. Register Format

Update `cioos_metadata_conversion/record.py`:

```python
OUTPUT_FORMATS = {
    # ... existing formats ...
    "my_standard": my_standard.to_my_standard,
}
```

### 3. Add Tests

```python
# tests/test_my_standard.py

def test_my_standard_conversion():
    record = load_test_record()
    result = my_standard.to_my_standard(record)
    # Add assertions
```

### 4. Document Mapping

Create `docs/mappings/cioos-to-my-standard.md` documenting the field mappings.

### 5. Update Documentation

- Add to list in `docs/index.md`
- Update `docs/output-formats.md`
- Add usage examples in `docs/usage.md`

## Documentation

### Building Documentation

```bash
# Install dependencies
uv sync --dev

# Serve documentation locally
mkdocs serve

# Build static site
mkdocs build
```

### Documentation Structure

```
docs/
├── index.md              # Home page
├── installation.md       # Installation guide
├── quickstart.md         # Quick start guide
├── cli.md               # CLI reference
├── usage.md             # Usage guide
├── mappings/            # Field mapping docs
│   ├── index.md
│   └── *.md
└── api/                 # API reference
    └── *.md
```

## Release Process

(For maintainers)

### 1. Update Version

Edit `pyproject.toml`:

```toml
[project]
version = "0.2.0"
```

### 2. Update Changelog

Document changes in `CHANGELOG.md`

### 3. Create Release

```bash
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

### 4. Deploy Documentation

```bash
mkdocs gh-deploy
```

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Issues**: Check existing issues or create a new one
- **Chat**: (Add link to Slack/Discord if available)

## Code of Conduct

Please be respectful and constructive in all interactions. We aim to foster an inclusive, welcoming community.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Acknowledgments

Thank you for contributing to CIOOS Metadata Conversion! Your efforts help improve ocean data sharing and discovery.

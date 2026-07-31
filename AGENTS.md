# AGENTS.md - Guidelines for Agentic Coding

This document provides essential information for agentic coding agents working on the cioos-metadata-conversion repository.

## Project Overview

CIOOS Metadata Conversion is a Python tool that converts metadata records between different standards and formats (ACDD, ERDDAP, ISO19115-3, DataCite, CFF, etc.). It uses Click for CLI, Loguru for logging, and ruff for linting.

**Tech Stack**: Python 3.11+, uv (package manager), pytest, ruff

## Build, Lint, and Test Commands

### Setup
```bash
# Install dependencies
uv sync

# Run the CLI
uv run python -m cioos_metadata_conversion --help
```

### Testing
```bash
# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_cli.py

# Run a specific test function
uv run pytest tests/test_cli.py::test_cli_help

# Run tests matching a keyword
uv run pytest -k test_convert

# Run tests with verbose output and stop on first failure
uv run pytest -xvs

# Run tests in parallel with xdist
uv run pytest -n auto

# Run with coverage reporting
uv run pytest --cov=cioos_metadata_conversion
```

### Linting and Formatting
```bash
# Check for lint violations
uv run ruff check .

# Automatically fix violations
uv run ruff check --fix .

# Format code (ruff format is available but check is the main tool)
uv run ruff check cioos_metadata_conversion tests
```

## Code Style Guidelines

### Imports
- Organize imports in three groups: stdlib, third-party, local (separated by blank lines)
- Use absolute imports: `from cioos_metadata_conversion import acdd`
- Avoid wildcard imports (`from module import *`)
- Import order example:
  ```python
  import json
  from enum import Enum
  from pathlib import Path
  
  import requests
  from loguru import logger
  
  from cioos_metadata_conversion import acdd, datacite
  ```

### Formatting
- Line length: Ruff defaults to 88 characters (follows Black)
- Use 4 spaces for indentation (no tabs)
- Two blank lines between top-level definitions
- One blank line between method definitions
- No trailing whitespace

### Type Hints
- Use type hints for function parameters and return types
- Use modern syntax: `dict` instead of `Dict`, `list` instead of `List`, etc.
- Union types: use `|` instead of `Union` (e.g., `str | int`)
- Optional types: use `Type | None` instead of `Optional[Type]`
- Example:
  ```python
  def _get_contact(contact: dict, role: str) -> dict:
  def load_from(self, file: str, schema: str = "CIOOS") -> Record:
  ```

### Naming Conventions
- Classes: `PascalCase` (e.g., `Record`, `InputSchemas`)
- Functions/methods: `snake_case` (e.g., `load_from_file`, `convert_to_cioos_schema`)
- Private functions: Prefix with underscore (e.g., `_get_contact`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `SOURCE_FILE_EXTENSIONS`, `OUTPUT_FORMATS`)
- Module names: `snake_case` (e.g., `citation_cff.py`, `firebase_to_cioos.py`)

### Error Handling
- Use loguru's `@logger.catch()` decorator for error handling in public functions
- Log with context: `logger.error("message", variable)` instead of f-strings in some cases
- Raise meaningful exceptions with descriptive messages:
  ```python
  raise ValueError("Unsupported schema. Supported schemas are: ...")
  ```
- Log warnings for recoverable issues:
  ```python
  logger.warning(f"No organization found for {role} contact.")
  ```

### Comments and Docstrings
- Use docstrings for modules, classes, and public functions
- Keep docstrings concise and use Google/NumPy style when helpful
- Use comments for non-obvious logic, not for restating code
- Include TODOs with context: `# TODO map cioos roles to datacite contributor roles`

### Code Organization
- One primary class/feature per file
- Keep related utilities in `utils.py`
- Use enum.Enum for schemas and fixed value sets
- Functions should be focused and single-purpose
- Prefix internal helper functions with underscore

### Dependencies and Logging
- Use loguru for all logging (`from loguru import logger`)
- Available libraries: requests, yaml, json, lxml, click, datacite, pyyaml, pycountry, cffconvert
- Use Click decorators for CLI commands and options
- Validate input early and provide helpful error messages

### Testing
- Test fixtures defined in `conftest.py`
- Use pytest conventions: `test_*.py` files, `def test_*` functions
- Use Click's `CliRunner` for CLI testing
- Fixtures example: `@pytest.fixture` decorator for reusable test data
- Keep tests focused and readable with clear assertion messages

## Project Structure

```
cioos-metadata-conversion/
├── cioos_metadata_conversion/      # Main package
│   ├── __main__.py                 # CLI entry point
│   ├── record.py                   # Core Record class
│   ├── acdd.py                     # ACDD format conversion
│   ├── datacite.py                 # DataCite format conversion
│   ├── citation_cff.py             # CFF format conversion
│   ├── erddap.py                   # ERDDAP format conversion
│   ├── xml.py                      # ISO19115-3 XML conversion
│   ├── utils.py                    # Utility functions
│   ├── firebase_to_cioos.py        # Firebase schema conversion
│   └── load_from/                  # Loading from various sources
│       └── datacite.py             # Load from DOI/DataCite
├── tests/                          # Test suite
│   ├── conftest.py                 # Test fixtures
│   ├── records/                    # Test data (YAML files)
│   └── test_*.py                   # Test files
├── pyproject.toml                  # Project config (uv, ruff, pytest)
└── README.md                       # Project documentation
```

## Important Notes

- Python version: 3.11+ (specified in `pyproject.toml` and `.python-version`)
- No `.cursorrules` or `copilot-instructions.md` currently exist in this repo
- The package uses enum.Enum for `InputSchemas` and `OutputSchemas`
- All conversions go through the `Record` class as the central abstraction
- Use `@logger.catch(reraise=True)` for CLI commands to handle exceptions gracefully
- File paths: prefer `pathlib.Path` over string paths

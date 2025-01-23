from pathlib import Path

import pytest

from cioos_metadata_conversion.__main__ import load

Path("tests/results").mkdir(exist_ok=True)


@pytest.fixture
def record():
    return load("tests/records/test_record1.yaml", "yaml")

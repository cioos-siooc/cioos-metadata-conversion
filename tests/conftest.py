import pytest

from hakai_metadata_conversion.__main__ import load


@pytest.fixture
def record():
    return load("tests/records/test_record1.yaml", "yaml")

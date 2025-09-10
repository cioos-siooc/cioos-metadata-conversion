from pathlib import Path

import pytest

from cioos_metadata_conversion.converter import Converter

Path("tests/results").mkdir(exist_ok=True)


@pytest.fixture
def record():
    record = Converter("tests/records/test_record1.yaml", "yaml")
    record.load()
    record.convert_to_cioos_schema()
    return record.metadata

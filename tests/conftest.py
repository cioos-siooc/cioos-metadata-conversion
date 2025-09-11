from pathlib import Path

import pytest

from cioos_metadata_conversion.record import Record


Path("tests/results").mkdir(exist_ok=True)


@pytest.fixture
def record_file_yaml():
    return "tests/records/test_record1.yaml"


def test_record_file_yaml(record_file_yaml):
    assert Path(record_file_yaml).exists()
    assert record_file_yaml.endswith((".yaml", ".yml"))


@pytest.fixture
def record(record_file_yaml):
    record = Record(record_file_yaml, "CIOOS")
    record.load()
    record.convert_to_cioos_schema()
    return record.metadata

from glob import glob

import pytest

from cioos_metadata_conversion.__main__ import load
from cioos_metadata_conversion.xml import xml


def test_xml(record):
    result = xml(record)
    assert result
    assert isinstance(result, str)


@pytest.mark.parametrize(
    "file",
    glob("tests/records/**/*.yaml", recursive=True),
)
def test_cioos_records_xml(file):
    record = load(file, "CIOOS")
    result = xml(record)

    assert result
    assert isinstance(result, str)

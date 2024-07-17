import pytest
from glob import glob

from hakai_metadata_conversion.__main__ import load
from hakai_metadata_conversion.xml import xml

def test_xml(record):
    result = xml(record)
    assert result
    assert isinstance(result, str)



@pytest.mark.parametrize(
    "file",
    glob("tests/records/hakai-metadata-entry-form-files/**/*.yaml", recursive=True),
)
def test_hakai_records_xml(file):
    record = load(file, "yaml")
    result = xml(record)
    
    assert result
    assert isinstance(result, str)

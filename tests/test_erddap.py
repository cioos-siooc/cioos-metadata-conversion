import pytest
from glob import glob
from hakai_metadata_conversion.__main__ import load
from hakai_metadata_conversion.erddap import global_attributes


def test_erddap_global_attributes(record):
    result = global_attributes(record, output=None, language="en")
    assert result
    assert isinstance(result, dict)
    assert "title" in result
    assert "summary" in result
    assert "project" in result
    assert "keywords" in result
    assert "id" in result
    assert "naming_authority" in result
    assert "date_modified" in result
    assert "date_created" in result
    assert "product_version" in result
    assert "history" in result
    assert "license" in result
    assert "creator_name" in result
    assert "creator_institution" in result
    assert "creator_address" in result
    assert "creator_city" in result
    assert "creator_country" in result
    assert "creator_url" in result
    assert "publisher_name" in result
    assert "publisher_institution" in result
    assert "publisher_address" in result
    assert "publisher_city" in result
    assert "publisher_country" in result
    assert "publisher_url" in result
    assert "metadata_link" in result


def test_erddap_global_attirbutes_xml(record):
    result = global_attributes(record, output="xml", language="en")
    assert result

@pytest.mark.parametrize("file", glob("tests/records/hakai-metadata-entry-form-files/**/*.yaml", recursive=True))
def test_hakai_metadata_files_to_erddap(file):
    data = load(file, "yaml")
    result = global_attributes(data, output="xml", language="en")

    assert result

@pytest.mark.parametrize("file", glob("tests/records/hakai-metadata-entry-form-files/**/*.yaml", recursive=True))
def test_hakai_metadata_files_to_erddap_fr(file):
    data = load(file, "yaml")
    result_fr = global_attributes(data, output="xml", language="fr")

    assert result_fr
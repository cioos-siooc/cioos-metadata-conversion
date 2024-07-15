from glob import glob
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

import hakai_metadata_conversion.erddap as erddap
from hakai_metadata_conversion.__main__ import load


def test_erddap_global_attributes(record):
    result = erddap.global_attributes(record, output=None, language="en")
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


def test_erddap_global_attributes_xml(record):
    result = erddap.global_attributes(record, output="xml", language="en")
    assert result


@pytest.mark.parametrize(
    "file",
    glob("tests/records/hakai-metadata-entry-form-files/**/*.yaml", recursive=True),
)
def test_hakai_metadata_files_to_erddap(file):
    data = load(file, "yaml")
    result = erddap.global_attributes(data, output="xml", language="en")

    assert result


@pytest.mark.parametrize(
    "file",
    glob("tests/records/hakai-metadata-entry-form-files/**/*.yaml", recursive=True),
)
def test_hakai_metadata_files_to_erddap_fr(file):
    data = load(file, "yaml")
    result_fr = erddap.global_attributes(data, output="xml", language="fr")

    assert result_fr


def test_erddap_update_dataset_xml(record):
    comment = "Some commented text that should remain"
    attributes = erddap.global_attributes(record, output=None, language="en")
    datasets = erddap.ERDDAP("tests/erddap_xmls/test_datasets.xml")
    datasets.read()
    dataset_xml_content = datasets.tostring()
    assert comment in dataset_xml_content

    datasets.update( "TestDataset1", attributes)
    result = datasets.tostring()
    assert result
    assert isinstance(result, str)
    assert "TestDataset1" in result
    assert comment in result
    for key,value in attributes.items():
        assert key in result
        assert not value or value in result

    Path("tests/results/test_erddap_update_dataset.xml").write_text(
        result, encoding="utf-8"
    )

    # test that output can be parsed
    root = ET.fromstring(result)
    assert root

def test_erddap_update_datasets_d_xml(record):
    comment = "Some commented text that should remain"
    attributes = erddap.global_attributes(record, output=None, language="en")
    dataset_d_files = list(Path("tests/erddap_xmls/datasets.d").glob("*.xml"))
    
    assert dataset_d_files, "No dataset files found in test_datasets.d"
    for file in dataset_d_files:
        dataset= erddap.ERDDAP(file)
        dataset.read()
        dataset_xml_content = dataset.tostring()
        assert comment in dataset_xml_content
        dataset.update("TestDataset1", attributes)
        result = dataset.tostring()
        assert result
        assert isinstance(result, str)
        assert "TestDataset1" in result
        assert comment in result

        Path("tests/results/test_erddap_update_datasets_d.xml").write_text(
            result, encoding="utf-8"
        )

        # test that output can be parsed
        root = ET.fromstring(result)
        assert root
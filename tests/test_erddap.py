from glob import glob

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


def test_erddap_dataset_xml_update(record, tmp_path):
    erddap.update_dataset_xml(
        "tests/erddap_xmls/test_datasets.xml",
        [record],
        erddap_url="https://catalogue.hakai.org/erddap",
        output_dir=tmp_path,
    )
    assert (tmp_path / "test_datasets.xml").exists()


def test_erddap_dataset_xml_update_string(tmp_path):
    erddap.update_dataset_xml(
        "tests/erddap_xmls/test_datasets.xml",
        "tests/records/*.yaml",
        erddap_url="https://catalogue.hakai.org/erddap",
        output_dir=tmp_path,
    )
    assert (tmp_path / "test_datasets.xml").exists()


def test_erddap_dataset_d_xml_update(record, tmp_path):
    erddap.update_dataset_xml(
        "tests/erddap_xmls/dataset.d/*.xml",
        [record],
        erddap_url="https://catalogue.hakai.org/erddap",
        output_dir=tmp_path,
    )
    files = tmp_path.glob("dataset.d/*.xml")
    assert files

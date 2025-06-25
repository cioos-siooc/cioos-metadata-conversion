import subprocess
from glob import glob

import pytest

from cioos_metadata_conversion import citation_cff
from cioos_metadata_conversion.__main__ import load


def test_citation_cff(record):
    result = citation_cff.citation_cff(record, output_format=None, language="en")
    assert result
    assert isinstance(result, dict)
    assert "cff-version" in result
    assert "date-released" in result
    assert "contact" in result
    assert "authors" in result
    assert "identifiers" in result
    assert "keywords" in result
    assert "license" in result
    assert "license-url" in result
    assert "message" in result
    assert "type" in result
    assert "url" in result
    assert "version" in result
    assert "identifiers" in result


def test_ctation_cff_yaml(record, tmp_path):
    result = citation_cff.citation_cff(record, output_format="yaml", language="en")
    (tmp_path / "CITATION.cff").write_text(result, encoding="utf-8")


def test_citation_cff_validation(record, tmp_path):
    result = citation_cff.citation_cff(record, output_format="yaml", language="en")
    (tmp_path / "CITATION.cff").write_text(result, encoding="utf-8")
    # run cffconvert validate cli
    result = subprocess.run(
        ["cffconvert", "--validate", "-i", str(tmp_path / "CITATION.cff")],
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "file",
    glob("tests/records/**/*.yaml", recursive=True),
)
def test_cioos_metadata_entry_form_files_cff(file, tmp_path):
    data = load(file, "CIOOS")
    result = citation_cff.citation_cff(data, output_format="yaml", language="en")
    assert result

    # validate cff
    (tmp_path / "CITATION.cff").write_text(result, encoding="utf-8")
    validation_result = subprocess.run(
        ["cffconvert", "--validate", "-i", str(tmp_path / "CITATION.cff")],
        capture_output=True,
    )
    assert validation_result.returncode == 0, validation_result.stderr.decode("utf-8")


@pytest.mark.parametrize(
    "file",
    glob("tests/records/**/*.yaml", recursive=True),
)
def test_cioos_metadata_entry_form_files_cff_fr(file, tmp_path):
    data = load(file, "CIOOS")
    result_fr = citation_cff.citation_cff(data, output_format="yaml", language="fr")
    assert result_fr

    # validate cff
    (tmp_path / "CITATION.cff").write_text(result_fr, encoding="utf-8")
    validation_result = subprocess.run(
        ["cffconvert", "--validate", "-i", str(tmp_path / "CITATION.cff")],
        capture_output=True,
    )
    assert validation_result.returncode == 0, validation_result.stderr.decode("utf-8")

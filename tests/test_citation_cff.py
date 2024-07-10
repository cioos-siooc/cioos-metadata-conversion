import subprocess

from hakai_metadata_conversion import citation_cff


def test_citation_cff(record):
    result = citation_cff.citation_cff(record, output_format=None, language="en")
    assert result
    assert isinstance(result, dict)
    assert "cff-version" in result
    assert "date" in result
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


def test_citation_cff_validation(record, tmp_path):

    result = citation_cff.citation_cff(record, output_format="yaml", language="en")
    (tmp_path / "CITATION.cff").write_text(result, encoding="utf-8")
    # run cffconvert validate cli
    result = subprocess.run(
        ["cffconvert", "--validate", "-i", str(tmp_path / "CITATION.cff")],
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr

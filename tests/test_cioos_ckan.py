import json
from pathlib import Path

import pytest

from cioos_metadata_conversion import cioos_ckan
from cioos_metadata_conversion.firebase_to_cioos import record_json_to_yaml


def test_ckan_generation(record):
    """
    Test the CKAN record generation.
    """
    ckan_record = cioos_ckan.generate_ckan_record(record)
    assert ckan_record

    # Check required fields
    assert "title_translated" in ckan_record
    assert "notes_translated" in ckan_record
    assert "keywords" in ckan_record
    assert "metadata-point-of-contact" in ckan_record

    # Verify bilingual fields
    assert "en" in ckan_record["title_translated"]
    assert "en" in ckan_record["notes_translated"]


def test_json_output(record, tmp_path):
    """
    Test the JSON output generation.
    """
    test_file = tmp_path / "test_ckan.json"
    json_output = cioos_ckan.to_json(record, test_file)

    assert json_output
    assert isinstance(json_output, str)
    assert test_file.exists()

    # Verify it's valid JSON
    parsed = json.loads(json_output)
    assert "title_translated" in parsed


def test_contact_mapping(record):
    """
    Test that contacts are properly mapped.
    """
    ckan_record = cioos_ckan.generate_ckan_record(record)

    # Check metadata-point-of-contact
    assert len(ckan_record["metadata-point-of-contact"]) > 0
    poc = ckan_record["metadata-point-of-contact"][0]
    assert "role" in poc

    # If cited-responsible-party exists, check it
    if "cited-responsible-party" in ckan_record:
        assert len(ckan_record["cited-responsible-party"]) > 0
        party = ckan_record["cited-responsible-party"][0]
        assert "role" in party


def test_spatial_conversion(record):
    """
    Test spatial data conversion to GeoJSON.
    """
    ckan_record = cioos_ckan.generate_ckan_record(record)

    if "spatial" in ckan_record:
        # Should be a JSON string containing GeoJSON
        spatial = json.loads(ckan_record["spatial"])
        assert "type" in spatial
        assert spatial["type"] == "Polygon"
        assert "coordinates" in spatial


def test_temporal_extent(record):
    """
    Test temporal extent conversion.
    """
    ckan_record = cioos_ckan.generate_ckan_record(record)

    if "temporal-extent" in ckan_record:
        temporal = ckan_record["temporal-extent"]
        assert isinstance(temporal, dict)
        # Should have at least begin or end
        assert "begin" in temporal or "end" in temporal


def test_keywords_extraction(record):
    """
    Test keywords are properly extracted and formatted.
    """
    ckan_record = cioos_ckan.generate_ckan_record(record)

    assert "keywords" in ckan_record
    keywords = ckan_record["keywords"]

    # Should have bilingual keywords
    assert "en" in keywords
    assert isinstance(keywords["en"], list)


def test_eov_extraction(record):
    """
    Test Essential Ocean Variables extraction.
    """
    ckan_record = cioos_ckan.generate_ckan_record(record)

    # EOV is optional but should be a list if present
    if "eov" in ckan_record:
        assert isinstance(ckan_record["eov"], list)


def test_resources_conversion(record):
    """
    Test resources/distribution conversion.
    """
    ckan_record = cioos_ckan.generate_ckan_record(record)

    if "resources" in ckan_record:
        resources = ckan_record["resources"]
        assert isinstance(resources, list)

        for resource in resources:
            assert "url" in resource
            # Check for bilingual name if present
            if "name_translated" in resource:
                assert isinstance(resource["name_translated"], dict)


@pytest.mark.parametrize(
    "firebase_record", (Path(__file__).parent / "records" / "firebase").glob("*.json")
)
def test_firebase_record_to_ckan_json(firebase_record, tmp_path):
    """
    Test the conversion of a Firebase record to CKAN JSON.
    """
    with open(firebase_record, "r") as f:
        record = json.load(f)
    record = record_json_to_yaml(record)

    # Convert the record to CKAN JSON
    test_file = tmp_path / "test_ckan.json"
    json_output = cioos_ckan.to_json(record, test_file)

    assert json_output
    assert isinstance(json_output, str)
    assert test_file.exists()

    # Verify required fields are present
    parsed = json.loads(json_output)
    assert "title_translated" in parsed
    assert "notes_translated" in parsed
    assert "metadata-point-of-contact" in parsed

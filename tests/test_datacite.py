import json
from pathlib import Path

import pytest
from datacite import schema45

from cioos_metadata_conversion import datacite
from cioos_metadata_conversion.firebase_to_cioos import record_json_to_yaml


def test_dataset_cite(record):
    """
    Test the dataset citation generation.
    """
    datacite_record = datacite.generate_datacite_record(record)
    assert datacite_record

    # validate schema
    schema45.validator.validate(datacite_record)


def test_json_output(record, tmp_path):
    """
    Test the JSON output generation.
    """
    test_file = tmp_path / "test.json"
    json_output = datacite.to_json(record, test_file)

    assert json_output
    assert isinstance(json_output, str)  # Ensure it's a string
    assert test_file.exists()  # Ensure the path exists


def test_xml_output(record, tmp_path):
    """
    Test the XML output generation.
    """
    test_file = tmp_path / "test.xml"
    xml_output = datacite.to_xml(record, test_file)

    assert xml_output
    assert isinstance(xml_output, str)  # Ensure it's a string
    assert test_file.exists()  # Ensure the path exists


@pytest.mark.parametrize(
    "firebase_record", (Path(__file__).parent / "records" / "firebase").glob("*.json")
)
def test_firebase_record_to_xml(firebase_record):
    """
    Test the conversion of a Firebase record to XML.
    """
    with open(firebase_record, "r") as f:
        record = json.load(f)
    record = record_json_to_yaml(record)

    # Convert the record to XML
    test_file = firebase_record.with_suffix(".xml")
    xml_output = datacite.to_xml(record, test_file)

    assert xml_output
    assert isinstance(xml_output, str)  # Ensure it's a string
    assert test_file.exists()  # Ensure the path exists


@pytest.mark.parametrize(
    "firebase_record", (Path(__file__).parent / "records" / "firebase").glob("*.json")
)
def test_firebase_record_schema(firebase_record):
    """
    Test the conversion of a Firebase record to XML.
    """
    with open(firebase_record, "r") as f:
        record = json.load(f)
    record = record_json_to_yaml(record)

    # Convert the record to XML
    datacite_record = datacite.generate_datacite_record(record)

    assert datacite_record
    schema45.validator.validate(datacite_record)


@pytest.mark.parametrize(
    "firebase_record", (Path(__file__).parent / "records" / "firebase").glob("*.json")
)
def test_firebase_record_to_json(firebase_record, tmp_path):
    """
    Test the conversion of a Firebase record to JSON.
    """
    with open(firebase_record, "r") as f:
        record = json.load(f)
    record = record_json_to_yaml(record)

    # Convert the record to XML
    test_file = tmp_path / "test.json"
    json_output = datacite.to_json(record, test_file)

    assert json_output
    assert isinstance(json_output, str)  # Ensure it's a string
    assert test_file.exists()  # Ensure the path exists


def test_datacite_record_conversion():
    """
    Test the full conversion process from Firebase to CIOOS to DataCite.
    """
    firebase_record_path = (
        Path(__file__).parent / "records" / "firebase" / "test-dataset-record.json"
    )
    with open(firebase_record_path, "r") as f:
        firebase_record = json.load(f)

    # Convert Firebase to CIOOS
    cioos_record = record_json_to_yaml(firebase_record)

    # Generate DataCite record
    datacite_record = datacite.generate_datacite_record(cioos_record)

    assert datacite_record
    assert isinstance(datacite_record, dict)

    assert datacite_record.get("titles")
    assert datacite_record.get("creators")
    assert datacite_record.get("publisher")
    assert datacite_record.get("publicationYear")
    assert datacite_record.get("types")
    assert datacite_record["types"].get("resourceTypeGeneral") == "Dataset"

    # Review dates
    assert datacite_record.get("dates")
    assert any(
        [date for date in datacite_record["dates"] if date.get("dateType") == "Created"]
    ), "Missing 'Created' date"
    assert any(
        [date for date in datacite_record["dates"] if date.get("dateType") == "Updated"]
    ), "Missing 'Updated' date"
    assert any(
        [
            date
            for date in datacite_record["dates"]
            if date.get("dateType") == "Collected"
        ]
    ), "Missing 'Collected' date"

    # Review Geospatial items
    assert datacite_record.get("geoLocations")
    assert datacite_record["geoLocations"][0].get("geoLocationPolygon"), "Missing 'geoLocationPolygon'"
    assert datacite_record["geoLocations"][0].get("geoLocationPlace"), "Missing 'geoLocationPlace'"

    # Validate funder
    assert datacite_record.get("fundingReferences")
    assert len(datacite_record["fundingReferences"]) == 1
    assert datacite_record["fundingReferences"][0].get("funderName")
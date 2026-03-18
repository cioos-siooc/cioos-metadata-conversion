import json
import os
from pathlib import Path

import pytest
import requests
from datacite import schema45
from dotenv import load_dotenv

from cioos_metadata_conversion import datacite
from cioos_metadata_conversion.firebase_to_cioos import record_json_to_yaml

load_dotenv()

DATACITE_API_URL = "https://api.test.datacite.org/dois"
DATACITE_REPOSITORY_ID = os.environ.get("DATACITE_REPOSITORY_ID")
DATACITE_PASSWORD = os.environ.get("DATACITE_PASSWORD")
DATACITE_PREFIX = os.environ.get("DATACITE_PREFIX")

has_datacite_credentials = all([DATACITE_REPOSITORY_ID, DATACITE_PASSWORD, DATACITE_PREFIX])


def _submit_datacite_draft(datacite_record):
    """Submit a DataCite record as a draft DOI and return the response.

    Removes any existing DOI and adds the test prefix so DataCite
    auto-generates a suffix. The draft is cleaned up by the caller.
    """
    attributes = {**datacite_record}
    attributes.pop("doi", None)
    attributes["prefix"] = DATACITE_PREFIX

    payload = {
        "data": {
            "type": "dois",
            "attributes": attributes,
        }
    }

    response = requests.post(
        DATACITE_API_URL,
        json=payload,
        headers={"Content-Type": "application/vnd.api+json"},
        auth=(DATACITE_REPOSITORY_ID, DATACITE_PASSWORD),
    )
    return response


def _delete_datacite_draft(doi):
    """Delete a draft DOI from the DataCite test API."""
    requests.delete(
        f"{DATACITE_API_URL}/{doi}",
        auth=(DATACITE_REPOSITORY_ID, DATACITE_PASSWORD),
    )


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

def test_datacite_doi_url_with_prefix(record):
    """
    Test the URL and DOI generation in the DataCite record.
    """
    url = "http://CATALOGUE_URL.com/dataset/cioos-ca_"
    doi_prefix = "10.12345"

    # Drop doi from record for this test
    if "identifier" in record["identification"]:
        record["identification"].pop("identifier")
    datacite_record = datacite.generate_datacite_record(record, url, doi_prefix=doi_prefix)

    assert datacite_record.get("url").startswith(url)
    assert datacite_record.get("prefix") == doi_prefix
    
def test_datacite_doi_url_without_prefix(record):
    """
    Test the URL and DOI generation in the DataCite record without a DOI prefix.
    """
    url = "http://CATALOGUE_URL.com/dataset/cioos-ca_"

    datacite_record = datacite.generate_datacite_record(record, url)

    assert datacite_record.get("url").startswith(url)
    assert datacite_record.get("doi") == record["identification"].get("identifier").replace("https://doi.org/", "")
    assert datacite_record.get("prefix") is None


def test_datacite_doi_url_with_existing_doi(record):
    """
    Test the URL and DOI generation in the DataCite record with an existing DOI.
    """
    url = "http://CATALOGUE_URL.com/dataset/cioos-ca_"
    doi_prefix = "10.12345"
    existing_doi = "10.12345/abcdefg"

    record["identification"]["identifier"] = f"https://doi.org/{existing_doi}"
    datacite_record = datacite.generate_datacite_record(record, url, doi_prefix=doi_prefix)

    assert datacite_record.get("url").startswith(url)
    assert datacite_record.get("doi") == existing_doi
    assert datacite_record.get("prefix") is None


def test_datacite_doi_url_with_nonmatching_prefix(record):
    """
    Test the URL and DOI generation in the DataCite record with a non-matching DOI prefix.
    """
    url = "http://CATALOGUE_URL.com/dataset/cioos-ca_"
    doi_prefix = "10.12345"
    existing_doi = "10.67890/abcdefg"

    record["identification"]["identifier"] = f"https://doi.org/{existing_doi}"
    datacite_record = datacite.generate_datacite_record(record, url, doi_prefix=doi_prefix)

    assert datacite_record.get("url").startswith(url)
    assert datacite_record.get("doi") == existing_doi
    assert datacite_record.get("prefix") is None


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
    collected_date = [
        date
        for date in datacite_record["dates"]
        if date.get("dateType") == "Collected"
    ]
    assert datacite_record.get("dates")
    assert any(
        [date for date in datacite_record["dates"] if date.get("dateType") == "Created"]
    ), "Missing 'Created' date"
    assert any(
        [date for date in datacite_record["dates"] if date.get("dateType") == "Updated"]
    ), "Missing 'Updated' date"
    assert any(
        collected_date
    ), "Missing 'Collected' date"
    assert len(collected_date) == 1, "Multiple 'Collected' dates found"
    assert collected_date[0].get("date"), "'Collected' date is empty"
    assert "/" in collected_date[0]["date"]

    # Review Geospatial items
    assert datacite_record.get("geoLocations")
    assert datacite_record["geoLocations"][0].get("geoLocationPolygon"), "Missing 'geoLocationPolygon'"
    assert datacite_record["geoLocations"][0].get("geoLocationPlace"), "Missing 'geoLocationPlace'"

    # Validate funder
    assert datacite_record.get("fundingReferences")
    assert len(datacite_record["fundingReferences"]) == 1
    assert datacite_record["fundingReferences"][0].get("funderName")

@pytest.mark.integration
@pytest.mark.skipif(
    not has_datacite_credentials,
    reason="DataCite test API credentials not set (DATACITE_REPOSITORY_ID, DATACITE_PASSWORD, DATACITE_PREFIX)",
)
@pytest.mark.parametrize(
    "firebase_record", (Path(__file__).parent / "records" / "firebase").glob("*.json")
)
def test_firebase_record_submit_datacite_api(firebase_record):
    """
    Test submitting a Firebase-converted DataCite record to the DataCite test API.
    """
    with open(firebase_record, "r") as f:
        record = json.load(f)
    record = record_json_to_yaml(record)
    datacite_record = datacite.generate_datacite_record(record)

    doi = None
    try:
        response = _submit_datacite_draft(datacite_record)
        assert response.status_code == 201, (
            f"DataCite API returned {response.status_code} for {firebase_record.name}: "
            f"{response.json().get('errors', response.text)}"
        )
        data = response.json()
        doi = data["data"]["id"]
        assert data["data"]["attributes"]["state"] == "draft"
    finally:
        if doi:
            _delete_datacite_draft(doi)


@pytest.mark.integration
@pytest.mark.skipif(
    not has_datacite_credentials,
    reason="DataCite test API credentials not set (DATACITE_REPOSITORY_ID, DATACITE_PASSWORD, DATACITE_PREFIX)",
)
def test_cioos_record_submit_datacite_api(record):
    """
    Test submitting a CIOOS YAML-based DataCite record to the DataCite test API.
    """
    datacite_record = datacite.generate_datacite_record(record)

    doi = None
    try:
        response = _submit_datacite_draft(datacite_record)
        assert response.status_code == 201, (
            f"DataCite API returned {response.status_code}: "
            f"{response.json().get('errors', response.text)}"
        )
        data = response.json()
        doi = data["data"]["id"]
        assert data["data"]["attributes"]["state"] == "draft"
    finally:
        if doi:
            _delete_datacite_draft(doi)

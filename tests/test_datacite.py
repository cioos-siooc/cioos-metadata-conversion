import json
from pathlib import Path
import os

import pytest
from datacite import DataCiteRESTClient, schema45
from deepdiff import DeepDiff

from cioos_metadata_conversion import datacite
from cioos_metadata_conversion.load_from import datacite as datacite_loader
from cioos_metadata_conversion.firebase_to_cioos import record_json_to_yaml
from dotenv import load_dotenv

load_dotenv()


DATACITE_CREDENTIALS_AVAILABLE = all(
    os.getenv(var)
    for var in ["DATACITE_ACCOUNT_ID", "DATACITE_PASSWORD", "DATACITE_PREFIX"]
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


@pytest.fixture
def datacite_client():
    """
    Fixture to create a DataCiteRESTClient instance.
    """
    client = DataCiteRESTClient(
        username=os.getenv("DATACITE_ACCOUNT_ID"),
        password=os.getenv("DATACITE_PASSWORD"),
        prefix=os.getenv("DATACITE_PREFIX"),
        test_mode=True,
    )
    return client


@pytest.fixture
def doi():
    return f"{os.getenv('DATACITE_PREFIX')}/cioos-metadata-conversion-tests"


@pytest.mark.skipif(
    not DATACITE_CREDENTIALS_AVAILABLE,
    reason="Datacite credentials not available in environment variables.",
)
class TestDataCiteSubmission:
    """
    Test class for DataCite submission and deletion.
    """

    @pytest.fixture
    def datacite_record(self, record):
        """
        Generate a DataCite record from the given record.
        """
        return datacite.generate_datacite_record(record)

    def test_datacite_draft_submission(self, datacite_record, datacite_client, doi):
        """
        Test the submission of a record to DataCite.
        """
        returned_doi = datacite_client.draft_doi(datacite_record, doi=doi)

        assert doi == returned_doi, "The returned DOI does not match the expected DOI."

    def test_datacite_retrieval(self, datacite_client, doi, record):
        """
        Test the retrieval of a record from DataCite.
        """
        retrieved_datacite_record = datacite_client.metadata_get(doi)
        assert (
            retrieved_datacite_record is not None
        ), "The DOI was not found in DataCite: {}".format(retrieved_datacite_record)

        firebase_record = datacite_loader.map_datacite_to_firebase(
            retrieved_datacite_record
        )

        diff = DeepDiff(
            record,
            firebase_record,
            ignore_order=True,
            significant_digits=5,
        )
        assert (
            diff == {}
        ), "The retrieved record does not match the original record: {}".format(diff)

    @pytest.mark.dependency(depends=["TestDataCiteSubmission::test_datacite_retrieval"])
    def test_datacite_deletion(self, datacite_client, doi):
        """
        Test the deletion of a record from DataCite.
        """
        response = datacite_client.delete_doi(doi)

        assert not response, "The DOI was not successfully deleted: {}".format(response)

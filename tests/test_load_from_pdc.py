"""
Unit tests for Polar Data Catalogue (PDC) retrieval and Firebase mapping.

Tests cover:
- Parsing PDC ISO 19139 XML records
- PDC to Firebase metadata mapping
- Integration with the Record class
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cioos_metadata_conversion.load_from.pdc import (
    PDC_ISO,
    PDCRetrievalError,
    _apply_role_mapping,
    _contact_name,
    _parse_date,
    fetch_pdc_metadata,
    retrieve_pdc_as_firebase_record,
)
from cioos_metadata_conversion.record import InputSchemas, Record

# CCIN reference number of the public PDC record used across the tests.
CCIN = "13172"


@pytest.fixture(scope="session")
def pdc_iso_file(tmp_path_factory):
    """Download the PDC ISO XML record once per test session.

    The record is fetched live from the Polar Data Catalogue rather than
    committed to the repository. Tests depending on it are skipped when the
    catalogue cannot be reached (e.g. offline environments).
    """
    try:
        xml = fetch_pdc_metadata(CCIN)
    except PDCRetrievalError as e:
        pytest.skip(f"Could not download PDC record {CCIN}: {e}")
    # File name must match "<ccin>_iso.xml" so the CCIN can be inferred from it.
    path = tmp_path_factory.mktemp("pdc") / f"{CCIN}_iso.xml"
    path.write_text(xml, encoding="utf-8")
    return str(path)


def _mock_doi_not_found():
    """Mock response so _get_doi does not hit doi.org."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    return mock_response


# Tests for helper functions


class TestParseDate:
    def test_parse_valid_date(self):
        assert _parse_date("2024-07-18") == "2024-07-18T00:00:00Z"

    def test_parse_empty_date(self):
        assert _parse_date("") is None
        assert _parse_date(None) is None
        assert _parse_date("Undefined") is None

    def test_parse_invalid_date_is_returned_as_is(self):
        assert _parse_date("July 2024") == "July 2024"


class TestContactName:
    def test_split_given_and_last_names(self):
        assert _contact_name("John Doe") == ["John", "Doe"]

    def test_comma_separated_name_is_reversed(self):
        assert _contact_name("Doe, John") == ["John", "Doe"]

    def test_name_mapping(self):
        assert _contact_name("Polar Data Catalogue") == ["Polar Data Catalogue", ""]

    def test_no_name(self):
        assert _contact_name(None) == [""]


class TestRoleMapping:
    def test_mapped_role(self):
        assert _apply_role_mapping("Originator") == "originator"

    def test_already_mapped_role(self):
        assert _apply_role_mapping("pointOfContact") == "pointOfContact"

    def test_unknown_role(self):
        assert _apply_role_mapping("unknownRole") is None


# Tests for PDC_ISO parsing


class TestPDCISO:
    def test_parse_from_file(self, pdc_iso_file):
        record = PDC_ISO(pdc_iso_file)
        assert record.get(".//gmd:title/gco:CharacterString").startswith(
            "CCGS Amundsen underway gas measurements"
        )

    def test_parse_from_text(self, pdc_iso_file):
        xml_text = Path(pdc_iso_file).read_text(encoding="utf-8")
        record = PDC_ISO(xml_text)
        assert record.get(".//gmd:title/gco:CharacterString").startswith(
            "CCGS Amundsen underway gas measurements"
        )

    def test_get_keywords(self, pdc_iso_file):
        record = PDC_ISO(pdc_iso_file)
        keywords = record._get_keywords()
        assert "Biogeochemistry" in keywords

    def test_get_eov_from_keywords(self, pdc_iso_file):
        record = PDC_ISO(pdc_iso_file)
        eovs = record._get_eov_from_keywords()
        assert isinstance(eovs, list)
        assert len(eovs) > 0


# Tests for PDC to Firebase mapping


class TestToFirebase:
    @pytest.fixture
    def firebase_record(self, pdc_iso_file):
        with patch(
            "cioos_metadata_conversion.load_from.pdc.requests.get",
            return_value=_mock_doi_not_found(),
        ):
            return PDC_ISO(pdc_iso_file).to_firebase(
                userID="test-user",
                filename="ccin-13172",
                recordID="ccin-13172",
                status="published",
                license="CC-BY-4.0",
                region="amundsen",
            )

    def test_expected_firebase_keys(self, firebase_record):
        expected_keys = [
            "userID",
            "title",
            "abstract",
            "contacts",
            "created",
            "datasetIdentifier",
            "dateStart",
            "dateEnd",
            "keywords",
            "language",
            "license",
            "map",
            "metadataScope",
            "progress",
            "recordID",
            "status",
            "associated_resources",
            "eov",
        ]
        for key in expected_keys:
            assert key in firebase_record, f"Missing expected key: {key}"

    def test_title_and_abstract(self, firebase_record):
        assert firebase_record["title"]["en"].startswith(
            "CCGS Amundsen underway gas measurements"
        )
        assert firebase_record["abstract"]["en"]

    def test_contacts(self, firebase_record):
        assert len(firebase_record["contacts"]) > 0
        for contact in firebase_record["contacts"]:
            for field in ["lastName", "givenNames", "orgName", "role"]:
                assert field in contact, f"Contact missing field: {field}"

    def test_dates(self, firebase_record):
        assert firebase_record["dateStart"] == "2018-07-24T00:00:00Z"
        assert firebase_record["dateEnd"] == "2019-08-15T00:00:00Z"
        assert firebase_record["created"] == "2024-07-18T00:00:00Z"

    def test_map_bounds(self, firebase_record):
        assert firebase_record["map"]["north"] == "81.84"
        assert firebase_record["map"]["south"] is not None
        assert firebase_record["map"]["east"] is not None
        assert firebase_record["map"]["west"] is not None

    def test_language_and_progress(self, firebase_record):
        assert firebase_record["language"] == "en"
        assert firebase_record["progress"] == "underDevelopment"

    def test_keywords(self, firebase_record):
        assert "Biogeochemistry" in firebase_record["keywords"]["en"]
        assert firebase_record["keywords"]["fr"] == []

    def test_passed_in_values(self, firebase_record):
        assert firebase_record["userID"] == "test-user"
        assert firebase_record["recordID"] == "ccin-13172"
        assert firebase_record["license"] == "CC-BY-4.0"
        assert firebase_record["region"] == "amundsen"
        assert firebase_record["status"] == "published"

    def test_associated_resources_point_to_pdc(self, firebase_record):
        assert firebase_record["associated_resources"][0]["code"] == (
            "https://www.polardata.ca/pdcsearch/PDCSearchDOI.jsp?doi_id=13172"
        )

    def test_identifier_is_generated(self, firebase_record):
        assert firebase_record["identifier"].startswith("ccin-")
        assert len(firebase_record["identifier"]) > len("ccin-")


# Tests for retrieval


class TestFetchPDCMetadata:
    @patch("cioos_metadata_conversion.load_from.pdc.requests.get")
    def test_fetch_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = "<xml/>"
        mock_get.return_value = mock_response

        result = fetch_pdc_metadata("13172")

        assert result == "<xml/>"
        called_url = mock_get.call_args[0][0]
        assert called_url == "https://polardata.ca/pdcsearch/xml/iso/13172_iso.xml"

    @patch("cioos_metadata_conversion.load_from.pdc.requests.get")
    def test_fetch_failure(self, mock_get):
        import requests

        mock_get.side_effect = requests.ConnectionError("Network error")

        with pytest.raises(PDCRetrievalError):
            fetch_pdc_metadata("13172")


class TestRetrievePDCAsFirebaseRecord:
    @patch(
        "cioos_metadata_conversion.load_from.pdc.requests.get",
        return_value=_mock_doi_not_found(),
    )
    def test_retrieve_from_local_file(self, mock_get, pdc_iso_file):
        record = retrieve_pdc_as_firebase_record(pdc_iso_file)

        assert record["title"]["en"].startswith("CCGS Amundsen")
        # CCIN inferred from the file name
        assert record["filename"] == f"ccin-{CCIN}"
        assert record["recordID"] == f"ccin-{CCIN}"

    def test_retrieve_invalid_file(self):
        with pytest.raises(PDCRetrievalError):
            retrieve_pdc_as_firebase_record("missing_file.xml")


# Integration with the Record class


class TestRecordIntegration:
    @patch(
        "cioos_metadata_conversion.load_from.pdc.requests.get",
        return_value=_mock_doi_not_found(),
    )
    def test_load_pdc_xml_file(self, mock_get, pdc_iso_file):
        record = Record(source=pdc_iso_file, schema="pdc").load()

        assert record.schema == InputSchemas.firebase
        assert record.metadata["title"]["en"].startswith("CCGS Amundsen")

    @patch(
        "cioos_metadata_conversion.load_from.pdc.requests.get",
        return_value=_mock_doi_not_found(),
    )
    def test_convert_to_cioos_schema(self, mock_get, pdc_iso_file):
        record = (
            Record(source=pdc_iso_file, schema="pdc")
            .load()
            .convert_to_cioos_schema()
        )

        assert record.schema == InputSchemas.CIOOS
        identification = record.metadata["identification"]
        assert identification["title"]["en"].startswith("CCGS Amundsen")
        assert record.metadata["spatial"]["bbox"]
        assert record.metadata["contact"]


# Real-world test hitting the PDC and doi.org (network required)


@pytest.mark.parametrize("ccin", ["13172"])
def test_real_pdc_record(ccin):
    """Test retrieval and mapping of a real PDC record."""
    firebase_record = retrieve_pdc_as_firebase_record(ccin)

    assert firebase_record["title"]["en"]
    assert firebase_record["filename"] == f"ccin-{ccin}"
    assert firebase_record["contacts"]

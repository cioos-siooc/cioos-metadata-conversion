"""
Unit tests for DOI retrieval and Firebase mapping functionality.

Tests cover:
- DOI metadata fetching from DataCite API
- DataCite to Firebase metadata mapping
- Proper handling of edge cases and missing data
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from cioos_metadata_conversion.load_from.datacite import (
    fetch_doi_metadata,
    map_datacite_to_firebase,
    retrieve_doi_as_firebase_record,
    DOIRetrievalError,
    _map_title,
    _map_abstract,
    _map_contacts,
    _map_associated_resources,
    _map_license,
    _map_resource_type,
    _extract_orcid,
    _extract_org_name,
)
import requests

# Fixtures for test data

@pytest.fixture
def sample_datacite_response():
    """Sample DataCite API response for a typical dataset."""
    return {
        "data": {
            "id": "10.26071/mxtr-gp72",
            "type": "dois",
            "attributes": {
                "doi": "10.26071/mxtr-gp72",
                "titles": [
                    {
                        "title": "St. Lawrence Global Observatory Dataset",
                        "lang": "en"
                    },
                    {
                        "title": "Observatoire mondial du Saint-Laurent",
                        "lang": "fr"
                    }
                ],
                "descriptions": [
                    {
                        "description": "A comprehensive marine dataset covering the St. Lawrence region.",
                        "descriptionType": "Abstract",
                        "lang": "en"
                    },
                    {
                        "description": "Un ensemble de données marines complet couvrant la région du Saint-Laurent.",
                        "descriptionType": "Abstract",
                        "lang": "fr"
                    }
                ],
                "creators": [
                    {
                        "name": "María-Emilia Rodríguez-Cuicas",
                        "nameType": "Personal",
                        "givenName": "María-Emilia",
                        "familyName": "Rodríguez-Cuicas",
                        "nameIdentifier": {
                            "nameIdentifier": "https://orcid.org/0000-0003-0067-3670",
                            "nameIdentifierScheme": "ORCID",
                            "schemeUri": "https://orcid.org"
                        },
                        "affiliation": [
                            {
                                "name": "St. Lawrence Global Observatory",
                                "affiliationIdentifier": "https://ror.org/03wfagk22",
                                "affiliationIdentifierScheme": "ROR"
                            }
                        ]
                    }
                ],
                "keywords": [
                    "marine science",
                    "ocean research",
                    "coastal zones",
                    "environmental monitoring"
                ],
                "publicationYear": 2024,
                "language": "en",
                "types": {
                    "resourceType": "Dataset",
                    "resourceTypeGeneral": "Dataset"
                },
                "rightsList": [
                    {
                        "rights": "CC-BY-4.0",
                        "rightsUri": "https://creativecommons.org/licenses/by/4.0/"
                    }
                ],
                "relatedIdentifiers": [
                    {
                        "relatedIdentifier": "10.1002/jqs.3531",
                        "relatedIdentifierType": "DOI",
                        "relationType": "IsCitedBy",
                        "title": "A 600-year marine record"
                    },
                    {
                        "relatedIdentifier": "https://obis.org/dataset/06704bbe",
                        "relatedIdentifierType": "URL",
                        "relationType": "IsReferencedBy"
                    }
                ]
            }
        }
    }


@pytest.fixture
def sample_firebase_structure():
    """Sample Firebase record structure for comparison."""
    return {
        "datasetIdentifier": "https://doi.org/10.26071/mxtr-gp72",
        "title": {
            "en": "St. Lawrence Global Observatory Dataset",
            "fr": "Observatoire mondial du Saint-Laurent"
        },
        "abstract": {
            "en": "A comprehensive marine dataset covering the St. Lawrence region.",
            "fr": "Un ensemble de données marines complet couvrant la région du Saint-Laurent."
        },
        "keywords": {
            "en": ["marine science", "ocean research", "coastal zones", "environmental monitoring"]
        },
        "license": "CC-BY-4.0",
        "language": "en"
    }


# Tests for DOI metadata fetching

class TestFetchDOIMetadata:
    """Test suite for fetch_doi_metadata function."""

    @patch('cioos_metadata_conversion.load_from.datacite.requests.get')
    def test_fetch_doi_success(self, mock_get, sample_datacite_response):
        """Test successful DOI metadata retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_datacite_response
        mock_get.return_value = mock_response

        result = fetch_doi_metadata("10.26071/mxtr-gp72")

        assert result == sample_datacite_response
        mock_get.assert_called_once()

    @patch('cioos_metadata_conversion.load_from.datacite.requests.get')
    def test_fetch_doi_with_url_format(self, mock_get, sample_datacite_response):
        """Test that DOI URL format is properly normalized."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_datacite_response
        mock_get.return_value = mock_response

        fetch_doi_metadata("https://doi.org/10.26071/mxtr-gp72")

        # Should strip the URL prefix before calling API
        called_url = mock_get.call_args[0][0]
        assert "10.26071/mxtr-gp72" in called_url
        assert "https://doi.org" not in called_url

    @patch('cioos_metadata_conversion.load_from.datacite.requests.get')
    def test_fetch_doi_not_found(self, mock_get):
        """Test handling of non-existent DOI."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(DOIRetrievalError) as exc_info:
            fetch_doi_metadata("10.invalid/invalid")

        assert "DOI not found" in str(exc_info.value)

    @patch('cioos_metadata_conversion.load_from.datacite.requests.get')
    def test_fetch_doi_network_error(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = requests.ConnectionError("Network error")

        with pytest.raises(DOIRetrievalError):
            fetch_doi_metadata("10.26071/mxtr-gp72")


# Tests for DataCite to Firebase mapping

class TestMapDoCiteToFirebase:
    """Test suite for map_datacite_to_firebase function."""

    def test_map_complete_record(self, sample_datacite_response):
        """Test mapping a complete DataCite record."""
        result = map_datacite_to_firebase(sample_datacite_response, "10.26071/mxtr-gp72")

        assert result["datasetIdentifier"] == "https://doi.org/10.26071/mxtr-gp72"
        assert "en" in result["title"]
        assert "en" in result["abstract"]
        assert len(result["contacts"]) > 0
        assert result["license"] == "CC-BY-4.0"

    def test_map_missing_optional_fields(self):
        """Test mapping with minimal DataCite data."""
        minimal_datacite = {
            "data": {
                "attributes": {
                    "titles": [{"title": "Test Dataset"}],
                    "creators": []
                }
            }
        }

        result = map_datacite_to_firebase(minimal_datacite, "10.test/test")

        assert result["title"]["en"] == "Test Dataset"
        assert result["abstract"] == {"en": ""}
        assert result["contacts"] == []

    def test_map_preserves_multilingual_data(self, sample_datacite_response):
        """Test that multilingual data is properly preserved."""
        result = map_datacite_to_firebase(sample_datacite_response, "10.26071/mxtr-gp72")

        assert result["title"]["en"] is not None
        assert result["title"]["fr"] is not None
        assert result["abstract"]["en"] is not None
        assert result["abstract"]["fr"] is not None


# Tests for individual mapping functions

class TestMapTitle:
    """Test suite for _map_title function."""

    def test_map_single_language(self):
        """Test mapping title in single language."""
        titles = [{"title": "Dataset Title", "lang": "en"}]
        result = _map_title(titles)
        assert result == {"en": "Dataset Title"}

    def test_map_multilingual_titles(self):
        """Test mapping multilingual titles."""
        titles = [
            {"title": "English Title", "lang": "en"},
            {"title": "French Title", "lang": "fr"}
        ]
        result = _map_title(titles)
        assert result["en"] == "English Title"
        assert result["fr"] == "French Title"

    def test_ignore_non_en_fr_languages(self):
        """Test that non-English/French titles are ignored."""
        titles = [
            {"title": "English Title", "lang": "en"},
            {"title": "Spanish Title", "lang": "es"}
        ]
        result = _map_title(titles)
        assert "es" not in result
        assert result["en"] == "English Title"

    def test_empty_titles(self):
        """Test handling of empty titles array."""
        result = _map_title([])
        assert result["en"] == ""


class TestMapAbstract:
    """Test suite for _map_abstract function."""

    def test_map_abstract_with_correct_type(self):
        """Test that only Abstract descriptionType is mapped."""
        descriptions = [
            {
                "description": "This is the abstract",
                "descriptionType": "Abstract",
                "lang": "en"
            },
            {
                "description": "This is other info",
                "descriptionType": "Methods",
                "lang": "en"
            }
        ]
        result = _map_abstract(descriptions)
        assert result["en"] == "This is the abstract"

    def test_empty_abstracts(self):
        """Test handling of empty abstracts."""
        result = _map_abstract([])
        assert result == {"en": ""}


class TestMapContacts:
    """Test suite for _map_contacts function."""

    def test_map_personal_creator(self):
        """Test mapping personal creator information."""
        creators = [
            {
                "name": "John Doe",
                "nameType": "Personal",
                "givenName": "John",
                "familyName": "Doe",
                "nameIdentifier": {"nameIdentifier": "https://orcid.org/0000-0001-2345-6789"},
                "affiliation": [{"name": "Test University"}]
            }
        ]
        result = _map_contacts(creators)

        assert len(result) == 1
        assert result[0]["givenNames"] == "John"
        assert result[0]["lastName"] == "Doe"
        assert result[0]["indOrcid"] == "https://orcid.org/0000-0001-2345-6789"
        assert result[0]["orgName"] == "Test University"
        assert "owner" in result[0]["role"]

    def test_map_organizational_creator(self):
        """Test mapping organizational creator information."""
        creators = [
            {
                "name": "Research Institute",
                "nameType": "Organizational"
            }
        ]
        result = _map_contacts(creators)

        assert len(result) == 1
        assert result[0]["orgName"] == "Research Institute"
        assert "publisher" in result[0]["role"]

    def test_multiple_creators_roles(self):
        """Test that first creator gets 'owner' role and others get 'collaborator'."""
        creators = [
            {"name": "First Author", "nameType": "Personal", "givenName": "First", "familyName": "Author"},
            {"name": "Second Author", "nameType": "Personal", "givenName": "Second", "familyName": "Author"}
        ]
        result = _map_contacts(creators)

        assert "owner" in result[0]["role"]
        assert "collaborator" in result[1]["role"]


class TestMapAssociatedResources:
    """Test suite for _map_associated_resources function."""

    def test_map_related_identifiers(self):
        """Test mapping of related identifiers."""
        related_ids = [
            {
                "relatedIdentifier": "10.1002/jqs.3531",
                "relatedIdentifierType": "DOI",
                "relationType": "IsCitedBy"
            }
        ]
        result = _map_associated_resources(related_ids)

        assert len(result) == 1
        assert result[0]["authority"] == "DOI"
        assert result[0]["code"] == "10.1002/jqs.3531"
        assert result[0]["association_type"] == "IsCitedBy"

    def test_empty_related_identifiers(self):
        """Test handling of empty related identifiers."""
        result = _map_associated_resources([])
        assert result == []


class TestExtractORCID:
    """Test suite for _extract_orcid function."""

    def test_extract_orcid_from_dict(self):
        """Test extracting ORCID from dictionary format."""
        name_id = {"nameIdentifier": "https://orcid.org/0000-0001-2345-6789"}
        result = _extract_orcid(name_id)
        assert result == "https://orcid.org/0000-0001-2345-6789"

    def test_extract_orcid_without_url_prefix(self):
        """Test extracting ORCID when URL prefix is missing."""
        name_id = {"nameIdentifier": "0000-0001-2345-6789"}
        result = _extract_orcid(name_id)
        assert result == "https://orcid.org/0000-0001-2345-6789"

    def test_extract_orcid_as_string(self):
        """Test extracting ORCID when provided as string."""
        result = _extract_orcid("https://orcid.org/0000-0001-2345-6789")
        assert result == "https://orcid.org/0000-0001-2345-6789"


class TestIntegration:
    """Integration tests for complete DOI retrieval workflow."""

    @patch('cioos_metadata_conversion.load_from.datacite.fetch_doi_metadata')
    def test_full_workflow(self, mock_fetch, sample_datacite_response):
        """Test complete workflow from DOI to Firebase record."""
        mock_fetch.return_value = sample_datacite_response

        result = retrieve_doi_as_firebase_record("10.26071/mxtr-gp72")

        assert result["datasetIdentifier"] == "https://doi.org/10.26071/mxtr-gp72"
        assert "title" in result
        assert "contacts" in result
        assert "associated_resources" in result


# Test real-world scenario against the Firebase test file structure

class TestFirebaseCompatibility:
    """Tests to ensure compatibility with existing Firebase records."""

    def test_generated_record_matches_firebase_structure(self, sample_datacite_response):
        """Test that generated record has expected Firebase structure keys."""
        result = map_datacite_to_firebase(sample_datacite_response, "10.26071/mxtr-gp72")

        # Check that key Firebase fields are present
        expected_keys = [
            "datasetIdentifier",
            "title",
            "abstract",
            "keywords",
            "license",
            "contacts",
            "associated_resources",
            "language",
            "metadataScope",
            "doiCreationStatus",
            "progress"
        ]

        for key in expected_keys:
            assert key in result, f"Missing expected key: {key}"

    def test_title_structure_matches_firebase(self, sample_datacite_response):
        """Test that title structure matches Firebase expectations."""
        result = map_datacite_to_firebase(sample_datacite_response, "10.26071/mxtr-gp72")

        assert isinstance(result["title"], dict)
        assert "en" in result["title"] or len(result["title"]) > 0

    def test_contacts_structure_matches_firebase(self, sample_datacite_response):
        """Test that contacts structure matches Firebase expectations."""
        result = map_datacite_to_firebase(sample_datacite_response, "10.26071/mxtr-gp72")

        assert isinstance(result["contacts"], list)
        for contact in result["contacts"]:
            expected_contact_fields = ["lastName", "givenNames", "orgName", "role"]
            for field in expected_contact_fields:
                assert field in contact, f"Contact missing field: {field}"


@pytest.mark.parametrize("doi", ["10.71708/zgvv-xk59"])
def test_real_doi(doi):
    """Test retrieval and mapping of a real DOI."""
    firebase_record = retrieve_doi_as_firebase_record(doi)

    assert "datasetIdentifier" in firebase_record
    assert firebase_record["datasetIdentifier"] == f"https://doi.org/{doi}"
    assert "title" in firebase_record
    assert "abstract" in firebase_record
"""
Unit tests for DOI retrieval and Firebase mapping functionality.

Tests cover:
- DOI metadata fetching from the DataCite API (via DataCiteRESTClient)
- DataCite to Firebase metadata mapping
- Proper handling of edge cases and missing data
"""

import pytest
from unittest.mock import patch
from cioos_metadata_conversion.load_from.datacite import (
    fetch_doi_metadata,
    map_datacite_to_firebase,
    normalize_doi,
    retrieve_doi_as_firebase_record,
    DOIRetrievalError,
    _map_title,
    _map_abstract,
    _map_keywords,
    _map_contacts,
    _map_associated_resources,
    _extract_orcid,
)
import requests

# Fixtures for test data

@pytest.fixture
def sample_datacite_attributes():
    """Sample DataCite metadata attributes as returned by
    DataCiteRESTClient.get_metadata (i.e. response["data"]["attributes"])."""
    return {
        "doi": "10.0000/test-doi",
        "state": "findable",
        "titles": [
            {
                "title": "Example Marine Dataset",
                "lang": "en"
            },
            {
                "title": "Exemple de jeu de données marines",
                "lang": "fr"
            }
        ],
        "descriptions": [
            {
                "description": "A comprehensive marine dataset covering an example region.",
                "descriptionType": "Abstract",
                "lang": "en"
            },
            {
                "description": "Un ensemble de données marines complet couvrant une région d'exemple.",
                "descriptionType": "Abstract",
                "lang": "fr"
            }
        ],
        "creators": [
            {
                "name": "Doe, Jane",
                "nameType": "Personal",
                "givenName": "Jane",
                "familyName": "Doe",
                "nameIdentifiers": [
                    {
                        "nameIdentifier": "https://orcid.org/0000-0000-0000-0000",
                        "nameIdentifierScheme": "ORCID",
                        "schemeUri": "https://orcid.org"
                    }
                ],
                "affiliation": [
                    {
                        "name": "Example Observatory",
                        "affiliationIdentifier": "https://ror.org/00000000",
                        "affiliationIdentifierScheme": "ROR"
                    }
                ]
            }
        ],
        "subjects": [
            {"subject": "marine science", "lang": "en"},
            {"subject": "ocean research", "lang": "en"},
            {"subject": "coastal zones", "lang": "en"},
            {"subject": "science marine", "lang": "fr"},
            {
                "subject": "FOS: Earth and related environmental sciences",
                "schemeUri": "http://www.oecd.org/science/inno/38235147.pdf",
                "subjectScheme": "Fields of Science and Technology (FOS)"
            }
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


# Tests for DOI normalization

class TestNormalizeDOI:
    """Test suite for normalize_doi function."""

    def test_bare_doi(self):
        assert normalize_doi("10.0000/test-doi") == "10.0000/test-doi"

    def test_url_prefix(self):
        assert normalize_doi("https://doi.org/10.0000/test-doi") == "10.0000/test-doi"

    def test_doi_prefix(self):
        assert normalize_doi("doi:10.0000/test-doi") == "10.0000/test-doi"


# Tests for DOI metadata fetching

class TestFetchDOIMetadata:
    """Test suite for fetch_doi_metadata function."""

    @patch('cioos_metadata_conversion.load_from.datacite.datacite_client')
    def test_fetch_doi_success(self, mock_client, sample_datacite_attributes):
        """Test successful DOI metadata retrieval."""
        mock_client.get_metadata.return_value = sample_datacite_attributes

        result = fetch_doi_metadata("10.0000/test-doi")

        assert result == sample_datacite_attributes
        mock_client.get_metadata.assert_called_once_with("10.0000/test-doi")

    @patch('cioos_metadata_conversion.load_from.datacite.datacite_client')
    def test_fetch_doi_with_url_format(self, mock_client, sample_datacite_attributes):
        """Test that DOI URL format is properly normalized."""
        mock_client.get_metadata.return_value = sample_datacite_attributes

        fetch_doi_metadata("https://doi.org/10.0000/test-doi")

        # Should strip the URL prefix before calling the API
        mock_client.get_metadata.assert_called_once_with("10.0000/test-doi")

    @patch('cioos_metadata_conversion.load_from.datacite.datacite_client')
    def test_fetch_doi_not_found(self, mock_client):
        """Test handling of non-existent DOI."""
        mock_client.get_metadata.side_effect = Exception("DOI not found")

        with pytest.raises(DOIRetrievalError) as exc_info:
            fetch_doi_metadata("10.invalid/invalid")

        assert "DOI not found" in str(exc_info.value)

    @patch('cioos_metadata_conversion.load_from.datacite.datacite_client')
    def test_fetch_doi_network_error(self, mock_client):
        """Test handling of network errors."""
        mock_client.get_metadata.side_effect = requests.ConnectionError("Network error")

        with pytest.raises(DOIRetrievalError):
            fetch_doi_metadata("10.0000/test-doi")


# Tests for DataCite to Firebase mapping

class TestMapDataCiteToFirebase:
    """Test suite for map_datacite_to_firebase function."""

    def test_map_complete_record(self, sample_datacite_attributes):
        """Test mapping a complete DataCite record."""
        result = map_datacite_to_firebase(sample_datacite_attributes)

        assert result["datasetIdentifier"] == "https://doi.org/10.0000/test-doi"
        assert "en" in result["title"]
        assert "en" in result["abstract"]
        assert len(result["contacts"]) > 0
        assert result["license"] == "CC-BY-4.0"

    def test_map_with_explicit_doi(self, sample_datacite_attributes):
        """Test that an explicitly passed DOI takes precedence."""
        result = map_datacite_to_firebase(
            sample_datacite_attributes, "https://doi.org/10.9999/other"
        )

        assert result["datasetIdentifier"] == "https://doi.org/10.9999/other"

    def test_map_missing_optional_fields(self):
        """Test mapping with minimal DataCite data."""
        minimal_datacite = {
            "titles": [{"title": "Test Dataset"}],
            "creators": []
        }

        result = map_datacite_to_firebase(minimal_datacite, "10.test/test")

        assert result["datasetIdentifier"] == "https://doi.org/10.test/test"
        assert result["title"]["en"] == "Test Dataset"
        assert result["abstract"] == {"en": ""}
        assert result["contacts"] == []

    def test_map_preserves_multilingual_data(self, sample_datacite_attributes):
        """Test that multilingual data is properly preserved."""
        result = map_datacite_to_firebase(sample_datacite_attributes)

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


class TestMapKeywords:
    """Test suite for _map_keywords function."""

    def test_map_subjects(self):
        """Test mapping DataCite subjects with languages."""
        subjects = [
            {"subject": "marine science", "lang": "en"},
            {"subject": "science marine", "lang": "fr"},
            {"subject": "no language"},
        ]
        result = _map_keywords(subjects)
        assert result["en"] == ["marine science", "no language"]
        assert result["fr"] == ["science marine"]

    def test_map_flat_keyword_list(self):
        """Test that flat string lists are accepted and assumed English."""
        result = _map_keywords(["marine science", "ocean research"])
        assert result == {"en": ["marine science", "ocean research"]}

    def test_empty_keywords(self):
        """Test handling of empty keywords."""
        assert _map_keywords([]) == {}


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
                "nameIdentifiers": [
                    {
                        "nameIdentifier": "https://orcid.org/0000-0001-2345-6789",
                        "nameIdentifierScheme": "ORCID"
                    }
                ],
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

    def test_extract_orcid_from_list(self):
        """Test extracting ORCID from a nameIdentifiers list."""
        name_ids = [
            {"nameIdentifier": "https://isni.org/1234", "nameIdentifierScheme": "ISNI"},
            {
                "nameIdentifier": "https://orcid.org/0000-0001-2345-6789",
                "nameIdentifierScheme": "ORCID"
            }
        ]
        result = _extract_orcid(name_ids)
        assert result == "https://orcid.org/0000-0001-2345-6789"

    def test_extract_orcid_from_empty_list(self):
        """Test handling of an empty nameIdentifiers list."""
        assert _extract_orcid([]) == ""

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
    def test_full_workflow(self, mock_fetch, sample_datacite_attributes):
        """Test complete workflow from DOI to Firebase record."""
        mock_fetch.return_value = sample_datacite_attributes

        result = retrieve_doi_as_firebase_record("10.0000/test-doi")

        assert result["datasetIdentifier"] == "https://doi.org/10.0000/test-doi"
        assert "title" in result
        assert "contacts" in result
        assert "associated_resources" in result


# Test real-world scenario against the Firebase test file structure

class TestFirebaseCompatibility:
    """Tests to ensure compatibility with existing Firebase records."""

    def test_generated_record_matches_firebase_structure(self, sample_datacite_attributes):
        """Test that generated record has expected Firebase structure keys."""
        result = map_datacite_to_firebase(sample_datacite_attributes)

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

    def test_title_structure_matches_firebase(self, sample_datacite_attributes):
        """Test that title structure matches Firebase expectations."""
        result = map_datacite_to_firebase(sample_datacite_attributes)

        assert isinstance(result["title"], dict)
        assert "en" in result["title"] or len(result["title"]) > 0

    def test_contacts_structure_matches_firebase(self, sample_datacite_attributes):
        """Test that contacts structure matches Firebase expectations."""
        result = map_datacite_to_firebase(sample_datacite_attributes)

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

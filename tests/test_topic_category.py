"""Tests for topic category mapping from the firebase schema into ISO XML.

Regression coverage for topic categories defaulting to "oceans" regardless of
the value selected in the metadata entry form (firebase `resourceType` field).
"""

import re

from cioos_metadata_conversion.firebase_to_cioos import (
    normalize_topic_categories,
    record_json_to_yaml,
)
from cioos_metadata_conversion.record import Record

# Minimal firebase record that renders to valid ISO-19115-3 XML.
BASE_RECORD = {
    "map": {"west": "0", "south": "0", "east": "1", "north": "1"},
    "noVerticalExtent": True,
    "contacts": [{"role": ["owner"], "orgName": "Org", "indEmail": "a@b.ca"}],
    "keywords": {"en": ["k"], "fr": ["k"]},
    "title": {"en": "Test", "fr": "Test"},
    "language": "en",
    "identifier": "id-1",
    "datasetIdentifier": "ds-1",
    "abstract": {"en": "a", "fr": "a"},
    "created": "2020-01-01",
    "timeFirstPublished": "2020-01-01T00:00:00",
    "dateStart": "2020-01-01",
    "status": "onGoing",
    "edition": "1",
}


def _record(resource_type=None, **extra):
    record = dict(BASE_RECORD, **extra)
    if resource_type is not None:
        record["resourceType"] = resource_type
    return record


def _topic_codes(record):
    xml = (
        Record(record, schema="firebase")
        .load()
        .convert_to_cioos_schema()
        .convert_to("iso19115-3_xml")
    )
    return re.findall(
        r"<mri:MD_TopicCategoryCode>(.*?)</mri:MD_TopicCategoryCode>", xml
    )


def test_normalize_resource_type_array():
    assert normalize_topic_categories({"resourceType": ["biota", "oceans"]}) == [
        "biota",
        "oceans",
    ]


def test_normalize_legacy_values_to_iso():
    assert normalize_topic_categories(
        {"resourceType": ["oceanographic", "biological"]}
    ) == ["oceans", "biota"]


def test_normalize_falls_back_to_deprecated_category_field():
    assert normalize_topic_categories({"category": "oceanographic"}) == ["oceans"]


def test_normalize_empty_returns_empty_list():
    assert normalize_topic_categories({}) == []
    assert normalize_topic_categories({"resourceType": []}) == []


def test_cioos_schema_includes_topic_category():
    cioos = record_json_to_yaml(_record(["biota", "oceans"]))
    assert cioos["identification"]["topic_category"] == ["biota", "oceans"]


def test_xml_emits_selected_topic_categories():
    assert _topic_codes(_record(["biota", "oceans"])) == ["biota", "oceans"]


def test_xml_normalizes_legacy_topic_category():
    assert _topic_codes(_record(["oceanographic"])) == ["oceans"]


def test_xml_defaults_to_oceans_when_none_selected():
    assert _topic_codes(_record([])) == ["oceans"]

from cioos_metadata_conversion.acdd import acdd
import json
import yaml


def test_acdd_output(record):
    """
    Test the ACDD output generation.
    """
    acdd_output = acdd(record)

    assert acdd_output
    assert isinstance(acdd_output, dict)  # Ensure it's a dict
    assert "title" in acdd_output  # Ensure required field exists
    assert "summary" in acdd_output  # Ensure required field exists
    assert "keywords" in acdd_output  # Ensure required field exists
    assert "keywords_vocabulary" in acdd_output  # Ensure required field exists
    assert "institution" in acdd_output  # Ensure required field exists
    assert "comment" in acdd_output  # Ensure required field exists


def test_acdd_json_output(record):
    """
    Test the ACDD JSON output generation.
    """
    acdd_output = acdd(record, output="json")

    assert acdd_output
    assert isinstance(acdd_output, str)  # Ensure it's a string

    # Validate JSON format
    acdd_json = json.loads(acdd_output)
    assert isinstance(acdd_json, dict)  # Ensure it's a dict
    assert "title" in acdd_json  # Ensure required field exists
    assert "summary" in acdd_json  # Ensure required field exists
    assert "keywords" in acdd_json  # Ensure required field exists


def test_acdd_yaml_output(record):
    """
    Test the ACDD YAML output generation.
    """
    acdd_output = acdd(record, output="yaml")

    assert acdd_output
    assert isinstance(acdd_output, str)  # Ensure it's a string

    # Validate YAML format
    acdd_yaml = yaml.safe_load(acdd_output)
    assert isinstance(acdd_yaml, dict)  # Ensure it's a dict
    assert "title" in acdd_yaml  # Ensure required field exists
    assert "summary" in acdd_yaml  # Ensure required field exists
    assert "keywords" in acdd_yaml  # Ensure required field exists

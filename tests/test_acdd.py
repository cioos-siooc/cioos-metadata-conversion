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


def test_acdd_multilingual_suffix(record):
    """
    Test the ACDD multilingual output generation with suffix method.
    """
    acdd_output = acdd(record, output="json", multilingual="suffix")

    assert acdd_output
    assert isinstance(acdd_output, str)  # Ensure it's a string

    # Validate JSON format
    acdd_json = json.loads(acdd_output)
    assert isinstance(acdd_json, dict)  # Ensure it's a dict
    assert "title_en" in acdd_json  # Ensure English title field exists
    assert "title_fr" in acdd_json  # Ensure French title field exists
    assert "summary_en" in acdd_json  # Ensure English summary field exists
    assert "summary_fr" in acdd_json  # Ensure French summary field exists


def test_acdd_multilingual_nested(record):
    """
    Test the ACDD multilingual output generation with nested method.
    """
    output = acdd(record, multilingual="nested")

    # Validate JSON format
    assert isinstance(output, dict)  # Ensure it's a dict
    assert "title" in output  # Ensure title field exists
    assert "(en)" in output["title"]  # Ensure English title part exists
    assert "(fr)" in output["title"]  # Ensure French title part exists
    assert "summary" in output  # Ensure summary field exists
    assert "(en)" in output["summary"]  # Ensure English summary part exists
    assert "(fr)" in output["summary"]  # Ensure French summary part exists

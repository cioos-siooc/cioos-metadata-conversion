from cioos_metadata_conversion import datacite
from datacite import schema45


def test_dataset_cite(record):
    """
    Test the dataset citation generation.
    """
    datacite_record = datacite.generate_record(record)
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
    assert isinstance(json_output, dict)  # Ensure it's a string
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

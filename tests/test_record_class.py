from cioos_metadata_conversion.record import Record, OUTPUT_FORMATS
import pytest

def test_record_loading_from_file(record_file_yaml, tmp_path):
    """
    Test loading from file.
    """
    record = Record(source=record_file_yaml, schema="CIOOS")
    record.load()
    assert record.metadata
    assert isinstance(record.metadata, dict)


def test_record_conversion_to_cioos_schema(record_file_yaml):
    """
    Test conversion to CIOOS schema.
    """
    record = Record(source=record_file_yaml, schema="CIOOS")
    record = record.load()
    assert record.metadata
    assert isinstance(record.metadata, dict)
    assert record.schema.value == "CIOOS"


@pytest.mark.parametrize("output_format", OUTPUT_FORMATS.keys())
def test_record_conversion_to_output_formats(record_file_yaml, tmp_path, output_format):
    """
    Test conversion to various output formats.
    """
    record = Record(source=record_file_yaml, schema="CIOOS").load()
    output = record.convert_to(output_format)
    assert output
    assert isinstance(output, str) 


@pytest.mark.parametrize("output_format", OUTPUT_FORMATS.keys())
def test_chain_methods(record_file_yaml, output_format):
    """
    Test method chaining for loading and converting.
    """
    record = (
        Record(source=record_file_yaml, schema="CIOOS")
        .load()
        .convert_to_cioos_schema()
        .convert_to(output_format)
    )
    assert record
    assert isinstance(record, str)  # Final output should be a string in JSON format
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

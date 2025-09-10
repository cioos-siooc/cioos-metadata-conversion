from cioos_metadata_conversion import eml


def test_eml_xml(firebase_record):
    result = eml.eml_xml(firebase_record)
    assert result

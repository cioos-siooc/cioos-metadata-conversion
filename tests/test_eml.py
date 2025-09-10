from cioos_metadata_conversion import eml
import difflib



def test_eml_xml(firebase_record):
    result = eml.eml_xml(firebase_record)
    assert result

def test_eml_xml_with_citation(firebase_record):
    result = eml.eml_xml(firebase_record, citation="Test Citation")
    assert result
    assert "Test Citation" in result

def test_eml_xml_with_original_eml(firebase_record):
    """Test EML generation against original EML file."""

    result = eml.eml_xml(firebase_record)

    # Load original EML from the record
    with open("tests/firebase-records/some_english_title__copy__anot_041d7_eml.xml", "r") as f:
        original_eml = f.read()
    
    # Retrieve diff between original and generated EML
    diff = difflib.unified_diff(
        original_eml.splitlines(keepends=True),
        result.splitlines(keepends=True),
        fromfile='original.xml',
        tofile='generated.xml',
    )
    # Save result to tests/results for inspection if needed
    with open("tests/firebase-records/generated_eml.xml", "w") as f:
        f.write(result)
    assert not list(diff), "Generated EML does not match original EML: \n" + "".join(diff)
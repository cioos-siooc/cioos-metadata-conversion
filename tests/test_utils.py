import pytest
from cioos_metadata_conversion.utils import camel_to_title

@pytest.mark.parametrize(
    "inp, expected",
    [
        ("", ""),
        (None, ""),  # gracefully handles None via 'if not s'
        ("surfaceTemperature", "Surface Temperature"),
        ("SurfaceTemperature", "Surface Temperature"),
        ("httpServerError", "Http Server Error"),
        ("sea_surface_temperature", "Sea Surface Temperature"),
        ("sea--surface__TEMP", "Sea Surface TEMP"),
        ("Single", "Single"),
        ("Already Spaced", "Already Spaced"),
        ("version2ID", "Version2 ID"),
        ("gpsLAT", "Gps LAT"),
        ("a", "A"),
        ("A", "A"),
        ("APIResponseOK", "API Response OK"),
    ],
)
def test_camel_to_title_various(inp, expected):
    assert camel_to_title(inp) == expected


def test_acronym_preservation():
    assert camel_to_title("NASADataAPI") == "NASA Data API"


def test_multiple_separators_collapsed():
    assert camel_to_title("multi___part---Value") == "Multi Part Value"


def test_idempotency_on_output():
    # Running twice should not change result
    s = "subSurfaceTemperature"
    assert camel_to_title(camel_to_title(s)) == camel_to_title(s)
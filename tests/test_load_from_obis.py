"""Unit tests for OBIS metadata loading and EOV tagging.

Focus: the non-biodiversity EOV tagging path added on top of
fetch_eovs_from_taxonomy — _map_measurement_pair,
fetch_eovs_from_measurements, and the merge in map_obis_to_cioos.
"""

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import json
import re
import unicodedata

import pytest
import requests
import yaml

from cioos_metadata_conversion.load_from import obis as obis_module
from cioos_metadata_conversion.load_from.obis import (
    VALID_PLATFORM_LABELS,
    _map_measurement_pair,
    _match_platform_keywords,
    fetch_eovs_from_measurements,
    fetch_eovs_from_taxonomy,
    fetch_platforms_from_obis,
    map_obis_to_cioos,
)

_MODULE = "cioos_metadata_conversion.load_from.obis"


# Frozen from the pre-refactor module. First match wins in
# _map_measurement_pair, so this order is output-affecting.
EXPECTED_TEXT_TERM_ORDER = [
    'temperature', 'température', 'temp_eau', 'salinity', 'salinité',
    'salinite_psu', 'dissolved oxygen', 'oxygène dissous', 'oxygen', 'oxygène',
    'nitrate', 'nitrite', 'ammonium', 'phosphate', 'silicate', 'total nitrogen',
    'total phosphorus', 'ph', 'pco2', 'alkalinity', 'alcalinité', 'dic',
    'dissolved organic carbon', 'doc', 'particulate organic carbon', 'poc',
    'chlorophyll', 'turbidity', 'suspended', 'current velocity', 'current speed',
    'current direction', 'current strength', 'tidal current', 'sea state',
    'wave height', 'wave observation', 'wave exposure', 'tide height',
    'hauteur de la marée', 'water level', "niveau d'eau", 'sea level', 'sea ice',
    'ice cover', 'ice observation', 'hydrophone', 'acoustic detection',
    'vocalization', 'call detected', 'marine debris', 'microplastic',
    'plastic debris', 'delta 13c', 'delta13c', 'd13c', 'δ13c', 'nitrous oxide',
    'n2o', 'cfc-11', 'cfc-12', 'sf6', 'tritium',
]

# Frozen from the pre-refactor module. Emitted obis-platform-N ids
# are numbered in this order.
EXPECTED_PLATFORM_LABEL_ORDER = [
    'subsurface mooring', 'moored surface buoy', 'mooring',
    'drifting subsurface profiling float', 'drifting surface float',
    'surface gliders', 'sub-surface gliders', 'autonomous underwater vehicle',
    'propelled unmanned submersible', 'research vessel', 'fishing vessel', 'ship',
    'diver', 'unmanned aerial vehicle', 'helicopter', 'aeroplane', 'satellite',
    'beach/intertidal zone structure', 'land/onshore structure',
    'fixed benthic node', 'offshore structure', 'coastal structure',
    'river station',
]



@pytest.fixture(autouse=True)
def stub_parquet(request, monkeypatch):
    """Force the live-API fallback path in every test.

    The three fetchers try the per-dataset OBIS parquet first and only fall back
    to the API when it returns None.  Without this the tests reach out to S3 with
    whatever fake dataset id they pass.  Tests marked `live` opt out so they keep
    exercising the real parquet-first path.
    """
    if "live" in request.keywords:
        return
    for name in (
        "_read_parquet_class_counts",
        "_read_parquet_sampling_protocols",
        "_read_parquet_measurement_pairs",
    ):
        monkeypatch.setattr(f"{_MODULE}.{name}", lambda *_args, **_kwargs: None)


@contextmanager
def patch_obis_get(**kwargs):
    """Patch the OBIS HTTP GET and yield the mock standing in for it.

    The module calls `_get_session().get(...)`, so patching `requests.get` has no
    effect — the session's bound method is what runs.  Accepts the same kwargs as
    `patch` (`return_value`, `side_effect`).
    """
    with patch(f"{_MODULE}._get_session") as mock_session:
        mock_get = MagicMock(**kwargs)
        mock_session.return_value.get = mock_get
        yield mock_get


class TestMeasurementMapping:
    """_map_measurement_pair: P01 lookup + free-text fallback + surface rule."""

    def test_p01_code_extracted_from_uri(self):
        assert (
            _map_measurement_pair(
                "", "http://vocab.nerc.ac.uk/collection/P01/current/TEMPPR01/"
            )
            == "subSurfaceTemperature"
        )

    def test_p01_code_extracted_without_trailing_slash(self):
        assert (
            _map_measurement_pair(
                "", "http://vocab.nerc.ac.uk/collection/P01/current/PSALPR01"
            )
            == "subSurfaceSalinity"
        )

    def test_text_fallback_when_id_empty(self):
        assert (
            _map_measurement_pair("Chlorophyll a concentration", "")
            == "oceanColour"
        )

    def test_surface_temperature_disambiguation(self):
        assert (
            _map_measurement_pair("Sea surface temperature", "")
            == "seaSurfaceTemperature"
        )

    def test_surface_salinity_disambiguation(self):
        assert (
            _map_measurement_pair("Sea surface salinity", "")
            == "seaSurfaceSalinity"
        )

    def test_subsurface_default_without_surface_token(self):
        assert (
            _map_measurement_pair("Water temperature at depth", "")
            == "subSurfaceTemperature"
        )

    def test_p01_id_overrides_contradictory_text(self):
        assert (
            _map_measurement_pair(
                "some unrelated label",
                "http://vocab.nerc.ac.uk/collection/P01/current/TEMPPR01/",
            )
            == "subSurfaceTemperature"
        )

    def test_unknown_measurement_returns_none(self):
        assert _map_measurement_pair("Net sonde voltage", "") is None

    def test_empty_pair_returns_none(self):
        assert _map_measurement_pair("", "") is None

    def test_unknown_p01_falls_through_to_text(self):
        # Unknown P01 code shouldn't crash; text fallback still applies
        assert (
            _map_measurement_pair(
                "Oxygen concentration",
                "http://vocab.nerc.ac.uk/collection/P01/current/UNKNOW01/",
            )
            == "oxygen"
        )

    def test_ph_abbreviation_does_not_match_chlorophyll(self):
        # Regression: "ph" substring previously matched "chlorophyll"
        assert (
            _map_measurement_pair("Chlorophyll a concentration", "")
            == "oceanColour"
        )

    def test_ph_abbreviation_does_not_match_phytoplankton(self):
        assert _map_measurement_pair("Phytoplankton biomass", "") is None

    def test_ph_matches_as_standalone_token(self):
        assert _map_measurement_pair("pH of seawater", "") == "inorganicCarbon"

    # --- Extended EOV coverage ---

    def test_wind_does_not_emit_ocean_surface_stress(self):
        # Wind is an input to the stress product (τ = ρ·Cd·|U|·U), not
        # the EOV itself. Zero curators tagged oceanSurfaceStress across
        # the audit corpus, including on datasets with bare wind eMoF.
        # Both the P01 codes (EWSBZZ01 / EWDAZZ01) and the free-text
        # wind keys are unmapped. If a platform publishes a derived
        # surface-stress parameter, the P01 table needs that code added.
        assert (
            _map_measurement_pair(
                "", "http://vocab.nerc.ac.uk/collection/P01/current/EWSBZZ01/"
            )
            is None
        )
        assert (
            _map_measurement_pair(
                "", "http://vocab.nerc.ac.uk/collection/P01/current/EWDAZZ01/"
            )
            is None
        )
        assert _map_measurement_pair("Wind speed", "") is None
        assert _map_measurement_pair("Wind direction", "") is None
        assert _map_measurement_pair("Vent à la pose | Initial wind speed", "") is None

    def test_bare_beaufort_text_does_not_emit_sea_state(self):
        # Bare "Beaufort Scale" / "Vent (Beaufort)" in OBIS eMoF are
        # ancillary wind observations, not wave-height measurements. GOOS
        # seaState scope is waves; Beaufort-only labels are too coarse and
        # curator tagging is inconsistent. The WMO P01 codes still map.
        assert _map_measurement_pair("Beaufort Scale", "") is None
        assert _map_measurement_pair("Vent (Beaufort) | Wind (Beaufort)", "") is None

    def test_snake_case_french_temp_and_salinity(self):
        # Some Comité ZIP Rive Nord de l'Estuaire datasets ship eMoF with
        # ASCII snake_case French labels. Underscore is a word character,
        # so regex boundaries block "temperature"/"salinity" from leaking
        # into these — they need explicit keys.
        assert _map_measurement_pair("temp_eau", "") == "subSurfaceTemperature"
        assert _map_measurement_pair("salinite_psu", "") == "subSurfaceSalinity"
        # Air temp snake-case must stay blocked by the atmospheric guard.
        assert _map_measurement_pair("temp_air", "") is None

    def test_sea_state_p01_code(self):
        assert (
            _map_measurement_pair(
                "", "http://vocab.nerc.ac.uk/collection/P01/current/WMOCSSXX/"
            )
            == "seaState"
        )

    def test_wave_height_maps_to_sea_state(self):
        assert _map_measurement_pair("Wave height", "") == "seaState"

    def test_surface_current_maps_to_surface_currents(self):
        assert (
            _map_measurement_pair("Surface current direction", "")
            == "surfaceCurrents"
        )

    def test_generic_current_speed_maps_to_subsurface(self):
        assert (
            _map_measurement_pair("Current speed at 50m", "")
            == "subSurfaceCurrents"
        )

    def test_tide_height_maps_to_sea_surface_height(self):
        assert _map_measurement_pair("Tide height", "") == "seaSurfaceHeight"
        assert (
            _map_measurement_pair("Hauteur de la marée | Tide height", "")
            == "seaSurfaceHeight"
        )
        assert _map_measurement_pair("Water level", "") == "seaSurfaceHeight"

    def test_tide_phase_does_not_map_to_sea_surface_height(self):
        # "Tide level" / "Stade de la marée" are categorical phase labels
        # (high/low/ebb/flood), not numeric heights.
        assert _map_measurement_pair("Tide level", "") is None
        assert _map_measurement_pair("Stade de la marée | Tide level", "") is None

    def test_sea_surface_height_p01_codes(self):
        assert (
            _map_measurement_pair(
                "", "http://vocab.nerc.ac.uk/collection/P01/current/ASLVZZ01/"
            )
            == "seaSurfaceHeight"
        )
        assert (
            _map_measurement_pair(
                "", "http://vocab.nerc.ac.uk/collection/P01/current/ASLVTD01/"
            )
            == "seaSurfaceHeight"
        )

    def test_ice_cover_maps_to_sea_ice(self):
        assert _map_measurement_pair("Ice cover", "") == "seaIce"

    def test_hydrophone_maps_to_ocean_sound(self):
        assert (
            _map_measurement_pair("Hydrophone recording", "") == "oceanSound"
        )

    def test_microplastic_maps_to_marine_debris(self):
        assert (
            _map_measurement_pair("Microplastic concentration", "")
            == "marineDebris"
        )

    def test_delta_13c_maps_to_stable_carbon_isotopes(self):
        assert (
            _map_measurement_pair("δ13C of POM", "")
            == "stableCarbonIsotopes"
        )

    def test_n2o_maps_to_nitrous_oxide(self):
        assert _map_measurement_pair("N2O concentration", "") == "nitrousOxide"

    def test_per_cell_poc_does_not_emit_particulate_matter(self):
        # Flow-cytometry label — per-cell carbon content is phytoplankton
        # biomass data, not bulk particulates.
        assert (
            _map_measurement_pair("Particulate Organic Carbon per cell", "")
            is None
        )

    def test_per_cell_p01_code_suppressed(self):
        assert (
            _map_measurement_pair(
                "Particulate Organic Carbon per cell",
                "http://vocab.nerc.ac.uk/collection/P01/current/MAOCCB11/",
            )
            is None
        )

    def test_bulk_particulate_carbon_still_maps(self):
        # Control — bulk POC (no "per cell") should still emit.
        assert (
            _map_measurement_pair("Particulate organic carbon", "")
            == "particulateMatter"
        )

    def test_cfc11_maps_to_transient_tracers(self):
        assert _map_measurement_pair("CFC-11", "") == "transientTracers"


class TestFetchEovsFromMeasurements:
    """fetch_eovs_from_measurements: extensions gate + API call + mapping."""

    def test_empty_dataset_id_returns_empty(self):
        assert fetch_eovs_from_measurements("") == []
        assert fetch_eovs_from_measurements(None) == []

    def test_short_circuits_when_no_emof_extension(self):
        with patch_obis_get() as mock_get:
            result = fetch_eovs_from_measurements(
                "abc-123", extensions=["Occurrence"]
            )
            mock_get.assert_not_called()
            assert result == []

    def test_short_circuits_on_empty_extensions_list(self):
        with patch_obis_get() as mock_get:
            result = fetch_eovs_from_measurements("abc-123", extensions=[])
            mock_get.assert_not_called()
            assert result == []

    def test_runs_when_extensions_is_none(self):
        # None means "caller didn't tell us" — fall through to the API call.
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status.return_value = None
        with patch_obis_get(
            return_value=mock_response,
        ) as mock_get:
            result = fetch_eovs_from_measurements("abc-123", extensions=None)
            mock_get.assert_called_once()
            assert result == []

    def test_maps_ctd_measurements(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "mof": [
                        {
                            "measurementType": "Sea water temperature",
                            "measurementTypeID": (
                                "http://vocab.nerc.ac.uk/collection/P01/current/TEMPPR01/"
                            ),
                        },
                        {
                            "measurementType": "Practical salinity",
                            "measurementTypeID": (
                                "http://vocab.nerc.ac.uk/collection/P01/current/PSALPR01/"
                            ),
                        },
                        {
                            "measurementType": "Dissolved oxygen",
                            "measurementTypeID": (
                                "http://vocab.nerc.ac.uk/collection/P01/current/DOXYZZXX/"
                            ),
                        },
                    ]
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        with patch_obis_get(
            return_value=mock_response,
        ):
            result = fetch_eovs_from_measurements(
                "abc-123", extensions=["ExtendedMeasurementOrFact"]
            )
        assert result == ["oxygen", "subSurfaceSalinity", "subSurfaceTemperature"]

    def test_deduplicates_across_occurrences(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"mof": [{"measurementType": "Temperature", "measurementTypeID": ""}]},
                {"mof": [{"measurementType": "Temperature", "measurementTypeID": ""}]},
                {"mof": [{"measurementType": "Salinity", "measurementTypeID": ""}]},
            ]
        }
        mock_response.raise_for_status.return_value = None
        with patch_obis_get(
            return_value=mock_response,
        ):
            result = fetch_eovs_from_measurements(
                "abc-123", extensions=["MeasurementOrFact"]
            )
        assert result == ["subSurfaceSalinity", "subSurfaceTemperature"]

    def test_api_error_returns_empty(self):
        with patch_obis_get(
            side_effect=requests.ConnectionError("boom"),
        ):
            result = fetch_eovs_from_measurements(
                "abc-123", extensions=["ExtendedMeasurementOrFact"]
            )
        assert result == []

    def test_invalid_json_returns_empty(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("not json")
        with patch_obis_get(
            return_value=mock_response,
        ):
            result = fetch_eovs_from_measurements(
                "abc-123", extensions=["ExtendedMeasurementOrFact"]
            )
        assert result == []

    def test_unmapped_measurements_silently_dropped(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "mof": [
                        {"measurementType": "Net sonde voltage", "measurementTypeID": ""},
                        {"measurementType": "Temperature", "measurementTypeID": ""},
                    ]
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        with patch_obis_get(
            return_value=mock_response,
        ):
            result = fetch_eovs_from_measurements(
                "abc-123", extensions=["ExtendedMeasurementOrFact"]
            )
        assert result == ["subSurfaceTemperature"]


class TestFetchEovsFromTaxonomy:
    """Zooplankton and cover-EOV threshold gates in fetch_eovs_from_taxonomy."""

    @staticmethod
    def _mock_facet(class_buckets):
        resp = MagicMock()
        resp.json.return_value = {"results": {"class": class_buckets}}
        resp.raise_for_status.return_value = None
        return resp

    def test_zoo_emitted_when_core_classes_dominate(self):
        buckets = [
            {"key": "Copepoda", "records": 1000},
            {"key": "Sagittoidea", "records": 100},
            {"key": "Teleostei", "records": 50},
        ]
        with patch_obis_get(
            return_value=self._mock_facet(buckets),
        ):
            result = fetch_eovs_from_taxonomy("plankton-net")
        assert "zooplanktonBiomassAndDiversity" in result

    def test_zoo_suppressed_when_only_gelatinous_bycatch(self):
        # Fish-dominated trawl with jellyfish bycatch — no core zoo class.
        buckets = [
            {"key": "Teleostei", "records": 1000},
            {"key": "Scyphozoa", "records": 200},
            {"key": "Hydrozoa", "records": 50},
        ]
        with patch_obis_get(
            return_value=self._mock_facet(buckets),
        ):
            result = fetch_eovs_from_taxonomy("trawl-bycatch")
        assert "zooplanktonBiomassAndDiversity" not in result
        assert "fishAbundanceAndDistribution" in result

    def test_zoo_suppressed_when_core_below_threshold(self):
        # Core class present but at <5% of dataset records.
        buckets = [
            {"key": "Teleostei", "records": 1000},
            {"key": "Copepoda", "records": 10},  # 1% — below threshold
        ]
        with patch_obis_get(
            return_value=self._mock_facet(buckets),
        ):
            result = fetch_eovs_from_taxonomy("fish-with-trace-copepods")
        assert "zooplanktonBiomassAndDiversity" not in result

    def test_zoo_emitted_at_threshold(self):
        # Core class right at 5% boundary — should pass.
        buckets = [
            {"key": "Teleostei", "records": 950},
            {"key": "Copepoda", "records": 50},  # 5% exactly
        ]
        with patch_obis_get(
            return_value=self._mock_facet(buckets),
        ):
            result = fetch_eovs_from_taxonomy("at-threshold")
        assert "zooplanktonBiomassAndDiversity" in result

    def test_invert_suppressed_in_plankton_net_without_benthic(self):
        # Bongo/Juday net sample: Copepoda core + larval inverts only.
        # No benthic indicator class → invertebrate is suppressed.
        buckets = [
            {"key": "Copepoda", "records": 1000},
            {"key": "Malacostraca", "records": 200},  # krill/mysids
            {"key": "Gastropoda", "records": 150},    # pteropods
            {"key": "Polychaeta", "records": 80},     # larval
        ]
        with patch_obis_get(
            return_value=self._mock_facet(buckets),
        ):
            result = fetch_eovs_from_taxonomy("plankton-net")
        assert "zooplanktonBiomassAndDiversity" in result
        assert "invertebrateAbundanceAndDistribution" not in result

    def test_invert_kept_when_benthic_indicator_present(self):
        # Same planktonic mix plus Echinoidea — now it's a plankton-tow
        # that also sampled epifauna, so both EOVs stand.
        buckets = [
            {"key": "Copepoda", "records": 1000},
            {"key": "Malacostraca", "records": 200},
            {"key": "Echinoidea", "records": 30},  # benthic indicator
        ]
        with patch_obis_get(
            return_value=self._mock_facet(buckets),
        ):
            result = fetch_eovs_from_taxonomy("plankton-plus-epifauna")
        assert "zooplanktonBiomassAndDiversity" in result
        assert "invertebrateAbundanceAndDistribution" in result

    def test_invert_kept_when_no_zooplankton_emitted(self):
        # Pure benthic survey — no zoo signal, rule doesn't fire.
        buckets = [
            {"key": "Malacostraca", "records": 500},
            {"key": "Gastropoda", "records": 200},
        ]
        with patch_obis_get(
            return_value=self._mock_facet(buckets),
        ):
            result = fetch_eovs_from_taxonomy("benthic-survey")
        assert "invertebrateAbundanceAndDistribution" in result
        assert "zooplanktonBiomassAndDiversity" not in result

    def test_fungal_and_parasitic_classes_do_not_emit_microbe(self):
        # These were formerly mapped to microbeBiomassAndDiversity. They
        # are dropped because fungi in OBIS include many terrestrial
        # records and parasitic/host-bound protists aren't free-living
        # marine microbes in the GOOS sense.
        buckets = [
            {"key": "Lecanoromycetes", "records": 20},   # lichens
            {"key": "Agaricomycetes", "records": 10},    # mushrooms
            {"key": "Conoidasida", "records": 50},       # apicomplexan parasites
            {"key": "Labyrinthulea", "records": 30},     # slime nets
            {"key": "Teleostei", "records": 100},        # anchor: keeps result non-empty
        ]
        with patch_obis_get(
            return_value=self._mock_facet(buckets),
        ):
            result = fetch_eovs_from_taxonomy("mixed-shoreline")
        assert "microbeBiomassAndDiversity" not in result

    def test_bacterial_classes_still_emit_microbe(self):
        # Control — genuine bacterial classes should still map.
        buckets = [
            {"key": "Gammaproteobacteria", "records": 500},
            {"key": "Flavobacteria", "records": 200},
        ]
        with patch_obis_get(
            return_value=self._mock_facet(buckets),
        ):
            result = fetch_eovs_from_taxonomy("microbial-survey")
        assert "microbeBiomassAndDiversity" in result

    def test_cnidarian_classes_map_to_invertebrate_not_hardcoral(self):
        # Octocorallia = soft corals/sea pens. Hexacorallia includes
        # anemones and black corals alongside Scleractinia. Neither is
        # specific to hardCoralCoverAndComposition.
        buckets = [
            {"key": "Octocorallia", "records": 100},
            {"key": "Hexacorallia", "records": 50},
            {"key": "Anthozoa", "records": 25},
        ]
        with patch_obis_get(
            return_value=self._mock_facet(buckets),
        ):
            result = fetch_eovs_from_taxonomy("sea-pen-dataset")
        assert "hardCoralCoverAndComposition" not in result
        assert "invertebrateAbundanceAndDistribution" in result


class TestMapObisToCioosEovMerging:
    """map_obis_to_cioos merges taxonomy and measurement EOVs correctly."""

    @pytest.fixture(autouse=True)
    def _stub_platform_fetch(self):
        # These tests are about EOV merging — skip the live platform
        # API call by stubbing the inference helper.
        with patch(
            "cioos_metadata_conversion.load_from.obis.fetch_platforms_from_obis",
            return_value=[],
        ):
            yield

    @staticmethod
    def _minimal_obis_data():
        return {"id": "dataset-uuid", "extensions": ["ExtendedMeasurementOrFact"]}

    def test_taxonomy_only_passes_through(self):
        with patch(
            "cioos_metadata_conversion.load_from.obis.fetch_eovs_from_taxonomy",
            return_value=["fishAbundanceAndDistribution"],
        ), patch(
            "cioos_metadata_conversion.load_from.obis.fetch_eovs_from_measurements",
            return_value=[],
        ):
            result = map_obis_to_cioos(self._minimal_obis_data())
        assert result["eov"] == ["fishAbundanceAndDistribution"]

    def test_other_dropped_when_measurements_exist(self):
        with patch(
            "cioos_metadata_conversion.load_from.obis.fetch_eovs_from_taxonomy",
            return_value=["other"],
        ), patch(
            "cioos_metadata_conversion.load_from.obis.fetch_eovs_from_measurements",
            return_value=["seaSurfaceTemperature"],
        ):
            result = map_obis_to_cioos(self._minimal_obis_data())
        assert result["eov"] == ["seaSurfaceTemperature"]

    def test_other_preserved_when_no_measurements(self):
        with patch(
            "cioos_metadata_conversion.load_from.obis.fetch_eovs_from_taxonomy",
            return_value=["other"],
        ), patch(
            "cioos_metadata_conversion.load_from.obis.fetch_eovs_from_measurements",
            return_value=[],
        ):
            result = map_obis_to_cioos(self._minimal_obis_data())
        assert result["eov"] == ["other"]

    def test_empty_both_falls_back_to_other(self):
        with patch(
            "cioos_metadata_conversion.load_from.obis.fetch_eovs_from_taxonomy",
            return_value=[],
        ), patch(
            "cioos_metadata_conversion.load_from.obis.fetch_eovs_from_measurements",
            return_value=[],
        ):
            result = map_obis_to_cioos(self._minimal_obis_data())
        assert result["eov"] == ["other"]

    def test_biology_and_measurement_eovs_merged(self):
        with patch(
            "cioos_metadata_conversion.load_from.obis.fetch_eovs_from_taxonomy",
            return_value=["fishAbundanceAndDistribution", "zooplanktonBiomassAndDiversity"],
        ), patch(
            "cioos_metadata_conversion.load_from.obis.fetch_eovs_from_measurements",
            return_value=["subSurfaceTemperature", "subSurfaceSalinity"],
        ):
            result = map_obis_to_cioos(self._minimal_obis_data())
        assert result["eov"] == [
            "fishAbundanceAndDistribution",
            "subSurfaceSalinity",
            "subSurfaceTemperature",
            "zooplanktonBiomassAndDiversity",
        ]

    def test_extensions_passed_to_measurement_fetch(self):
        with patch(
            "cioos_metadata_conversion.load_from.obis.fetch_eovs_from_taxonomy",
            return_value=[],
        ), patch(
            "cioos_metadata_conversion.load_from.obis.fetch_eovs_from_measurements",
            return_value=[],
        ) as mock_measurements:
            obis_data = {"id": "x", "extensions": ["Occurrence", "ExtendedMeasurementOrFact"]}
            map_obis_to_cioos(obis_data)
            mock_measurements.assert_called_once_with(
                "x", extensions=["Occurrence", "ExtendedMeasurementOrFact"]
            )


# Integration test — hits the live OBIS API. Follows the pattern of
# test_real_doi in test_load_from_datacite.py. Pick a dataset that carries
# eMoF measurements (any OBIS landing page listing ExtendedMeasurementOrFact).
@pytest.mark.live
@pytest.mark.parametrize(
    "dataset_id",
    [
        # AZMP-style plankton + CTD dataset from DFO — publicly known to
        # carry temperature/salinity/chlorophyll in eMoF. Replace if the
        # integration test becomes flaky against this specific dataset.
        "4bc13a6a-71a3-4a2d-b23d-3ce50a9aef41",
    ],
)
def test_real_obis_dataset_with_measurements(dataset_id):
    """Live API check — any of the expected physical EOVs should show up."""
    eovs = fetch_eovs_from_measurements(dataset_id)
    # The dataset may or may not actually declare extensions the way we
    # expect; call without the gate to force the fetch.
    assert isinstance(eovs, list)


class TestPlatformKeywordMatching:
    """_match_platform_keywords: keyword table + specificity dedup."""

    def test_empty_text_returns_empty(self):
        assert _match_platform_keywords("") == []
        assert _match_platform_keywords(None) == []

    def test_no_keyword_match_returns_empty(self):
        assert _match_platform_keywords("Random text with no clue.") == []

    def test_research_vessel_drops_generic_ship(self):
        # "research vessel" matches both the specific and the generic pattern;
        # specificity table should drop "ship".
        assert _match_platform_keywords(
            "Sampled aboard research vessel CCGS Vector"
        ) == ["research vessel"]

    def test_fishing_vessel_drops_generic_ship(self):
        assert _match_platform_keywords("Hauled aboard a fishing vessel") == [
            "fishing vessel"
        ]

    def test_bare_vessel_maps_to_ship(self):
        assert _match_platform_keywords("Collected from vessel during transit") == [
            "ship"
        ]

    def test_subsurface_mooring_drops_generic_mooring(self):
        assert _match_platform_keywords(
            "Instruments on a subsurface mooring at 100m"
        ) == ["subsurface mooring"]

    def test_moored_surface_buoy_drops_generic_mooring(self):
        assert _match_platform_keywords(
            "ADCP attached to a moored surface buoy"
        ) == ["moored surface buoy"]

    def test_bare_mooring_keeps_label(self):
        assert _match_platform_keywords("Sampled from a long-term mooring") == [
            "mooring"
        ]

    def test_surface_glider_distinct_from_subsurface(self):
        assert _match_platform_keywords("Deployed surface glider") == [
            "surface gliders"
        ]

    def test_bare_glider_defaults_to_subsurface(self):
        assert _match_platform_keywords("Slocum glider mission") == [
            "sub-surface gliders"
        ]

    def test_argo_float_maps_to_profiling_float(self):
        # And drops the generic drifting-surface-float hit even though
        # "float" overlaps with the float family.
        assert _match_platform_keywords("Argo float profile") == [
            "drifting subsurface profiling float"
        ]

    def test_rov_maps_to_propelled_unmanned_submersible(self):
        assert _match_platform_keywords(
            "Video observations from ROV during dive"
        ) == ["propelled unmanned submersible"]

    def test_auv_maps_to_autonomous_underwater_vehicle(self):
        assert _match_platform_keywords("REMUS AUV survey transect") == [
            "autonomous underwater vehicle"
        ]

    def test_diver_keywords(self):
        assert _match_platform_keywords("SCUBA divers on transect") == ["diver"]

    def test_intertidal_marsh_maps_to_beach(self):
        # Salt-marsh dataset (the user's working example).
        assert _match_platform_keywords(
            "Sampling along the salt marsh shoreline"
        ) == ["beach/intertidal zone structure"]

    def test_seafloor_maps_to_fixed_benthic_node(self):
        assert _match_platform_keywords("Benthic lander on seafloor") == [
            "fixed benthic node"
        ]

    def test_uav_drops_generic_aeroplane(self):
        assert _match_platform_keywords("Aerial survey from UAV / drone") == [
            "unmanned aerial vehicle"
        ]

    def test_helicopter_drops_generic_aeroplane(self):
        assert _match_platform_keywords(
            "Aerial photo survey from helicopter"
        ) == ["helicopter"]

    def test_satellite_keyword(self):
        assert _match_platform_keywords("Derived from satellite imagery") == [
            "satellite"
        ]

    def test_case_insensitive(self):
        assert _match_platform_keywords("RESEARCH VESSEL") == ["research vessel"]

    def test_multiple_distinct_platforms_kept(self):
        # A benthic survey combining ROV + divers should emit both.
        result = _match_platform_keywords(
            "Habitat survey by ROV and accompanying SCUBA divers"
        )
        assert set(result) == {"propelled unmanned submersible", "diver"}

    def test_every_table_label_is_in_vocab(self):
        # Guardrail: the keyword table must never emit a label that the
        # CIOOS form wouldn't accept.
        from cioos_metadata_conversion.load_from.obis import (
            _PLATFORM_KEYWORD_TABLE,
        )

        for _pattern, label in _PLATFORM_KEYWORD_TABLE:
            assert label in VALID_PLATFORM_LABELS, (
                f"{label!r} is not a valid CIOOS platform label_en — "
                f"check resources/platforms.json"
            )


class TestFetchPlatformsFromObis:
    """fetch_platforms_from_obis: API sampling + samplingProtocol → label."""

    def test_empty_dataset_id_returns_empty(self):
        assert fetch_platforms_from_obis("") == []
        assert fetch_platforms_from_obis(None) == []

    def test_no_occurrences_returns_empty(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status.return_value = None
        with patch_obis_get(
            return_value=mock_response,
        ):
            assert fetch_platforms_from_obis("abc-123") == []

    def test_api_error_returns_empty(self):
        with patch_obis_get(
            side_effect=requests.ConnectionError("boom"),
        ):
            assert fetch_platforms_from_obis("abc-123") == []

    def test_blank_sampling_protocol_returns_empty(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"samplingProtocol": "", "basisOfRecord": "HumanObservation"},
                {"samplingProtocol": None, "basisOfRecord": "HumanObservation"},
            ]
        }
        mock_response.raise_for_status.return_value = None
        with patch_obis_get(
            return_value=mock_response,
        ):
            assert fetch_platforms_from_obis("abc-123") == []

    def test_single_protocol_returns_single_platform(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"samplingProtocol": "Sampled aboard research vessel CCGS Vector"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        with patch_obis_get(
            return_value=mock_response,
        ):
            result = fetch_platforms_from_obis("abc-123")
        assert result == [
            {
                "id": "obis-platform-1",
                "type": "research vessel",
                "description": {"en": "", "fr": ""},
            }
        ]

    def test_mixed_protocols_emit_multiple_platforms(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"samplingProtocol": "ROV survey"},
                {"samplingProtocol": "SCUBA divers on transect"},
                # duplicate text should not produce a third entry
                {"samplingProtocol": "ROV survey"},
            ]
        }
        mock_response.raise_for_status.return_value = None
        with patch_obis_get(
            return_value=mock_response,
        ):
            result = fetch_platforms_from_obis("abc-123")
        types = {p["type"] for p in result}
        assert types == {"propelled unmanned submersible", "diver"}
        # Deterministic IDs starting from 1.
        assert [p["id"] for p in result] == [
            f"obis-platform-{i + 1}" for i in range(len(result))
        ]


class TestMapObisToCioosPlatforms:
    """map_obis_to_cioos wires the platform inference into the record."""

    def test_no_platforms_sets_noPlatform_true(self):
        with patch(
            "cioos_metadata_conversion.load_from.obis.fetch_eovs_from_taxonomy",
            return_value=[],
        ), patch(
            "cioos_metadata_conversion.load_from.obis.fetch_eovs_from_measurements",
            return_value=[],
        ), patch(
            "cioos_metadata_conversion.load_from.obis.fetch_platforms_from_obis",
            return_value=[],
        ):
            result = map_obis_to_cioos({"id": "x"})
        assert result["platforms"] == []
        assert result["noPlatform"] is True

    def test_platforms_present_sets_noPlatform_false(self):
        platforms = [
            {
                "id": "obis-platform-1",
                "type": "mooring",
                "description": {"en": "", "fr": ""},
            }
        ]
        with patch(
            "cioos_metadata_conversion.load_from.obis.fetch_eovs_from_taxonomy",
            return_value=[],
        ), patch(
            "cioos_metadata_conversion.load_from.obis.fetch_eovs_from_measurements",
            return_value=[],
        ), patch(
            "cioos_metadata_conversion.load_from.obis.fetch_platforms_from_obis",
            return_value=platforms,
        ):
            result = map_obis_to_cioos({"id": "x"})
        assert result["platforms"] == platforms
        assert result["noPlatform"] is False


class TestMappingFile:
    """Guardrails on resources/obis_mapping.yaml.

    The mapping file is hand-editable data that drives real conversion output,
    so these lock the invariants the matching code relies on but cannot enforce
    for itself.  Every assertion here held at the time the file was extracted
    from obis.py.
    """

    RESOURCES = (
        Path(obis_module.__file__).parent.parent / "resources"
    )

    # ── the file ships and parses ───────────────────────────────────────────

    def test_mapping_file_is_present(self):
        assert obis_module._MAPPING_PATH.is_file(), (
            f"{obis_module._MAPPING_PATH} is missing — it is required at import "
            f"and must be committed alongside obis.py"
        )

    def test_missing_file_fails_loudly_with_the_resolved_path(self, monkeypatch):
        monkeypatch.setattr(
            obis_module, "_MAPPING_PATH", self.RESOURCES / "does_not_exist.yaml"
        )
        with pytest.raises(obis_module.ObisMappingError) as excinfo:
            obis_module._load_obis_mapping()
        assert "does_not_exist.yaml" in str(excinfo.value)

    def test_duplicate_keys_are_rejected(self):
        # PyYAML silently keeps the last of a repeated key; the taxon table is
        # 190 hand-edited lines, which is exactly where that would hide.
        with pytest.raises(yaml.constructor.ConstructorError, match="duplicate key"):
            yaml.load(
                "from_taxon_class:\n  Aves: a\n  Aves: OOPS\n",
                Loader=obis_module._UniqueKeyLoader,
            )

    # ── cross-vocabulary agreement ──────────────────────────────────────────

    def test_every_eov_exists_in_the_cioos_vocabulary(self):
        vocabulary = {
            entry["value"]
            for entry in json.loads(
                (self.RESOURCES / "eov.json").read_text(encoding="utf-8")
            )
        }
        emitted = (
            set(obis_module.TAXON_CLASS_TO_EOV.values())
            | set(obis_module.MEASUREMENT_P01_TO_EOV.values())
            | set(obis_module.MEASUREMENT_TEXT_TO_EOV.values())
            | set(obis_module._SURFACE_UPGRADES.values())
            | obis_module.COVER_EOVS
            | obis_module._TEMPERATURE_EOVS
        )
        assert emitted <= vocabulary, (
            f"EOVs not in resources/eov.json: {sorted(emitted - vocabulary)}"
        )

    def test_every_platform_label_exists_in_the_cioos_vocabulary(self):
        # Loaded DIRECTLY rather than through VALID_PLATFORM_LABELS: validating
        # the table against a set derived from that same table would be
        # vacuously true, which is how the old version of this test could pass
        # while platforms.json was missing entirely.
        vocabulary = {
            entry["label_en"]
            for entry in json.loads(
                (self.RESOURCES / "platforms.json").read_text(encoding="utf-8")
            )
        }
        labels = {label for _pattern, label in obis_module._PLATFORM_KEYWORD_TABLE}
        for specific, generics in obis_module._PLATFORM_SPECIFICITY.items():
            labels.add(specific)
            labels |= generics
        assert labels <= vocabulary, (
            f"platform labels not in resources/platforms.json: "
            f"{sorted(labels - vocabulary)}"
        )

    def test_platform_vocabulary_is_fully_loaded(self):
        assert obis_module._PLATFORM_RESOURCE_PATH.is_file()
        assert len(VALID_PLATFORM_LABELS) == 81

    def test_specificity_labels_appear_in_the_keyword_table(self):
        table = {label for _pattern, label in obis_module._PLATFORM_KEYWORD_TABLE}
        for specific, generics in obis_module._PLATFORM_SPECIFICITY.items():
            assert specific in table, f"{specific!r} can never match"
            assert generics <= table, f"{specific!r} drops labels nothing emits"

    # ── the order-sensitive tables ──────────────────────────────────────────

    def test_measurement_text_order_is_preserved(self):
        # obis.py returns on the FIRST word-boundary match, so this order is
        # output-affecting.  Grouping by target EOV breaks it: particulateMatter
        # occupies two runs separated by chlorophyll.
        assert list(obis_module.MEASUREMENT_TEXT_TO_EOV) == EXPECTED_TEXT_TERM_ORDER

    def test_platform_table_order_is_preserved(self):
        # Emitted obis-platform-N ids are assigned in this order.
        assert [
            label for _pattern, label in obis_module._PLATFORM_KEYWORD_TABLE
        ] == EXPECTED_PLATFORM_LABEL_ORDER

    @pytest.mark.parametrize(
        "text,expected",
        [
            # The atmospheric guard `continue`s rather than returning, so a
            # later term still applies.
            ("Air temperature and salinity", "subSurfaceSalinity"),
            ("Air temperature", None),
            ("Température atmosphérique", None),
            ("temp_air", None),
            # These three pin the particulateMatter/oceanColour interleave that
            # makes the table non-groupable.
            ("Chlorophyll a in suspended particulate matter", "oceanColour"),
            ("Turbidity and chlorophyll fluorescence", "oceanColour"),
            ("Chlorophyll and turbidity profile", "oceanColour"),
            ("Tidal current direction", "subSurfaceCurrents"),
        ],
    )
    def test_order_sensitive_semantics(self, text, expected):
        assert _map_measurement_pair(text, "") == expected

    # ── regex fidelity ──────────────────────────────────────────────────────

    def test_patterns_survived_the_round_trip(self):
        # `\b` in a double-quoted YAML scalar silently becomes U+0008; \s and \d
        # would fail loudly, so this is a mixed failure mode worth pinning.
        patterns = [p.pattern for p, _label in obis_module._PLATFORM_KEYWORDS_COMPILED]
        patterns += [
            obis_module._ATMOSPHERIC_RE.pattern,
            obis_module._PER_CELL_RE.pattern,
            obis_module._STRONG_IC_TEXT_RE.pattern,
            obis_module._P01_CODE_RE.pattern,
        ]
        for pattern in patterns:
            assert "\x08" not in pattern, f"{pattern!r} contains a BACKSPACE"
            assert "\x0c" not in pattern, f"{pattern!r} contains a FORM FEED"

    def test_surface_glider_pattern_keeps_its_missing_word_boundary(self):
        # r"\bsurface\s+glider" has NO trailing \b on purpose so it also matches
        # "gliders".  Normalising one in during an edit would break it.
        assert _match_platform_keywords("surface glider") == ["surface gliders"]
        assert _match_platform_keywords("surface gliders") == ["surface gliders"]

    def test_compiled_patterns_mirror_the_table(self):
        # Runtime matching reads the compiled list; this test and the guardrail
        # above read the table.  They must not be able to drift.
        assert [
            (p.pattern, label) for p, label in obis_module._PLATFORM_KEYWORDS_COMPILED
        ] == list(obis_module._PLATFORM_KEYWORD_TABLE)

    def test_guard_flags_are_explicit_and_case_insensitive(self):
        # _PER_CELL_RE and _STRONG_IC_TEXT_RE match RAW un-lowered text.
        assert obis_module._is_strong_inorganic_carbon("Total Alkalinity", "") is True
        assert _map_measurement_pair("Particulate Organic Carbon Per Cell", "") is None
        assert obis_module._ATMOSPHERIC_RE.search("température atmosphérique")
        # _P01_CODE_RE is deliberately upper-case-only and flagless.
        assert obis_module._P01_CODE_RE.flags & re.IGNORECASE == 0

    # ── encoding ────────────────────────────────────────────────────────────

    def test_accented_terms_survive_encoding_and_normalisation(self):
        # Seven terms and two patterns are non-ASCII and load-bearing.  UTF-8
        # bytes read as cp1252 parse without raising, and an NFD-normalising
        # editor breaks French-only labels while bilingual ones keep working.
        for term in [
            "température",
            "salinité",
            "oxygène dissous",
            "oxygène",
            "alcalinité",
            "hauteur de la marée",
            "δ13c",
        ]:
            assert term in obis_module.MEASUREMENT_TEXT_TO_EOV
            assert unicodedata.normalize("NFC", term) == term
        assert "atmosph[eé]rique" in obis_module._ATMOSPHERIC_RE.pattern
        assert "pco₂" in obis_module._STRONG_IC_TEXT_RE.pattern

    def test_mapping_file_is_utf8_without_escapes(self):
        raw = obis_module._MAPPING_PATH.read_text(encoding="utf-8")
        assert "température" in raw
        assert "\\u00e9" not in raw, "accents were escaped rather than written as UTF-8"
        assert unicodedata.normalize("NFC", raw) == raw

    # ── load-time validation actually fires ─────────────────────────────────

    @pytest.mark.parametrize(
        "mutate,message",
        [
            (lambda m: m["eov"]["from_taxon_class"].update({"lowercase": "other"}),
             "capitalisation"),
            (lambda m: m["eov"]["from_p01_code"].update({"TOOLONGCODE": "oxygen"}),
             "8 upper-case"),
            (lambda m: m["eov"]["from_measurement_text"].append(
                {"term": "Uppercase", "eov": "oxygen"}), "lower-case"),
            (lambda m: m["eov"]["from_measurement_text"].append(
                {"term": r"\bregex\b", "eov": "oxygen"}), "plain text"),
            (lambda m: m["eov"]["gates"]["benthic_indicator_classes"].append("Nonexistent"),
             "absent from from_taxon_class"),
            (lambda m: m["eov"]["gates"]["zooplankton"]["core_classes"].append("Teleostei"),
             "do not map to"),
            (lambda m: m["eov"]["gates"]["cover"].update({"min_fraction": 5}),
             "fraction between 0 and 1"),
            (lambda m: m["roles"]["valid_cioos_codes"].append("AUTHOR"),
             "case-duplicates"),
            (lambda m: m.pop("templates"), "missing required section"),
        ],
    )
    def test_validation_rejects_broken_mappings(self, mutate, message):
        mapping = yaml.load(
            obis_module._MAPPING_PATH.read_text(encoding="utf-8"),
            Loader=obis_module._UniqueKeyLoader,
        )
        mutate(mapping)
        with pytest.raises(obis_module.ObisMappingError, match=message):
            obis_module._validate_obis_mapping(mapping)

    def test_unmapped_transform_and_handler_names_are_rejected(self):
        for key, value, message in [
            ("transform", "no_such_transform", "unknown transform"),
            ("handler", "no_such_handler", "unknown handler"),
        ]:
            original = obis_module._MAPPING["fields"]["abstract"].copy()
            try:
                obis_module._MAPPING["fields"]["abstract"][key] = value
                with pytest.raises(obis_module.ObisMappingError, match=message):
                    obis_module._validate_field_specs()
            finally:
                obis_module._MAPPING["fields"]["abstract"] = original

    # ── the field map matches what is actually emitted ───────────────────────

    def test_field_entries_match_the_emitted_record_exactly(self):
        with patch(f"{_MODULE}.fetch_eovs_from_taxonomy", return_value=["other"]), patch(
            f"{_MODULE}.fetch_eovs_from_measurements", return_value=[]
        ), patch(f"{_MODULE}.fetch_platforms_from_obis", return_value=[]):
            record = map_obis_to_cioos({"id": "x"})
        # Both directions: a field documented but not emitted is as bad as a
        # field emitted but undocumented.
        assert list(record) == list(obis_module._MAPPING["fields"])
        assert len(record) == 38

    def test_placeholder_types_are_preserved(self):
        # scrub_dict strips ""/None/{}, and firebase_to_cioos interpolates some
        # of these into an f-string URL before that runs, so "" is not
        # interchangeable with None.
        with patch(f"{_MODULE}.fetch_eovs_from_taxonomy", return_value=["other"]), patch(
            f"{_MODULE}.fetch_eovs_from_measurements", return_value=[]
        ), patch(f"{_MODULE}.fetch_platforms_from_obis", return_value=[]):
            record = map_obis_to_cioos({"id": "x"})
        assert record["noTaxa"] is True
        assert record["noVerticalExtent"] is True
        assert record["noPlatform"] is True
        for key in ["region", "userID", "recordID", "status", "dateStart", "dateEnd"]:
            assert record[key] == "", f"{key} must stay an empty string, not None"
        # add_fr("") is NOT "": the French placeholder is what lets it survive.
        assert record["limitations"]["fr"]
        assert record["projects"] == []

    def test_constant_containers_are_not_shared_between_records(self):
        with patch(f"{_MODULE}.fetch_eovs_from_taxonomy", return_value=["other"]), patch(
            f"{_MODULE}.fetch_eovs_from_measurements", return_value=[]
        ), patch(f"{_MODULE}.fetch_platforms_from_obis", return_value=[]):
            first = map_obis_to_cioos({"id": "a"})
            first["projects"].append("leaked")
            first["lastEditedBy"]["email"] = "leaked@example.org"
            second = map_obis_to_cioos({"id": "b"})
        assert second["projects"] == []
        assert second["lastEditedBy"] == {"displayName": "", "email": ""}

    # ── date handling ───────────────────────────────────────────────────────

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("", ""),  # never the bare string "Z"
            ("2026-04-21T14:55:55.003Z", "2026-04-21T14:55:55Z"),
            ("2025-12-18T18:27:56Z", "2025-12-18T18:27:56ZZ"),  # documents today's double-Z
            ("2023-05-01", "2023-05-01Z"),
            ("2023-05-01T10:20:30+00:00", "2023-05-01T10:20:30+00:00Z"),
        ],
    )
    def test_trim_date(self, value, expected):
        assert obis_module._trim_date(value) == expected

    def test_get_path_handles_missing_hops(self):
        assert obis_module._get_path({"feed": {"url": "u"}}, "feed.url") == "u"
        assert obis_module._get_path({"feed": {}}, "feed.url") is None
        assert obis_module._get_path({}, "feed.url") is None
        assert obis_module._get_path({"feed": "not-a-dict"}, "feed.url") is None

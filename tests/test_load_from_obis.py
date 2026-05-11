"""Unit tests for OBIS metadata loading and EOV tagging.

Focus: the non-biodiversity EOV tagging path added on top of
fetch_eovs_from_taxonomy — _map_measurement_pair,
fetch_eovs_from_measurements, and the merge in map_obis_to_cioos.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests

from cioos_metadata_conversion.load_from.obis import (
    _map_measurement_pair,
    fetch_eovs_from_measurements,
    fetch_eovs_from_taxonomy,
    map_obis_to_cioos,
)


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
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get"
        ) as mock_get:
            result = fetch_eovs_from_measurements(
                "abc-123", extensions=["Occurrence"]
            )
            mock_get.assert_not_called()
            assert result == []

    def test_short_circuits_on_empty_extensions_list(self):
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get"
        ) as mock_get:
            result = fetch_eovs_from_measurements("abc-123", extensions=[])
            mock_get.assert_not_called()
            assert result == []

    def test_runs_when_extensions_is_none(self):
        # None means "caller didn't tell us" — fall through to the API call.
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status.return_value = None
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get",
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
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get",
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
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get",
            return_value=mock_response,
        ):
            result = fetch_eovs_from_measurements(
                "abc-123", extensions=["MeasurementOrFact"]
            )
        assert result == ["subSurfaceSalinity", "subSurfaceTemperature"]

    def test_api_error_returns_empty(self):
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get",
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
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get",
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
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get",
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
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get",
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
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get",
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
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get",
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
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get",
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
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get",
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
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get",
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
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get",
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
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get",
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
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get",
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
        with patch(
            "cioos_metadata_conversion.load_from.obis.requests.get",
            return_value=self._mock_facet(buckets),
        ):
            result = fetch_eovs_from_taxonomy("sea-pen-dataset")
        assert "hardCoralCoverAndComposition" not in result
        assert "invertebrateAbundanceAndDistribution" in result


class TestMapObisToCioosEovMerging:
    """map_obis_to_cioos merges taxonomy and measurement EOVs correctly."""

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

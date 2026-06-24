"""Error-path coverage (SU-4b) for siege_utilities.geo.census_data_selector.

Exercises the ``except ValueError`` guard in select_datasets_for_analysis,
which converts an invalid geography-level string into an error result instead
of letting the GeographyLevel(...) conversion raise.
"""

from siege_utilities.geo.census_data_selector import CensusDataSelector


def test_select_datasets_returns_error_on_invalid_geography_level():
    sel = CensusDataSelector()
    result = sel.select_datasets_for_analysis("demographics", "not_a_level")
    assert "error" in result
    assert "Invalid geography level" in result["error"]

"""Error-path coverage (SU-4b) for siege_utilities.geo.census.dataset_selector.

Forces the ValueError guards in DatasetSelector across get_dataset_path,
validate_geography, and build_geography_clause.
"""

import pytest

from siege_utilities.geo.census.dataset_selector import DatasetSelector


def test_get_dataset_path_rejects_unknown_dataset():
    with pytest.raises(ValueError) as exc_info:
        DatasetSelector.get_dataset_path(2020, "not_a_dataset")
    assert "Unknown dataset" in str(exc_info.value)


def test_validate_geography_rejects_invalid_geography():
    with pytest.raises(ValueError) as exc_info:
        DatasetSelector.validate_geography("not_a_geo", None, None)
    assert "Invalid geography" in str(exc_info.value)


def test_validate_geography_requires_state_for_tract():
    with pytest.raises(ValueError) as exc_info:
        DatasetSelector.validate_geography("tract", None, None)
    assert "State FIPS code is required" in str(exc_info.value)


def test_validate_geography_county_requires_state():
    with pytest.raises(ValueError) as exc_info:
        DatasetSelector.validate_geography("county", None, "001")
    assert "County FIPS requires state FIPS" in str(exc_info.value)


def test_build_geography_clause_requires_state_for_tract():
    with pytest.raises(ValueError) as exc_info:
        DatasetSelector.build_geography_clause("tract", None, None)
    assert "state_fips is required for tract" in str(exc_info.value)


def test_build_geography_clause_requires_state_for_block_group():
    with pytest.raises(ValueError) as exc_info:
        DatasetSelector.build_geography_clause("block_group", None, None)
    assert "state_fips is required for block_group" in str(exc_info.value)


def test_build_geography_clause_rejects_unsupported_geography():
    with pytest.raises(ValueError) as exc_info:
        DatasetSelector.build_geography_clause("galaxy", None, None)
    assert "Unsupported geography" in str(exc_info.value)

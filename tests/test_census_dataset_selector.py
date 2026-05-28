"""Error-path tests for siege_utilities.geo.census.dataset_selector (SU-4b)."""

import pytest

try:
    from siege_utilities.geo.census.dataset_selector import DatasetSelector
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="pandas or census deps missing")


class TestGetDatasetPathErrors:
    """Error paths for DatasetSelector.get_dataset_path."""

    def test_unknown_dataset_raises(self):
        """Unknown dataset identifier must raise ValueError."""
        with pytest.raises(ValueError, match="Unknown dataset"):
            DatasetSelector.get_dataset_path(2020, "nonexistent")

    def test_empty_dataset_raises(self):
        """Empty dataset string must raise ValueError."""
        with pytest.raises(ValueError, match="Unknown dataset"):
            DatasetSelector.get_dataset_path(2020, "")


class TestValidateGeographyErrors:
    """Error paths for DatasetSelector.validate_geography."""

    def test_invalid_geography_raises(self):
        """Invalid geography level must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid geography"):
            DatasetSelector.validate_geography("galaxy_cluster", None, None)


class TestGetDatasetPathHappyPath:
    """Sanity checks for get_dataset_path."""

    def test_acs5_returns_correct_path(self):
        """ACS 5-year returns correct API path."""
        result = DatasetSelector.get_dataset_path(2020, "acs5")
        assert result == "2020/acs/acs5"

    def test_decennial_returns_correct_path(self):
        """Decennial returns correct API path."""
        result = DatasetSelector.get_dataset_path(2020, "dec")
        assert result == "2020/dec/pl"

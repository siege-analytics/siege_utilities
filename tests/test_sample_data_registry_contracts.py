"""Root-import contracts for the sample-data registry.

Covers list_available_datasets and load_sample_data: the working synthetic
datasets, the unknown-name error path, and the current census-sample gap
(tracked in issue #1313) so a behavior change there is flagged.
"""

import pytest

from siege_utilities import list_available_datasets
from siege_utilities import load_sample_data

_SYNTHETIC = {
    "synthetic_population": 1000,
    "synthetic_businesses": 500,
    "synthetic_housing": 300,
}
_CENSUS = [
    "census_tract_sample",
    "census_county_sample",
    "metropolitan_sample",
]


class TestListAvailableDatasets:
    def test_returns_documented_catalog(self):
        catalog = list_available_datasets()
        assert isinstance(catalog, dict)
        expected = set(_SYNTHETIC) | set(_CENSUS)
        assert expected <= set(catalog)
        # Every entry carries a human-readable description.
        for name in expected:
            assert catalog[name].get("description")


class TestLoadSampleData:
    @pytest.mark.parametrize("name, rows", list(_SYNTHETIC.items()))
    def test_synthetic_datasets_load_with_default_size(self, name, rows):
        pytest.importorskip(
            "faker", reason="Faker is required to generate synthetic datasets"
        )
        df = load_sample_data(name)
        assert df.shape[0] == rows

    def test_unknown_dataset_raises_value_error(self):
        with pytest.raises(ValueError) as excinfo:
            load_sample_data("no_such_dataset_xyz")
        assert "no_such_dataset_xyz" in str(excinfo.value)

    @pytest.mark.parametrize("name", _CENSUS)
    def test_census_datasets_are_currently_unavailable(self, name):
        # Registry advertises these but they are not loadable today, in either
        # of two capability shapes (tracked in issue #1313):
        #   - ImportError when the census/geo extras are absent
        #     (CENSUS_AVAILABLE/GEOPANDAS_AVAILABLE false), raised before any
        #     data call;
        #   - NotImplementedError when those extras are importable but the
        #     underlying get_census_data() remains a stub.
        # Accept both so the contract is portable across core/no-GDAL and
        # full-extras environments; if census loading is implemented, update.
        with pytest.raises((ImportError, NotImplementedError)):
            load_sample_data(name)

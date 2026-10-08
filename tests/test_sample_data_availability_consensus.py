"""The census sample datasets are declared but not implemented.

Consensus findings C9 + C10 (#1360): the reference.sample_data registry
advertised three census_* datasets as peers of the working synthetic
ones with no availability flag, while the functions behind them chain to
get_census_data, which raises NotImplementedError. These tests pin the
availability flag (C10) and the honest, loud failure at the load entry
point (C9).
"""
import pytest

from siege_utilities.reference import sample_data as sd

CENSUS = ["census_tract_sample", "census_county_sample", "metropolitan_sample"]
SYNTHETIC = ["synthetic_population", "synthetic_businesses", "synthetic_housing"]


def test_registry_flags_census_datasets_unavailable():
    listing = sd.list_available_datasets()
    for name in CENSUS:
        assert listing[name]["available"] is False, f"{name} should be flagged unavailable"
    for name in SYNTHETIC:
        assert listing[name]["available"] is True, f"{name} should be flagged available"


@pytest.mark.parametrize("name", CENSUS)
def test_load_sample_data_raises_for_declared_but_unimplemented(name):
    with pytest.raises(NotImplementedError, match="#1360"):
        sd.load_sample_data(name)


def test_get_census_data_does_not_return_silently():
    """The root dead function must raise, never return a frame or None."""
    with pytest.raises((NotImplementedError, ImportError)):
        sd.get_census_data()


def test_unknown_dataset_still_raises_valueerror():
    with pytest.raises(ValueError, match="Unknown dataset"):
        sd.load_sample_data("not_a_real_dataset")

"""The data.world connector is removed (upstream product discontinued).

C15/C16 (#1358) were originally "fix the data.world wrappers," but the
upstream open-source datadotworld product was discontinued, so the
connector is removed outright rather than repaired. These tests pin the
removal so a stale re-registration cannot creep back.
"""
import importlib.util

import siege_utilities
import siege_utilities.analytics as analytics


def test_datadotworld_module_is_gone():
    assert (
        importlib.util.find_spec("siege_utilities.analytics.datadotworld_connector")
        is None
    )


def test_datadotworld_symbols_not_exported():
    for name in (
        "get_datadotworld_connector",
        "DataDotWorldConnector",
        "search_datadotworld_datasets",
        "load_datadotworld_dataset",
        "query_datadotworld_dataset",
    ):
        assert not hasattr(analytics, name), f"{name} should be removed from analytics"
        assert not hasattr(siege_utilities, name), f"{name} should be removed from top level"

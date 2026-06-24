"""Error-path coverage (SU-4b) for geo.django.services.crosswalk_service.

populate() wraps the crosswalk load in a (OSError, ValueError, TypeError,
ImportError, RuntimeError) handler, but populate() runs inside
@transaction.atomic and therefore needs a live database (unavailable in the
unit-test environment / the CI ``test`` job, which has no Postgres service).

This test instead forces the load failure that the handler is designed to
catch: with the underlying get_crosswalk patched to raise, _load_crosswalk_data
must propagate the error (so populate's handler has something to catch). It is
DB-free and fail-on-revert.
"""
import pytest

import siege_utilities.geo.crosswalk as crosswalk_pkg
from siege_utilities.geo.django.services.crosswalk_service import (
    CrosswalkPopulationService,
)


def test_load_crosswalk_data_propagates_source_failure(monkeypatch):
    def boom(**kwargs):
        raise ValueError("crosswalk source unavailable")

    monkeypatch.setattr(crosswalk_pkg, "get_crosswalk", boom)
    svc = CrosswalkPopulationService()
    with pytest.raises(ValueError) as exc_info:
        svc._load_crosswalk_data("tract", 2010, 2020)
    assert "crosswalk source unavailable" in str(exc_info.value)

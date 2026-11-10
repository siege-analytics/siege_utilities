"""Reviewer pre-check for #1550. In-memory ORM stand-in; GDAL/GEOS required."""
import contextlib
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from django.core.exceptions import ImproperlyConfigured

try:
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.gis.geos import GEOSGeometry  # noqa: F401
    from siege_utilities.geo.django.models import DemographicSnapshot
    from siege_utilities.geo.django.services.demographic_service import DemographicPopulationService
except (ImportError, ImproperlyConfigured, OSError, RuntimeError):
    pytest.skip("GeoDjango (GDAL/GEOS) required", allow_module_level=True)

pytestmark = pytest.mark.requires_gdal

CT = ContentType(id=1, app_label="siege_geo", model="tract")
TRACT = "06001400100"


class _QS(list):
    def first(self):
        return self[0] if self else None

    def exists(self):
        return bool(self)

    def count(self):  # QuerySet.count(), not list.count(x)
        return len(self)

    def filter(self, **kw):
        return _QS(o for o in self if all(getattr(o, k) == v for k, v in kw.items()))


class _Table:
    """Rows persist across populate() calls, like a real table."""

    def __init__(self):
        self.rows = []

    def filter(self, **kw):
        return _QS(self.rows).filter(**kw)

    def bulk_create(self, objs, **kw):
        self.rows.extend(o for o in objs if o not in self.rows)
        return list(objs)

    def bulk_update(self, objs, fields, **kw):  # like Django: no save(), no derivation
        return len(objs)


@contextlib.contextmanager
def _env():
    table = _Table()

    def save_base(self, *a, **kw):  # Model.save() reaches here after save() derivations
        if self not in table.rows:
            table.rows.append(self)

    with patch("django.db.transaction.Atomic.__enter__", lambda self: None), patch(
        "django.db.transaction.Atomic.__exit__", lambda self, *a: False
    ), patch.object(DemographicSnapshot, "objects", table), patch.object(
        DemographicSnapshot, "save_base", save_base
    ), patch.object(DemographicPopulationService, "_get_content_type", return_value=CT):
        yield table


def _load(svc, df, group, **kw):
    svc._client = MagicMock(fetch_data=MagicMock(return_value=df))
    return svc.populate("tract", 2022, "06", variable_group=group, **kw)


def test_second_variable_group_merges_into_existing_snapshot():
    svc = DemographicPopulationService(api_key="dummy")
    with _env() as table:
        _load(svc, pd.DataFrame({"GEOID": [TRACT], "NAME": ["Tract 4001"],
                                 "B01001_001E": ["3000"]}), "total_population")
        second = _load(svc, pd.DataFrame({"GEOID": [TRACT], "NAME": ["Tract 4001"],
                                          "B19013_001E": ["85000"]}), "income")
    [snap] = table.rows
    assert {"B01001_001E", "B19013_001E"} <= set(snap.values), snap.values
    assert second.records_skipped == 0


def test_name_column_is_not_stored_as_a_variable():
    svc = DemographicPopulationService(api_key="dummy")
    with _env() as table:
        _load(svc, pd.DataFrame({"GEOID": [TRACT], "NAME": ["Census Tract 4001; Alameda"],
                                 "B01001_001E": ["3000"]}), "total_population")
    [snap] = table.rows
    assert "NAME" not in snap.values


def test_census_sentinel_never_reaches_median_household_income():
    svc = DemographicPopulationService(api_key="dummy")
    with _env() as table:
        _load(svc, pd.DataFrame({"GEOID": [TRACT], "B01001_001E": ["0"]}), "total_population")
        _load(svc, pd.DataFrame({"GEOID": [TRACT], "B19013_001E": ["-666666666"]}),
              "income", update_existing=True)
    [snap] = table.rows
    # PositiveIntegerField + CHECK >= 0: a negative value is an IntegrityError in PostGIS
    assert snap.median_household_income is None

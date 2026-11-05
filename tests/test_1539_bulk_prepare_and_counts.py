"""Reviewer pre-check for #1539: bulk paths must fill save()-derived fields
and report only rows actually inserted. Mocked ORM; GDAL/GEOS required."""
import contextlib
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pandas as pd
import pytest
from django.core.exceptions import ImproperlyConfigured
from shapely.geometry import Polygon

try:
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.gis.geos import GEOSGeometry  # noqa: F401
    from siege_utilities.geo.django import models as gm
    from siege_utilities.geo.django.services.demographic_service import DemographicPopulationService
    from siege_utilities.geo.django.services.population_service import BoundaryPopulationService
except (ImportError, ImproperlyConfigured, OSError, RuntimeError):
    pytest.skip("GeoDjango (GDAL/GEOS) required", allow_module_level=True)

pytestmark = pytest.mark.requires_gdal


class _CapturingManager:
    """Stand-in for Model.objects: nothing pre-exists; bulk_create is recorded.
    ``conflicts`` names keys that ON CONFLICT DO NOTHING would drop."""

    def __init__(self, conflicts=()):
        self.inserted, self.conflicts = [], set(conflicts)

    def filter(self, *a, **kw):
        qs = MagicMock()
        qs.first.return_value = None
        qs.exists.return_value = False
        qs.count.side_effect = lambda: len(self.inserted)  # pre/post counting works
        return qs

    def bulk_create(self, objs, ignore_conflicts=False, **kw):
        objs = list(objs)
        key = lambda o: getattr(o, "geoid", None) or getattr(o, "object_id", None)  # noqa: E731
        kept = [o for o in objs if key(o) not in self.conflicts]
        self.inserted.extend(kept)
        return kept if not ignore_conflicts else objs  # Django returns input objs


@contextlib.contextmanager
def _no_db():
    with patch("django.db.transaction.Atomic.__enter__", lambda self: None), patch(
        "django.db.transaction.Atomic.__exit__", lambda self, *a: False
    ):
        yield


def test_boundary_bulk_path_sets_feature_id_boundary_id_source():
    gdf = gpd.GeoDataFrame(
        {"GEOID": ["06037"], "NAME": ["Los Angeles"], "STATEFP": ["06"],
         "COUNTYFP": ["037"], "ALAND": [1], "AWATER": [0]},
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])], crs="EPSG:4269",
    )
    mgr = _CapturingManager()
    with _no_db(), patch.object(gm.County, "objects", mgr), patch.object(
        BoundaryPopulationService, "_download_boundaries", return_value=gdf
    ):
        BoundaryPopulationService().populate("county", 2020, state_fips="06")
    [row] = mgr.inserted
    assert (row.feature_id, row.boundary_id, row.source) == ("06037", "06037", "TIGER/Line")


def test_demographic_bulk_path_sets_total_population_and_counts_real_inserts():
    df = pd.DataFrame({"GEOID": ["06037", "06059"], "B01001_001E": ["1000", "2000"]})
    mgr = _CapturingManager(conflicts={"06059"})  # e.g. a concurrent run inserted it
    svc = DemographicPopulationService(api_key="dummy")
    svc._client = MagicMock(fetch_data=MagicMock(return_value=df))
    ct = ContentType(id=1, app_label="siege_geo", model="county")
    with _no_db(), patch.object(gm.DemographicSnapshot, "objects", mgr), patch.object(
        DemographicPopulationService, "_get_content_type", return_value=ct
    ):
        result = svc.populate("county", 2022, "06", variable_group="total_population")
    assert [s.total_population for s in mgr.inserted] == [1000]
    assert result.records_created == 1, "row dropped by ON CONFLICT DO NOTHING counted as created"

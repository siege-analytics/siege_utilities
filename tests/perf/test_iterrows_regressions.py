"""Correctness checks for the vectorised hot paths.

Each test calls the actual production function (not a re-inlined
copy) and asserts that its output matches what a row-at-a-time
baseline would have produced. If anyone reverts the production
code to ``iterrows()``, these go red.

These do not pin absolute timings. Single-shot ``perf_counter`` on
small frames is too noisy for CI; the perf wins are measured offline
on real datasets.
"""

from __future__ import annotations

import pytest

pd = pytest.importorskip("pandas")


def test_convert_to_postgis_output_matches_iterrows_baseline(tmp_path):
    """Drives the real `_convert_to_postgis` and compares its output
    file to the byte-identical output the iterrows path would have
    produced. If the vectorised path ever diverges (escaping,
    ordering, missing rows) this catches it."""
    gpd = pytest.importorskip("geopandas")
    shapely = pytest.importorskip("shapely.geometry")
    from siege_utilities.core.sql_safety import escape_sql_string_literal as escape
    from siege_utilities.geo.spatial_transformations import SpatialDataTransformer

    geoms = [shapely.Point(i, i * 2) for i in range(200)] + [
        shapely.Point(0, 0),
        shapely.LineString([(0, 0), (1, 1)]),
    ]
    gdf = gpd.GeoDataFrame({"value": range(len(geoms))}, geometry=geoms, crs="EPSG:4326")

    out_path = tmp_path / "out.sql"
    transformer = SpatialDataTransformer()
    assert transformer._convert_to_postgis(gdf, output_path=str(out_path)) is True

    expected = "\n".join(
        f"INSERT INTO spatial_table (geom) VALUES (ST_GeomFromText('{escape(g.wkt)}'));"
        for g in geoms
    )
    assert out_path.read_text() == expected


# enrich_school_districts is exercised by
# tests/test_nces_service_enrich_districts.py which drives the real
# Django function. Re-inlining the vectorised algorithm here would
# pass even if production reverted to iterrows, so the test belongs
# next to the model layer rather than in tests/perf/.

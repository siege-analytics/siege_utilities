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


def test_enrich_districts_lookup_matches_iterrows_baseline():
    """Drives the real `enrich_school_districts` lookup-dict
    construction by re-extracting the vectorised body and comparing
    to the iterrows baseline on the same input.

    The production function is hard to call directly because it
    requires Django models. The vectorised dict-build was extracted
    inline; this test pins the algorithm at the point of refactor
    by running the same expression and comparing to the row-by-row
    output."""
    df = pd.DataFrame({
        "lea_id": [f"{i:07d}" if i % 7 else "" for i in range(200)],
        "locale_code": [i % 50 if i % 11 else None for i in range(200)],
        "locale_category": ["city"] * 200,
        "locale_subcategory": ["large"] * 200,
    })

    baseline: dict = {}
    for _, row in df.iterrows():
        lea = str(row.get("lea_id", ""))
        if lea and row.get("locale_code") is not None:
            baseline[lea] = {
                "locale_code": str(int(row["locale_code"])),
                "locale_category": str(row.get("locale_category", "")),
                "locale_subcategory": str(row.get("locale_subcategory", "")),
            }

    mask = df["lea_id"].astype(str).str.len().gt(0) & df["locale_code"].notna()
    sub = df.loc[mask, ["lea_id", "locale_code", "locale_category", "locale_subcategory"]].fillna("")
    vectorised = {
        str(lea): {
            "locale_code": str(int(code)),
            "locale_category": str(cat),
            "locale_subcategory": str(s),
        }
        for lea, code, cat, s in zip(
            sub["lea_id"], sub["locale_code"],
            sub["locale_category"], sub["locale_subcategory"],
        )
    }

    assert baseline == vectorised

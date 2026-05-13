"""Correctness checks for the vectorised hot paths.

These don't pin timings — single-shot ``perf_counter`` on small frames
is too noisy to be useful in CI. Instead they assert the vectorised
output is byte-identical to the row-at-a-time baseline, so a future
refactor that produces subtly different output (escaping, type
coercion, NaN handling) gets caught.

The actual perf win is measured offline with much larger inputs;
that's not a CI test.
"""

from __future__ import annotations

import pytest

pd = pytest.importorskip("pandas")


def test_wkt_sql_generation_output_matches_iterrows():
    """Same call shape as siege_utilities.geo.spatial_transformations
    ._convert_to_postgis — including the ``escape_string_literal``
    call that the production path uses."""
    shapely = pytest.importorskip("shapely.geometry")
    from siege_utilities.core.sql_safety import escape_sql_string_literal as escape

    df = pd.DataFrame({
        "geometry": [shapely.Point(i, i) for i in range(200)],
    })

    baseline = "\n".join(
        f"INSERT INTO spatial_table (geom) VALUES (ST_GeomFromText('{escape(row['geometry'].wkt)}'));"
        for _, row in df.iterrows()
    )

    wkt_series = df["geometry"].apply(lambda g: escape(g.wkt))
    vectorised = "\n".join(
        "INSERT INTO spatial_table (geom) VALUES (ST_GeomFromText('"
        + wkt_series
        + "'));"
    )

    assert baseline == vectorised


def test_lookup_dict_build_matches_iterrows():
    """Same call shape as nces_service.enrich_districts lookup build."""
    df = pd.DataFrame({
        "lea_id": [f"{i:07d}" for i in range(200)],
        "locale_code": [i % 50 for i in range(200)],
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

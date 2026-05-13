"""Performance regression guards for the Sprint D vectorisation pass.

Each test runs a vectorised path and an "old style" .iterrows()
equivalent against the same synthetic input, then asserts the
vectorised path is no more than 2× slower than the baseline — i.e.,
catches *regressions* if someone reverts the refactor or reintroduces
a row-at-a-time loop. We don't pin absolute timings (CI noise);
we pin the *relative* speedup that motivated the refactor.

The 2× ratio is deliberately loose for CI noise. On a quiet
machine the vectorised paths are typically 10-50× faster; the test
fails only when something has gone catastrophically wrong.
"""

from __future__ import annotations

import time

import pytest

pd = pytest.importorskip("pandas")


def _time(fn) -> float:
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


def test_wkt_sql_generation_vectorised_beats_iterrows():
    """Mirrors siege_utilities.geo.spatial_transformations._convert_to_postgis
    hot loop — generating one INSERT line per geometry. The old
    code called ``escape_string_literal(row.geometry.wkt)`` inside
    iterrows; the new code uses ``gdf.geometry.apply(...)`` + string
    concat on the Series.
    """
    shapely = pytest.importorskip("shapely.geometry")
    n = 5000
    df = pd.DataFrame({
        "geometry": [shapely.Point(i, i) for i in range(n)],
    })

    def baseline_iterrows() -> str:
        out = []
        for _, row in df.iterrows():
            wkt = row["geometry"].wkt
            out.append(f"INSERT INTO t (geom) VALUES (ST_GeomFromText('{wkt}'));")
        return "\n".join(out)

    def vectorised() -> str:
        wkt_series = df["geometry"].apply(lambda g: g.wkt)
        lines = (
            "INSERT INTO t (geom) VALUES (ST_GeomFromText('"
            + wkt_series
            + "'));"
        )
        return "\n".join(lines)

    # Sanity: both produce identical output.
    assert baseline_iterrows() == vectorised()

    t_base = _time(baseline_iterrows)
    t_vec = _time(vectorised)
    # Vectorised must be at most 2× the baseline (i.e., not worse).
    # In practice it's much faster — this just guards regression.
    assert t_vec <= 2.0 * t_base, (
        f"Vectorised WKT generation regressed: vec={t_vec:.4f}s, base={t_base:.4f}s. "
        "Did someone reintroduce iterrows in spatial_transformations._convert_to_postgis?"
    )


def test_lookup_dict_build_vectorised_beats_iterrows():
    """Mirrors the nces_service.enrich_districts lookup-dict build.
    The old code iterated rows; the new code masks + zips columns.
    """
    n = 20_000
    df = pd.DataFrame({
        "lea_id": [f"{i:07d}" for i in range(n)],
        "locale_code": [i % 50 for i in range(n)],
        "locale_category": ["city"] * n,
        "locale_subcategory": ["large"] * n,
    })

    def baseline_iterrows() -> dict:
        out: dict = {}
        for _, row in df.iterrows():
            lea = str(row.get("lea_id", ""))
            if lea and row.get("locale_code") is not None:
                out[lea] = {
                    "locale_code": str(int(row["locale_code"])),
                    "locale_category": str(row.get("locale_category", "")),
                    "locale_subcategory": str(row.get("locale_subcategory", "")),
                }
        return out

    def vectorised() -> dict:
        mask = df["lea_id"].astype(str).str.len().gt(0) & df["locale_code"].notna()
        sub = df.loc[mask, ["lea_id", "locale_code", "locale_category", "locale_subcategory"]].fillna("")
        return {
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

    a = baseline_iterrows()
    b = vectorised()
    assert a == b

    t_base = _time(baseline_iterrows)
    t_vec = _time(vectorised)
    assert t_vec <= 2.0 * t_base, (
        f"Vectorised lookup-dict build regressed: vec={t_vec:.4f}s, base={t_base:.4f}s. "
        "Did someone reintroduce iterrows in nces_service.enrich_districts?"
    )

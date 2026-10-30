"""R-1852 with a mixed pair: one GeoDataFrame input and one attrs-based frame.

One side carries its CRS on a live GeoSeries, the other only in the
siege_geometry_crs attrs map. The rule must apply identically; where both exist
the GeoSeries wins.
"""
import pytest

from siege_utilities.engines.dataframe_engine import DuckDBEngine


@pytest.fixture
def e():
    engine = DuckDBEngine()
    yield engine
    engine._connection.close()


def _frame(e, crs, name="geometry", as_gdf=False):
    cast = "" if crs is None else f"::GEOMETRY('EPSG:{crs}')"
    out = e.query(f"SELECT 7 AS pid, ST_Point(1, 1){cast} AS {name}")
    return e.to_geodataframe(out, name) if as_gdf else out


@pytest.mark.parametrize("gdf_side", ["left", "right"])
@pytest.mark.parametrize("how", ["inner", "left", "right", "outer"])
def test_mixed_known_conflict_rejected_all_modes(e, how, gdf_side):
    left = _frame(e, 4326, as_gdf=(gdf_side == "left"))
    right = _frame(e, 3857, as_gdf=(gdf_side == "right"))
    with pytest.raises(ValueError, match="conflicting geometry CRS"):
        e.join(left, right, on="geometry", how=how)


def test_mixed_outer_known_vs_attrs_none_rejected(e):
    # GeoDataFrame known CRS on one side, attrs-based unknown on the other.
    with pytest.raises(ValueError, match="outer join"):
        e.join(_frame(e, 4326, as_gdf=True), _frame(e, None), on="geometry", how="outer")


def test_mixed_right_join_geoseries_crs_wins_over_attrs_none_end_to_end(e):
    # left is attrs-based with unknown CRS; right is a GeoDataFrame known 3857.
    # Immutable bytes avoid the pre-existing composite/raw-WKB hashability
    # limit so the merge is observable end to end.
    left = _frame(e, None)
    left["geometry"] = left["geometry"].map(bytes)
    right = _frame(e, 3857, as_gdf=True)
    out = e.to_geodataframe(e.join(left, right, on="geometry", how="right"))
    assert len(out) == 1 and out.crs is not None and out.crs.to_epsg() == 3857


def test_mixed_resolver_selects_right_geoseries_crs(e):
    resolved = DuckDBEngine._resolve_geometry_key_crs(
        _frame(e, None), _frame(e, 3857, as_gdf=True), "geometry", "right"
    )
    from siege_utilities.geo.crs import _normalize_crs

    assert _normalize_crs(resolved["geometry"]) == "EPSG:3857"

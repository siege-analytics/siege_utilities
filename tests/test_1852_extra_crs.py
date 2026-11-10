"""Independent coalesced-key checks with actual public engine outputs."""
import pytest

pytest.importorskip("duckdb")

from siege_utilities.engines.dataframe_engine import DuckDBEngine

@pytest.fixture
def e():
    e=DuckDBEngine()
    yield e
    e._connection.close()

def require_typed_geometry():
    import duckdb
    if tuple(map(int, duckdb.__version__.split(".")[:2])) < (1, 5):
        pytest.skip("requires duckdb>=1.5 for CRS-qualified geometry types; install siege-utilities[performance]")

def to_gdf(e,df,name='geometry'):
    # Only the GeoDataFrame conversions need GeoPandas; raw-WKB cases still run.
    pytest.importorskip("geopandas")
    return e.to_geodataframe(df,name)

def frame(e,crs,name='geometry',as_gdf=False):
    if crs is not None:
        require_typed_geometry()
    cast='' if crs is None else f"::GEOMETRY('EPSG:{crs}')"
    out=e.query(f'SELECT 7 AS pid, ST_Point(1,1){cast} AS {name}')
    return to_gdf(e,out,name) if as_gdf else out

@pytest.mark.parametrize('how',['inner','left','right','outer'])
def test_known_conflicts_rejected_after_public_conversion(e,how):
    left=frame(e,4326,as_gdf=True);right=frame(e,3857,as_gdf=True)
    with pytest.raises(ValueError,match='conflicting geometry CRS'):
        e.join(left,right,on='geometry',how=how)

def test_right_key_crs_after_public_conversion(e):
    left=frame(e,None,as_gdf=True);right=frame(e,3857,as_gdf=True)
    out=to_gdf(e,e.join(left,right,on='geometry',how='right'))
    assert out.crs is not None and out.crs.to_epsg()==3857

def test_outer_known_none_rejected_after_public_conversion(e):
    with pytest.raises(ValueError,match='outer join'):
        e.join(frame(e,4326,as_gdf=True),frame(e,None,as_gdf=True),on='geometry',how='outer')

def test_raw_composite_wkb_right_join_keeps_right_crs(e):
    # #1864: pandas cannot hash mutable bytearray WKB keys. Only that exact
    # cause is an expected failure; any other TypeError fails the test, and
    # once #1864 is fixed the correct right-join result is asserted.
    try:
        joined=e.join(frame(e,None),frame(e,3857),on=['pid','geometry'],how='right')
    except TypeError as exc:
        if "unhashable type: 'bytearray'" not in str(exc):
            raise
        pytest.xfail("#1864: pandas cannot hash bytearray WKB join keys")
    out=to_gdf(e,joined)
    assert len(out)==1 and out.crs.to_epsg()==3857

@pytest.mark.parametrize('name',['geometry','geometry_x'])
def test_immutable_wkb_composite_right_source_end_to_end(e,name):
    left=frame(e,None,name);right=frame(e,3857,name)
    left[name]=left[name].map(bytes);right[name]=right[name].map(bytes)
    out=to_gdf(e,e.join(left,right,on=['pid',name],how='right'),name)
    assert len(out)==1 and out.crs.to_epsg()==3857

"""Independent coalesced-key checks with actual public engine outputs."""
import pytest
from siege_utilities.engines.dataframe_engine import DuckDBEngine

@pytest.fixture
def e():
    e=DuckDBEngine()
    yield e
    e._connection.close()

def frame(e,crs,name='geometry',as_gdf=False):
    cast='' if crs is None else f"::GEOMETRY('EPSG:{crs}')"
    out=e.query(f'SELECT 7 AS pid, ST_Point(1,1){cast} AS {name}')
    return e.to_geodataframe(out,name) if as_gdf else out

@pytest.mark.parametrize('how',['inner','left','right','outer'])
def test_known_conflicts_rejected_after_public_conversion(e,how):
    left=frame(e,4326,as_gdf=True);right=frame(e,3857,as_gdf=True)
    with pytest.raises(ValueError,match='conflicting geometry CRS'):
        e.join(left,right,on='geometry',how=how)

def test_right_key_crs_after_public_conversion(e):
    left=frame(e,None,as_gdf=True);right=frame(e,3857,as_gdf=True)
    out=e.to_geodataframe(e.join(left,right,on='geometry',how='right'))
    assert out.crs is not None and out.crs.to_epsg()==3857

def test_outer_known_none_rejected_after_public_conversion(e):
    with pytest.raises(ValueError,match='outer join'):
        e.join(frame(e,4326,as_gdf=True),frame(e,None,as_gdf=True),on='geometry',how='outer')

def test_raw_composite_wkb_preexisting_limit(e):
    with pytest.raises(TypeError,match="unhashable type: 'bytearray'"):
        e.join(frame(e,None),frame(e,3857),on=['pid','geometry'],how='right')

@pytest.mark.parametrize('name',['geometry','geometry_x'])
def test_immutable_wkb_composite_right_source_end_to_end(e,name):
    left=frame(e,None,name);right=frame(e,3857,name)
    left[name]=left[name].map(bytes);right[name]=right[name].map(bytes)
    out=e.to_geodataframe(e.join(left,right,on=['pid',name],how='right'),name)
    assert len(out)==1 and out.crs.to_epsg()==3857

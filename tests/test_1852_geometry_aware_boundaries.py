"""Public join/conversion probes for the geometry-aware delta, no live services."""
import copy
import geopandas as gpd
import pandas as pd
import pytest
from pyproj import CRS
from shapely.geometry import Point
from siege_utilities.engines.dataframe_engine import DuckDBEngine

pytest.importorskip("duckdb")

META='siege_geometry_crs'
@pytest.fixture
def e():
    engine=DuckDBEngine();yield engine;engine._connection.close()

def geo(crs,name='geometry',kind='point'):
    values=[] if kind=='empty' else [None if kind=='null' else Point(1,1)]
    return gpd.GeoDataFrame({'pid':pd.Series([7]*len(values),dtype='int64'),name:gpd.GeoSeries(values,crs=crs)},geometry=name)

def epsg(value):return None if value is None else CRS.from_user_input(value).to_epsg()
SNAPSHOTS=[]
AUDIT={'cases':0,'frames':0}
def saved(frame):
    state=frame.copy(deep=True),copy.deepcopy(frame.attrs)
    SNAPSHOTS.append((frame,state))
    return state

@pytest.fixture(autouse=True)
def all_captured_inputs_unchanged():
    SNAPSHOTS.clear()
    yield
    for frame,state in SNAPSHOTS:unchanged(frame,state)
    AUDIT['cases']+=1;AUDIT['frames']+=len(SNAPSHOTS)

def unchanged(frame,before):
    pd.testing.assert_frame_equal(frame,before[0]);assert frame.attrs==before[1]
    for c in frame.columns:
        if isinstance(frame[c],gpd.GeoSeries):assert frame[c].crs==before[0][c].crs

@pytest.mark.parametrize('how',['inner','left','right','outer'])
def test_plain_crs_index_label_does_not_create_geometry_key(e,how):
    left=pd.DataFrame({'key':['EPSG:4326','match'],'value':[1,2]},index=['crs','row'])
    right=pd.DataFrame({'key':['EPSG:3857','match'],'value':[3,4]},index=['crs','row'])
    expected=pd.merge(left,right,on='key',how=how)
    result=e.join(left,right,on='key',how=how)
    pd.testing.assert_frame_equal(result,expected)
    assert META not in result.attrs

def test_plain_crs_index_label_does_not_poison_nonkey_attrs(e):
    left=pd.DataFrame({'pid':[7],'value':[10]},index=['crs'])
    right=pd.DataFrame({'pid':[7],'value':[20]},index=['crs'])
    result=e.join(left,right,on='pid')
    assert META not in result.attrs

def test_index_level_join_never_calls_set_crs_on_plain_series(e):
    left=pd.DataFrame({'value':['EPSG:4326']},index=pd.Index(['crs'],name='pid'))
    right=pd.DataFrame({'value':['EPSG:3857']},index=pd.Index(['crs'],name='pid'))
    result=e.join(left,right,on='pid')
    pd.testing.assert_frame_equal(result,pd.merge(left,right,on='pid'))
    assert META not in result.attrs

def test_nonkey_column_named_crs_is_ordinary_data(e):
    left=pd.DataFrame({'pid':[7],'crs':['EPSG:4326']})
    right=pd.DataFrame({'pid':[7],'crs':['EPSG:3857']})
    result=e.join(left,right,on='pid')
    pd.testing.assert_frame_equal(result,pd.merge(left,right,on='pid'))
    assert META not in result.attrs

@pytest.mark.parametrize('name',['geometry','boundary'])
@pytest.mark.parametrize('lc,rc,how,expected',[
    (None,3857,'inner',None),(None,3857,'left',None),(None,3857,'right',3857),
    (3857,None,'right',None),(3857,None,'inner',3857),(3857,None,'left',3857),
    (3857,3857,'outer',3857),(None,None,'outer',None),
])
def test_public_output_source_crs_and_input_immutability(e,name,lc,rc,how,expected):
    left=geo(lc,name);right=geo(rc,name);sl=saved(left);sr=saved(right)
    out=e.to_geodataframe(e.join(left,right,on=name,how=how),name)
    assert epsg(out.crs)==expected
    assert list(out.geometry)==[Point(1,1)]
    unchanged(left,sl);unchanged(right,sr)

@pytest.mark.parametrize('how',['inner','left','right','outer'])
@pytest.mark.parametrize('spelling',['wkt','projjson'])
def test_live_geoseries_equal_crs_spellings(e,how,spelling):
    c=CRS.from_epsg(4326)
    other=c.to_wkt() if spelling=='wkt' else c.to_json()
    left=geo('EPSG:4326');right=geo(other)
    out=e.to_geodataframe(e.join(left,right,on='geometry',how=how))
    assert epsg(out.crs)==4326 and list(out.geometry)==[Point(1,1)]

@pytest.mark.parametrize('how',['inner','left','right','outer'])
def test_live_unknown_geoseries_wins_over_stale_known_attrs(e,how):
    left=geo(None);right=geo(None)
    left.attrs[META]={'geometry':'EPSG:3857'};right.attrs[META]={'geometry':'EPSG:3857'}
    sl=saved(left);sr=saved(right)
    out=e.to_geodataframe(e.join(left,right,on='geometry',how=how))
    assert out.crs is None
    unchanged(left,sl);unchanged(right,sr)

@pytest.mark.parametrize('side',['left','right'])
def test_unknown_live_crs_does_not_become_a_false_conflict(e,side):
    unknown=geo(None);unknown.attrs[META]={'geometry':'EPSG:4326'}
    known=geo(3857)
    left,right=(unknown,known) if side=='left' else (known,unknown)
    how='inner' if side=='left' else 'right'
    out=e.to_geodataframe(e.join(left,right,on='geometry',how=how))
    assert out.crs is None

@pytest.mark.parametrize('side',['left','right'])
def test_known_live_crs_wins_over_stale_attrs(e,side):
    left=geo(4326);right=geo(4326)
    (left if side=='left' else right).attrs[META]={'geometry':'EPSG:3857'}
    out=e.to_geodataframe(e.join(left,right,on='geometry'))
    assert epsg(out.crs)==4326

@pytest.mark.parametrize('kind',['empty','null'])
@pytest.mark.parametrize('name',['geometry','boundary'])
@pytest.mark.parametrize('how',['inner','left','right','outer'])
def test_empty_allnull_nondefault_geometry(e,kind,name,how):
    left=geo(3857,name,kind);right=geo(3857,name,kind)
    sl=saved(left);sr=saved(right)
    out=e.to_geodataframe(e.join(left,right,on=name,how=how),name)
    assert epsg(out.crs)==3857
    assert len(out)==(0 if kind=='empty' else 1)
    if kind=='null':assert out.geometry.isna().all()
    unchanged(left,sl);unchanged(right,sr)

def raw(e,crs,name='geometry'):
    cast='' if crs is None else f"::GEOMETRY('EPSG:{crs}')"
    out=e.query(f'SELECT 7 AS pid, ST_Point(1,1){cast} AS {name}')
    out[name]=out[name].map(bytes)
    return out

@pytest.mark.parametrize('gdf_side',['left','right'])
@pytest.mark.parametrize('how',['inner','left','right'])
@pytest.mark.parametrize('aux',[False,True])
def test_mixed_key_output_end_to_end_with_auxiliary_geometry(e,gdf_side,how,aux):
    left=geo(None) if gdf_side=='left' else raw(e,None)
    right=geo(3857) if gdf_side=='right' else raw(e,3857)
    if aux:
        frame=left if gdf_side=='left' else right
        frame['aux']=gpd.GeoSeries([Point(2,2)],crs=2193)
    sl=saved(left);sr=saved(right)
    out=e.to_geodataframe(e.join(left,right,on='geometry',how=how))
    assert epsg(out.crs)==(3857 if how=='right' else None)
    assert len(out)==(0 if how=='inner' else 1)
    if len(out):assert list(out.geometry)==[Point(1,1)]
    unchanged(left,sl);unchanged(right,sr)

@pytest.mark.parametrize('pair',['both_geo','geo_left','geo_right'])
@pytest.mark.parametrize('selected,expected',[('geometry_x',4326),('geometry_y',3857)])
def test_selected_suffixed_nonkey_geometry_end_to_end(e,pair,selected,expected):
    left=raw(e,4326) if pair=='geo_right' else geo(4326)
    right=raw(e,3857) if pair=='geo_left' else geo(3857)
    sl=saved(left);sr=saved(right)
    joined=e.join(left,right,on='pid')
    out=e.to_geodataframe(joined,selected)
    assert out.geometry.name==selected
    assert epsg(out.crs)==expected
    assert list(out.geometry)==[Point(1,1)]
    unchanged(left,sl);unchanged(right,sr)

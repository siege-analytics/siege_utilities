import pytest

gpd=pytest.importorskip("geopandas")
pytest.importorskip("duckdb")

import pandas as pd  # noqa: E402 - after the optional-dependency skips
from shapely.geometry import Point  # noqa: E402
from siege_utilities.engines.dataframe_engine import DuckDBEngine  # noqa: E402

META='siege_geometry_crs'
@pytest.fixture
def engine():
    e=DuckDBEngine();yield e;e._connection.close()
@pytest.mark.parametrize('kind',['shapely','wkb'])
@pytest.mark.parametrize('index_label',['crs','ordinary'])
def test_plain_dataframe_crs_row_label_is_not_crs(engine,kind,index_label):
    # A row labelled "crs" never supplies the CRS. Shapely objects are read at
    # the default CRS, as on Pandas; WKB bytes carry no CRS and stay unknown.
    from siege_utilities.geo.crs import get_default_crs
    pt=Point(1,1);v=pt if kind=='shapely' else pt.wkb
    frame=pd.DataFrame({'geometry':[v]},index=[index_label])
    out=engine.to_geodataframe(frame)
    if kind=='shapely':
        assert out.crs==get_default_crs()
    else:
        assert out.crs is None
    assert out.geometry.iloc[0].equals(pt)
@pytest.mark.parametrize('live',[None,4326])
@pytest.mark.parametrize('stale',[False,True])
def test_nonactive_live_geoseries_wins_over_stale_metadata_and_does_not_mutate(engine,live,stale):
    f=gpd.GeoDataFrame({'geometry':gpd.GeoSeries([Point(0,0)],crs=2193),'boundary':gpd.GeoSeries([Point(1,1)],crs=live)},geometry='geometry')
    if stale:f.attrs[META]={'boundary':'EPSG:3857'}
    before=f.copy(deep=True);array=f['boundary'].values;crs=array.crs
    try:out=engine.to_geodataframe(f,'boundary')
    finally:
        assert array.crs==crs,'to_geodataframe mutated input GeometryArray CRS'
        pd.testing.assert_frame_equal(f,before)
    assert out.geometry.name=='boundary'
    assert (None if out.crs is None else out.crs.to_epsg())==live

from siege_utilities import download_dataset
from siege_utilities import download_osm_data


class FakeCensusSource:
    def __init__(self):
        self.calls = []

    def download_dataset(self, year, geographic_level, state_fips=None):
        self.calls.append(("download_dataset", year, geographic_level, state_fips))
        return {"fake": "census-geodataframe"}


class FakeOpenStreetMapSource:
    def __init__(self):
        self.calls = []

    def download_osm_data(self, query, bbox=None):
        self.calls.append(("download_osm_data", query, bbox))
        return {"fake": "osm-geodataframe"}


def test_download_dataset_delegates_and_reprojects(monkeypatch):
    source = FakeCensusSource()
    monkeypatch.setattr(
        "siege_utilities.geo.spatial_data._get_census_source", lambda: source
    )
    monkeypatch.setattr(
        "siege_utilities.geo.spatial_data.reproject_if_needed",
        lambda gdf, crs=None: {"reprojected": gdf, "crs": crs},
    )

    result = download_dataset(2020, "tract", "06", crs="EPSG:3310")

    assert result == {"reprojected": {"fake": "census-geodataframe"}, "crs": "EPSG:3310"}
    assert source.calls == [("download_dataset", 2020, "tract", "06")]


def test_download_osm_data_delegates_bbox_and_reprojects(monkeypatch):
    source = FakeOpenStreetMapSource()
    bbox = [-77.1, 38.8, -76.9, 39.0]
    monkeypatch.setattr(
        "siege_utilities.geo.spatial_data.OpenStreetMapDataSource", lambda: source
    )
    monkeypatch.setattr(
        "siege_utilities.geo.spatial_data.reproject_if_needed",
        lambda gdf, crs=None: {"reprojected": gdf, "crs": crs},
    )

    result = download_osm_data("amenity=school", bbox=bbox, crs="EPSG:3857")

    assert result == {"reprojected": {"fake": "osm-geodataframe"}, "crs": "EPSG:3857"}
    assert source.calls == [("download_osm_data", "amenity=school", bbox)]

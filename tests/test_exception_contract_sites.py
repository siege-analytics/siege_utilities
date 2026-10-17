"""Failure injection at the remaining #1532 sites; all I/O is local or mocked."""

import importlib
import json
import sqlite3
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
import requests
import yaml


@pytest.mark.parametrize("module", ["enhanced_config", "migration"])
def test_missing_user_and_corrupt_client_not_migrated(tmp_path, module):
    cls = importlib.import_module(
        f"siege_utilities.config.{module}"
    ).ConfigurationMigrator
    migrator = cls(tmp_path, tmp_path / "new")
    result = migrator.migrate_all_configurations()
    assert not result["user_profile"]["migrated"] and result["error"]
    (tmp_path / "user_config.yaml").write_text("username: demo\n", encoding="utf-8")
    clients = tmp_path / "clients"
    clients.mkdir()
    bad = clients / "DEMO.yaml"
    bad.write_text("client_name: [unclosed\n", encoding="utf-8")
    with pytest.raises(yaml.YAMLError):
        migrator.migrate_client_profile(bad, "DEMO")
    result = migrator.migrate_all_configurations()
    assert result["user_profile"]["migrated"]
    assert result["client_profiles"]["migrated"] == []
    assert result["client_profiles"]["errors"]


def test_locale_population_reachable_after_census_factory_disabled():
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import box
    from siege_utilities.geo.locale import NCESLocaleClassifier

    with pytest.raises(ValueError):
        NCESLocaleClassifier.from_census_year(2020)
    ua = gpd.GeoDataFrame({"UACE20": ["00001"]}, geometry=[box(-1, -1, 1, 1)], crs=4326)
    city = gpd.GeoDataFrame(
        {"POP": ["n/a"]}, geometry=[box(-0.5, -0.5, 0.5, 0.5)], crs=4326
    )
    classifier = NCESLocaleClassifier(
        urbanized_areas=ua,
        urban_clusters=None,
        principal_cities=city,
        place_populations={},
        ua_populations={"00001": 5_000_000},
    )
    with pytest.raises(ValueError, match="population"):
        classifier.classify_point(0, 0)


def test_invalid_state_raises_before_download(monkeypatch):
    from siege_utilities.geo import spatial_data

    source = Mock()
    monkeypatch.setattr(spatial_data, "CensusDataSource", lambda: source)
    with (
        pytest.warns(DeprecationWarning),
        pytest.raises(ValueError, match="state identifier"),
    ):
        spatial_data.get_census_boundaries(2020, "county", state_identifier="invalid")
    source.get_geographic_boundaries.assert_not_called()


@pytest.mark.parametrize("column", ["STATEFP", "statefp20", "StateFp10"])
def test_state_filter_accepts_case_variants(monkeypatch, column):
    from siege_utilities.geo import spatial_data

    source = Mock()
    source.get_geographic_boundaries.return_value = pd.DataFrame({column: ["48", "06"]})
    monkeypatch.setattr(spatial_data, "CensusDataSource", lambda: source)
    with pytest.warns(DeprecationWarning):
        result = spatial_data.get_census_boundaries(
            2020, "county", state_identifier="TX"
        )
    assert result[column].tolist() == ["48"]


@pytest.mark.parametrize(
    "status,body,error",
    [
        (404, "{}", LookupError),
        (503, "{}", requests.HTTPError),
        (201, '{"label": "unexpected"}', requests.HTTPError),
        (200, "not json", ValueError),
        (200, "[]", ValueError),
        (200, "{}", ValueError),
    ],
)
def test_metadata_failures_are_distinct(monkeypatch, status, body, error):
    from siege_utilities.geo.census.variable_registry import VariableRegistry

    response = requests.Response()
    response.status_code = status
    response._content = body.encode()
    get = Mock(return_value=response)
    monkeypatch.setattr(requests, "get", get)
    with pytest.raises(error):
        VariableRegistry().get_variable_metadata("ZZ_MISSING", 2020, timeout=2)
    assert get.call_args.kwargs["timeout"] == 2


@pytest.mark.parametrize(
    "method,kwargs",
    [
        ("create_bar_chart", {}),
        ("create_line_chart", {"x_column": "missing"}),
        ("create_pie_chart", {}),
        (
            "create_proportional_text_bar_chart",
            {"labels_column": "missing", "values_column": "missing"},
        ),
        (
            "create_heatmap_text_chart",
            {"x_column": "missing", "y_column": "missing", "value_column": "missing"},
        ),
    ],
)
def test_chart_failures_raise(method, kwargs):
    pytest.importorskip("reportlab")
    pytest.importorskip("matplotlib")
    from siege_utilities.reporting.chart_generator import ChartGenerator

    with pytest.raises(RuntimeError):
        getattr(ChartGenerator(), method)(pd.DataFrame({"label": ["x"]}), **kwargs)


def test_swmaps_query_failure_is_not_missing_attribute(tmp_path):
    from siege_utilities.geo.data_reception import extract_attributes_swmaps
    from siege_utilities.geo.swmaps_reader import open_swmaps, read_features

    path = tmp_path / "broken.sqlite"
    with sqlite3.connect(path, timeout=5) as conn:
        conn.executescript("""
            CREATE TABLE features (uuid TEXT, name TEXT, layer_id TEXT);
            CREATE TABLE points (fid TEXT, seq INTEGER, lat REAL, lon REAL, elv REAL);
            CREATE TABLE feature_layers (uuid TEXT, name TEXT, group_name TEXT, geom_type TEXT);
        """)
    with pytest.raises(sqlite3.DatabaseError, match="attribute query"):
        extract_attributes_swmaps(str(path), "one", ["name"])
    with open_swmaps(str(path)) as archive:
        with pytest.raises(sqlite3.DatabaseError, match="attribute join"):
            list(read_features(archive))


@pytest.mark.parametrize(
    "name", ["SpatialDataTransformer", "PostGISConnector", "DuckDBConnector"]
)
def test_spatial_constructors_reject_broken_config(monkeypatch, name):
    from siege_utilities.geo import spatial_transformations as module

    monkeypatch.setattr(module, "DUCKDB_AVAILABLE", True)
    monkeypatch.setattr(
        module, "get_user_config", Mock(side_effect=ValueError("bad config"))
    )
    with pytest.raises(ValueError, match="bad config"):
        getattr(module, name)()


def test_postgis_rejects_failed_connection(monkeypatch):
    psycopg2 = pytest.importorskip("psycopg2")
    from siege_utilities.geo import spatial_transformations as module

    monkeypatch.setattr(module, "get_user_config", lambda: None)
    monkeypatch.setattr(
        psycopg2, "connect", Mock(side_effect=psycopg2.OperationalError("offline"))
    )
    with pytest.raises(ConnectionError, match="PostGIS"):
        module.PostGISConnector("postgresql://localhost/test")
    with pytest.raises(ValueError, match="no connection_string"):
        module.PostGISConnector()


def test_mapclassify_error_does_not_switch_backend(monkeypatch):
    from siege_utilities.geo import classification

    monkeypatch.setattr(classification, "_MAPCLASSIFY_AVAILABLE", True)
    monkeypatch.setattr(
        classification,
        "_classify_with_mapclassify",
        Mock(side_effect=ValueError("bad breaks")),
    )
    with pytest.raises(RuntimeError, match="mapclassify") as exc:
        classification.classify_series([1, 2, 4, 8], scheme="quantiles", k=2)
    assert isinstance(exc.value.__cause__, ValueError)


def test_invalid_crs_raises():
    from siege_utilities.geo.crs import _normalize_crs

    with pytest.raises(ValueError, match="Invalid CRS"):
        _normalize_crs("not-a-coordinate-system")



@pytest.mark.parametrize("timestamp", ["not-a-date", None, 42])
def test_invalid_cache_timestamp_is_expired(tmp_path, timestamp):
    from siege_utilities.geo.providers.nlrb_cache import NLRBCache

    (tmp_path / "entry.json").write_text(
        json.dumps({"fetched_at": timestamp, "cases": []})
    )
    assert NLRBCache(tmp_path).get("entry") is None


def test_gadm_read_failure_never_downloads(monkeypatch):
    from siege_utilities.geo import boundary_sources

    provider = Mock()
    monkeypatch.setattr(boundary_sources, "_load_gadm_via_provider", provider)
    engine = SimpleNamespace(
        load_polygons=Mock(side_effect=ValueError("corrupt parquet"))
    )
    with pytest.raises(RuntimeError, match="staged GADM"):
        boundary_sources.load_gadm_boundaries(engine)
    provider.assert_not_called()


def test_default_geocoder_construction_raises(monkeypatch):
    from siege_utilities.geo import codification

    monkeypatch.setattr(
        codification, "_get_default_geocoder", Mock(side_effect=ImportError("missing"))
    )
    with pytest.raises(RuntimeError, match="default geocoder"):
        codification.codify_area(["123 Main St"])


def test_hdfs_sync_failure_never_returns_local_path(tmp_path, monkeypatch):
    from siege_utilities.distributed.hdfs_operations import AbstractHDFSOperations

    ops = AbstractHDFSOperations.__new__(AbstractHDFSOperations)
    ops.config = Mock()
    monkeypatch.setattr(ops, "check_hdfs_status", lambda: True)
    monkeypatch.setattr(
        ops, "sync_directory_to_hdfs", Mock(side_effect=RuntimeError("sync failed"))
    )
    create = Mock()
    monkeypatch.setattr(ops, "create_spark_session", create)
    with pytest.raises(RuntimeError, match="HDFS distributed setup failed"):
        ops.setup_distributed_environment(str(tmp_path))
    create.assert_not_called()

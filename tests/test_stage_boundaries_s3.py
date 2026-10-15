"""Credential and bounded-export regressions for stage_boundaries_s3 (#1578)."""

import argparse
import builtins
import json
import runpy
from contextlib import closing
from pathlib import Path
from unittest.mock import create_autospec

import pytest

try:
    import boto3
    import geopandas as gpd
    import pyarrow.parquet as pq
    from botocore.exceptions import ClientError, NoCredentialsError
    from django.core.exceptions import ImproperlyConfigured
    from django.core.management.base import CommandError
    from django.db.models import QuerySet
    from django.contrib.gis.geos import GEOSGeometry
    from django.contrib.gis.db import models as _gis_models  # noqa: F401
    from geopandas.testing import assert_geodataframe_equal
except ImportError as exc:
    pytest.skip(
        f"Install siege_utilities[s3,geo,data,geodjango] to run export tests: {exc}",
        allow_module_level=True,
    )
except (ImproperlyConfigured, OSError) as exc:
    pytest.skip(
        f"Install GDAL and GEOS and configure their library paths: {exc}",
        allow_module_level=True,
    )

# Import the command only after its optional dependency guards.
from siege_utilities.geo.django.management.commands import stage_boundaries_s3 as stage  # noqa: E402


@pytest.fixture
def command():
    return stage.Command()


def options(command, *flags):
    return vars(command.create_parser("manage.py", "stage_boundaries_s3").parse_args(
        ["--year", "2020", "--type", "county", *flags]
    ))


def test_no_flags_have_no_credential_defaults(command):
    parser = argparse.ArgumentParser()
    command.add_arguments(parser)
    # Only year/type are required business inputs; inspect auth with NO flags.
    for action in parser._actions:
        if action.dest in ("year", "type"):
            action.required = False
    parsed = parser.parse_args([])
    assert getattr(parsed, "access_key", None) is None
    assert getattr(parsed, "secret_key", None) is None


def test_endpoint_default_is_none(command):
    assert options(command)["endpoint_url"] is None


@pytest.mark.parametrize("flag", ["--secret-key", "--access-key"])
def test_credential_flags_are_rejected(command, flag):
    with pytest.raises(CommandError, match="unrecognized arguments"):
        options(command, flag, "test-only-credential")


@pytest.fixture
def aws_session(monkeypatch, tmp_path):
    # A real isolated boto3 session, with no credentials/network from the host.
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-access-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret-key")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "test-session-token")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ENDPOINT_URL", "https://storage.example.test")
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "config"))
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "credentials"))
    for name in ("AWS_PROFILE", "AWS_DEFAULT_PROFILE", "AWS_ENDPOINT_URL_S3",
                 "AWS_IGNORE_CONFIGURED_ENDPOINT_URLS"):
        monkeypatch.delenv(name, raising=False)
    session = boto3.Session()
    monkeypatch.setattr(stage.boto3, "client", session.client)
    return session


@pytest.mark.parametrize("endpoint", [None, "https://override.example.test"])
def test_handle_uses_boto3_environment_chain(command, aws_session, monkeypatch, endpoint):
    clients = []
    monkeypatch.setattr(command, "_export_type", lambda s3, *a, **kw: clients.append(s3))
    flags = [] if endpoint is None else ["--endpoint-url", endpoint]
    command.handle(**options(command, "--dry-run", *flags))
    client = clients[0]
    credentials = client._request_signer._credentials.get_frozen_credentials()
    assert credentials.access_key == "test-access-key"
    assert credentials.secret_key == "test-secret-key"
    assert credentials.token == "test-session-token"
    assert client.meta.endpoint_url == (endpoint or "https://storage.example.test")
    client.close()


@pytest.mark.parametrize(
    "service_endpoint,global_endpoint,cli_endpoint,ignore_configured,expected",
    [
        (None, "https://global.example.test", None, None, "https://global.example.test"),
        ("https://service.example.test", "https://global.example.test", None,
         None, "https://service.example.test"),
        ("https://service.example.test", "https://global.example.test",
         "https://cli.example.test", None, "https://cli.example.test"),
        ("https://service.example.test", "https://global.example.test", None,
         "true", None),
    ],
)
def test_handle_forwards_endpoint_on_older_boto3(
    command, aws_session, monkeypatch, service_endpoint, global_endpoint,
    cli_endpoint, ignore_configured, expected,
):
    """The minimum supported boto3 may not read AWS_ENDPOINT_URL itself."""
    if service_endpoint is None:
        monkeypatch.delenv("AWS_ENDPOINT_URL_S3", raising=False)
    else:
        monkeypatch.setenv("AWS_ENDPOINT_URL_S3", service_endpoint)
    monkeypatch.setenv("AWS_ENDPOINT_URL", global_endpoint)
    if ignore_configured is None:
        monkeypatch.delenv("AWS_IGNORE_CONFIGURED_ENDPOINT_URLS", raising=False)
    else:
        monkeypatch.setenv("AWS_IGNORE_CONFIGURED_ENDPOINT_URLS", ignore_configured)

    calls = []
    client = object()

    def client_without_environment_endpoint(service_name, **kwargs):
        calls.append((service_name, kwargs))
        return client

    monkeypatch.setattr(stage.boto3, "client", client_without_environment_endpoint)
    exports = []
    monkeypatch.setattr(command, "_export_type", lambda s3, *a, **kw: exports.append(s3))
    flags = [] if cli_endpoint is None else ["--endpoint-url", cli_endpoint]
    command.handle(**options(command, "--dry-run", *flags))
    assert calls == [("s3", {"endpoint_url": expected})]
    assert exports == [client]


def test_handle_uses_shared_profile_credentials(command, aws_session, monkeypatch, tmp_path):
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        monkeypatch.delenv(name)
    (tmp_path / "credentials").write_text(
        "[default]\naws_access_key_id = profile-access\n"
        "aws_secret_access_key = profile-secret\n"
    )
    clients = []
    monkeypatch.setattr(command, "_export_type", lambda s3, *a, **kw: clients.append(s3))
    command.handle(**options(command, "--dry-run"))
    credentials = clients[0]._request_signer._credentials.get_frozen_credentials()
    assert credentials.access_key == "profile-access"
    assert credentials.secret_key == "profile-secret"
    assert credentials.token is None
    clients[0].close()


def test_handle_uses_default_aws_endpoint(command, aws_session, monkeypatch):
    monkeypatch.delenv("AWS_ENDPOINT_URL")
    clients = []
    monkeypatch.setattr(command, "_export_type", lambda s3, *a, **kw: clients.append(s3))
    command.handle(**options(command, "--dry-run"))
    assert clients[0].meta.endpoint_url == "https://s3.amazonaws.com"
    clients[0].close()


@pytest.fixture
def boundaries():
    # Real GeoDjango objects exercise the WKT seam, including a null first batch.
    return [
        stage.County(
            feature_id=f"060{index:02d}", geoid=f"060{index:02d}",
            name=f"County {index} \N{LATIN SMALL LETTER E WITH ACUTE}",
            vintage_year=2020, state_fips="06",
            geometry=None if index < 2 else GEOSGeometry(
                f"MULTIPOLYGON ((({index} 0, {index + 1} 0, "
                f"{index + 1} 1, {index} 1, {index} 0)))", srid=4326,
            ),
        )
        for index in range(5)
    ]


class UploadRecorder:
    """Copy completed files as an S3 upload would, while they still exist."""

    def __init__(self, directory):
        self.directory = directory
        self.uploads = {}
        self.sources = []

    def upload_file(self, Filename, Bucket, Key, ExtraArgs=None):
        destination = self.directory / Path(Key).name
        destination.write_bytes(Path(Filename).read_bytes())
        self.uploads[Key] = (Bucket, destination, ExtraArgs or {})
        self.sources.append(Path(Filename))

    def put_object(self, *, Bucket, Key, Body, ContentType):
        destination = self.directory / Path(Key).name
        destination.write_bytes(Body)
        self.uploads[Key] = (Bucket, destination, {"ContentType": ContentType})


@pytest.fixture
def export_setup(boundaries, monkeypatch, tmp_path):
    qs = create_autospec(QuerySet, instance=True, spec_set=True)
    qs.count.return_value = len(boundaries)
    qs.filter.return_value = qs
    qs.iterator.side_effect = lambda **kwargs: iter(boundaries)
    qs.__iter__.side_effect = AssertionError("Do not materialize the queryset")
    monkeypatch.setattr(stage.County.objects, "filter", lambda **kwargs: qs)
    monkeypatch.setattr(stage, "EXPORT_CHUNK_SIZE", 2, raising=False)
    return qs, UploadRecorder(tmp_path)


@pytest.mark.parametrize("output_format", ["parquet", "geojson", "both"])
def test_export_serializes_before_consuming_next_batch(
    command, export_setup, boundaries, monkeypatch, output_format,
):
    qs, s3 = export_setup
    serialized = []
    original_wkb = gpd.GeoDataFrame.to_wkb
    original_features = gpd.GeoDataFrame.iterfeatures

    def to_wkb(frame, *args, **kwargs):
        serialized.append(len(frame))
        return original_wkb(frame, *args, **kwargs)

    def iterfeatures(frame, *args, **kwargs):
        serialized.append(len(frame))
        yield from original_features(frame, *args, **kwargs)

    def iterator(*, chunk_size):
        yield from boundaries[:2]
        assert serialized, "First batch must be serialized before fetching more rows"
        yield from boundaries[2:]

    qs.iterator.side_effect = iterator
    monkeypatch.setattr(gpd.GeoDataFrame, "to_wkb", to_wkb)
    monkeypatch.setattr(gpd.GeoDataFrame, "iterfeatures", iterfeatures)
    command._export_type(s3, "boundaries", "county", 2020, output_format=output_format)
    assert max(serialized) <= 2
    assert sum(serialized) == (10 if output_format == "both" else 5)
    assert all(not path.exists() for path in s3.sources)
    qs.iterator.assert_called_once_with(chunk_size=2)
    qs.__iter__.assert_not_called()


@pytest.mark.parametrize("state_fips", [None, "06"])
def test_chunked_exports_preserve_contents_and_paths(
    command, export_setup, boundaries, state_fips,
):
    qs, s3 = export_setup
    command._export_type(s3, "boundaries", "county", 2020, state_fips=state_fips)
    prefix = "boundaries/tiger/county/2020" + (f"/{state_fips}" if state_fips else "")
    assert set(s3.uploads) == {f"{prefix}/data.parquet", f"{prefix}/data.geojson"}
    parquet = s3.uploads[f"{prefix}/data.parquet"][1]
    geojson = s3.uploads[f"{prefix}/data.geojson"][1]
    expected = gpd.GeoDataFrame({
        "feature_id": [obj.feature_id for obj in boundaries],
        "name": [obj.name for obj in boundaries],
        "vintage_year": [2020] * 5,
        "geoid": [obj.geoid for obj in boundaries],
        "state_fips": ["06"] * 5,
        "geometry": gpd.GeoSeries.from_wkt([
            obj.geometry.wkt if obj.geometry else None for obj in boundaries
        ]),
    }, crs="EPSG:4326")
    with parquet.open("rb") as source:
        assert_geodataframe_equal(gpd.read_parquet(source), expected)
    assert json.loads(geojson.read_text()) == json.loads(expected.to_json())
    with parquet.open("rb") as source:
        assert pq.ParquetFile(source).num_row_groups == 3
    assert s3.uploads[f"{prefix}/data.geojson"][2] == {
        "ContentType": "application/geo+json",
    }


def test_dry_run_does_not_iterate_or_upload(command, export_setup):
    qs, s3 = export_setup
    command._export_type(s3, "boundaries", "county", 2020, dry_run=True)
    qs.iterator.assert_not_called()
    assert s3.uploads == {}


def test_empty_queryset_does_not_upload(command, export_setup):
    qs, s3 = export_setup
    qs.count.return_value = 0
    command._export_type(s3, "boundaries", "county", 2020)
    qs.iterator.assert_not_called()
    assert s3.uploads == {}


def test_queryset_error_propagates_without_uploading_partial_files(command, export_setup):
    qs, s3 = export_setup
    from django.db import DatabaseError

    def fail_after_batch(**kwargs):
        yield stage.County(feature_id="06001", geoid="06001", vintage_year=2020)
        yield stage.County(feature_id="06003", geoid="06003", vintage_year=2020)
        raise DatabaseError("cursor interrupted")

    qs.iterator.side_effect = fail_after_batch
    with pytest.raises(DatabaseError, match="cursor interrupted"):
        command._export_type(s3, "boundaries", "county", 2020)
    assert s3.uploads == {}


def test_upload_error_propagates_and_removes_temporary_files(command, export_setup, monkeypatch):
    qs, s3 = export_setup

    def failed_upload(Filename, *args, **kwargs):
        s3.sources.append(Path(Filename))
        raise NoCredentialsError()

    monkeypatch.setattr(s3, "upload_file", failed_upload)
    with pytest.raises(NoCredentialsError, match="Unable to locate credentials"):
        command._export_type(s3, "boundaries", "county", 2020)
    assert s3.sources
    assert all(not path.exists() for path in s3.sources)


@pytest.mark.parametrize("dependency", ["boto3", "geopandas"])
def test_optional_import_error_raises_with_install_hint(monkeypatch, dependency):
    original_import = builtins.__import__

    def missing_dependency(name, *args, **kwargs):
        if name == dependency:
            raise ImportError(f"test: {dependency} unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing_dependency)
    isolated_module = runpy.run_path(stage.__file__)
    with pytest.raises(CommandError, match=f"{dependency} is required.*siege_utilities"):
        isolated_module["Command"]().handle()


def test_parquet_dependency_error_has_install_hint(command, export_setup, monkeypatch):
    qs, s3 = export_setup
    original_import = builtins.__import__

    def missing_pyarrow(name, *args, **kwargs):
        if name == "pyarrow":
            raise ImportError("test: pyarrow unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", missing_pyarrow)
    with pytest.raises(CommandError, match=r"pyarrow is required.*siege_utilities\[data\]"):
        command._export_type(s3, "boundaries", "county", 2020)
    assert s3.uploads == {}


def test_missing_bucket_creation_error_propagates(command, aws_session):
    from botocore.stub import Stubber

    with closing(aws_session.client("s3")) as client, Stubber(client) as stubber:
        stubber.add_client_error("head_bucket", service_error_code="404",
                                 expected_params={"Bucket": "boundaries"})
        stubber.add_client_error("create_bucket", service_error_code="AccessDenied",
                                 expected_params={"Bucket": "boundaries"})
        with pytest.raises(ClientError, match="AccessDenied"):
            command._ensure_bucket(client, "boundaries")
        stubber.assert_no_pending_responses()

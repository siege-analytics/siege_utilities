"""Environment opt-in and warning isolation for spatial and NCES downloads."""

import importlib
import importlib.util
import io
import logging
import warnings
import zipfile
from functools import partial

import geopandas as gpd
import pytest
import requests
from shapely.geometry import Point
from urllib3.exceptions import InsecureRequestWarning

from siege_utilities.files import remote


def _fresh_module(name):
    # Warm dependencies without leaking their filters or replacing shared classes.
    with warnings.catch_warnings():
        original = importlib.import_module(name)
    spec = importlib.util.spec_from_file_location(name, original.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_spatial_import_with_ssl_opt_in_preserves_warning_filters(monkeypatch):
    monkeypatch.setenv("SIEGE_INSECURE_SSL", "1")
    with warnings.catch_warnings():
        importlib.import_module("siege_utilities.geo.spatial_data")
    before = warnings.filters[:]
    with warnings.catch_warnings():
        module = _fresh_module("siege_utilities.geo.spatial_data")
        assert module._ALLOW_INSECURE_SSL is True
        assert warnings.filters == before
        with pytest.warns(InsecureRequestWarning, match="Unverified HTTPS request"):
            warnings.warn("Unverified HTTPS request to unrelated service", InsecureRequestWarning)


@pytest.fixture(params=[None, "1"], ids=["strict", "opt-in"])
def ssl_modules(request, monkeypatch):
    monkeypatch.delenv("SIEGE_INSECURE_SSL", raising=False)
    if request.param is not None:
        monkeypatch.setenv("SIEGE_INSECURE_SSL", request.param)
    with warnings.catch_warnings():
        spatial = _fresh_module("siege_utilities.geo.spatial_data")
        nces = _fresh_module("siege_utilities.geo.providers.nces_download")
        yield spatial, nces, request.param == "1"


@pytest.fixture
def boundary_zip(tmp_path):
    directory = tmp_path / "shapefile"
    directory.mkdir()
    frame = gpd.GeoDataFrame({"GEOID": ["06001"]}, geometry=[Point(-120, 38)], crs="EPSG:4326")
    frame.to_file(directory / "boundary.shp")
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zipped:
        for path in directory.iterdir():
            zipped.write(path, path.name)
    return archive.getvalue()


@pytest.mark.geo
@pytest.mark.parametrize("site", ["tiger", "tiger-invalid-zip-retry", "government", "nces"])
def test_download_sites_honor_ssl_environment(
    ssl_modules, site, boundary_zip, tmp_path, monkeypatch, caplog,
):
    spatial, nces, opted_in = ssl_modules
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    monkeypatch.setattr(spatial, "get_download_directory", lambda: downloads)
    monkeypatch.setattr(spatial.CensusDirectoryDiscovery, "get_available_years", lambda self: [2023])
    verification = []
    forwarded = []
    real_download = remote.download_file

    def record_download(*args, **kwargs):
        forwarded.append(kwargs.get("allow_insecure_fallback"))
        return real_download(*args, **kwargs)

    def get_response(url, **kwargs):
        verification.append(kwargs["verify"])
        if kwargs["verify"] is not False:
            raise requests.exceptions.SSLError("certificate verify failed")
        response = requests.Response()
        response.status_code = 200
        body = boundary_zip
        if site == "tiger-invalid-zip-retry" and len(forwarded) == 1:
            body = b"<html>Retry download</html>"
        response.raw = io.BytesIO(body)
        return response

    monkeypatch.setattr(remote, "download_file", record_download)
    monkeypatch.setattr(spatial, "download_file", record_download)
    monkeypatch.setattr(remote.requests, "get", get_response)
    url = "https://example.test/boundary.zip"
    if site == "nces":
        source = nces.NCESDownloader(cache_dir=str(downloads))
        run = partial(source._download_and_extract, url, "locale_boundaries", 2023)
        error_type = nces.NCESDownloadError
    elif site == "government":
        source = spatial.GovernmentDataSource("https://example.test")
        run = partial(source._download_and_process_dataset, url, "shapefile")
        error_type = spatial.SpatialDataError
    else:
        source = spatial.CensusDataSource()
        run = partial(source._download_and_process_tiger, url, "county")
        error_type = spatial.BoundaryDownloadError

    with caplog.at_level(logging.ERROR, logger=remote.log.name):
        if opted_in:
            result = run()
            if site == "nces":
                assert (result / "boundary.shp").is_file()
            else:
                assert len(result) == 1
                assert result.geometry.iloc[0].equals(Point(-120, 38))
        else:
            with pytest.raises(error_type) as exc:
                run()
            assert isinstance(exc.value.__cause__, requests.exceptions.SSLError)
            assert list(downloads.glob("*.zip")) == []

    attempts = 2 if opted_in and site == "tiger-invalid-zip-retry" else 1
    assert forwarded == [opted_in] * attempts
    assert len(verification) == attempts * (2 if opted_in else 1)
    assert verification.count(False) == (attempts if opted_in else 0)
    assert all(value is not False for value in verification[::2])
    messages = [record.message for record in caplog.records if record.levelno == logging.ERROR]
    expected = "retrying WITHOUT verification" if opted_in else "refusing insecure retry"
    assert sum(expected in message for message in messages) == attempts


@pytest.mark.geo
@pytest.mark.parametrize("method,args", [
    ("get_available_years", ()),
    ("get_year_directory_contents", (2023,)),
    ("validate_download_url", ("https://example.test/boundary.zip",)),
])
def test_discovery_suppresses_only_opt_in_request_warnings(
    monkeypatch, method, args,
):
    monkeypatch.setenv("SIEGE_INSECURE_SSL", "1")
    with warnings.catch_warnings():
        spatial = _fresh_module("siege_utilities.geo.spatial_data")
    calls = []

    def get_response(url, **kwargs):
        calls.append(kwargs.get("verify", True))
        if calls[-1] is not False:
            raise requests.exceptions.SSLError("certificate verify failed")
        warnings.warn("Unverified HTTPS request to Census", InsecureRequestWarning)
        warnings.warn("Unrelated warning", UserWarning)
        response = requests.Response()
        response.status_code = 200
        response._content = b'<a href="TIGER2023/">TIGER2023</a><a href="COUNTY/">COUNTY</a>'
        response._content_consumed = True
        return response

    monkeypatch.setattr(spatial.requests, "get", get_response)
    discovery = spatial.CensusDirectoryDiscovery()
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        before = warnings.filters[:]
        getattr(discovery, method)(*args)
        assert warnings.filters == before
        warnings.warn("Unverified HTTPS request elsewhere", InsecureRequestWarning)

    assert calls == [True, False]
    assert [(str(w.message), w.category) for w in captured] == [
        ("Unrelated warning", UserWarning),
        ("Unverified HTTPS request elsewhere", InsecureRequestWarning),
    ]

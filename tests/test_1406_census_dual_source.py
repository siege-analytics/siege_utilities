"""Regression contracts for Census dual-source retrieval (#1406)."""

import asyncio
from io import BytesIO
import os
from pathlib import Path
import time
from unittest.mock import Mock

import httpx
import pandas as pd
import pytest
import requests

from siege_utilities.geo.census import api as api_module
from siege_utilities.geo.census.api import CensusAPI
from siege_utilities.geo.census.dual_source import (
    AlternationPolicy, ApiSource, BulkFileSource, DualSourceCensusClient,
    SUMMARY_FILE_BASE_URL,
)

FIXTURES = Path(__file__).parent / "data" / "summary_file"
TABLES = ("b01003", "b19013")
URLS = tuple(
    f"{SUMMARY_FILE_BASE_URL}/2022/table-based-SF/data/1YRData/acsdt1y2022-{table}.dat"
    for table in TABLES
)
REQUEST = dict(
    variables=["B01003_001E", "B19013_001E"], year=2022, dataset="acs1",
    geography="county", state_fips="06", include_moe=False,
)
# Independent API wire fixture; the bulk path uses Census pipe-delimited files.
API_ROWS = [
    ["NAME", "B01003_001E", "B19013_001E", "state", "county"],
    ["Alameda County, California", "1628997", "122159", "06", "001"],
    ["Los Angeles County, California", "9721138", "82516", "06", "037"],
    ["San Diego County, California", "3276208", "98928", "06", "073"],
]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(
        requests.sessions.Session, "request",
        Mock(side_effect=AssertionError("Live network is forbidden")),
    )

    async def forbidden(*args, **kwargs):
        raise AssertionError("Live network is forbidden")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)


@pytest.fixture
def wire(monkeypatch):
    """Intercept only HTTP transport, leaving both source implementations real."""
    def body_for(url):
        return (FIXTURES / url.rsplit("/", 1)[1]).read_bytes()

    bulk_get = Mock(side_effect=body_for)
    api_get = Mock(return_value=API_ROWS)

    def get(url, **kwargs):
        response = requests.Response()
        response.status_code = 200
        response.url = url
        if url.startswith(SUMMARY_FILE_BASE_URL):
            response.raw = BytesIO(bulk_get(url))
        else:
            response.json = lambda: api_get(url)
        return response

    monkeypatch.setattr(requests, "get", get)
    client_class = httpx.AsyncClient
    transport = httpx.MockTransport(lambda req: httpx.Response(200, content=bulk_get(str(req.url))))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: client_class(transport=transport, **kw))
    return api_get, bulk_get


@pytest.fixture
def sources(tmp_path):
    api = CensusAPI(api_key="test-secret", cache_dir=tmp_path / "api")
    return ApiSource(api), BulkFileSource(tmp_path / "bulk")


def test_bulk_provenance_lists_both_urls_and_cache_paths(sources, wire):
    _, bulk = sources
    first, live = bulk.fetch(**REQUEST)
    second, cached = BulkFileSource(bulk.cache_dir).fetch(**REQUEST)

    assert live.location == URLS  # Ticket falsifier: neither table can disappear.
    assert cached.location == URLS
    assert live.cache_hit is False
    assert cached.cache_hit is True
    assert live.cache_paths == ()
    assert cached.cache_paths == tuple(str(bulk.cache_dir / url.rsplit("/", 1)[1]) for url in URLS)
    assert cached.url_or_path == cached.cache_paths[0]
    pd.testing.assert_frame_equal(first, second)
    assert wire[1].call_count == 2


def test_partial_bulk_cache_hit_identifies_cached_table(sources, wire):
    _, bulk = sources
    bulk.fetch(**{**REQUEST, "variables": ["B01003_001E"]})
    _, provenance = bulk.fetch(**REQUEST)
    assert provenance.location == URLS
    assert provenance.cache_hit is True
    assert provenance.cache_paths == (str(bulk.cache_dir / "acsdt1y2022-b01003.dat"),)
    assert wire[1].call_count == 2


def test_api_provenance_distinguishes_live_and_parquet_cache(sources, wire):
    api, _ = sources
    _, live = api.fetch(**REQUEST)
    _, cached = api.fetch(**REQUEST)
    assert live.cache_hit is False
    assert cached.cache_hit is True
    assert live.location == cached.location
    assert "for=county:*" in live.location[0]
    assert "test-secret" not in repr(live)
    assert "test-secret" not in repr(cached)
    assert live.cache_paths == ()
    assert len(cached.cache_paths) == 1
    assert Path(cached.cache_paths[0]).is_file()
    assert wire[0].call_count == 1


@pytest.mark.parametrize("operation", ["stat", "unlink"])
def test_expired_parquet_concurrent_deletion_is_a_cache_miss(sources, wire, monkeypatch, operation):
    api, _ = sources
    api.fetch(**REQUEST)
    path, = api.api.cache_dir.glob("*.parquet")
    os.utime(path, (0, 0))
    original_exists = Path.exists
    monkeypatch.setattr(Path, "exists", lambda self: True if self == path else original_exists(self))
    original = getattr(Path, operation)
    raced = False

    def racing(self, *args, **kwargs):
        nonlocal raced
        if self == path and not raced:
            raced = True
            raise FileNotFoundError("another worker removed the expired key")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, operation, racing)
    _, provenance = api.fetch(**REQUEST)
    assert raced
    assert provenance.cache_hit is False
    assert wire[0].call_count == 2


def test_nation_returns_data_through_dual_client(sources, wire):
    api, bulk = sources
    wire[0].return_value = [
        ["NAME", "B01003_001E", "us"], ["United States", "333287557", "1"],
    ]
    request = {**REQUEST, "variables": ["B01003_001E"], "geography": "nation", "state_fips": None}
    frame, provenance = DualSourceCensusClient(api, bulk).fetch(**request)
    assert frame.to_dict("list") == {
        "GEOID": [""], "NAME": ["United States"], "B01003_001E": [333287557],
    }
    assert "for=us:1" in wire[0].call_args.args[0]
    assert provenance.source == "api"
    assert wire[1].call_count == 0


@pytest.mark.parametrize("filters", [{"state_fips": "06"}, {"county_fips": "037"}])
def test_nation_rejects_filters_before_transport(sources, wire, filters):
    with pytest.raises(ValueError, match="Nation geography does not accept state/county filters"):
        DualSourceCensusClient(*sources).fetch(**{
            **REQUEST, "geography": "nation", "state_fips": None, **filters,
        })
    assert wire[0].call_count == wire[1].call_count == 0


def test_consistent_shape_and_provenance_from_independent_wire_fixtures(sources, wire):
    api, bulk = sources
    api_frame, api_origin = DualSourceCensusClient(api, bulk).fetch(**REQUEST)
    wire[0].side_effect = requests.Timeout("force bulk fallback")
    api.api.clear_cache()
    # A fake clock is installed in the retry test; here avoid transport retries.
    api.api._make_request_with_retry = Mock(side_effect=requests.Timeout("force fallback"))
    bulk_frame, bulk_origin = DualSourceCensusClient(
        api, bulk, AlternationPolicy(max_api_attempts=1),
    ).fetch(**REQUEST)
    assert list(api_frame) == list(bulk_frame) == ["GEOID", "NAME", *REQUEST["variables"]]
    assert api_frame.shape == bulk_frame.shape == (3, 4)
    pd.testing.assert_frame_equal(api_frame.drop(columns="NAME"), bulk_frame.drop(columns="NAME"))
    assert api_frame.NAME.notna().all()
    assert bulk_frame.NAME.isna().all()
    assert api_origin.source == "api" and not api_origin.degraded
    assert bulk_origin.source == "bulk" and bulk_origin.degraded
    assert bulk_origin.location == URLS


class FakeClock:
    def __init__(self):
        self.now = 0
        self.sleeps = []

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def test_real_api_timeout_retry_stack_reaches_bulk_with_fake_clock(sources, wire, monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(api_module, "time", clock)
    wire[0].side_effect = requests.Timeout("transport timed out")
    frame, provenance = DualSourceCensusClient(
        *sources, AlternationPolicy(max_api_attempts=2),
    ).fetch(**REQUEST)
    assert frame.shape == (3, 4)
    assert wire[0].call_count == 2 * api_module.CENSUS_RETRY_ATTEMPTS
    assert clock.sleeps == [2 ** n for n in range(api_module.CENSUS_RETRY_ATTEMPTS)] * 2
    assert clock.now == sum(clock.sleeps)
    assert provenance.source == "bulk"
    assert provenance.attempts == 3 and provenance.degraded


@pytest.mark.parametrize("corruption", ["truncated", "same_size", "missing_checksum"])
def test_bulk_cache_integrity_failure_redownloads(sources, wire, corruption):
    _, bulk = sources
    first, _ = bulk.fetch(**REQUEST)
    path = bulk.cache_dir / "acsdt1y2022-b01003.dat"
    if corruption == "truncated":
        path.write_bytes(path.read_bytes().splitlines(keepends=True)[0])
    elif corruption == "same_size":
        path.write_bytes(path.read_bytes().replace(b"9721138", b"9999999"))
    else:
        for checksum in bulk.cache_dir.glob("*.sha256"):
            checksum.unlink()
    frame, provenance = BulkFileSource(bulk.cache_dir).fetch(**REQUEST)
    pd.testing.assert_frame_equal(first, frame)
    assert wire[1].call_count == (4 if corruption == "missing_checksum" else 3)
    assert provenance.location == URLS


def test_bulk_total_deadline_cancels_stalled_stream(tmp_path, monkeypatch):
    closed = []

    class StalledStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"GEO_ID|B01003_E001\n"
            await asyncio.sleep(10)
            yield b"0500000US06037|9721138\n"

        async def aclose(self):
            closed.append(True)

    client_class = httpx.AsyncClient
    transport = httpx.MockTransport(lambda req: httpx.Response(200, stream=StalledStream()))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: client_class(transport=transport, **kw))
    # Current develop consumes this complete response and never checks a deadline.
    response = requests.Response()
    response.status_code = 200
    response.raw = BytesIO(b"GEO_ID|B01003_E001\n0500000US06037|9721138\n")
    monkeypatch.setattr(requests, "get", Mock(return_value=response))
    source = BulkFileSource(tmp_path)
    source.total_timeout = 0.05
    started = time.monotonic()
    with pytest.raises(requests.Timeout, match="total download timeout"):
        source.fetch(**{**REQUEST, "variables": ["B01003_001E"]})
    assert time.monotonic() - started < 2
    assert closed
    assert list(tmp_path.iterdir()) == []

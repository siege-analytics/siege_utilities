"""Exercise the real Census transport and Summary File fallback for #1404."""

import json
import socket
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from siege_utilities.geo.census.api import CensusAPI
from siege_utilities.geo.census.dual_source import (
    AlternationPolicy,
    ApiSource,
    BulkFileSource,
    DualSourceCensusClient,
)
from siege_utilities.geo.census_api_client import (
    CensusAPIError,
    CensusRateLimitError,
    CensusServerError,
)


REQUEST = {
    "variables": ["B01001_001E"],
    "year": 2022,
    "dataset": "acs5",
    "geography": "county",
    "state_fips": "06",
    "county_fips": "037",
    "include_moe": False,
}
# Five transport attempts, with four 60-second waits, instead of 900 seconds.
RATE_LIMIT_WAIT_BOUND = 240


def http_response(status):
    response = requests.Response()
    response.status_code = status
    response.url = "https://api.census.gov/data/2022/acs/acs5"
    response._content = b"error: unknown variable 'B01001_999E'"
    return response


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(
        "requests.sessions.Session.request",
        Mock(side_effect=AssertionError("Live network is forbidden")),
    )


@pytest.fixture
def fake_clock(monkeypatch):
    sleeps = []
    monkeypatch.setattr("siege_utilities.geo.census.api.time.sleep", sleeps.append)
    return sleeps


@pytest.fixture
def client(tmp_path, settings):
    # A real per-test cache keeps the transport tests independent of Parquet.
    settings.CACHES = {"default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": str(tmp_path),
    }}
    api = CensusAPI(api_key="test-key", cache_backend="django")
    bulk_dir = tmp_path / "bulk"
    bulk_dir.mkdir()
    (bulk_dir / "acsdt5y2022-b01001.dat").write_text(
        "GEO_ID|B01001_E001\n0500000US06037|100\n", encoding="utf-8",
    )
    bulk = BulkFileSource(cache_dir=bulk_dir)
    bulk.fetch = Mock(wraps=bulk.fetch)
    return DualSourceCensusClient(ApiSource(api), bulk)


def assert_bulk_result(result, provenance, client):
    pd.testing.assert_frame_equal(
        result,
        pd.DataFrame({"GEOID": ["06037"], "NAME": [None], "B01001_001E": [100]}),
    )
    assert provenance.source == "bulk"
    assert provenance.degraded is True
    assert provenance.attempts == 2
    client.secondary.fetch.assert_called_once_with(**REQUEST)


@pytest.mark.parametrize("status", [500, 503, 599])
def test_server_error_falls_back(client, fake_clock, monkeypatch, status):
    get = Mock(return_value=http_response(status))
    monkeypatch.setattr("requests.get", get)

    result, provenance = client.fetch(**REQUEST)

    assert_bulk_result(result, provenance, client)
    assert get.call_count == 5
    assert fake_clock == [1, 2, 4, 8]


@pytest.mark.parametrize(
    "failure, error_type",
    [
        (http_response(503), CensusServerError),
        (requests.exceptions.ConnectionError("Connection refused"), CensusServerError),
        (requests.exceptions.Timeout("Read timed out"), CensusServerError),
        (http_response(429), CensusRateLimitError),
        (http_response(400), CensusAPIError),
    ],
    ids=["server", "connection", "timeout", "rate-limit", "client"],
)
def test_single_transport_attempt_never_sleeps(
    client, fake_clock, monkeypatch, failure, error_type,
):
    monkeypatch.setattr("siege_utilities.geo.census.api.CENSUS_RETRY_ATTEMPTS", 1)
    get = Mock(side_effect=[failure])
    monkeypatch.setattr("requests.get", get)

    with pytest.raises(error_type) as raised:
        client.primary.api.fetch_data(**REQUEST)

    assert type(raised.value) is error_type
    assert get.call_count == 1
    assert fake_clock == []


def test_server_fallback_can_be_disabled(client, fake_clock, monkeypatch):
    client.policy = AlternationPolicy(fallback_on=())
    get = Mock(return_value=http_response(503))
    monkeypatch.setattr("requests.get", get)

    with pytest.raises(CensusServerError):
        client.fetch(**REQUEST)

    assert get.call_count == 5
    assert fake_clock == [1, 2, 4, 8]
    client.secondary.fetch.assert_not_called()


@pytest.mark.parametrize("failures", [0, 4])
@pytest.mark.parametrize("status", [429, 503])
def test_api_success_within_transport_budget(
    client, fake_clock, monkeypatch, failures, status,
):
    success = http_response(200)
    success._content = json.dumps([
        ["NAME", "B01001_001E", "state", "county"],
        ["Los Angeles County, California", "100", "06", "037"],
    ]).encode("utf-8")
    get = Mock(side_effect=[http_response(status)] * failures + [success])
    monkeypatch.setattr("requests.get", get)

    result, provenance = client.fetch(**REQUEST)

    assert result.loc[0, "GEOID"] == "06037"
    assert result.loc[0, "B01001_001E"] == 100
    assert provenance.source == "api"
    assert provenance.degraded is False
    assert provenance.attempts == 1
    assert get.call_count == failures + 1
    assert fake_clock == ([60] * failures if status == 429 else [1, 2, 4, 8][:failures])
    client.secondary.fetch.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [
        requests.exceptions.ConnectionError("Connection refused"),
        requests.exceptions.ConnectionError(socket.gaierror("Name resolution failed")),
        requests.exceptions.Timeout("Read timed out"),
    ],
    ids=["connection", "dns", "timeout"],
)
def test_transport_error_falls_back(client, fake_clock, monkeypatch, error):
    get = Mock(side_effect=error)
    monkeypatch.setattr("requests.get", get)

    result, provenance = client.fetch(**REQUEST)

    assert_bulk_result(result, provenance, client)
    assert get.call_count == 5
    assert fake_clock == [1, 2, 4, 8]


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
def test_client_error_does_not_fall_back(client, fake_clock, monkeypatch, status):
    monkeypatch.setattr("requests.get", Mock(return_value=http_response(status)))

    with pytest.raises(CensusAPIError) as raised:
        client.fetch(**{**REQUEST, "variables": ["B01001_999E"]})

    assert type(raised.value) is CensusAPIError
    client.secondary.fetch.assert_not_called()


@pytest.mark.parametrize("source_budget", [None, 1, 7])
def test_sustained_rate_limit_has_bounded_wait(
    client, fake_clock, monkeypatch, source_budget,
):
    if source_budget is not None:
        client.policy = AlternationPolicy(max_api_attempts=source_budget)
    get = Mock(return_value=http_response(429))
    monkeypatch.setattr("requests.get", get)

    result, provenance = client.fetch(**REQUEST)

    assert sum(fake_clock) <= RATE_LIMIT_WAIT_BOUND
    assert fake_clock == [60, 60, 60, 60]
    assert get.call_count == 5
    assert_bulk_result(result, provenance, client)

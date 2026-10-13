"""Request URL credentials must not escape through diagnostics (#1400)."""

import logging
import traceback
from datetime import date

import pytest
import requests
import requests_mock as requests_mock_module
from urllib3.exceptions import MaxRetryError

from siege_utilities.analytics.instagram import (
    BASE_URL,
    InstagramConnector,
    SocialMediaAuthError,
    SocialMediaError,
    SocialMediaRateLimitError,
)
from siege_utilities.geo.census import api as census_api
from siege_utilities.geo.census_api_client import CensusAPIError
from siege_utilities.geo.providers.redistricting_data_hub import RDHClient


SECRET = "SENTINEL_SECRET_abc123"


@pytest.fixture(autouse=True)
def _force_log_capture(caplog):
    """Keep diagnostic assertions independent of ambient logging levels."""
    # requests-mock logs raw fixture URLs at DEBUG, outside client diagnostics.
    caplog.set_level(logging.INFO, logger="requests_mock.adapter")
    caplog.set_level(logging.DEBUG)


@pytest.fixture
def requests_mock():
    with requests_mock_module.Mocker(case_sensitive=True) as mocker:
        yield mocker


@pytest.fixture
def census(tmp_path, monkeypatch):
    monkeypatch.setattr(census_api, "CENSUS_RETRY_ATTEMPTS", 2)
    monkeypatch.setattr(census_api.time, "sleep", lambda _: None)
    return census_api.CensusAPI(api_key=SECRET, cache_dir=tmp_path)


@pytest.fixture
def rdh(tmp_path):
    with RDHClient(username="test@example.org", password=SECRET, cache_dir=tmp_path) as client:
        yield client


@pytest.fixture
def instagram():
    with InstagramConnector(
        SECRET, ig_user_id="123", retry_attempts=2, retry_backoff=0,
    ) as client:
        yield client


def assert_safe_diagnostics(exc, caplog):
    assert SECRET not in str(exc)
    assert SECRET not in caplog.text
    assert SECRET not in repr([(record.msg, record.args) for record in caplog.records])
    assert SECRET not in "".join(traceback.format_exception(exc))


@pytest.mark.parametrize("parameter", [
    "key", "password", "access_token", "token", "sig", "client_secret",
    "ACCESS_TOKEN", "%61ccess_token",
])
def test_census_request_error_redacts_query_values(census, requests_mock, caplog, parameter):
    url = census._build_url(["B01001_001E"], 2023, "acs5", "state", None, None)
    failed_url = f"https://api.census.gov/data?{parameter}={SECRET}&get=NAME&{parameter}={SECRET}"
    requests_mock.get(url, exc=requests.ConnectionError(
        MaxRetryError(None, failed_url, "connection refused"),
    ))

    with pytest.raises(CensusAPIError, match="Census API request failed") as caught:
        census._make_request_with_retry(url)

    assert_safe_diagnostics(caught.value, caplog)
    assert "Request failed" in caplog.text
    assert f"{parameter}=[REDACTED]&get=NAME" in str(caught.value)
    assert requests_mock.call_count == 2
    assert requests_mock.last_request.qs["key"] == [SECRET]


def test_census_http_error_redacts_key(census, requests_mock, caplog):
    url = census._build_url(["B01001_001E"], 2023, "acs5", "state", None, None)
    requests_mock.get(url, status_code=403)

    with pytest.raises(CensusAPIError, match="403 Client Error") as caught:
        census._make_request_with_retry(url)

    assert_safe_diagnostics(caught.value, caplog)
    assert "Request failed" in caplog.text


def test_census_timeout_redacts_exception_chain(census, requests_mock, caplog):
    url = census._build_url(["B01001_001E"], 2023, "acs5", "state", None, None)
    requests_mock.get(url, exc=requests.Timeout(f"Timed out requesting {url}"))

    with pytest.raises(CensusAPIError, match="timed out after 2 attempts") as caught:
        census._make_request_with_retry(url)

    assert_safe_diagnostics(caught.value, caplog)
    assert "Request timeout" in caplog.text


def test_census_parse_error_redacts_url(census, requests_mock, caplog, monkeypatch):
    url = census._build_url(["B01001_001E"], 2023, "acs5", "state", None, None)
    requests_mock.get(url, text="invalid JSON")

    def invalid_json(response, **kwargs):
        raise ValueError(f"Invalid JSON from {response.url}")

    monkeypatch.setattr(requests.Response, "json", invalid_json)
    with pytest.raises(CensusAPIError, match="Invalid API response") as caught:
        census._make_request_with_retry(url)

    assert_safe_diagnostics(caught.value, caplog)
    assert "Failed to parse API response" in caplog.text


@pytest.mark.parametrize("operation", ["list", "download"])
@pytest.mark.parametrize("failure", ["transport", "http"])
def test_rdh_request_error_redacts_password(rdh, requests_mock, caplog, operation, failure):
    caplog.set_level(logging.INFO)
    url = rdh.base_url if operation == "list" else "https://redistrictingdatahub.org/files/data.csv"
    failed_url = f"{url}?password={SECRET}&format=csv"
    response = (
        {"exc": requests.ConnectionError(MaxRetryError(None, failed_url, "connection refused"))}
        if failure == "transport" else {"status_code": 403}
    )
    requests_mock.get(url, **response)
    action = rdh.list_datasets if operation == "list" else lambda: rdh.download_dataset(url)
    download_error = requests.ConnectionError if failure == "transport" else requests.HTTPError
    error_type = ConnectionError if operation == "list" else download_error

    with pytest.raises(error_type, match="connection refused|403") as caught:
        action()

    assert_safe_diagnostics(caught.value, caplog)
    assert requests_mock.last_request.qs["password"] == [SECRET]


def test_rdh_stream_error_redacts_password(rdh, requests_mock, caplog, monkeypatch):
    url = f"https://redistrictingdatahub.org/files/data.csv?password={SECRET}"
    requests_mock.get(url, content=b"data")

    def failed_stream(response, **kwargs):
        raise requests.exceptions.ChunkedEncodingError(f"Broken stream from {response.url}")

    monkeypatch.setattr(requests.Response, "iter_content", failed_stream)
    with pytest.raises(requests.RequestException) as caught:
        rdh.download_dataset(url)

    assert_safe_diagnostics(caught.value, caplog)
    assert "RDH download failed" in caplog.text


def test_rdh_error_envelope_redacts_password(rdh, requests_mock, caplog):
    requests_mock.get(rdh.base_url, json={
        "code": "rest_cannot_access",
        "message": f"Access denied: {rdh.base_url}?password={SECRET}",
    })

    with pytest.raises(ValueError, match="RDH API error: Access denied") as caught:
        rdh.list_datasets()

    assert_safe_diagnostics(caught.value, caplog)


@pytest.mark.parametrize("use_cache", [False, True])
def test_rdh_download_logs_redact_query_password(rdh, requests_mock, caplog, use_cache):
    caplog.set_level(logging.INFO)
    url = f"https://redistrictingdatahub.org/files/data.csv?password={SECRET}&format=csv"
    requests_mock.get(url, content=b"id\n1\n")
    rdh.download_dataset(url, use_cache=False)
    rdh.download_dataset(url, use_cache=use_cache)

    assert "RDH: Downloading" in caplog.text
    assert "RDH: Saved" in caplog.text
    assert SECRET not in caplog.text
    assert "password=[REDACTED]&format=csv" in caplog.text


@pytest.mark.parametrize("trusted_host", [
    "redistrictingdatahub.org", "data.redistrictingdatahub.org",
    "nested.data.redistrictingdatahub.org", "REDISTRICTINGDATAHUB.ORG:443",
])
def test_rdh_auth_accepts_real_hosts_and_rejects_lookalike(rdh, trusted_host):
    assert rdh._auth_params("https://evilredistrictingdatahub.org/files/data.csv") == {}
    assert rdh._auth_params(f"https://{trusted_host}/files/data.csv") == {
        "username": "test@example.org", "password": SECRET,
    }
    assert rdh._auth_params("https://redistrictingdatahub.org.evil.example/files/data.csv") == {}
    assert rdh._auth_params("https://redistrictingdatahub.org@evil.example/files/data.csv") == {}


def test_rdh_download_does_not_authenticate_lookalike(rdh, requests_mock):
    url = "https://evilredistrictingdatahub.org/files/data.csv"
    requests_mock.get(url, content=b"id\n1\n")
    rdh.download_dataset(url)

    assert SECRET not in requests_mock.last_request.url
    assert "password" not in requests_mock.last_request.qs
    assert "username" not in requests_mock.last_request.qs


def test_instagram_request_error_redacts_token(instagram, requests_mock, caplog):
    url = f"{BASE_URL}/123?access_token={SECRET}&fields=id"
    requests_mock.get(requests_mock_module.ANY, exc=requests.ConnectionError(
        MaxRetryError(None, url, "connection refused"),
    ))

    with pytest.raises(SocialMediaError, match="failed after 2 attempts") as caught:
        instagram._request_url("GET", url)

    assert_safe_diagnostics(caught.value, caplog)
    assert "attempt 2/2 failed" in caplog.text
    assert requests_mock.call_count == 2


def test_instagram_auth_uses_bearer_header(instagram, requests_mock):
    requests_mock.get(f"{BASE_URL}/123", json={"id": "123", "username": "example"})
    instagram.authenticate()

    assert instagram.is_connected()
    assert SECRET not in requests_mock.last_request.url
    assert "access_token" not in requests_mock.last_request.qs
    assert requests_mock.last_request.headers["Authorization"] == f"Bearer {SECRET}"


@pytest.mark.parametrize("paging_base", [BASE_URL, "https://graph.facebook.com/v23.0"])
def test_instagram_paging_error_logs_redact_next_url(instagram, requests_mock, caplog, paging_base):
    first = f"{BASE_URL}/123/media"
    next_url = f"{paging_base}/123/media?after=cursor&access_token={SECRET}"

    def page_response(request, context):
        if "after" in request.qs:
            context.status_code = 503
            return {"error": {"message": "Temporarily unavailable"}}
        return {"data": [], "paging": {"next": next_url}}

    requests_mock.get(requests_mock_module.ANY, json=page_response)
    instagram._authenticated = True
    with pytest.raises(SocialMediaError, match="503") as caught:
        instagram.get_posts(date(2026, 1, 1), date(2026, 1, 31))

    assert_safe_diagnostics(caught.value, caplog)
    assert "after=cursor" in caplog.text
    assert "5xx 503" in caplog.text
    assert requests_mock.request_history[0].url.startswith(first)
    assert "access_token" not in requests_mock.last_request.qs
    assert requests_mock.last_request.headers["Authorization"] == f"Bearer {SECRET}"


def test_instagram_removes_token_from_url_and_params(instagram, requests_mock):
    requests_mock.get(requests_mock_module.ANY, json={"data": []})
    instagram._request_url(
        "GET", f"{BASE_URL}/123/media?after=cursor&access_token={SECRET}&access_token={SECRET}",
        params={"access_token": SECRET, "fields": "id"},
    )

    assert SECRET not in requests_mock.last_request.url
    assert requests_mock.last_request.qs == {"after": ["cursor"], "fields": ["id"]}
    assert requests_mock.last_request.headers["Authorization"] == f"Bearer {SECRET}"


@pytest.mark.parametrize("status,error_type", [
    (400, SocialMediaError), (401, SocialMediaAuthError),
    (403, SocialMediaAuthError), (429, SocialMediaRateLimitError),
    (503, SocialMediaError),
])
def test_instagram_status_error_redacts_url_and_body(instagram, requests_mock, caplog, status, error_type):
    url = f"{BASE_URL}/123?access_token={SECRET}&client_secret={SECRET}&after=cursor"
    requests_mock.get(requests_mock_module.ANY, status_code=status, json={
        "error": {"message": f"Request failed for {url}"},
    })

    with pytest.raises(error_type, match=f"{status}|rate limit") as caught:
        instagram._request_url("GET", url)

    assert_safe_diagnostics(caught.value, caplog)


@pytest.mark.parametrize("status", [200, 400, 401])
def test_instagram_non_json_error_redacts_url_and_body(instagram, requests_mock, caplog, status):
    url = f"{BASE_URL}/123?access_token={SECRET}"
    requests_mock.get(requests_mock_module.ANY, status_code=status, text=f"Invalid response from {url}")

    with pytest.raises(SocialMediaError, match="Instagram API") as caught:
        instagram._request_url("GET", url)

    assert_safe_diagnostics(caught.value, caplog)

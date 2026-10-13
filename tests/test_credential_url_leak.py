"""Request URL credentials must not escape through diagnostics (#1400)."""

import logging
import traceback
from datetime import date
from urllib.error import HTTPError, URLError

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
from siege_utilities.files import remote
from siege_utilities.geo.providers import tamu_batch
from siege_utilities.geo.providers.batch_geocoder import AddressInput


SECRET = "SENTINEL_SECRET_abc123"


@pytest.fixture(autouse=True)
def _force_log_capture(caplog):
    """Keep diagnostic assertions independent of ambient logging levels."""
    # requests-mock logs raw fixture URLs at DEBUG, outside client diagnostics.
    caplog.set_level(logging.INFO, logger="requests_mock.adapter")
    caplog.set_level(logging.DEBUG)


@pytest.fixture(autouse=True)
def enable_client_logging(monkeypatch, caplog, _force_log_capture):
    # Django's disable_existing_loggers must not make caplog assertions vacuous.
    for name in (census_api.__name__, remote.__name__, tamu_batch.__name__,
                 "siege_utilities.analytics.instagram", "siege_utilities"):
        monkeypatch.setattr(logging.getLogger(name), "disabled", False)
        caplog.set_level(logging.DEBUG, logger=name)


@pytest.fixture
def requests_mock():
    with requests_mock_module.Mocker(case_sensitive=True) as mocker:
        yield mocker


@pytest.fixture
def census(tmp_path, monkeypatch):
    monkeypatch.setattr(census_api, "CENSUS_RETRY_ATTEMPTS", 2)
    monkeypatch.setattr(census_api.time, "sleep", lambda _: None)
    client = census_api.CensusAPI(api_key=SECRET, cache_dir=tmp_path)
    # Construction may initialize Django and disable pre-existing loggers.
    monkeypatch.setattr(census_api.log, "disabled", False)
    return client


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
    assert SECRET not in caplog.text
    assert SECRET not in repr([(record.msg, record.args) for record in caplog.records])
    assert SECRET not in "".join(traceback.format_exception(exc))
    pending = [exc]
    seen = set()
    while pending:
        current = pending.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        assert SECRET not in str(current)
        assert SECRET not in repr(getattr(current, "args", ()))
        assert SECRET not in str(getattr(current, "url", ""))
        assert SECRET not in str(getattr(current, "full_url", ""))
        assert SECRET not in str(getattr(current, "doc", ""))
        for attribute in ("__cause__", "__context__", "request", "response", "reason"):
            pending.append(getattr(current, attribute, None))


@pytest.mark.parametrize("parameter", [
    "key", "password", "access_token", "token", "sig", "client_secret",
    "ACCESS_TOKEN", "%61ccess_token",
    "apiKey", "api_key", "APIKEY", "secret", "X-Amz-Signature", "auth",
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
@pytest.mark.parametrize("failure", ["transport", "http403", "http404"])
def test_rdh_request_error_redacts_password(rdh, requests_mock, caplog, operation, failure):
    caplog.set_level(logging.INFO)
    url = rdh.base_url if operation == "list" else "https://redistrictingdatahub.org/files/data.csv"
    failed_url = f"{url}?password={SECRET}&format=csv"
    response = (
        {"exc": requests.ConnectionError(
            MaxRetryError(None, failed_url, "connection refused"),
            request=requests.Request("GET", failed_url).prepare(),
        )}
        if failure == "transport" else {"status_code": int(failure[4:])}
    )
    requests_mock.get(url, **response)
    action = rdh.list_datasets if operation == "list" else lambda: rdh.download_dataset(url)
    download_error = requests.ConnectionError if failure == "transport" else requests.HTTPError
    error_type = ConnectionError if operation == "list" else download_error

    with pytest.raises(error_type, match="connection refused|403|404") as caught:
        action()

    assert_safe_diagnostics(caught.value, caplog)
    assert requests_mock.last_request.qs["password"] == [SECRET]
    assert type(caught.value) is error_type
    assert caught.value.__context__ is None
    assert getattr(caught.value, "request", None) is None
    assert getattr(caught.value, "response", None) is None


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


@pytest.mark.parametrize("parameter", [
    "key", "password", "access_token", "token", "apiKey", "apikey", "api_key",
    "API_KEY", "%61piKey", "secret", "SECRET", "sig", "X-Amz-Signature",
    "client_secret", "auth",
])
def test_redact_url_secrets_sensitive_parameters(parameter):
    from siege_utilities.core._http import redact_url_secrets

    assert redact_url_secrets(f"https://h/p?{parameter}=S&x=1") == (
        f"https://h/p?{parameter}=[REDACTED]&x=1"
    )


@pytest.mark.parametrize("failure", ["http", "transport", "timeout", "stream", "ssl"])
@pytest.mark.parametrize("ssl_retry", [False, True])
def test_remote_download_error_redacts_token(
    tmp_path, requests_mock, caplog, monkeypatch, failure, ssl_retry,
):
    caplog.set_level(logging.INFO)
    url = f"https://example.org/f.zip?token={SECRET}"
    request = requests.Request("GET", url).prepare()
    errors = {
        "http": {"status_code": 403, "reason": f"Forbidden for {url}"},
        "transport": {"exc": requests.ConnectionError(
            MaxRetryError(None, url, "connection refused"), request=request,
        )},
        "timeout": {"exc": requests.Timeout(f"Timed out: {url}", request=request)},
        "ssl": {"exc": requests.exceptions.SSLError(f"SSL failed: {url}", request=request)},
        "stream": {"content": b"data"},
    }
    responses = [errors[failure]]
    if ssl_retry:
        responses.insert(0, {"exc": requests.exceptions.SSLError(f"SSL failed: {url}")})
    requests_mock.get(url, responses)
    if failure == "stream":
        def failed_stream(response, **kwargs):
            raise requests.exceptions.ChunkedEncodingError(
                f"Broken stream: {response.url}", response=response,
            )
        monkeypatch.setattr(requests.Response, "iter_content", failed_stream)

    with pytest.raises((ConnectionError, requests.RequestException)) as caught:
        remote.download_file(url, tmp_path / "f.zip")

    assert_safe_diagnostics(caught.value, caplog)
    assert "Downloading" in caplog.text
    assert "token=[REDACTED]" in caplog.text
    assert requests_mock.call_count == (2 if failure == "ssl" else 1 + ssl_retry)
    assert requests_mock.last_request.qs["token"] == [SECRET]


@pytest.mark.parametrize("ssl_retry", [False, True])
def test_remote_download_success_redacts_token(tmp_path, requests_mock, caplog, ssl_retry):
    caplog.set_level(logging.INFO)
    url = f"https://example.org/f.zip?token={SECRET}"
    responses = [{"content": b"data"}]
    if ssl_retry:
        responses.insert(0, {"exc": requests.exceptions.SSLError(f"SSL failed: {url}")})
    requests_mock.get(url, responses)

    result = remote.download_file(url, tmp_path / "f.zip")

    assert result == str(tmp_path / "f.zip")
    assert (tmp_path / "f.zip").read_bytes() == b"data"
    assert_safe_diagnostics(None, caplog)
    assert "Successfully downloaded" in caplog.text


@pytest.mark.parametrize("failure", ["http", "transport"])
def test_remote_retry_error_redacts_token(tmp_path, requests_mock, caplog, failure):
    caplog.set_level(logging.INFO)
    url = f"https://example.org/f.zip?token={SECRET}"
    response = ({"status_code": 403} if failure == "http" else
                {"exc": requests.ConnectionError(f"Connection refused: {url}")})
    requests_mock.get(url, **response)
    with pytest.raises(ConnectionError, match="failed after 2 attempts") as caught:
        remote.download_file_with_retry(url, tmp_path / "f.zip", max_retries=1, retry_delay=0)
    assert_safe_diagnostics(caught.value, caplog)
    assert "Retry attempt" in caplog.text
    assert "Download attempt" in caplog.text


@pytest.mark.parametrize("failure", ["http", "transport"])
def test_remote_file_info_error_redacts_token(requests_mock, caplog, failure):
    caplog.set_level(logging.DEBUG)
    url = f"https://example.org/f.zip?token={SECRET}"
    response = ({"status_code": 403} if failure == "http" else
                {"exc": requests.ConnectionError(f"Connection refused: {url}")})
    requests_mock.head(url, **response)
    with pytest.raises((ConnectionError, requests.RequestException)) as caught:
        remote.get_file_info(url)
    assert_safe_diagnostics(caught.value, caplog)
    assert "Getting file info" in caplog.text


def test_remote_file_info_success_redacts_token(requests_mock, caplog):
    caplog.set_level(logging.DEBUG)
    url = f"https://example.org/f.zip?token={SECRET}"
    requests_mock.head(url, headers={"content-length": "3"})
    info = remote.get_file_info(url)
    assert info["url"] == url
    assert info["size"] == 3
    assert_safe_diagnostics(None, caplog)
    assert "File info for" in caplog.text


def test_remote_invalid_filename_redacts_token(tmp_path, caplog):
    with pytest.raises(ValueError, match="Could not extract filename") as caught:
        remote.generate_local_path_from_url(f"https://example.org/?token={SECRET}", tmp_path)
    assert_safe_diagnostics(caught.value, caplog)


def test_remote_is_downloadable_error_redacts_token(requests_mock, caplog):
    url = f"https://example.org/f.zip?token={SECRET}"
    requests_mock.head(url, exc=requests.ConnectionError(f"HEAD failed: {url}"))
    requests_mock.get(url, exc=requests.ConnectionError(f"GET failed: {url}"))
    assert remote.is_downloadable(url) is False
    assert_safe_diagnostics(None, caplog)
    assert "file info check failed" in caplog.text
    assert "GET request failed" in caplog.text


def test_remote_malformed_header_redacts_token(requests_mock, caplog):
    url = f"https://example.org/f.zip?token={SECRET}"
    requests_mock.head(url, headers={"content-length": url})
    assert remote.get_file_info(url)["size"] == 0
    assert_safe_diagnostics(None, caplog)
    assert "Malformed Content-Length" in caplog.text


@pytest.mark.parametrize("failure", ["http", "transport", "parse"])
def test_tamu_request_error_redacts_api_key(monkeypatch, caplog, failure):
    client = tamu_batch.TAMUBatchGeocoder(api_key=SECRET, rate_limit=0, max_retries=1)
    addr = AddressInput(street="123 Main St", city="Chicago", state="IL", input_id="test")
    calls = []

    def failing_urlopen(request, timeout):
        calls.append(request)
        url = request.full_url
        if failure == "http":
            raise HTTPError(url, 403, f"Forbidden for {url}", {}, None)
        if failure == "transport":
            raise URLError(f"Connection refused for {url}")
        raise ValueError(f"Invalid response from {url}")

    monkeypatch.setattr(tamu_batch.urllib.request, "urlopen", failing_urlopen)
    with pytest.raises(Exception, match="Forbidden|Connection refused|Invalid response") as caught:
        client._tamu_request(addr)
    result = client.geocode([addr])

    assert_safe_diagnostics(caught.value, caplog)
    assert "TAMU geocode failed" in caplog.text
    assert "apiKey=[REDACTED]" in caplog.text
    assert len(calls) == 4
    assert result.total == 1
    assert not result.results[0].matched


def test_tamu_batch_warning_redacts_api_key(monkeypatch, caplog):
    client = tamu_batch.TAMUBatchGeocoder(api_key=SECRET, rate_limit=0)

    def failed_request(addr):
        raise URLError(f"Failed: https://h/p?apiKey={SECRET}")

    monkeypatch.setattr(client, "_tamu_request", failed_request)
    result = client.geocode(["123 Main St"])
    assert result.total == 1
    assert not result.results[0].matched
    assert_safe_diagnostics(None, caplog)
    assert "TAMU geocode failed" in caplog.text
    assert "apiKey=[REDACTED]" in caplog.text

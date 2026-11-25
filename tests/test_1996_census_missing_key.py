"""Census API key redirects raise CensusAPIKeyError without retrying (refs #1996).

The Census API answers a data request that has no key, or a rejected key,
with a 302 to an HTML page (``/data/missing_key.html`` or
``/data/invalid_key.html``). ``requests`` follows the redirect, so parsing
the page as JSON gave an opaque ``Expecting value: line 1 column 1`` error.
"""

import logging
import traceback
from unittest.mock import patch
from urllib.parse import quote

import pandas as pd
import pytest
import requests

from siege_utilities.geo.census import api as census_api
from siege_utilities.geo.census.api import CensusAPI
from siege_utilities.geo.census_api_client import CensusAPIError, CensusAPIKeyError

LOGGER = "siege_utilities.geo.census.api"
DATA_URL = "https://api.census.gov/data/2023/acs/acs5?get=NAME,B01001_001E&for=state:01"


def _response(url, *, status=200, body=b"<html><body>Missing key</body></html>",
              content_type="text/html", history=()):
    response = requests.Response()
    response.status_code = status
    response._content = body
    response.headers["Content-Type"] = content_type
    response.url = url
    response.history = list(history)
    return response


def _redirected_to(page, request_url=DATA_URL):
    redirect = _response(request_url, status=302, body=b"",
                         content_type="text/html")
    redirect.headers["Location"] = f"https://api.census.gov/data/{page}"
    return _response(f"https://api.census.gov/data/{page}", history=[redirect])


@pytest.fixture
def client(tmp_path):
    with patch.object(CensusAPI, "_resolve_api_key", return_value=None):
        return CensusAPI(cache_dir=tmp_path)


@pytest.fixture
def calls(monkeypatch):
    made = []

    def install(response):
        def fake_get(url, timeout=None, **kwargs):
            made.append(url)
            return response
        monkeypatch.setattr(census_api.requests, "get", fake_get)
        monkeypatch.setattr(census_api.time, "sleep", lambda seconds: None)
        return made

    return install


def test_missing_key_redirect_raises_key_required_without_retry(client, calls):
    made = calls(_redirected_to("missing_key.html"))

    with pytest.raises(CensusAPIKeyError, match="Census API key required") as raised:
        client._make_request_with_retry(DATA_URL)

    assert "CENSUS_API_KEY" in str(raised.value)
    assert made == [DATA_URL]


def test_invalid_key_redirect_raises_key_rejected_without_retry(client, calls):
    keyed_url = DATA_URL + "&key=SENTINEL_SECRETVALUE_1996"
    made = calls(_redirected_to("invalid_key.html", request_url=keyed_url))

    with pytest.raises(CensusAPIKeyError, match="Census API key rejected") as raised:
        client._make_request_with_retry(keyed_url)

    assert "SECRETVALUE" not in str(raised.value)
    assert made == [keyed_url]


CORE = "9f8e7d6c5b4a39281706f5e4d3c2b1a0deadbeef"  # 40 hex, like a Census key
_A, _B = CORE[:20], CORE[20:]
MALFORMED_KEYS = {
    "plain": CORE,
    "double_quoted": f'"{CORE}"',
    "single_quoted": f"'{CORE}'",
    "leading_space": f" {CORE}",
    "trailing_newline": f"{CORE}\n",
    "inner_space": f"{_A} {_B}",
    "angle_brackets": f"<{CORE}>",
    "key_equals_prefix": f"key={CORE}",
    "inner_ampersand": f"{_A}&{_B}",
    "inner_hash": f"{_A}#{_B}",
    "inner_percent": f"{_A}%{_B}",
    "inner_question_mark": f"{_A}?{_B}",
    "parenthesised": f"({CORE})",
    "bearer_prefix": f"Bearer {CORE}",
}


def _key_fragments(text):
    """Every run of 8 or more consecutive key characters found in text."""
    return [CORE[i:i + 8] for i in range(len(CORE) - 7) if CORE[i:i + 8] in text]


def _surfaces(error, records):
    surfaces = {
        "str": str(error),
        "repr": repr(error),
        "args": repr(error.args),
        "traceback": "".join(traceback.format_exception(error)),
    }
    for index, record in enumerate(records):
        surfaces[f"log[{index}]"] = record.getMessage()
    return surfaces


@pytest.mark.parametrize("encode", [False, True], ids=["raw", "percent-encoded"])
@pytest.mark.parametrize("shape", list(MALFORMED_KEYS))
def test_invalid_key_error_carries_no_part_of_a_malformed_key(client, calls, caplog, shape, encode):
    key = MALFORMED_KEYS[shape]
    keyed_url = DATA_URL + "&key=" + (quote(key, safe="") if encode else key)
    calls(_redirected_to("invalid_key.html", request_url=keyed_url))

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(CensusAPIKeyError, match="Census API key rejected") as raised:
            client._make_request_with_retry(keyed_url)

    error = raised.value
    leaks = {name: _key_fragments(text) for name, text in _surfaces(error, caplog.records).items()}
    assert {name: found for name, found in leaks.items() if found} == {}
    assert error.__cause__ is None
    assert error.__context__ is None
    assert str(error).endswith("Request: https://api.census.gov/data/2023/acs/acs5")


class _NoProfileKey:
    def get_api_key(self, name):
        return None


@pytest.mark.parametrize("route", ["explicit", "env"])
def test_a_key_with_a_question_mark_does_not_leak_through_fetch_data(tmp_path, monkeypatch, caplog, route):
    """The key reaches the URL through _resolve_api_key and _build_url.

    The message cuts the request URL at its first "?", which starts the query;
    the key always comes after it, so a "?" inside the key changes nothing.
    """
    key = MALFORMED_KEYS["inner_question_mark"]
    monkeypatch.setattr(census_api, "get_user_config", lambda: _NoProfileKey())
    monkeypatch.setattr(census_api.time, "sleep", lambda seconds: None)
    made = []

    def fake_get(url, timeout=None, **kwargs):
        made.append(url)
        redirect = _response(url, status=302, body=b"")
        redirect.headers["Location"] = "https://api.census.gov/data/invalid_key.html"
        return _response("https://api.census.gov/data/invalid_key.html", history=[redirect])

    monkeypatch.setattr(census_api.requests, "get", fake_get)
    if route == "env":
        monkeypatch.setenv("CENSUS_API_KEY", key)
        explicit_key = None
    else:
        monkeypatch.delenv("CENSUS_API_KEY", raising=False)
        explicit_key = key

    with caplog.at_level(logging.DEBUG):
        client = CensusAPI(api_key=explicit_key, cache_dir=tmp_path)
        assert client.api_key == key
        with pytest.raises(CensusAPIKeyError, match="Census API key rejected") as raised:
            client.fetch_data("B01001_001E", 2023, geography="state", include_moe=False)

    assert len(made) == 1 and made[0].endswith("&key=" + key)
    error = raised.value
    leaks = {name: _key_fragments(text) for name, text in _surfaces(error, caplog.records).items()}
    assert {name: found for name, found in leaks.items() if found} == {}
    assert error.__cause__ is None
    assert error.__context__ is None
    assert str(error).endswith("Request: https://api.census.gov/data/2023/acs/acs5")


@pytest.mark.parametrize("final_url", [
    "https://api.census.gov/data/missing_key.html/extra.json",
    "https://api.census.gov/data/not_a_missing_key.html",
    "https://api.census.gov/data/not_an_invalid_key.html",
], ids=["page_name_mid_path", "page_name_suffix", "invalid_page_name_suffix"])
def test_a_path_that_only_resembles_a_key_page_is_not_a_key_redirect(client, calls, final_url):
    """Detection matches the whole last path segment, from its leading "/"."""
    calls(_response(final_url, body=b"<html>other</html>"))

    with pytest.raises(CensusAPIError, match="Invalid API response") as raised:
        client._make_request_with_retry(DATA_URL)

    assert not isinstance(raised.value, CensusAPIKeyError)


def test_key_redirect_is_detected_from_the_redirect_hop_alone(client, calls):
    redirect = _response(DATA_URL, status=302, body=b"", content_type="text/html")
    redirect.headers["Location"] = "/data/missing_key.html"
    calls(_response("https://api.census.gov/data/landing", history=[redirect]))

    with pytest.raises(CensusAPIKeyError, match="Census API key required"):
        client._make_request_with_retry(DATA_URL)


def test_key_redirect_is_detected_from_the_final_url_alone(client, calls):
    calls(_response("https://api.census.gov/data/invalid_key.html"))

    with pytest.raises(CensusAPIKeyError, match="Census API key rejected"):
        client._make_request_with_retry(DATA_URL)


def test_page_name_in_the_query_string_is_not_a_key_redirect(client, calls):
    url = DATA_URL + "&get=X/missing_key.html"
    body = b'[["NAME","state"],["Alabama","01"]]'
    calls(_response(url, body=body, content_type="application/json"))

    frame = client._make_request_with_retry(url)

    assert frame.iloc[0].tolist() == ["Alabama", "01"]


def test_genuine_json_response_still_parses(client, calls):
    body = b'[["NAME","B01001_001E","state"],["Alabama","5108468","01"]]'
    calls(_response(DATA_URL, body=body, content_type="application/json;charset=utf-8"))

    frame = client._make_request_with_retry(DATA_URL)

    assert isinstance(frame, pd.DataFrame)
    assert list(frame.columns) == ["NAME", "B01001_001E", "state"]
    assert frame.iloc[0].tolist() == ["Alabama", "5108468", "01"]


def test_non_json_page_that_is_not_a_key_page_is_still_a_parse_error(client, calls):
    made = calls(_response(DATA_URL, body=b"<html>maintenance</html>"))

    with pytest.raises(CensusAPIError, match="Invalid API response") as raised:
        client._make_request_with_retry(DATA_URL)

    assert not isinstance(raised.value, CensusAPIKeyError)
    assert "content type 'text/html'" in str(raised.value)
    assert made == [DATA_URL]


def test_no_key_warning_says_a_key_is_needed(tmp_path, caplog):
    with patch.object(CensusAPI, "_resolve_api_key", return_value=None):
        with caplog.at_level(logging.WARNING, logger=LOGGER):
            CensusAPI(cache_dir=tmp_path)

    (warning,) = [r.getMessage() for r in caplog.records
                  if r.name == LOGGER and "No Census API key configured" in r.getMessage()]
    assert "will still work" not in warning
    assert "CensusAPIKeyError" in warning
    assert "CENSUS_API_KEY" in warning


def test_no_key_warning_promises_no_keyless_allowance(tmp_path, caplog):
    with patch.object(CensusAPI, "_resolve_api_key", return_value=None):
        with caplog.at_level(logging.WARNING, logger=LOGGER):
            CensusAPI(cache_dir=tmp_path)

    (warning,) = [r.getMessage() for r in caplog.records
                  if r.name == LOGGER and "No Census API key configured" in r.getMessage()]
    assert "500 requests" not in warning
    assert "without one" not in warning.split("CensusAPIKeyError", 1)[1]
    assert "50,000 requests a day" in warning

"""Tests for VistaSocialConnector (issue #306).

The endpoint *paths* this connector wraps are best-known and
unverified against Vista Social's private API docs. The tests below
verify the auth header, retry logic, error handling, and parameter
construction — i.e. everything we *can* validate without hitting the
real API.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from siege_utilities.analytics.vista_social import (
    DEFAULT_BASE_URL,
    VistaSocialAuthError,
    VistaSocialConnector,
    VistaSocialError,
    VistaSocialRateLimitError,
    VistaSocialResponse,
)


TEST_TOKEN = "vs_test_token_abcd1234"  # noqa: S105 — test fixture


# ---------------------------------------------------------------------------
# Construction + auth header
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_token_required(self):
        with pytest.raises(ValueError, match="api_token"):
            VistaSocialConnector(api_token="")

    def test_auth_header_set(self):
        c = VistaSocialConnector(api_token=TEST_TOKEN)
        assert c._session.headers["Authorization"] == f"Bearer {TEST_TOKEN}"
        assert c._session.headers["Accept"] == "application/json"

    def test_default_base_url(self):
        c = VistaSocialConnector(api_token=TEST_TOKEN)
        assert c._base_url == DEFAULT_BASE_URL

    def test_custom_base_url_strips_trailing_slash(self):
        c = VistaSocialConnector(api_token=TEST_TOKEN, base_url="https://custom/")
        assert c._base_url == "https://custom"

    def test_retry_attempts_floor_at_one(self):
        c = VistaSocialConnector(api_token=TEST_TOKEN, retry_attempts=0)
        assert c._retry_attempts == 1


# ---------------------------------------------------------------------------
# _request — HTTP plumbing
# ---------------------------------------------------------------------------

def _ok_response(json_body=None, status=200, headers=None):
    r = MagicMock()
    r.status_code = status
    r.content = b'{"data": []}' if json_body is None else b'{"x": 1}'
    r.json.return_value = json_body if json_body is not None else {"data": []}
    r.headers = headers or {}
    r.text = ""
    return r


class TestRequest:
    def test_get_success_returns_response(self):
        c = VistaSocialConnector(api_token=TEST_TOKEN)
        with patch.object(c._session, "request",
                          return_value=_ok_response({"data": [{"id": "1"}]})) as mock_req:
            resp = c._request("GET", "/v1/accounts")
        assert isinstance(resp, VistaSocialResponse)
        assert resp.status_code == 200
        assert resp.data == {"data": [{"id": "1"}]}
        mock_req.assert_called_once()
        # URL is fully qualified, leading slash on path is fine.
        kwargs = mock_req.call_args.kwargs
        assert kwargs["timeout"] == c._timeout
        # `requests.Session.request` got method + url positionally; check both.
        args = mock_req.call_args.args
        assert args[0] == "GET"
        assert args[1] == f"{DEFAULT_BASE_URL}/v1/accounts"

    def test_401_raises_auth_error(self):
        c = VistaSocialConnector(api_token=TEST_TOKEN, retry_attempts=2)
        with patch.object(c._session, "request",
                          return_value=_ok_response(status=401)) as mock_req:
            with pytest.raises(VistaSocialAuthError, match="api_token"):
                c._request("GET", "/v1/accounts")
        # Auth failure must NOT be retried.
        mock_req.assert_called_once()

    def test_429_raises_rate_limit_error(self):
        c = VistaSocialConnector(api_token=TEST_TOKEN, retry_attempts=2)
        resp = _ok_response(status=429, headers={"Retry-After": "30"})
        with patch.object(c._session, "request", return_value=resp) as mock_req:
            with pytest.raises(VistaSocialRateLimitError, match="Retry-After: 30"):
                c._request("GET", "/v1/accounts")
        # 429 is intentionally NOT retried — caller backs off.
        mock_req.assert_called_once()

    def test_500_retries_then_raises(self):
        c = VistaSocialConnector(
            api_token=TEST_TOKEN,
            retry_attempts=2,
            retry_backoff=1.0,
        )
        with patch.object(c._session, "request",
                          return_value=_ok_response(status=500)) as mock_req, \
                patch("siege_utilities.analytics.vista_social.time.sleep"):
            with pytest.raises(VistaSocialError, match="500"):
                c._request("GET", "/v1/accounts")
        assert mock_req.call_count == 2

    def test_400_does_not_retry(self):
        c = VistaSocialConnector(api_token=TEST_TOKEN, retry_attempts=3)
        bad_resp = _ok_response(status=400)
        bad_resp.text = "missing required field"
        with patch.object(c._session, "request", return_value=bad_resp) as mock_req:
            with pytest.raises(VistaSocialError, match="400"):
                c._request("GET", "/v1/accounts")
        mock_req.assert_called_once()

    def test_transport_error_retries(self):
        import requests as _r
        c = VistaSocialConnector(
            api_token=TEST_TOKEN, retry_attempts=3, retry_backoff=1.0,
        )
        with patch.object(c._session, "request",
                          side_effect=_r.exceptions.ConnectionError("nope")) as mock_req, \
                patch("siege_utilities.analytics.vista_social.time.sleep"):
            with pytest.raises(VistaSocialError, match="3 attempts"):
                c._request("GET", "/v1/accounts")
        assert mock_req.call_count == 3

    def test_recovers_after_transient_500(self):
        c = VistaSocialConnector(
            api_token=TEST_TOKEN, retry_attempts=3, retry_backoff=1.0,
        )
        bad = _ok_response(status=500)
        good = _ok_response({"data": [{"id": "ok"}]})
        with patch.object(c._session, "request",
                          side_effect=[bad, good]) as mock_req, \
                patch("siege_utilities.analytics.vista_social.time.sleep"):
            resp = c._request("GET", "/v1/accounts")
        assert resp.data == {"data": [{"id": "ok"}]}
        assert mock_req.call_count == 2


# ---------------------------------------------------------------------------
# High-level methods — verify URL/params, not endpoint correctness
# ---------------------------------------------------------------------------

class TestHighLevelMethods:
    def test_list_accounts_calls_correct_path(self):
        c = VistaSocialConnector(api_token=TEST_TOKEN)
        with patch.object(c._session, "request",
                          return_value=_ok_response({"data": [{"id": "a1"}, {"id": "a2"}]})) as mock_req:
            accounts = c.list_accounts()
        assert accounts == [{"id": "a1"}, {"id": "a2"}]
        args = mock_req.call_args.args
        assert args[0] == "GET"
        assert args[1].endswith("/v1/accounts")

    def test_list_accounts_empty_returns_empty_list(self):
        c = VistaSocialConnector(api_token=TEST_TOKEN)
        with patch.object(c._session, "request",
                          return_value=_ok_response({"data": []})):
            assert c.list_accounts() == []

    def test_list_profiles_requires_account_id(self):
        c = VistaSocialConnector(api_token=TEST_TOKEN)
        with pytest.raises(ValueError, match="account_id"):
            c.list_profiles("")

    def test_list_profiles_uses_path_segment(self):
        c = VistaSocialConnector(api_token=TEST_TOKEN)
        with patch.object(c._session, "request",
                          return_value=_ok_response({"data": []})) as mock_req:
            c.list_profiles("acc_123")
        args = mock_req.call_args.args
        assert args[1].endswith("/v1/accounts/acc_123/profiles")

    def test_get_account_analytics_passes_params(self):
        c = VistaSocialConnector(api_token=TEST_TOKEN)
        with patch.object(c._session, "request",
                          return_value=_ok_response({"impressions": 42})) as mock_req:
            data = c.get_account_analytics(
                account_id="acc_123",
                start_date="2026-01-01",
                end_date="2026-01-31",
                metrics=["impressions", "engagements"],
            )
        assert data == {"impressions": 42}
        kwargs = mock_req.call_args.kwargs
        assert kwargs["params"] == {
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
            "metrics": "impressions,engagements",
        }

    def test_get_account_analytics_omits_metrics_when_none(self):
        c = VistaSocialConnector(api_token=TEST_TOKEN)
        with patch.object(c._session, "request",
                          return_value=_ok_response({})) as mock_req:
            c.get_account_analytics(
                account_id="acc_123",
                start_date="2026-01-01",
                end_date="2026-01-31",
            )
        params = mock_req.call_args.kwargs["params"]
        assert "metrics" not in params

    def test_list_posts_optional_dates(self):
        c = VistaSocialConnector(api_token=TEST_TOKEN)
        with patch.object(c._session, "request",
                          return_value=_ok_response({"data": []})) as mock_req:
            c.list_posts("acc_123", start_date="2026-01-01", limit=50)
        params = mock_req.call_args.kwargs["params"]
        assert params == {"limit": 50, "start_date": "2026-01-01"}

    def test_list_posts_requires_account_id(self):
        c = VistaSocialConnector(api_token=TEST_TOKEN)
        with pytest.raises(ValueError, match="account_id"):
            c.list_posts("")


class TestNonJsonBody:
    """A 2xx with non-JSON body must raise rather than silently empty
    (Phase-3 silent-swallow discipline)."""

    def test_non_json_body_raises(self):
        c = VistaSocialConnector(api_token=TEST_TOKEN)
        bad = MagicMock()
        bad.status_code = 200
        bad.content = b"<html>oops</html>"
        bad.json.side_effect = ValueError("Expecting value")
        bad.headers = {}
        bad.text = "<html>oops</html>"
        with patch.object(c._session, "request", return_value=bad):
            with pytest.raises(VistaSocialError, match="non-JSON body"):
                c._request("GET", "/v1/accounts")

    def test_empty_body_ok(self):
        """204 No Content — empty body returns empty data, not an error."""
        c = VistaSocialConnector(api_token=TEST_TOKEN)
        empty = MagicMock()
        empty.status_code = 204
        empty.content = b""
        empty.headers = {}
        with patch.object(c._session, "request", return_value=empty):
            resp = c._request("GET", "/v1/accounts")
        assert resp.status_code == 204
        assert resp.data == {}

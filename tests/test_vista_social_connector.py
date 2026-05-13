"""Tests for siege_utilities.analytics.vista_social.

The connector ships against an undocumented public API; these tests
pin the well-tested ``_request`` plumbing and the auth / rate-limit
/ error-translation behavior -- that's the part that's correct
regardless of which endpoint paths Vista Social actually exposes.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def _patch_requests(monkeypatch):
    from siege_utilities.analytics import vista_social as mod

    fake_requests = MagicMock()
    fake_session = MagicMock()
    fake_session.headers = {}
    fake_requests.Session.return_value = fake_session
    # Real exception classes so isinstance checks work
    fake_requests.exceptions.RequestException = Exception
    monkeypatch.setattr(mod, "requests", fake_requests, raising=False)
    monkeypatch.setattr(mod, "REQUESTS_AVAILABLE", True)
    return {"requests": fake_requests, "session": fake_session}


def test_init_requires_api_token():
    from siege_utilities.analytics.vista_social import VistaSocialConnector

    with pytest.raises(ValueError, match="api_token"):
        VistaSocialConnector(api_token="")


def test_init_sets_bearer_header(_patch_requests):
    from siege_utilities.analytics.vista_social import VistaSocialConnector

    VistaSocialConnector(api_token="tok")
    headers = _patch_requests["session"].headers
    assert headers["Authorization"] == "Bearer tok"
    assert headers["Accept"] == "application/json"


def test_401_raises_auth_error_no_retry(_patch_requests):
    """401/403 are credential failures -- retrying would just waste
    quota and risk a rate-limit ban. Must raise immediately."""
    from siege_utilities.analytics.vista_social import (
        VistaSocialConnector, VistaSocialAuthError,
    )

    resp = MagicMock(status_code=401, content=b"", text="unauthorized", headers={})
    _patch_requests["session"].request.return_value = resp

    c = VistaSocialConnector(api_token="bad-tok", retry_attempts=5)
    with pytest.raises(VistaSocialAuthError):
        c.list_accounts()
    # Called exactly once -- never retried.
    assert _patch_requests["session"].request.call_count == 1


def test_429_raises_rate_limit_error(_patch_requests):
    """429 surfaces a typed exception so callers can back off
    explicitly rather than have our retry loop double-stack into
    a longer ban."""
    from siege_utilities.analytics.vista_social import (
        VistaSocialConnector, VistaSocialRateLimitError,
    )

    resp = MagicMock(
        status_code=429, content=b"", text="rate limited",
        headers={"Retry-After": "30"},
    )
    _patch_requests["session"].request.return_value = resp

    c = VistaSocialConnector(api_token="tok", retry_attempts=3)
    with pytest.raises(VistaSocialRateLimitError, match="Retry-After: 30"):
        c.list_accounts()
    assert _patch_requests["session"].request.call_count == 1


def test_5xx_retries_then_succeeds(_patch_requests, monkeypatch):
    """Transient 5xxs should retry with backoff and eventually
    return a successful 2xx response. Verifies the retry loop
    actually loops -- not just runs once."""
    from siege_utilities.analytics import vista_social as mod
    from siege_utilities.analytics.vista_social import VistaSocialConnector

    monkeypatch.setattr(mod.time, "sleep", lambda *_: None)
    fail = MagicMock(status_code=503, content=b"", text="upstream gone", headers={})
    ok = MagicMock(status_code=200, content=b'{"data":[{"id":"a"}]}', headers={})
    ok.json.return_value = {"data": [{"id": "a"}]}
    _patch_requests["session"].request.side_effect = [fail, fail, ok]

    c = VistaSocialConnector(api_token="tok", retry_attempts=3, retry_backoff=1.0)
    accounts = c.list_accounts()
    assert accounts == [{"id": "a"}]
    assert _patch_requests["session"].request.call_count == 3


def test_4xx_other_raises_without_retry(_patch_requests):
    """A 400/404/etc is the caller's fault, not transient -- must
    surface immediately without burning retry budget."""
    from siege_utilities.analytics.vista_social import (
        VistaSocialConnector, VistaSocialError,
    )

    resp = MagicMock(status_code=404, content=b"", text="not found", headers={})
    _patch_requests["session"].request.return_value = resp

    c = VistaSocialConnector(api_token="tok", retry_attempts=3)
    with pytest.raises(VistaSocialError, match="404"):
        c.list_accounts()
    assert _patch_requests["session"].request.call_count == 1


def test_list_profiles_requires_account_id(_patch_requests):
    from siege_utilities.analytics.vista_social import VistaSocialConnector

    c = VistaSocialConnector(api_token="tok")
    with pytest.raises(ValueError, match="account_id"):
        c.list_profiles("")


@pytest.mark.requires_api_key
def test_vista_social_live_list_accounts(api_credentials):
    from siege_utilities.analytics.vista_social import VistaSocialConnector

    creds = api_credentials.get("vista_social")
    if not creds:
        pytest.skip("no 'vista_social:' section in credentials file")
    c = VistaSocialConnector(api_token=creds["api_token"])
    accounts = c.list_accounts()
    assert isinstance(accounts, list)

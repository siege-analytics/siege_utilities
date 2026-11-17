"""Error-path coverage for connectors/_http.request_raw (#1417 / #1846).

request_raw is the shared bulk/multipart transport. It raises on auth
rejection (401/403), exhausted retries after persistent 5xx, a rate limit
that never clears, and repeated transport errors. Each raise is exercised
here; backoff is pinned to 0 so no real waiting occurs.
"""
import types

import pytest
import requests

from siege_utilities.connectors._http import request_raw
from siege_utilities.connectors._protocol import (
    ConnectorAuthError,
    ConnectorError,
    ConnectorRateLimitError,
)


class _Response:
    def __init__(self, status_code: int, headers: dict[str, str] | None = None) -> None:
        self.status_code = status_code
        self.headers = headers or {}


def _connector(attempts: int = 3) -> types.SimpleNamespace:
    # _retry_backoff / _max_retry_wait at 0 keep backoff_wait() -> 0.0 so the
    # retry loop never sleeps for real.
    return types.SimpleNamespace(
        _retry_attempts=attempts,
        _max_retry_wait=0.0,
        _retry_backoff=0.0,
    )


def test_request_raw_raises_connector_auth_error_on_401() -> None:
    with pytest.raises(ConnectorAuthError):
        request_raw(_connector(), "GET", lambda: _Response(401), None)


def test_request_raw_raises_connector_auth_error_on_403() -> None:
    with pytest.raises(ConnectorAuthError):
        request_raw(_connector(), "POST", lambda: _Response(403), None)


def test_request_raw_raises_connector_error_after_persistent_5xx() -> None:
    with pytest.raises(ConnectorError) as exc:
        request_raw(_connector(attempts=3), "GET", lambda: _Response(500), None)
    assert "after 3 attempts" in str(exc.value)


def test_request_raw_raises_on_rate_limit_that_never_clears() -> None:
    # 429 with no Retry-After: retries with zero backoff, then raises the typed
    # rate-limit error on the final attempt, after exactly ``attempts`` sends.
    sends: list[int] = []

    def send() -> _Response:
        sends.append(1)
        return _Response(429, {})

    with pytest.raises(ConnectorRateLimitError):
        request_raw(_connector(attempts=2), "GET", send, None)
    assert len(sends) == 2


def test_request_raw_raises_connector_error_on_repeated_transport_errors() -> None:
    def send() -> _Response:
        raise requests.ConnectionError("boom")

    with pytest.raises(ConnectorError):
        request_raw(_connector(attempts=2), "GET", send, None)

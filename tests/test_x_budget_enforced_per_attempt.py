"""X budget cap holds across retries (#1835).

The connector's existing budget policy, no request once estimated cost has
reached ``budget_limit``, must hold for every attempt, including retries after
a 429, a 5xx or a transport error. These tests use only the public
``authenticate()`` -> ``get_posts()`` path; the only stub is
``requests.Session.request``. Synthetic values; no network.
"""
from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest
import requests

from siege_utilities.analytics import x_twitter
from siege_utilities.analytics._social_protocol import SocialMediaError, SocialMediaRateLimitError

START, END = date(2026, 1, 1), date(2026, 1, 31)
AUTH = {"data": {"id": "123", "username": "dummy"}}
POSTS = {"data": [{"id": "1", "text": "t", "created_at": "2026-01-02T00:00:00Z",
                   "public_metrics": {"like_count": 1}}], "meta": {}}
# One read costs COST_PER_READ (0.005); authentication spends one read, so a
# 0.010 cap leaves exactly one more request.
AT_THRESHOLD_AFTER_ONE_MORE = 2 * x_twitter.COST_PER_READ


def _reply(status: int, body: object, headers: dict[str, str] | None = None) -> requests.Response:
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(body).encode()
    result.headers.update(headers or {})
    return result


class _Transport:
    """Scripted stand-in for requests.Session.request that records each send."""

    def __init__(self, replies: list[requests.Response | Exception]) -> None:
        self.replies = list(replies)
        self.urls: list[str] = []

    def send(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        self.urls.append(url)
        if not self.replies:
            raise AssertionError(f"unexpected request #{len(self.urls)}: {method} {url}")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Replace requests.Session.request (an unbound method) with this script."""

        def request(session: requests.Session, method: str, url: str, **kwargs: Any) -> requests.Response:
            return self.send(method, url, **kwargs)

        monkeypatch.setattr(requests.Session, "request", request)


def _run(monkeypatch: pytest.MonkeyPatch, budget: float, replies: list[requests.Response | Exception]) -> tuple[Any, _Transport]:
    transport = _Transport(replies)
    transport.install(monkeypatch)
    monkeypatch.setattr(x_twitter.time, "sleep", lambda seconds: None)
    connector = x_twitter.XTwitterConnector(
        "DUMMY_TOKEN", user_id="123", budget_limit=budget, retry_attempts=3, retry_backoff=0,
    )
    connector.authenticate()
    return connector, transport


@pytest.mark.parametrize("first_failure", [
    _reply(429, {}, {"Retry-After": "0"}),
    _reply(503, {}),
], ids=["429", "503"])
def test_retry_stops_once_the_budget_is_reached(
    monkeypatch: pytest.MonkeyPatch, first_failure: requests.Response,
) -> None:
    connector, transport = _run(monkeypatch, AT_THRESHOLD_AFTER_ONE_MORE, [
        _reply(200, AUTH), first_failure, _reply(200, POSTS),
    ])
    with pytest.raises(SocialMediaError, match="budget limit reached") as caught:
        connector.get_posts(START, END)
    assert not isinstance(caught.value, SocialMediaRateLimitError)
    assert len(transport.urls) == 2  # authentication plus the first posts attempt; no retry
    assert connector.estimated_cost == pytest.approx(AT_THRESHOLD_AFTER_ONE_MORE)
    assert len(transport.replies) == 1  # the success reply was never requested


def test_unbilled_transport_failure_may_retry_within_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    # A transport failure gets no response and adds no estimated cost, so the
    # budget is not reached and the existing policy allows the retry.
    connector, transport = _run(monkeypatch, AT_THRESHOLD_AFTER_ONE_MORE, [
        _reply(200, AUTH), requests.ConnectionError("transport failure"), _reply(200, POSTS),
    ])
    assert len(connector.get_posts(START, END)) == 1
    assert len(transport.urls) == 3
    assert connector.estimated_cost == pytest.approx(AT_THRESHOLD_AFTER_ONE_MORE)


def test_zero_budget_sends_no_request(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = _Transport([_reply(200, AUTH)])
    transport.install(monkeypatch)
    connector = x_twitter.XTwitterConnector("DUMMY_TOKEN", user_id="123", budget_limit=0.0)
    with pytest.raises(SocialMediaError, match="budget limit reached"):
        connector.authenticate()
    assert transport.urls == []
    assert connector.estimated_cost == 0.0


@pytest.mark.parametrize("first_failure", [
    _reply(429, {}, {"Retry-After": "0"}),
    _reply(503, {}),
], ids=["429", "503"])
def test_retry_succeeds_when_the_budget_allows_it(
    monkeypatch: pytest.MonkeyPatch, first_failure: requests.Response,
) -> None:
    connector, transport = _run(monkeypatch, 1.0, [_reply(200, AUTH), first_failure, _reply(200, POSTS)])
    frame = connector.get_posts(START, END)
    assert len(frame) == 1
    assert len(transport.urls) == 3
    assert connector.estimated_cost == pytest.approx(3 * x_twitter.COST_PER_READ)

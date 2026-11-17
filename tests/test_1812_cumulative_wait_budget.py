"""Cumulative retry-wait budget for the Instagram and X connectors (#1812).

``max_retry_wait`` bounds the total time one request may spend sleeping across
all of its retries, not only each individual wait. Every test is offline: the
session is mocked and ``time.sleep`` is recorded, never executed.
"""

import json
import time
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
import requests

from siege_utilities.analytics import instagram, x_twitter
from siege_utilities.analytics._social_protocol import (
    SocialMediaError,
    SocialMediaRateLimitError,
)


def response(status=200, body=None, *, headers=None):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(body or {}).encode()
    result.headers.update(headers or {})
    return result


@pytest.fixture
def sleep(monkeypatch):
    recorder = Mock()
    clock = SimpleNamespace(sleep=recorder, time=time.time)
    for module in (instagram, x_twitter):
        monkeypatch.setattr(module, "time", clock)
    monkeypatch.setattr(requests.Session, "request", Mock(side_effect=AssertionError("Unexpected HTTP")))
    return recorder


@pytest.fixture
def make_client(monkeypatch):
    clients = []

    def make(platform, replies, **kwargs):
        if platform == "instagram":
            client = instagram.InstagramConnector("DUMMY_TOKEN", ig_user_id="123", **kwargs)
        else:
            client = x_twitter.XTwitterConnector("DUMMY_TOKEN", user_id="123", **kwargs)
        clients.append(client)
        client._authenticated = True
        request = Mock(side_effect=replies)
        monkeypatch.setattr(client._session, "request", request)
        return client, request

    yield make
    for client in clients:
        client.close()


def total_slept(sleep):
    return sum(args[0] for args, _ in sleep.call_args_list)


@pytest.mark.parametrize("platform", ["instagram", "x"])
def test_retry_after_hints_cannot_sum_past_the_cap(make_client, sleep, platform):
    # Two 600 s hints would schedule 1,200 s in total; the second is refused.
    hint = response(429, headers={"Retry-After": "600"})
    client, request = make_client(platform, [hint, hint, response()], retry_attempts=3)
    with pytest.raises(SocialMediaRateLimitError) as caught:
        client._request("GET", "/123")
    assert caught.value.retry_after == 600
    assert sleep.call_args_list == [call(600.0)]
    assert request.call_count == 2
    assert total_slept(sleep) <= 900


@pytest.mark.parametrize("platform", ["instagram", "x"])
def test_waits_within_the_budget_still_retry(make_client, sleep, platform):
    hint = response(429, headers={"Retry-After": "450"})
    client, request = make_client(platform, [hint, hint, response()], retry_attempts=3)
    assert client._request("GET", "/123") == {}
    assert sleep.call_args_list == [call(450.0), call(450.0)]
    assert request.call_count == 3


@pytest.mark.parametrize("platform", ["instagram", "x"])
@pytest.mark.parametrize("failure", ["throttle", "server", "transport"])
def test_backoff_waits_cannot_sum_past_the_cap(make_client, sleep, platform, failure):
    fail = {"throttle": response(429), "server": response(503),
            "transport": requests.ConnectionError("dummy")}[failure]
    client, request = make_client(platform, [fail, fail, fail, response()],
                                  retry_attempts=4, retry_backoff=30)
    expected = SocialMediaRateLimitError if failure == "throttle" else SocialMediaError
    with pytest.raises(expected):
        client._request("GET", "/123")
    # Backoff is 30, then 900 (30 ** 2 capped); 30 + 900 exceeds the budget.
    assert sleep.call_args_list == [call(30)]
    assert request.call_count == 2
    assert total_slept(sleep) <= 900


@pytest.mark.parametrize("platform", ["instagram", "x"])
def test_exhausted_budget_reports_the_attempts_made(make_client, sleep, platform):
    client, _ = make_client(platform, [response(503), response(503), response()],
                            retry_attempts=3, retry_backoff=30)
    with pytest.raises(SocialMediaError) as caught:
        client._request("GET", "/123")
    assert "failed after 2 attempts" in str(caught.value)


@pytest.mark.parametrize("platform", ["instagram", "x"])
def test_custom_cap_bounds_the_total(make_client, sleep, platform):
    hint = response(429, headers={"Retry-After": "15"})
    client, request = make_client(platform, [hint, hint, response()],
                                  retry_attempts=3, max_retry_wait=20)
    with pytest.raises(SocialMediaRateLimitError):
        client._request("GET", "/123")
    assert sleep.call_args_list == [call(15.0)]
    assert request.call_count == 2

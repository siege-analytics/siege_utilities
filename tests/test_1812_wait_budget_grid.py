"""Exhaustive check of the cumulative retry-wait budget (#1812).

Every sequence of three Retry-After hints drawn from a small set, for both
connectors and two caps, is compared against a reference model: a wait is
taken only while the running total stays within ``max_retry_wait``; the first
wait that would exceed it ends the request with SocialMediaRateLimitError.
"""

import itertools
import json
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests

from siege_utilities.analytics import instagram, x_twitter
from siege_utilities.analytics._social_protocol import SocialMediaError, SocialMediaRateLimitError

HINTS = (0, 1, 15, 450, 600, 899, 900)
CAPS = (900.0, 20.0)


def response(status=200, *, headers=None):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps({}).encode()
    result.headers.update(headers or {})
    return result


def expected_schedule(hints, cap):
    """Reference model: (sleeps taken, whether the request succeeds)."""
    waited, sleeps = 0.0, []
    for hint in hints:
        if waited + hint > cap:
            return sleeps, False
        waited += hint
        sleeps.append(float(hint))
    return sleeps, True


@pytest.fixture
def sleep(monkeypatch):
    recorder = Mock()
    clock = SimpleNamespace(sleep=recorder, time=time.time)
    for module in (instagram, x_twitter):
        monkeypatch.setattr(module, "time", clock)
    monkeypatch.setattr(requests.Session, "request", Mock(side_effect=AssertionError("Unexpected HTTP")))
    return recorder


@pytest.mark.parametrize("platform", ["instagram", "x"])
@pytest.mark.parametrize("cap", CAPS)
def test_every_hint_sequence_respects_the_cumulative_cap(sleep, monkeypatch, platform, cap):
    checked = 0
    for hints in itertools.product(HINTS, repeat=3):
        sleep.reset_mock()
        if platform == "instagram":
            client = instagram.InstagramConnector(
                "DUMMY_TOKEN", ig_user_id="123", retry_attempts=4, max_retry_wait=cap)
        else:
            client = x_twitter.XTwitterConnector(
                "DUMMY_TOKEN", user_id="123", retry_attempts=4, max_retry_wait=cap)
        client._authenticated = True
        replies = [response(429, headers={"Retry-After": str(h)}) for h in hints] + [response()]
        monkeypatch.setattr(client._session, "request", Mock(side_effect=replies))
        sleeps, succeeds = expected_schedule(hints, cap)
        try:
            if succeeds:
                assert client._request("GET", "/123") == {}, hints
            else:
                with pytest.raises(SocialMediaRateLimitError):
                    client._request("GET", "/123")
        finally:
            client.close()
        actual = [args[0] for args, _ in sleep.call_args_list]
        assert actual == sleeps, (hints, cap, actual, sleeps)
        assert sum(actual) <= cap, (hints, cap, actual)
        checked += 1
    assert checked == len(HINTS) ** 3


# Mixed failures share the same budget. A 429 waits its hint; a 5xx or
# transport error waits the configured backoff (BACKOFF ** attempt, capped).
# Running out of budget on a 429 raises SocialMediaRateLimitError; running out
# on a 5xx or transport error stops retrying and raises plain SocialMediaError.
BACKOFF = 2.0
EVENTS = (("429", 0.0), ("429", 15.0), ("429", 450.0), ("5xx", None), ("transport", None))


def expected_mixed_outcome(
    events: tuple[tuple[str, float | None], ...], cap: float,
) -> tuple[list[float], type[Exception] | None]:
    """Reference model: (sleeps taken, error type raised or None on success)."""
    waited, sleeps = 0.0, []
    for attempt, (kind, hint) in enumerate(events, start=1):
        if kind == "429":
            if hint > cap or waited + hint > cap:
                return sleeps, SocialMediaRateLimitError
            delay = hint
        else:
            delay = min(BACKOFF ** attempt, cap)
            if waited + delay > cap:
                return sleeps, SocialMediaError
        waited += delay
        sleeps.append(float(delay))
    return sleeps, None


def mixed_reply(kind: str, hint: float | None) -> requests.Response | Exception:
    if kind == "429":
        return response(429, headers={"Retry-After": str(int(hint))})
    if kind == "5xx":
        return response(503)
    return requests.ConnectionError("transport failure")


@pytest.mark.parametrize("platform", ["instagram", "x"])
@pytest.mark.parametrize("cap", CAPS)
def test_mixed_429_5xx_and_transport_sequences_share_the_budget(
    sleep: Mock, monkeypatch: pytest.MonkeyPatch, platform: str, cap: float,
) -> None:
    outcomes: set[object] = set()
    for events in itertools.product(EVENTS, repeat=3):
        sleep.reset_mock()
        if platform == "instagram":
            client = instagram.InstagramConnector(
                "DUMMY_TOKEN", ig_user_id="123", retry_attempts=4,
                retry_backoff=BACKOFF, max_retry_wait=cap)
        else:
            client = x_twitter.XTwitterConnector(
                "DUMMY_TOKEN", user_id="123", retry_attempts=4,
                retry_backoff=BACKOFF, max_retry_wait=cap)
        client._authenticated = True
        replies = [mixed_reply(kind, hint) for kind, hint in events] + [response()]
        monkeypatch.setattr(client._session, "request", Mock(side_effect=replies))
        sleeps, error = expected_mixed_outcome(events, cap)
        try:
            if error is None:
                assert client._request("GET", "/123") == {}, events
            else:
                with pytest.raises(SocialMediaError) as caught:
                    client._request("GET", "/123")
                assert type(caught.value) is error, (events, cap, type(caught.value))
        finally:
            client.close()
        actual = [args[0] for args, _ in sleep.call_args_list]
        assert actual == sleeps, (events, cap, actual, sleeps)
        assert sum(actual) <= cap, (events, cap, actual)
        outcomes.add(error)
    # Each cap reaches success; the 20-second cap also reaches both exhaustion errors.
    assert None in outcomes
    if cap == 20.0:
        assert {SocialMediaRateLimitError, SocialMediaError} <= outcomes

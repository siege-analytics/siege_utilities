"""Offline reproductions of PR #1812 review blockers at d329eef7."""

import json
import logging
import time
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
import requests

from siege_utilities.analytics import instagram, x_twitter
from siege_utilities.analytics._social_protocol import (
    SocialMediaAuthError,
    SocialMediaError,
    SocialMediaRateLimitError,
)

START, END = date(2026, 1, 1), date(2026, 1, 31)
SECRETS = ("DUMMY_RENEWED_TOKEN", "DUMMY_APP_SECRET", "DUMMY_OLD_TOKEN")


def response(status=200, body=None, *, text=None, headers=None):
    result = requests.Response()
    result.status_code = status
    result._content = (text if text is not None else json.dumps(body or {})).encode()
    result.headers.update(headers or {})
    return result


@pytest.fixture(autouse=True)
def offline(monkeypatch, caplog):
    monkeypatch.setattr(requests.Session, "request", Mock(side_effect=AssertionError("Unexpected HTTP")))
    sleep = Mock()
    # Keep unrelated threads' sleeps out of connector retry assertions.
    clock = SimpleNamespace(sleep=sleep, time=time.time)
    for module in (instagram, x_twitter):
        monkeypatch.setattr(module, "time", clock)
        monkeypatch.setattr(module.log, "disabled", False)
        caplog.set_level(logging.WARNING, logger=module.__name__)
    yield sleep


def test_offline_sleep_ignores_unrelated_callers(offline):
    time.sleep(0)
    offline.assert_not_called()


@pytest.fixture
def make_client(monkeypatch):
    clients = []

    def make(platform="instagram", replies=(), **kwargs):
        if platform == "instagram":
            client = instagram.InstagramConnector(
                "DUMMY_OLD_TOKEN", ig_user_id="123", app_id="DUMMY_APP_ID",
                app_secret="DUMMY_APP_SECRET", **kwargs,
            )
        else:
            client = x_twitter.XTwitterConnector("DUMMY_OLD_TOKEN", user_id="123", **kwargs)
        clients.append(client)
        client._authenticated = True
        request = Mock(side_effect=replies)
        monkeypatch.setattr(client._session, "request", request)
        return client, request

    yield make
    for client in clients:
        client.close()


def capture_error(action, caplog):
    try:
        action()
    except SocialMediaError as exc:
        logging.getLogger(__name__).exception("Exchange failed")
        diagnostic = str(exc) + repr(exc) + caplog.text
        for secret in SECRETS:
            assert secret not in diagnostic
        return str(exc)
    pytest.fail("Expected a safe exchange error")


def test_b1_malformed_exchange_never_discloses_body(make_client, caplog):
    client, request = make_client(replies=[response(text='{"access_token":"DUMMY_RENEWED_TOKEN"')])
    message = capture_error(client.refresh_access_token, caplog)
    assert message == "Instagram token exchange returned an unparseable response (HTTP 200)."
    assert request.call_count == 1


@pytest.mark.parametrize("diagnostic", [
    "upstream Bearer DUMMY_OLD_TOKEN client_secret DUMMY_APP_SECRET DUMMY_RENEWED_TOKEN",
    "https://example.invalid/?client_secret=DUMMY_APP_SECRET&fb_exchange_token=DUMMY_OLD_TOKEN",
    "client_secret%3DDUMMY_APP_SECRET%26access_token%3DDUMMY_RENEWED_TOKEN DUMMY_OLD_TOKEN",
])
@pytest.mark.parametrize("after_retry", [False, True])
def test_b1_transport_diagnostics_use_only_class_and_attempt(make_client, caplog, diagnostic, after_retry):
    first = response(500) if after_retry else requests.ConnectionError(diagnostic)
    client, request = make_client(replies=[first, requests.ConnectionError(diagnostic)], retry_attempts=2)
    message = capture_error(client.refresh_access_token, caplog)
    assert message == "Instagram token exchange ConnectionError on attempt 2."
    assert "Instagram token exchange ConnectionError on attempt 2" in caplog.text
    assert request.call_count == 2


OPERATIONS = ["authenticate_id", "authenticate_username", "account", "posts", "insights"]


def x_operation(client, operation, identifier):
    client._user_id = identifier
    if operation == "authenticate_username":
        client._user_id = None
        client._username = identifier
        return client.authenticate()
    if operation == "authenticate_id":
        return client.authenticate()
    if operation == "account":
        return client.get_account_info()
    if operation == "posts":
        return client.get_posts(START, END)
    return client.get_post_insights(identifier)


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("identifier", ["..", ".", "", "../x", "a/b", "a?b", "a#b", "é", "1\n"])
def test_b2_invalid_path_never_requests(make_client, operation, identifier):
    data = [] if operation == "posts" else {"id": "123", "username": "dummy"}
    client, request = make_client("x", [response(body={"data": data})])
    with pytest.raises(ValueError):
        x_operation(client, operation, identifier)
    request.assert_not_called()


@pytest.mark.parametrize("operation", OPERATIONS)
@pytest.mark.parametrize("boundary", [False, True])
def test_b2_valid_prepared_endpoint(make_client, operation, boundary):
    identifier = ("a_1234567890123" if operation == "authenticate_username" else "1" * 19) if boundary else "123"
    data = [] if operation == "posts" else {"id": "123", "username": "dummy"}
    client, request = make_client("x", [response(body={"data": data})])
    x_operation(client, operation, identifier)
    suffix = {
        "authenticate_username": f"/users/by/username/{identifier}",
        "insights": f"/tweets/{identifier}",
        "posts": f"/users/{identifier}/tweets",
    }.get(operation, f"/users/{identifier}")
    prepared = requests.Request("GET", request.call_args.args[1], params=request.call_args.kwargs["params"]).prepare()
    assert prepared.url.split("?")[0] == x_twitter.BASE_URL + suffix


@pytest.mark.parametrize("operation", OPERATIONS)
def test_b2_identifier_length_limit(make_client, operation):
    identifier = "a" * 16 if operation == "authenticate_username" else "1" * 20
    client, request = make_client("x", [response(body={"data": [] if operation == "posts" else {"id": "123"}})])
    with pytest.raises(ValueError):
        x_operation(client, operation, identifier)
    request.assert_not_called()


@pytest.mark.parametrize("stage", ["first", "later", "exchange"])
@pytest.mark.parametrize("subcode", [463, 460])
@pytest.mark.parametrize("header", ["x-app-usage", "x-page-usage"])
def test_b3_auth_code_wins_over_usage(make_client, stage, subcode, header, offline):
    replies = []
    if stage == "later":
        replies.append(response(body={
            "data": [{"id": "123", "timestamp": "2026-01-02T00:00:00+0000"}],
            "paging": {"next": instagram.BASE_URL + "/123/media?after=dummy"},
        }))
    replies.append(response(400, {"error": {"code": 190, "error_subcode": subcode}},
                            headers={header: '{"call_count":100}'}))
    client, request = make_client(replies=replies, retry_attempts=1)
    with pytest.raises(SocialMediaAuthError):
        if stage == "exchange":
            client.refresh_access_token()
        else:
            client.get_posts(START, END)
    assert not client.is_connected()
    assert client.is_token_expired() is (subcode == 463)
    assert request.call_count == (2 if stage == "later" else 1)
    offline.assert_not_called()


@pytest.mark.parametrize("code", [10, 100])
def test_b3_classified_graph_error_does_not_use_telemetry(make_client, code):
    reply = response(400, {"error": {"code": code}}, headers={"x-app-usage": '{"call_count":100}'})
    client, _ = make_client(replies=[reply], retry_attempts=1)
    with pytest.raises(SocialMediaError) as caught:
        client._request("GET", "/123")
    assert not isinstance(caught.value, SocialMediaRateLimitError)


@pytest.mark.parametrize("platform", ["instagram", "x"])
@pytest.mark.parametrize("hint", ["1e300", "901", "Fri, 01 Jan 2100 00:00:00 GMT"])
def test_b4_oversize_retry_hint_stops_after_one_request(make_client, offline, platform, hint):
    reply = response(429, headers={"Retry-After": hint})
    client, request = make_client(platform, [reply, response()], retry_attempts=2)
    with pytest.raises(SocialMediaRateLimitError) as caught:
        client._request("GET", "/123")
    assert caught.value.retry_after > 900
    if hint != "Fri, 01 Jan 2100 00:00:00 GMT":
        assert caught.value.retry_after == float(hint)
    assert request.call_count == 1
    offline.assert_not_called()


@pytest.mark.parametrize("platform", ["instagram", "x"])
def test_b4_normal_retry_hint_sleeps_then_retries(make_client, offline, platform):
    client, request = make_client(platform, [response(429, headers={"Retry-After": "30"}), response()], retry_attempts=2)
    assert client._request("GET", "/123") == {}
    assert request.call_count == 2
    offline.assert_called_once_with(30)


def test_b4_far_future_x_reset_stops_after_one_request(make_client, offline):
    client, request = make_client("x", [response(429, headers={"x-rate-limit-reset": "4102444800"}), response()],
                                  retry_attempts=2)
    with pytest.raises(SocialMediaRateLimitError) as caught:
        client._request("GET", "/123")
    assert caught.value.retry_after > 900
    assert request.call_count == 1
    offline.assert_not_called()


@pytest.mark.parametrize("platform", ["instagram", "x"])
@pytest.mark.parametrize("failure", ["throttle", "server", "transport"])
def test_b4_configured_backoff_is_capped(make_client, offline, platform, failure):
    fail = {"throttle": response(429), "server": response(503), "transport": requests.ConnectionError("dummy")}[failure]
    client, request = make_client(platform, [fail, fail, response()], retry_attempts=3, retry_backoff=1e300)
    assert client._request("GET", "/123") == {}
    assert request.call_count == 3
    assert offline.call_args_list == [call(900), call(900)]


@pytest.mark.parametrize("platform", ["instagram", "x"])
@pytest.mark.parametrize("hint", [20, 30])
def test_b4_custom_cap_includes_boundary(make_client, offline, platform, hint):
    client, request = make_client(platform, [response(429, headers={"Retry-After": str(hint)}), response()],
                                  retry_attempts=2, max_retry_wait=20)
    if hint == 20:
        assert client._request("GET", "/123") == {}
        offline.assert_called_once_with(20)
        assert request.call_count == 2
    else:
        with pytest.raises(SocialMediaRateLimitError) as caught:
            client._request("GET", "/123")
        assert caught.value.retry_after == 30
        offline.assert_not_called()
        assert request.call_count == 1


@pytest.mark.parametrize("setting", ["max_retry_wait", "retry_backoff"])
@pytest.mark.parametrize("value", [-1, float("inf"), float("nan")])
@pytest.mark.parametrize("platform", ["instagram", "x"])
def test_b4_invalid_wait_settings(make_client, platform, setting, value):
    with pytest.raises(ValueError, match=setting):
        make_client(platform, **{setting: value})


def test_b4_exchange_oversize_hint_never_sleeps(make_client, offline):
    client, request = make_client(replies=[response(429, headers={"Retry-After": "1e300"})])
    with pytest.raises(SocialMediaRateLimitError) as caught:
        client.refresh_access_token()
    assert caught.value.retry_after == 1e300
    assert request.call_count == 1
    offline.assert_not_called()


def test_b4_x_reset_larger_than_float_never_overflows(make_client, offline):
    client, request = make_client("x", [response(429, headers={"x-rate-limit-reset": "9" * 400})])
    with pytest.raises(SocialMediaRateLimitError):
        client._request("GET", "/123")
    assert request.call_count == 1
    offline.assert_not_called()


def test_b1_success_after_transport_failure_has_safe_logs(make_client, caplog):
    client, request = make_client(replies=[
        requests.ConnectionError("Bearer DUMMY_OLD_TOKEN client_secret DUMMY_APP_SECRET DUMMY_RENEWED_TOKEN"),
        response(body={"access_token": "DUMMY_RENEWED_TOKEN", "expires_in": 60}),
    ], retry_attempts=2)
    assert client.refresh_access_token() == "DUMMY_RENEWED_TOKEN"
    assert request.call_count == 2
    assert "ConnectionError on attempt 1" in caplog.text
    for secret in SECRETS:
        assert secret not in caplog.text


def test_b3_rejected_replacement_does_not_expire_current_token(make_client):
    reply = response(400, {"error": {"code": 190, "error_subcode": 463}},
                     headers={"x-app-usage": '{"call_count":100}'})
    client, _ = make_client(replies=[reply])
    with pytest.raises(SocialMediaAuthError):
        client.refresh_access_token(access_token="DUMMY_REPLACEMENT_TOKEN")
    assert client.is_connected()
    assert not client.is_token_expired()

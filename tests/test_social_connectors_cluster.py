"""Offline regressions for social connector issues #1458, #1465 and #1474."""

import json
import logging
from datetime import date
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from siege_utilities.analytics import facebook_business, instagram, x_twitter
from siege_utilities.analytics._social_protocol import (
    SocialMediaAuthError,
    SocialMediaError,
    SocialMediaRateLimitError,
)

START = date(2026, 1, 1)
END = date(2026, 1, 31)
DEPRECATED = {
    "impressions", "engagement", "taps_forward", "taps_back", "exits",
    "page_fans", "page_engaged_users", "page_impressions",
}
# Graph v22.0 metric contract, reviewed 2026-10-18 against Meta's references:
# /docs/instagram-platform/instagram-graph-api/reference/ig-user/insights/
# /docs/instagram-platform/instagram-graph-api/reference/ig-media/insights/
# /docs/graph-api/reference/v22.0/insights/
# Account defaults must support daily time_series (views/profile_views do not).
CURRENT_DEFAULTS = {
    "account": {"reach", "follower_count"},
    "post": {"views", "reach", "total_interactions", "saved", "shares"},
    "story": {"views", "reach", "replies", "navigation"},
    "page": {
        "page_media_view", "page_post_engagements", "page_follows",
        "page_views_total", "page_actions_post_reactions_total",
    },
}


def response(status=200, body=None, headers=None):
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(body if body is not None else {}).encode()
    result.headers.update(headers or {})
    return result


@pytest.fixture(autouse=True)
def offline(monkeypatch, caplog):
    """Fail on any unmocked HTTP call and never sleep during retries."""
    monkeypatch.setattr(requests.Session, "request", Mock(side_effect=AssertionError("Unexpected HTTP")))
    sleep = Mock()
    monkeypatch.setattr(instagram.time, "sleep", sleep)
    for module in (instagram, x_twitter):
        monkeypatch.setattr(module.log, "disabled", False)
        caplog.set_level(logging.WARNING, logger=module.__name__)
    return sleep


def connector(platform, monkeypatch, responses, *, attempts=1):
    if platform == "instagram":
        client = instagram.InstagramConnector("test-token", ig_user_id="123", retry_attempts=attempts)
    else:
        client = x_twitter.XTwitterConnector("test-token", user_id="123", retry_attempts=attempts)
    client._authenticated = True
    request = Mock(side_effect=responses)
    monkeypatch.setattr(client._session, "request", request)
    return client, request


@pytest.mark.parametrize("kind", ["account", "post", "story"])
def test_instagram_defaults_use_current_metrics(kind, monkeypatch):
    responses = [response(body={"data": []})]
    if kind == "story":
        responses.insert(0, response(body={"data": [{"id": "story-1"}]}))
    client, request = connector("instagram", monkeypatch, responses)
    if kind == "account":
        client.get_account_insights(START, END)
    elif kind == "post":
        client.get_post_insights("post-1")
    else:
        client.get_stories_insights()
    sent = set(request.call_args.kwargs["params"]["metric"].split(","))
    assert not sent & DEPRECATED
    assert sent == CURRENT_DEFAULTS[kind]


@pytest.mark.parametrize("kind", ["account", "post", "story"])
def test_instagram_metrics_remain_overridable(kind, monkeypatch):
    responses = [response(body={"data": []})]
    if kind == "story":
        responses.insert(0, response(body={"data": [{"id": "story-1"}]}))
    client, request = connector("instagram", monkeypatch, responses)
    if kind == "account":
        client.get_account_insights(START, END, metrics=["reach"])
    elif kind == "post":
        client.get_post_insights("post-1", metrics=["reach"])
    else:
        client.get_stories_insights(metrics=["reach"])
    assert request.call_args.kwargs["params"]["metric"] == "reach"


@pytest.mark.parametrize("custom", [False, True])
def test_facebook_page_defaults_and_metric_parameter(monkeypatch, custom):
    # SDK is optional; intercept its boundary, with HTTP disabled by offline.
    monkeypatch.setattr(facebook_business, "FACEBOOK_BUSINESS_AVAILABLE", True)
    monkeypatch.setattr(facebook_business, "FacebookAdsApi", Mock(), raising=False)
    page = Mock()
    page.return_value.get_insights.return_value = []
    monkeypatch.setattr(facebook_business, "Page", page, raising=False)
    client = facebook_business.FacebookBusinessConnector("test-token")
    metrics = ["page_follows"] if custom else None
    client.get_page_insights("123", str(START), str(END), metrics=metrics)
    kwargs = page.return_value.get_insights.call_args.kwargs
    sent = set(kwargs.get("params", {}).get("metric", kwargs.get("fields", [])))
    assert not sent & DEPRECATED
    assert sent == (set(metrics) if custom else CURRENT_DEFAULTS["page"])
    assert set(kwargs["params"]["metric"]) == sent


@pytest.mark.parametrize("body", [{"data": {}}, {"errors": [{"detail": "User not found"}]}, {"data": None}])
def test_x_nonexistent_user_id_fails_authentication(monkeypatch, body):
    client, _ = connector("x", monkeypatch, [response(body=body)])
    client._authenticated = False
    with pytest.raises(SocialMediaAuthError):
        client.authenticate()
    assert not client.is_connected()


@pytest.mark.parametrize("limit", [1, 4, 5, 101])
def test_x_small_limits_use_valid_page_size_and_trim(monkeypatch, limit):
    client, request = connector("x", monkeypatch, [response(body={
        "data": [{"id": str(i)} for i in range(10)],
    })])
    result = client.get_posts(START, END, limit=limit)
    assert 5 <= request.call_args.kwargs["params"]["max_results"] <= 100
    assert len(result) == min(limit, 10)


@pytest.mark.parametrize("metrics", [None, ["like_count", "url_link_clicks", "user_profile_clicks"]])
def test_x_insights_merge_all_metric_groups_with_public_precedence(monkeypatch, metrics):
    client, _ = connector("x", monkeypatch, [response(body={"data": {
        "public_metrics": {"like_count": 5},
        "non_public_metrics": {"url_link_clicks": 7, "like_count": 3},
        "organic_metrics": {"user_profile_clicks": 9, "url_link_clicks": 2, "like_count": 1},
    }})])
    result = client.get_post_insights("tweet-1", metrics=metrics).set_index("metric")["value"].to_dict()
    assert result == {"like_count": 5, "url_link_clicks": 7, "user_profile_clicks": 9}


@pytest.mark.parametrize("platform", ["instagram", "x"])
@pytest.mark.parametrize("retry_after", ["7", "0", None, "invalid", "inf", "nan"])
def test_rate_limit_retries_then_succeeds(monkeypatch, offline, platform, retry_after):
    headers = {"Retry-After": retry_after} if retry_after is not None else {}
    client, request = connector(platform, monkeypatch, [
        response(429, headers=headers), response(body={"data": {"id": "123"}}),
    ], attempts=2)
    assert client._request("GET", "/123") == {"data": {"id": "123"}}
    assert request.call_count == 2
    expected = float(retry_after) if retry_after in ("7", "0") else client._retry_backoff
    offline.assert_called_once_with(expected)


@pytest.mark.parametrize("platform", ["instagram", "x"])
def test_retry_after_http_date_is_honored(monkeypatch, offline, platform):
    monkeypatch.setattr(instagram.time, "time", lambda: 1767225600.0)
    client, _ = connector(platform, monkeypatch, [
        response(429, headers={"Retry-After": "Thu, 01 Jan 2026 00:00:07 GMT"}),
        response(body={"data": []}),
    ], attempts=2)
    assert client._request("GET", "/123") == {"data": []}
    offline.assert_called_once_with(7.0)


def test_x_rate_reset_hint_is_used_when_retry_after_is_invalid(monkeypatch, offline):
    monkeypatch.setattr(x_twitter.time, "time", lambda: 1767225600.0)
    client, _ = connector("x", monkeypatch, [
        response(429, headers={"Retry-After": "invalid", "x-rate-limit-reset": "1767225611"}),
        response(body={"data": []}),
    ], attempts=2)
    assert client._request("GET", "/123") == {"data": []}
    offline.assert_called_once_with(11.0)


@pytest.mark.parametrize("platform", ["instagram", "x"])
def test_rate_limit_retry_budget_exhaustion_keeps_error_type(monkeypatch, offline, platform):
    client, request = connector(platform, monkeypatch, [response(429, headers={"Retry-After": "2"})] * 3, attempts=3)
    with pytest.raises(SocialMediaRateLimitError) as caught:
        client._request("GET", "/123")
    assert caught.value.retry_after == 2
    assert request.call_count == 3
    assert [call.args[0] for call in offline.call_args_list] == [2, 2]


@pytest.mark.parametrize("code", [4, 17, 32, 613, 80001, 80014])
@pytest.mark.parametrize("status", [400, 403])
def test_graph_throttle_codes_are_rate_limits(monkeypatch, code, status):
    client, _ = connector("instagram", monkeypatch, [response(status, {"error": {"code": code}})])
    with pytest.raises(SocialMediaRateLimitError):
        client._request("GET", "/123")


def test_graph_throttle_code_retries(monkeypatch, offline):
    client, request = connector("instagram", monkeypatch, [
        response(403, {"error": {"code": 4}}), response(body={"data": []}),
    ], attempts=2)
    assert client._request("GET", "/123") == {"data": []}
    assert request.call_count == 2
    offline.assert_called_once_with(client._retry_backoff)


@pytest.mark.parametrize("header", ["x-app-usage", "x-page-usage"])
@pytest.mark.parametrize("counter", ["call_count", "total_cputime", "total_time"])
def test_graph_usage_headers_detect_throttling(monkeypatch, header, counter):
    client, _ = connector("instagram", monkeypatch, [response(
        403, {"error": {"message": "Request limit"}}, {header: json.dumps({counter: 100})},
    )])
    with pytest.raises(SocialMediaRateLimitError):
        client._request("GET", "/123")


@pytest.mark.parametrize("usage", ["bad json", "null", "[]", '{"call_count": "invalid"}', '{"call_count": 99}'])
def test_graph_invalid_or_low_usage_does_not_mask_auth_error(monkeypatch, usage):
    client, _ = connector("instagram", monkeypatch, [response(403, headers={"x-app-usage": usage})])
    with pytest.raises(SocialMediaAuthError):
        client._request("GET", "/123")


def test_graph_success_with_exhausted_usage_is_kept(monkeypatch):
    client, _ = connector("instagram", monkeypatch, [response(
        body={"id": "123"}, headers={"x-page-usage": '{"call_count": 100}'},
    )])
    assert client._request("GET", "/123") == {"id": "123"}


@pytest.mark.parametrize("platform", ["instagram", "x"])
def test_rate_limit_after_first_page_returns_partial_results(monkeypatch, caplog, platform):
    first = {"data": [{"id": "first", "timestamp": "2026-01-15T00:00:00+0000"}]}
    if platform == "instagram":
        first["paging"] = {"next": f"{instagram.BASE_URL}/123/media?after=cursor"}
    else:
        first["meta"] = {"next_token": "cursor"}
    client, request = connector(platform, monkeypatch, [response(body=first), response(429), response(429)], attempts=2)
    result = client.get_posts(START, END)
    assert result["id"].tolist() == ["first"]
    assert request.call_count == 3
    assert "partial" in caplog.text.lower()


@pytest.mark.parametrize("platform", ["instagram", "x"])
def test_first_page_rate_limit_is_not_swallowed(monkeypatch, platform):
    client, _ = connector(platform, monkeypatch, [response(429)])
    with pytest.raises(SocialMediaRateLimitError):
        client.get_posts(START, END)


@pytest.mark.parametrize("platform", ["instagram", "x"])
def test_non_throttle_failure_after_first_page_is_not_swallowed(monkeypatch, platform):
    first = {"data": [{"id": "first"}], "meta": {"next_token": "cursor"},
             "paging": {"next": f"{instagram.BASE_URL}/123/media?after=cursor"}}
    client, _ = connector(platform, monkeypatch, [response(body=first), response(400)])
    with pytest.raises(SocialMediaError):
        client.get_posts(START, END)


def test_instagram_absolute_paging_url_preserves_partial_results(monkeypatch, caplog):
    first = {"data": [{"id": "first"}], "paging": {
        "next": "https://graph.facebook.com/v23.0/123/media?after=cursor",
    }}
    client, _ = connector("instagram", monkeypatch, [response(body=first), response(429)])
    assert client.get_posts(START, END)["id"].tolist() == ["first"]
    assert "partial" in caplog.text.lower()


def test_instagram_missing_account_metric_is_not_zero(monkeypatch):
    client, _ = connector("instagram", monkeypatch, [response(body={"data": [
        {"name": "reach", "values": [{"end_time": "2026-01-15", "value": 0}, {"end_time": "2026-01-16"}]},
        {"name": "follower_count", "values": [{"end_time": "2026-01-15"}, {"end_time": "2026-01-16", "value": 0}]},
    ]})])
    result = client.get_account_insights(START, END).set_index("date")
    assert result.loc["2026-01-15", "reach"] == 0
    assert result.loc["2026-01-16", "follower_count"] == 0
    assert pd.isna(result.loc["2026-01-16", "reach"])
    assert pd.isna(result.loc["2026-01-15", "follower_count"])


def test_x_missing_account_metrics_are_not_zero(monkeypatch):
    body = {"data": {"id": "123", "public_metrics": {"followers_count": 0}}}
    client, _ = connector("x", monkeypatch, [response(body=body), response(body=body)])
    info = client.get_account_info()
    assert info["followers_count"] == 0
    assert all(info[key] is None for key in ("following_count", "tweet_count", "listed_count", "like_count"))
    result = client.get_account_insights(START, END, metrics=["followers_count", "impressions"])
    assert result.loc[0, "followers_count"] == 0
    assert result.loc[0, "impressions"] is None


@pytest.mark.parametrize("kind", ["post", "story"])
@pytest.mark.parametrize("payload,expected", [
    ({"total_value": {"value": 12}}, 12),
    ({"values": [{"value": 0}]}, 0),
    ({"values": []}, None),
    ({"values": [{}]}, None),
])
def test_instagram_current_insight_response_shapes(monkeypatch, kind, payload, expected):
    responses = [response(body={"data": [{"name": "views", **payload}]})]
    if kind == "story":
        responses.insert(0, response(body={"data": [{"id": "story-1"}]}))
    client, _ = connector("instagram", monkeypatch, responses)
    if kind == "post":
        value = client.get_post_insights("post-1").loc[0, "value"]
    else:
        value = client.get_stories_insights().loc[0, "views"]
    assert value is None if expected is None else value == expected

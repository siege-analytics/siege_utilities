"""Instagram must not follow redirects off the Graph origin (#1794 review, #1439).

A fake transport adapter is mounted on the connector's real session, so Requests'
own redirect handling runs. No network is used and no credentials are real.
"""

import io
import json
import traceback
from datetime import date
from urllib.parse import urlsplit

import pytest
import requests
from requests.adapters import BaseAdapter

from siege_utilities.analytics.instagram import InstagramConnector, SocialMediaError


TOKEN = "DUMMY_1794_REDIRECT_SENTINEL"
GRAPH_HOSTS = {"graph.facebook.com", "graph.instagram.com"}
FOREIGN = f"https://evil.example.com/collect?access_token={TOKEN}"


def _response(request, status, body=None, location=None):
    response = requests.Response()
    response.status_code = status
    response.request = request
    response.url = request.url
    response.headers["Content-Type"] = "application/json"
    if location:
        response.headers["Location"] = location
    response._content = json.dumps(body if body is not None else {}).encode("utf-8")
    response._content_consumed = True
    response.raw = io.BytesIO(b"")
    response.encoding = "utf-8"
    return response


class FakeTransport(BaseAdapter):
    """Record every prepared request and answer from a route function."""

    def __init__(self, route):
        super().__init__()
        self.route = route
        self.sent = []

    def send(self, request, **kwargs):
        self.sent.append(request)
        return self.route(request)

    def close(self):
        pass


def _connector(route):
    transport = FakeTransport(route)
    connector = InstagramConnector(TOKEN, ig_user_id="123", retry_attempts=1, retry_backoff=0)
    connector._session.trust_env = False
    connector._session.mount("https://", transport)
    connector._session.mount("http://", transport)
    connector._authenticated = True
    return connector, transport


def _redirect_first(status, location):
    def route(request):
        if urlsplit(request.url).hostname in GRAPH_HOSTS:
            return _response(request, status, location=location)
        return _response(request, 200, {"data": [{"id": "stolen", "instagram_business_account": {"id": "x"}}]})
    return route


def _call(connector, entry_point):
    if entry_point == "posts":
        return connector.get_posts(date(2026, 1, 1), date(2026, 1, 31))
    if entry_point == "authenticate":
        connector._ig_user_id = None
        connector._authenticated = False
        return connector.authenticate()
    return connector._request_url("GET", "https://graph.facebook.com/v22.0/123/media")


@pytest.mark.parametrize("entry_point", ["direct", "posts", "authenticate"])
@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_graph_redirect_to_foreign_host_is_not_followed(caplog, entry_point, status):
    connector, transport = _connector(_redirect_first(status, FOREIGN))

    with pytest.raises(SocialMediaError, match="redirect") as caught:
        _call(connector, entry_point)

    assert [urlsplit(r.url).hostname for r in transport.sent] == ["graph.facebook.com"]
    assert all(TOKEN not in r.url for r in transport.sent)
    for text in (str(caught.value), repr(caught.value), "".join(traceback.format_exception(caught.value)), caplog.text):
        assert TOKEN not in text
        assert "evil.example.com" not in text
    if entry_point == "authenticate":
        assert connector._authenticated is False


def test_graph_to_graph_redirect_is_not_followed_either():
    location = f"https://graph.facebook.com/v23.0/123/media?access_token={TOKEN}"
    connector, transport = _connector(_redirect_first(302, location))

    with pytest.raises(SocialMediaError, match="redirect"):
        _call(connector, "direct")

    assert len(transport.sent) == 1


def test_official_graph_paging_still_works_over_the_transport():
    next_url = f"https://graph.instagram.com/v23.0/123/media?after=cursor&access_token={TOKEN}"

    def route(request):
        if "after=cursor" in request.url:
            return _response(request, 200, {"data": [{"id": "second", "timestamp": "2026-01-10T00:00:00+0000"}]})
        return _response(request, 200, {
            "data": [{"id": "first", "timestamp": "2026-01-20T00:00:00+0000"}],
            "paging": {"next": next_url},
        })

    connector, transport = _connector(route)

    posts = connector.get_posts(date(2026, 1, 1), date(2026, 1, 31))

    assert posts["id"].tolist() == ["first", "second"]
    assert [urlsplit(r.url).hostname for r in transport.sent] == ["graph.facebook.com", "graph.instagram.com"]
    assert all(r.headers["Authorization"] == f"Bearer {TOKEN}" for r in transport.sent)
    assert all(TOKEN not in r.url for r in transport.sent)

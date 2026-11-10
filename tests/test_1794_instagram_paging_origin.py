"""Instagram paging must never send the bearer token off the Graph origin (#1794, #1833)."""

import json
import traceback
from datetime import date
from urllib.parse import parse_qs, urlsplit

import pytest
import requests

from siege_utilities.analytics.instagram import InstagramConnector, SocialMediaError


# The only hosts allowed to receive the bearer token (spelled out, not imported).
GRAPH_HOSTS = {"graph.facebook.com", "graph.instagram.com"}
TOKEN = "DUMMY_1794_BEARER_SENTINEL"
START = date(2026, 1, 1)
END = date(2026, 1, 31)


@pytest.fixture
def transport(monkeypatch):
    """Inspect real prepared requests and replace every session send with a stub."""
    sent = []
    bodies = []

    def send(session, request, **kwargs):
        sent.append(request)
        parts = urlsplit(request.url)
        assert parts.scheme == "https" and parts.port in (None, 443), (
            "A non-HTTPS prepared request reached Session.send"
        )
        assert parts.hostname in GRAPH_HOSTS, "An off-origin prepared request reached Session.send"
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"
        assert TOKEN not in request.url
        assert bodies, "Unexpected extra request"
        response = requests.Response()
        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        response._content = json.dumps(bodies.pop(0)).encode("utf-8")
        response.request = request
        response.url = request.url
        return response

    monkeypatch.setattr(requests.Session, "send", send)
    with InstagramConnector(TOKEN, ig_user_id="123", retry_attempts=2, retry_backoff=0) as connector:
        connector._session.trust_env = False
        connector._authenticated = True
        yield connector, bodies, sent


def first_page(entry_point, next_url):
    """A trusted first response whose paging.next is the URL under test."""
    if entry_point == "authenticate":
        data = [{"id": "page-1", "name": "Unlinked page"}]
    elif entry_point == "insights":
        data = [{"name": "reach", "values": [{"end_time": "2026-01-02T00:00:00+0000", "value": 1}]}]
    else:
        data = [{"id": "first", "timestamp": "2026-01-20T00:00:00+0000"}]
    return {"data": data, "paging": {"next": next_url}}


def call(connector, entry_point, next_url):
    if entry_point == "posts":
        return connector.get_posts(START, END)
    if entry_point == "insights":
        return connector.get_account_insights(START, END, metrics=["reach"])
    if entry_point == "authenticate":
        connector._ig_user_id = None
        connector._authenticated = False
        return connector.authenticate()
    return connector._request_url("GET", next_url)


HOSTILE = [
    pytest.param("http://graph.facebook.com/v22.0/123/media", id="http-downgrade"),
    pytest.param("http://graph.instagram.com/v22.0/123/media", id="http-downgrade-instagram"),
    pytest.param("ftp://graph.facebook.com/collect", id="other-scheme"),
    pytest.param("https://evil.example.com/collect", id="foreign-host"),
    pytest.param("https://facebook.com/collect", id="parent-domain"),
    pytest.param("https://graph.facebook.com.evil.example.com/collect", id="host-suffix"),
    pytest.param("https://graph.instagram.com.evil.example.com/collect", id="host-suffix-instagram"),
    pytest.param("https://evilgraph.facebook.com/collect", id="host-prefix"),
    pytest.param("https://evil.graph.facebook.com/collect", id="subdomain"),
    pytest.param("https://graph.facebook.com./collect", id="trailing-dot"),
    pytest.param("https://graph%2Efacebook.com/collect", id="percent-encoded-host"),
    pytest.param("https://graph.facebοok.com/collect", id="unicode-lookalike"),
    pytest.param("https://graph.facebook.com@evil.example.com/collect", id="host-in-userinfo"),
    pytest.param("https://graph.facebook.com:443@evil.example.com/collect", id="host-port-in-userinfo"),
    pytest.param("https://evil.example.com\\@graph.facebook.com/collect", id="backslash-userinfo"),
    pytest.param("https://dummy:password@graph.facebook.com/collect", id="userinfo"),
    pytest.param("https://dummy@graph.instagram.com/collect", id="username-only"),
    pytest.param("https://graph.facebook.com:444/collect", id="alternate-port"),
    pytest.param("https://graph.instagram.com:8443/collect", id="alternate-port-instagram"),
    pytest.param("https://graph.facebook.com:80/collect", id="http-port"),
    pytest.param("https://graph.facebook.com:bad/collect", id="invalid-port"),
    pytest.param("https://graph.facebook.com:65536/collect", id="port-out-of-range"),
    pytest.param("https://[graph.facebook.com/collect", id="malformed-host"),
    pytest.param("//graph.facebook.com/v22.0/123/media", id="scheme-relative"),
    pytest.param("/v22.0/123/media", id="relative"),
]


@pytest.mark.parametrize("entry_point", ["posts", "authenticate", "insights", "direct"])
@pytest.mark.parametrize("target", HOSTILE)
def test_untrusted_url_raises_before_send(transport, caplog, entry_point, target):
    connector, bodies, sent = transport
    next_url = f"{target}?after=cursor&access_token={TOKEN}"
    bodies.extend([first_page(entry_point, next_url), {"data": []}])

    with pytest.raises(SocialMediaError, match=r"HTTPS Graph origin") as caught:
        call(connector, entry_point, next_url)

    # Paging sends only the first, trusted request; direct calls send nothing.
    assert len(sent) == (0 if entry_point == "direct" else 1)
    assert TOKEN not in str(caught.value)
    assert TOKEN not in repr(caught.value)
    assert TOKEN not in "".join(traceback.format_exception(caught.value))
    assert TOKEN not in caplog.text
    if entry_point == "authenticate":
        assert connector._authenticated is False
        assert connector._ig_user_id is None


@pytest.mark.parametrize("origin", [
    "https://graph.facebook.com",
    "https://graph.facebook.com:443",
    "https://GRAPH.FACEBOOK.COM",
    "https://graph.instagram.com",
])
def test_graph_paging_follows_next_url_with_bearer_header(transport, origin):
    connector, bodies, sent = transport
    next_url = f"{origin}/v23.0/123/media?after=cursor&access_token={TOKEN}"
    bodies.extend([
        first_page("posts", next_url),
        {"data": [{"id": "second", "timestamp": "2026-01-10T00:00:00+0000"}]},
    ])

    posts = connector.get_posts(START, END)

    assert posts["id"].tolist() == ["first", "second"]
    assert len(sent) == 2
    assert urlsplit(sent[1].url).path == "/v23.0/123/media"
    assert parse_qs(urlsplit(sent[1].url).query) == {"after": ["cursor"]}
    assert all(request.headers["Authorization"] == f"Bearer {TOKEN}" for request in sent)


def test_authenticate_follows_trusted_next_to_linked_page(transport):
    connector, bodies, sent = transport
    bodies.extend([
        first_page("authenticate", f"https://graph.facebook.com/v23.0/me/accounts?after=25&access_token={TOKEN}"),
        {"data": [{"id": "page-26", "name": "Linked", "instagram_business_account": {"id": "ig-9"}}]},
    ])

    call(connector, "authenticate", None)

    assert connector._authenticated is True
    assert connector._ig_user_id == "ig-9"
    assert len(sent) == 2

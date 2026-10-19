"""Instagram paging must never send credentials outside the Graph origin (#1833)."""

import json
import traceback
from datetime import date
from urllib.parse import parse_qs, urlsplit

import pytest
import requests

from siege_utilities.analytics.instagram import InstagramConnector, SocialMediaError


TOKEN = "DUMMY_1833_BEARER_SENTINEL"
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
        assert (parts.scheme, parts.hostname, parts.port or 443) == (
            "https", "graph.facebook.com", 443,
        ), "An off-origin prepared request reached Session.send"
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
    with InstagramConnector(
        TOKEN, ig_user_id="123", retry_attempts=2, retry_backoff=0,
    ) as connector:
        connector._session.trust_env = False
        connector._authenticated = True
        yield connector, bodies, sent


@pytest.mark.parametrize("entry_point", ["paging", "absolute"])
@pytest.mark.parametrize("target", [
    pytest.param("http://graph.facebook.com/v22.0/123/media", id="http"),
    pytest.param("https://evil.example.com/collect", id="foreign-host"),
    pytest.param("https://graph.facebook.com.evil.example.com/collect", id="host-suffix"),
    pytest.param("https://evilgraph.facebook.com/collect", id="host-prefix"),
    pytest.param("https://evil.graph.facebook.com/collect", id="subdomain"),
    pytest.param("https://graph.facebook.com@evil.example.com/collect", id="host-in-userinfo"),
    pytest.param("https://dummy:password@graph.facebook.com/collect", id="userinfo"),
    pytest.param("https://graph.facebook.com:444/collect", id="alternate-port"),
    pytest.param("https://graph.facebook.com:80/collect", id="http-port"),
    pytest.param("https://graph.facebook.com:bad/collect", id="invalid-port"),
    pytest.param("https://graph.facebook.com:65536/collect", id="port-out-of-range"),
    pytest.param("https://[graph.facebook.com/collect", id="malformed-host"),
    pytest.param("//graph.facebook.com/v22.0/123/media", id="scheme-relative"),
    pytest.param("/v22.0/123/media", id="relative"),
    pytest.param("ftp://graph.facebook.com/collect", id="other-scheme"),
])
def test_untrusted_url_raises_before_send(transport, caplog, entry_point, target):
    connector, bodies, sent = transport
    next_url = f"{target}?after=cursor&access_token={TOKEN}"
    bodies.extend([
        {"data": [{"id": "first"}], "paging": {"next": next_url}},
        {"data": [{"id": "second"}]},
    ])

    with pytest.raises(SocialMediaError, match=r"HTTPS graph\.facebook\.com origin") as caught:
        if entry_point == "paging":
            connector.get_posts(START, END)
        else:
            connector._request_url("GET", next_url)

    # Paging sends only the first, trusted request; direct calls send nothing.
    assert len(sent) == (1 if entry_point == "paging" else 0)
    assert all(urlsplit(request.url).hostname == "graph.facebook.com" for request in sent)
    assert TOKEN not in str(caught.value)
    assert TOKEN not in repr(caught.value)
    assert TOKEN not in "".join(traceback.format_exception(caught.value))
    assert TOKEN not in caplog.text


@pytest.mark.parametrize("origin", [
    "https://graph.facebook.com",
    "https://graph.facebook.com:443",
    "https://GRAPH.FACEBOOK.COM",
])
def test_graph_paging_follows_next_url_with_bearer_header(transport, origin):
    connector, bodies, sent = transport
    bodies.extend([
        {"data": [{"id": "first"}], "paging": {
            "next": f"{origin}/v23.0/123/media?after=cursor&access_token={TOKEN}",
        }},
        {"data": [{"id": "second"}]},
    ])

    posts = connector.get_posts(START, END)

    assert posts["id"].tolist() == ["first", "second"]
    assert len(sent) == 2
    assert urlsplit(sent[1].url).path == "/v23.0/123/media"
    assert parse_qs(urlsplit(sent[1].url).query) == {"after": ["cursor"]}
    assert all(request.headers["Authorization"] == f"Bearer {TOKEN}" for request in sent)

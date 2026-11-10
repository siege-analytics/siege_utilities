"""Instagram token exchange keeps credentials out of urllib3 DEBUG logs.

Meta's long-lived token exchange is a GET with ``client_secret`` and
``fb_exchange_token`` in the query string. urllib3 logs each request's full
path and query at DEBUG (the request line, ``Retry: <url>``), so enabling
DEBUG on ``urllib3.connectionpool`` would record both credentials. The fake
transport below emits urllib3's exact log calls through the real urllib3
logger with the URL requests would send. Synthetic values; no network.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any
from unittest.mock import Mock

import pytest
import requests

from siege_utilities.analytics import instagram
from siege_utilities.analytics._social_protocol import SocialMediaError

APP_SECRET = "SYNTHETIC_APP_SECRET_6d1e"
OLD_TOKEN = "SYNTHETIC_LOGIN_TOKEN_93ab"
NEW_TOKEN = "SYNTHETIC_RENEWED_TOKEN_51fc"
POOL = logging.getLogger("urllib3.connectionpool")


def _reply(status: int, body: dict[str, Any]) -> requests.Response:
    result = requests.Response()
    result.status_code = status
    result._content = json.dumps(body).encode()
    return result


def _urllib3_transport(*replies: requests.Response) -> Mock:
    """A session.request stand-in that logs as urllib3 2.x does, then replies."""
    pending = list(replies)

    def send(method: str, url: str, params: Any = None, **_: Any) -> requests.Response:
        path_url = requests.Request(method, url, params=params).prepare().path_url
        if len(pending) > 1:
            POOL.debug("Retry: %s", path_url)
        reply = pending.pop(0)
        POOL.debug('%s://%s:%s "%s %s %s" %s %s', "https", "graph.facebook.com", 443,
                   method, path_url, "HTTP/1.1", reply.status_code, None)
        return reply

    return Mock(side_effect=send)


@pytest.fixture
def connector(monkeypatch: pytest.MonkeyPatch) -> Iterator[instagram.InstagramConnector]:
    client = instagram.InstagramConnector(
        OLD_TOKEN, ig_user_id="123", app_id="SYNTHETIC_APP_ID", app_secret=APP_SECRET,
        retry_attempts=2, retry_backoff=0,
    )
    client._authenticated = True
    monkeypatch.setattr(instagram.time, "sleep", Mock())
    yield client
    client.close()


def _pool_text(caplog: pytest.LogCaptureFixture) -> str:
    return "\n".join(r.getMessage() for r in caplog.records if r.name == POOL.name)


def test_urllib3_debug_lines_during_exchange_omit_credentials(
    connector: instagram.InstagramConnector, caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger=POOL.name)
    connector._session.request = _urllib3_transport(
        _reply(500, {}), _reply(200, {"access_token": NEW_TOKEN, "expires_in": 60}),
    )
    assert connector.refresh_access_token() == NEW_TOKEN
    text = _pool_text(caplog)
    assert "/oauth/access_token" in text and "Retry:" in text  # urllib3 lines were emitted
    for secret in (APP_SECRET, OLD_TOKEN):
        assert secret not in text
        assert secret not in caplog.text
    assert "client_secret=[REDACTED]" in text and "fb_exchange_token=[REDACTED]" in text


def test_redaction_is_removed_after_the_exchange_even_on_failure(
    connector: instagram.InstagramConnector,
) -> None:
    before = list(POOL.filters)
    connector._session.request = _urllib3_transport(_reply(400, {"error": {"message": "bad"}}))
    with pytest.raises(SocialMediaError):
        connector.refresh_access_token()
    assert POOL.filters == before
    connector._session.request = _urllib3_transport(
        _reply(200, {"access_token": NEW_TOKEN, "expires_in": 60}),
    )
    connector.refresh_access_token()
    assert POOL.filters == before


def test_unrenderable_urllib3_record_is_suppressed_not_raised(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger=POOL.name)
    with instagram._urllib3_url_secrets_redacted():
        POOL.debug("%s %s", "/oauth/access_token?client_secret=" + APP_SECRET)  # one arg short
    assert APP_SECRET not in caplog.text
    assert instagram._URLLIB3_UNRENDERABLE in _pool_text(caplog)

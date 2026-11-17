"""Instagram token exchange keeps credentials out of urllib3 DEBUG logs.

Meta's long-lived token exchange is a GET with ``client_secret`` and
``fb_exchange_token`` in the query string, and urllib3 logs each request's
full path and query at DEBUG. These tests run the real call path:
``refresh_access_token`` -> ``requests`` -> urllib3's HTTPS connection pool,
including urllib3's own ``log.debug`` calls, for the real
``https://graph.facebook.com/...`` URL. They capture the native
``urllib3.connectionpool`` records. The real ``HTTPSConnectionPool`` runs, but
its ``ConnectionCls`` is replaced with a plain-HTTP ``HTTPConnection`` to a
local Graph stand-in. There is no TLS handshake: these tests prove the native
DEBUG sink and its redaction, not TLS or provider acceptance. Synthetic
sentinel credentials; no external network.
"""
from __future__ import annotations

import json
import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from unittest.mock import Mock

import pytest
import urllib3
from urllib3.connection import HTTPConnection

from siege_utilities.analytics import instagram
from siege_utilities.analytics._social_protocol import SocialMediaError

APP_SECRET = "SYNTHETIC_APP_SECRET_6d1e"
OLD_TOKEN = "SYNTHETIC_LOGIN_TOKEN_93ab"
NEW_TOKEN = "SYNTHETIC_RENEWED_TOKEN_51fc"
POOL = logging.getLogger("urllib3.connectionpool")

pytestmark = pytest.mark.filterwarnings("ignore::urllib3.exceptions.InsecureRequestWarning")


class _GraphStandIn(BaseHTTPRequestHandler):
    """Answers the exchange: queued statuses first, then a valid token body."""

    statuses: list[int] = []
    seen_paths: list[str] = []

    def do_GET(self) -> None:  # noqa: N802 - http.server naming
        type(self).seen_paths.append(self.path)
        status = type(self).statuses.pop(0) if type(self).statuses else 200
        body = (json.dumps({"access_token": NEW_TOKEN, "expires_in": 60}) if status == 200
                else json.dumps({"error": {"message": "temporarily unavailable"}})).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # silence the stand-in itself
        return


@pytest.fixture
def graph_socket(monkeypatch: pytest.MonkeyPatch) -> Iterator[type[_GraphStandIn]]:
    """Route urllib3 HTTPS pool sockets to a local plain-HTTP Graph stand-in."""
    _GraphStandIn.statuses, _GraphStandIn.seen_paths = [], []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _GraphStandIn)
    port = server.server_address[1]
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()

    class LocalSocketConnection(HTTPConnection):
        # The HTTPS pool passes TLS settings; a plain socket ignores them.
        def __init__(self, host: str, port_: int | None = None, **kwargs: Any) -> None:
            kept = {k: kwargs[k] for k in ("timeout", "source_address", "blocksize", "socket_options")
                    if k in kwargs}
            super().__init__("127.0.0.1", port, **kept)

    monkeypatch.setattr(urllib3.connectionpool.HTTPSConnectionPool, "ConnectionCls", LocalSocketConnection)
    for proxy in ("HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(proxy, raising=False)
    monkeypatch.setattr(instagram.time, "sleep", Mock())
    try:
        yield _GraphStandIn
    finally:
        server.shutdown()
        server.server_close()
        worker.join(5)


@pytest.fixture
def connector() -> Iterator[instagram.InstagramConnector]:
    client = instagram.InstagramConnector(
        OLD_TOKEN, ig_user_id="123", app_id="SYNTHETIC_APP_ID", app_secret=APP_SECRET,
        retry_attempts=2, retry_backoff=0,
    )
    client._authenticated = True
    yield client
    client.close()


class _PoolRecords(logging.Handler):
    """Collects urllib3.connectionpool records on that logger itself."""

    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def messages(self) -> list[str]:
        return [r.getMessage() for r in self.records]


@contextmanager
def _capture_pool_records() -> Iterator[_PoolRecords]:
    """Capture urllib3.connectionpool DEBUG records whatever earlier tests did to logging.

    In a full run, configuring the test Django project applies
    ``disable_existing_loggers=True``, which disables this origin logger, so it
    emits no records and caplog sees nothing. This re-enables the logger and
    attaches its own handler to it, and restores every setting it changed on
    exit.
    """
    previous_disable = logging.root.manager.disable
    previous_disabled, previous_level = POOL.disabled, POOL.level
    logging.disable(logging.NOTSET)
    POOL.disabled = False
    POOL.setLevel(logging.DEBUG)
    collector = _PoolRecords()
    POOL.addHandler(collector)
    try:
        yield collector
    finally:
        POOL.removeHandler(collector)
        POOL.setLevel(previous_level)
        POOL.disabled = previous_disabled
        logging.disable(previous_disable)


@pytest.fixture
def pool_records() -> Iterator[_PoolRecords]:
    with _capture_pool_records() as collector:
        yield collector


def test_native_urllib3_debug_records_omit_exchange_credentials(
    graph_socket: type[_GraphStandIn], connector: instagram.InstagramConnector,
    pool_records: _PoolRecords,
) -> None:
    graph_socket.statuses = [503]  # one connector retry, so two native request lines
    assert connector.refresh_access_token() == NEW_TOKEN

    # The stand-in really received the credentials in the query string ...
    assert len(graph_socket.seen_paths) == 2
    assert all(APP_SECRET in path and OLD_TOKEN in path for path in graph_socket.seen_paths)
    # ... and urllib3 itself logged both requests for the real Graph origin.
    lines = [m for m in pool_records.messages() if '"GET /' in m]
    assert len(lines) == 2, pool_records.messages()
    assert all(m.startswith("https://graph.facebook.com:443 ") and "/oauth/access_token?" in m for m in lines)
    # No native record carries either credential, in its message or raw args.
    for secret in (APP_SECRET, OLD_TOKEN):
        assert all(secret not in m for m in pool_records.messages())
        assert all(secret not in repr(r.args) for r in pool_records.records)
    assert all("client_secret=[REDACTED]" in m and "fb_exchange_token=[REDACTED]" in m for m in lines)


def test_capture_works_after_logging_was_disabled_by_earlier_setup(
    monkeypatch: pytest.MonkeyPatch, graph_socket: type[_GraphStandIn],
    connector: instagram.InstagramConnector,
) -> None:
    # The state the test Django project leaves behind in a full run: the
    # urllib3 logger disabled and its parent no longer propagating.
    monkeypatch.setattr(POOL, "disabled", True)
    monkeypatch.setattr(logging.getLogger("urllib3"), "propagate", False)
    with _capture_pool_records() as collector:
        connector.refresh_access_token()
    lines = [m for m in collector.messages() if '"GET /' in m]
    assert len(lines) == 1 and "client_secret=[REDACTED]" in lines[0]
    assert APP_SECRET not in lines[0] and OLD_TOKEN not in lines[0]
    assert POOL.disabled is True  # the capture restored the prior state


def test_redaction_is_removed_after_the_exchange_even_on_failure(
    graph_socket: type[_GraphStandIn], connector: instagram.InstagramConnector,
) -> None:
    before = list(POOL.filters)
    graph_socket.statuses = [400]
    with pytest.raises(SocialMediaError):
        connector.refresh_access_token()
    assert POOL.filters == before
    connector.refresh_access_token()
    assert POOL.filters == before


def test_unrenderable_urllib3_record_is_suppressed_not_raised(pool_records: _PoolRecords) -> None:
    with instagram._urllib3_url_secrets_redacted():
        POOL.debug("%s %s", "/oauth/access_token?client_secret=" + APP_SECRET)  # one arg short
    assert pool_records.messages() == [instagram._URLLIB3_UNRENDERABLE]
    assert all(APP_SECRET not in repr(r.args) for r in pool_records.records)

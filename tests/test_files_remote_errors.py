"""Error-path coverage (SU-4b) for siege_utilities.files.remote.

Forces:
- generate_local_path_from_url ValueError when no filename in the URL
- download_file_with_retry: the (OSError, ConnectionError, ValueError) retry
  handler and the final ConnectionError after attempts are exhausted;
  SSL failures propagate immediately without retrying or changing their type
- get_file_info ConnectionError on a non-ok HTTP response
- is_downloadable: both except handlers (info-check and GET) -> returns False
- download_file: an SSL verification failure with verify_ssl=True raises and
  never silently retries with verify=False (#1456 MITM downgrade), and the
  explicit allow_insecure_fallback opt-in is the only path that downgrades
"""

import logging

import pytest

import siege_utilities.files.remote as remote


class _FakeResp:
    def __init__(self, *, ok=True, status_code=200, headers=None):
        self.ok = ok
        self.status_code = status_code
        self.headers = headers or {}


class _FakeStreamResp:
    """Minimal streaming response usable as a context manager."""

    def __init__(self, *, body=b"data", ok=True, status_code=200, reason="OK", headers=None):
        self._body = body
        self.ok = ok
        self.status_code = status_code
        self.reason = reason
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_content(self, chunk_size=8192):
        yield self._body


def test_download_file_ssl_failure_raises_without_insecure_retry(tmp_path, monkeypatch):
    """#1456: verify_ssl=True must raise on SSL failure, never downgrade.

    On v4.0.0 the SSLError handler silently retried with verify=False and
    returned success; this test fails there (no exception, verify=False used,
    attacker bytes written). After the fix it passes.
    """
    out = tmp_path / "f.zip"
    calls = []

    def fake_get(url, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise remote.requests.exceptions.SSLError("certificate verify failed")
        # Only reached by the (removed) silent insecure retry path.
        return _FakeStreamResp(body=b"attacker-controlled-bytes")

    monkeypatch.setattr(remote.requests, "get", fake_get)

    with pytest.raises(remote.requests.exceptions.SSLError):
        remote.download_file(str("https://example.test/f.zip"), out, verify_ssl=True)

    # No unverified retry occurred.
    assert len(calls) == 1
    assert all(c.get("verify") is not False for c in calls)
    # No body was written.
    assert not out.exists()


def test_download_file_insecure_fallback_opt_in_retries_and_logs_error(tmp_path, monkeypatch, caplog):
    """The explicit opt-in (default OFF) is the only downgrade path; logs ERROR."""
    out = tmp_path / "f.zip"
    calls = []

    def fake_get(url, **kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise remote.requests.exceptions.SSLError("certificate verify failed")
        return _FakeStreamResp(body=b"payload")

    monkeypatch.setattr(remote.requests, "get", fake_get)

    with caplog.at_level(logging.ERROR, logger=remote.log.name):
        result = remote.download_file(
            "https://example.test/f.zip", out,
            verify_ssl=True, allow_insecure_fallback=True,
        )

    assert result == str(out)
    assert len(calls) == 2
    assert calls[0].get("verify") is not False  # first attempt verified
    assert calls[1].get("verify") is False  # explicit insecure retry
    assert out.read_bytes() == b"payload"
    assert any(rec.levelno == logging.ERROR for rec in caplog.records)


@pytest.mark.parametrize("url", ["https://example.com", "https://example.com/", "https://host"])
def test_generate_local_path_rejects_url_without_filename(url, tmp_path):
    with pytest.raises(ValueError) as exc_info:
        remote.generate_local_path_from_url(url, tmp_path)
    assert "Could not extract filename" in str(exc_info.value)


def test_download_file_with_retry_ssl_failure_raises_without_retry(tmp_path, monkeypatch):
    """SSL failures must bypass the OSError retry handler unchanged."""
    out = tmp_path / "f.zip"
    calls = []
    ssl_error = remote.requests.exceptions.SSLError("certificate verify failed")

    def fake_get(url, **kwargs):
        calls.append(kwargs)
        raise ssl_error

    monkeypatch.setattr(remote.requests, "get", fake_get)

    with pytest.raises(remote.requests.exceptions.SSLError, match="certificate verify failed") as exc_info:
        try:
            remote.download_file_with_retry(
                "https://example.test/f.zip", out, verify_ssl=True, retry_delay=0,
            )
        finally:
            # Check side effects even if the wrapper raises the wrong exception.
            assert len(calls) == 1
            assert all(c.get("verify") is not False for c in calls)
            assert not out.exists()

    assert exc_info.value is ssl_error


def test_download_file_with_retry_raises_after_attempts(tmp_path, monkeypatch):
    calls = {"n": 0}

    def always_fail(url, local_filename, **kwargs):
        calls["n"] += 1
        raise ConnectionError("refused")

    monkeypatch.setattr(remote, "download_file", always_fail)

    with pytest.raises(ConnectionError) as exc_info:
        remote.download_file_with_retry(
            "https://example.test/f.zip",
            tmp_path / "f.zip",
            max_retries=1,
            retry_delay=0,  # avoid real sleep between attempts
        )
    assert "failed after 2 attempts" in str(exc_info.value)
    assert calls["n"] == 2  # initial attempt + one retry


def test_get_file_info_raises_on_non_ok_response(monkeypatch):
    monkeypatch.setattr(
        remote.requests, "head",
        lambda *a, **k: _FakeResp(ok=False, status_code=404),
    )
    with pytest.raises(ConnectionError) as exc_info:
        remote.get_file_info("https://example.test/missing.zip")
    assert "HTTP 404" in str(exc_info.value)


def test_is_downloadable_returns_false_when_both_paths_fail(monkeypatch):
    def info_fails(url, timeout=10):
        raise ConnectionError("head failed")

    def get_fails(*a, **k):
        raise OSError("get failed")

    monkeypatch.setattr(remote, "get_file_info", info_fails)
    monkeypatch.setattr(remote.requests, "get", get_fails)

    assert remote.is_downloadable("https://example.test/x.zip") is False

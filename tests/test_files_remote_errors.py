"""Error-path coverage (SU-4b) for siege_utilities.files.remote.

Forces:
- generate_local_path_from_url ValueError when no filename in the URL
- download_file_with_retry: the (OSError, ConnectionError, ValueError) retry
  handler and the final ConnectionError after attempts are exhausted
- get_file_info ConnectionError on a non-ok HTTP response
- is_downloadable: both except handlers (info-check and GET) -> returns False
"""

import pytest

import siege_utilities.files.remote as remote


class _FakeResp:
    def __init__(self, *, ok=True, status_code=200, headers=None):
        self.ok = ok
        self.status_code = status_code
        self.headers = headers or {}


@pytest.mark.parametrize("url", ["https://example.com", "https://example.com/", "https://host"])
def test_generate_local_path_rejects_url_without_filename(url, tmp_path):
    with pytest.raises(ValueError) as exc_info:
        remote.generate_local_path_from_url(url, tmp_path)
    assert "Could not extract filename" in str(exc_info.value)


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

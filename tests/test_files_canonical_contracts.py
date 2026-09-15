"""Canonical contract tests for public file helpers tracked by #1203."""

import hashlib
import subprocess

import pytest

from siege_utilities import download_file
from siege_utilities import download_file_with_retry
from siege_utilities import get_file_info
from siege_utilities import get_quick_file_signature
from siege_utilities import is_downloadable
from siege_utilities import run_command
import siege_utilities.files.remote as remote


USER_AGENT = "siege_utilities/1.0 (Census/GIS data client)"


class _Response:
    def __init__(
        self,
        *,
        ok=True,
        status_code=200,
        reason="OK",
        headers=None,
        chunks=(),
    ):
        self.ok = ok
        self.status_code = status_code
        self.reason = reason
        self.headers = headers or {}
        self._chunks = list(chunks)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def iter_content(self, chunk_size=8192):
        yield from self._chunks


def test_download_file_writes_streamed_chunks_from_canonical_import(
    tmp_path,
    monkeypatch,
):
    target = tmp_path / "payload.bin"
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return _Response(
            headers={"content-length": "11"},
            chunks=[b"hello", b"", b" world"],
        )

    monkeypatch.setattr(remote.requests, "get", fake_get)
    monkeypatch.setattr(remote, "_get_ssl_verify_path", lambda: True)

    result = download_file(
        "https://example.test/payload.bin",
        target,
        chunk_size=3,
        timeout=7,
    )

    assert result == str(target)
    assert target.read_bytes() == b"hello world"
    assert calls == [
        (
            "https://example.test/payload.bin",
            {
                "stream": True,
                "allow_redirects": True,
                "timeout": 7,
                "verify": True,
                "headers": {"User-Agent": USER_AGENT},
            },
        )
    ]


def test_download_file_with_retry_returns_after_retry_from_canonical_import(
    tmp_path,
    monkeypatch,
):
    attempts = []

    def flaky_download(url, local_filename, **kwargs):
        attempts.append((url, local_filename, kwargs))
        if len(attempts) == 1:
            raise OSError("temporary disk/network failure")
        return str(local_filename)

    sleep_calls = []

    def fake_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(remote, "download_file", flaky_download)
    monkeypatch.setattr("time.sleep", fake_sleep)

    result = download_file_with_retry(
        "https://example.test/retry.bin",
        tmp_path / "retry.bin",
        max_retries=2,
        retry_delay=3,
        timeout=5,
    )

    assert result.endswith("retry.bin")
    assert len(attempts) == 2
    assert attempts[1][2] == {"timeout": 5}
    assert sleep_calls == [3]


def test_get_file_info_and_is_downloadable_use_head_metadata(monkeypatch):
    def fake_head(url, **kwargs):
        assert url == "https://example.test/data.csv"
        assert kwargs == {"timeout": 4, "allow_redirects": True}
        return _Response(
            headers={
                "content-length": "12",
                "content-type": "text/csv",
                "last-modified": "Mon, 14 Sep 2026 12:00:00 GMT",
                "etag": '"abc123"',
            }
        )

    monkeypatch.setattr(remote.requests, "head", fake_head)

    info = get_file_info("https://example.test/data.csv", timeout=4)

    assert info == {
        "url": "https://example.test/data.csv",
        "size": 12,
        "content_type": "text/csv",
        "last_modified": "Mon, 14 Sep 2026 12:00:00 GMT",
        "etag": '"abc123"',
    }
    assert (
        is_downloadable("https://example.test/data.csv", timeout=4) is True
    )


def test_is_downloadable_falls_back_to_get_when_head_has_no_size(monkeypatch):
    monkeypatch.setattr(
        remote,
        "get_file_info",
        lambda url, timeout=10: {
            "url": url,
            "size": 0,
            "content_type": "unknown",
        },
    )
    get_calls = []

    def fake_get(*args, **kwargs):
        get_calls.append((args, kwargs))
        return _Response(ok=True)

    monkeypatch.setattr(remote.requests, "get", fake_get)

    assert is_downloadable("https://example.test/stream", timeout=2) is True
    assert get_calls == [
        (
            ("https://example.test/stream",),
            {"stream": True, "timeout": 2},
        )
    ]


def test_get_quick_file_signature_hashes_large_file_contract(tmp_path):
    payload = (
        (b"a" * (64 * 1024))
        + (b"middle" * 200_000)
        + (b"z" * (64 * 1024))
    )
    path = tmp_path / "large.bin"
    path.write_bytes(payload)

    stat = path.stat()
    expected = hashlib.sha256()
    expected.update(payload[: 64 * 1024])
    expected.update(payload[-64 * 1024:])
    expected.update(f"{stat.st_size}_{stat.st_mtime}_{64 * 1024}".encode())

    assert get_quick_file_signature(path) == expected.hexdigest()


def test_run_command_uses_argv_execution_without_shell_from_canonical_import():
    list_result = run_command(["echo", "canonical"], allow_list={"echo"})

    assert isinstance(list_result, subprocess.CompletedProcess)
    assert list_result.returncode == 0
    assert list_result.stdout.strip() == "canonical"

    string_result = run_command("echo safe-string", allow_list={"echo"})

    assert isinstance(string_result, subprocess.CompletedProcess)
    assert string_result.returncode == 0
    assert string_result.stdout.strip() == "safe-string"


def test_run_command_rejects_unsafe_string_shell_metacharacters():
    with pytest.raises(ValueError, match="shell metacharacters"):
        run_command("echo canonical | cat", unsafe=True)

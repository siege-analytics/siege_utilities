"""RDH must never publish an interrupted or incomplete download to its cache."""

import gzip
import os
import stat
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Optional
from unittest.mock import Mock

import pytest
import requests
from requests.structures import CaseInsensitiveDict

from siege_utilities.geo.providers.redistricting_data_hub import RDHClient


URL = "https://redistrictingdatahub.org/files/precincts.csv"
CONTENT = b"GEOID,votes\n51001,42\n"
POSIX_ONLY = pytest.mark.skipif(
    os.name != "posix", reason="checks POSIX permission bits, which need a POSIX umask"
)


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[RDHClient]:
    with RDHClient(username="test-user", password="test-pass", cache_dir=tmp_path) as client:
        monkeypatch.setattr(client, "_session", Mock(spec=requests.Session))
        yield client


@pytest.fixture
def umask() -> Iterator[Callable[[int], int]]:
    """Let a test set the process umask; restore the original afterwards."""
    original = os.umask(0o022)
    os.umask(original)
    yield os.umask
    os.umask(original)


def _response_for(
    client: RDHClient, chunks: Iterable[bytes], content_length: Optional[int],
    content_encoding: Optional[str] = None,
) -> Mock:
    response = Mock(spec=requests.Response)
    # requests matches header names case-insensitively; so do these tests.
    response.headers = CaseInsensitiveDict(
        {} if content_length is None else {"content-length": str(content_length)}
    )
    if content_encoding is not None:
        response.headers["content-encoding"] = content_encoding
    response.iter_content.return_value = chunks
    client._session.get.return_value = response
    return response


@pytest.mark.parametrize("error_type", [requests.Timeout, OSError, KeyboardInterrupt])
def test_interrupted_download_leaves_no_cache_or_temp_file(
    client: RDHClient, error_type: type[BaseException],
) -> None:
    def interrupted_chunks() -> Iterator[bytes]:
        yield CONTENT[:8]
        raise error_type("stream interrupted")

    response = _response_for(client, interrupted_chunks(), len(CONTENT))
    dest = client.cache_dir / "precincts.csv"

    with pytest.raises(error_type, match="stream interrupted"):
        client.download_dataset(URL, use_cache=True)

    assert not dest.exists()
    assert list(client.cache_dir.iterdir()) == []
    response.close.assert_called_once()


@pytest.mark.parametrize("content_encoding", [None, "identity", " Identity "])
@pytest.mark.parametrize("content_length", [len(CONTENT) + 1, len(CONTENT) - 1])
def test_size_mismatch_leaves_no_cache_or_temp_file(
    client: RDHClient, content_length: int, content_encoding: Optional[str],
) -> None:
    response = _response_for(client, [CONTENT], content_length, content_encoding)
    dest = client.cache_dir / "precincts.csv"

    with pytest.raises(requests.RequestException, match="Content-Length"):
        client.download_dataset(URL, use_cache=True)

    assert not dest.exists()
    assert list(client.cache_dir.iterdir()) == []
    response.close.assert_called_once()


@pytest.mark.parametrize("content_length", [len(CONTENT), None])
def test_complete_download_is_published_then_reused(
    client: RDHClient, content_length: Optional[int],
) -> None:
    dest = client.cache_dir / "precincts.csv"

    def complete_chunks() -> Iterator[bytes]:
        yield CONTENT[:8]
        assert not dest.exists()
        yield b""
        yield CONTENT[8:]
        assert not dest.exists()

    response = _response_for(client, complete_chunks(), content_length)

    assert client.download_dataset(URL, use_cache=True) == dest
    assert dest.read_bytes() == CONTENT
    assert list(client.cache_dir.iterdir()) == [dest]
    assert client.download_dataset(URL, use_cache=True) == dest
    assert dest.read_bytes() == CONTENT
    client._session.get.assert_called_once()
    response.close.assert_called_once()


ENCODINGS = ["gzip", "GZIP", "x-gzip", "br", "gzip, identity", "compress"]


@pytest.mark.parametrize("content_encoding", ENCODINGS)
def test_encoded_response_is_checked_by_the_bytes_received(
    client: RDHClient, content_encoding: str,
) -> None:
    # A server may encode the body even though identity was requested.
    # requests may yield decoded bytes, while Content-Length counts the bytes
    # on the wire, so the wire count is compared, not the bytes written.
    encoded_length = len(gzip.compress(CONTENT))
    assert encoded_length != len(CONTENT)
    response = _response_for(client, [CONTENT], encoded_length, content_encoding)
    response.raw = Mock()
    response.raw.tell.return_value = encoded_length
    dest = client.cache_dir / "precincts.csv"

    assert client.download_dataset(URL, use_cache=True) == dest

    assert dest.read_bytes() == CONTENT
    assert list(client.cache_dir.iterdir()) == [dest]
    response.close.assert_called_once()


@pytest.mark.parametrize("content_encoding", ENCODINGS)
def test_truncated_encoded_response_leaves_no_cache_or_temp_file(
    client: RDHClient, content_encoding: str,
) -> None:
    # A transport that does not enforce Content-Length (urllib3 1.26 by
    # default) can end an encoded body early without raising; the wire count
    # still shows the shortfall.
    encoded_length = len(gzip.compress(CONTENT))
    response = _response_for(client, [CONTENT[:8]], encoded_length, content_encoding)
    response.raw = Mock()
    response.raw.tell.return_value = encoded_length - 5

    with pytest.raises(requests.RequestException, match="Content-Length mismatch"):
        client.download_dataset(URL, use_cache=True)

    assert list(client.cache_dir.iterdir()) == []


def test_encoded_response_without_a_wire_count_is_rejected(client: RDHClient) -> None:
    response = _response_for(client, [CONTENT], len(gzip.compress(CONTENT)), "gzip")
    response.raw = object()

    with pytest.raises(requests.RequestException, match="Cannot verify the size"):
        client.download_dataset(URL, use_cache=True)

    assert list(client.cache_dir.iterdir()) == []


def test_temp_file_is_synced_before_it_is_published(
    client: RDHClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Without an fsync, a power loss after the rename can publish an empty or
    # short entry, which the existence-only cache hit would then reuse.
    module = "siege_utilities.geo.providers.redistricting_data_hub.os"
    real_fsync, real_replace = os.fsync, os.replace
    # (event, inode, size or -1 for a directory)
    events: list[tuple[str, int, int]] = []

    def recording_fsync(fd: int) -> None:
        info = os.fstat(fd)
        size = -1 if stat.S_ISDIR(info.st_mode) else info.st_size
        events.append(("fsync", info.st_ino, size))
        real_fsync(fd)

    def recording_replace(src: Path, dst: Path) -> None:
        events.append(("replace", os.stat(src).st_ino, 0))
        real_replace(src, dst)

    monkeypatch.setattr(f"{module}.fsync", recording_fsync)
    monkeypatch.setattr(f"{module}.replace", recording_replace)
    _response_for(client, [CONTENT], len(CONTENT))

    dest = client.download_dataset(URL, use_cache=True)

    assert dest.read_bytes() == CONTENT
    replace_index = next(i for i, event in enumerate(events) if event[0] == "replace")
    published_inode = events[replace_index][1]
    # The published file was synced after its last write, before the rename.
    assert ("fsync", published_inode, len(CONTENT)) in events[:replace_index], events
    if os.name == "posix":
        # The rename itself is then made durable by syncing the directory.
        directory_inode = os.stat(client.cache_dir).st_ino
        assert ("fsync", directory_inode, -1) in events[replace_index:], events


def test_sync_failure_cleans_temp_file_and_keeps_existing_entry(
    client: RDHClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    dest = client.cache_dir / "precincts.csv"
    dest.write_bytes(b"old")
    monkeypatch.setattr(
        "siege_utilities.geo.providers.redistricting_data_hub.os.fsync",
        Mock(side_effect=OSError("fsync failed")),
    )
    _response_for(client, [CONTENT], len(CONTENT))

    with pytest.raises(OSError, match="fsync failed"):
        client.download_dataset(URL, use_cache=False)

    assert dest.read_bytes() == b"old"
    assert list(client.cache_dir.iterdir()) == [dest]


def test_failed_refresh_preserves_complete_cached_file(client: RDHClient) -> None:
    dest = client.cache_dir / "precincts.csv"
    dest.write_bytes(CONTENT)
    _response_for(client, [CONTENT[:8]], len(CONTENT))

    with pytest.raises(requests.RequestException, match="Content-Length"):
        client.download_dataset(URL, use_cache=False)

    assert dest.read_bytes() == CONTENT
    assert list(client.cache_dir.iterdir()) == [dest]


def test_response_close_failure_leaves_no_cache_or_temp_file(client: RDHClient) -> None:
    response = _response_for(client, [CONTENT], len(CONTENT))
    response.close.side_effect = OSError("response close failed")

    with pytest.raises(OSError, match="response close failed"):
        client.download_dataset(URL, use_cache=True)

    assert list(client.cache_dir.iterdir()) == []


def test_replace_failure_cleans_temp_file(
    client: RDHClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _response_for(client, [CONTENT], len(CONTENT))
    monkeypatch.setattr(
        "siege_utilities.geo.providers.redistricting_data_hub.os.replace",
        Mock(side_effect=OSError("replace failed")),
    )

    with pytest.raises(OSError, match="replace failed"):
        client.download_dataset(URL, use_cache=True)

    assert list(client.cache_dir.iterdir()) == []


@POSIX_ONLY
def test_new_download_gets_the_umask_mode(
    client: RDHClient, umask: Callable[[int], int],
) -> None:
    # A new cache entry is created like any new file (0666 masked by the
    # umask), not with the owner-only 0600 of a private temporary file.
    umask(0o022)
    _response_for(client, [CONTENT], len(CONTENT))

    dest = client.download_dataset(URL, use_cache=True)

    assert stat.S_IMODE(dest.stat().st_mode) == 0o644


@POSIX_ONLY
def test_refresh_keeps_the_existing_entry_mode(
    client: RDHClient, umask: Callable[[int], int],
) -> None:
    # Refreshing a shared entry must not narrow it to the refreshing process's
    # umask: the replacement keeps the entry's own permission bits.
    dest = client.cache_dir / "precincts.csv"
    dest.write_bytes(b"old")
    dest.chmod(0o640)
    umask(0o077)
    _response_for(client, [CONTENT], len(CONTENT))

    assert client.download_dataset(URL, use_cache=False) == dest

    assert dest.read_bytes() == CONTENT
    assert stat.S_IMODE(dest.stat().st_mode) == 0o640
    assert list(client.cache_dir.iterdir()) == [dest]

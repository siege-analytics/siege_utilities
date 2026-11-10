"""RDH must never publish an interrupted or incomplete download to its cache."""

import os
import stat
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from typing import Optional
from unittest.mock import Mock

import pytest
import requests

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
) -> Mock:
    response = Mock(spec=requests.Response)
    response.headers = (
        {} if content_length is None else {"Content-Length": str(content_length)}
    )
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


@pytest.mark.parametrize("content_length", [len(CONTENT) + 1, len(CONTENT) - 1])
def test_size_mismatch_leaves_no_cache_or_temp_file(
    client: RDHClient, content_length: int,
) -> None:
    response = _response_for(client, [CONTENT], content_length)
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

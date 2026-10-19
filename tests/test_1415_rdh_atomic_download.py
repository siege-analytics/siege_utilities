"""RDH must never publish an interrupted or incomplete download to its cache."""

from unittest.mock import Mock

import pytest
import requests

from siege_utilities.geo.providers.redistricting_data_hub import RDHClient


URL = "https://redistrictingdatahub.org/files/precincts.csv"
CONTENT = b"GEOID,votes\n51001,42\n"


@pytest.fixture
def client(tmp_path, monkeypatch):
    with RDHClient(username="test-user", password="test-pass", cache_dir=tmp_path) as client:
        monkeypatch.setattr(client, "_session", Mock(spec=requests.Session))
        yield client


def response_for(client, chunks, content_length):
    response = Mock(spec=requests.Response)
    response.headers = (
        {} if content_length is None else {"Content-Length": str(content_length)}
    )
    response.iter_content.return_value = chunks
    client._session.get.return_value = response
    return response


@pytest.mark.parametrize("error_type", [requests.Timeout, OSError, KeyboardInterrupt])
def test_interrupted_download_leaves_no_cache_or_temp_file(client, error_type):
    def interrupted_chunks():
        yield CONTENT[:8]
        raise error_type("stream interrupted")

    response_for(client, interrupted_chunks(), len(CONTENT))
    dest = client.cache_dir / "precincts.csv"

    with pytest.raises(error_type, match="stream interrupted"):
        client.download_dataset(URL, use_cache=True)

    assert not dest.exists()
    assert list(client.cache_dir.iterdir()) == []


@pytest.mark.parametrize("content_length", [len(CONTENT) + 1, len(CONTENT) - 1])
def test_size_mismatch_leaves_no_cache_or_temp_file(client, content_length):
    response_for(client, [CONTENT], content_length)
    dest = client.cache_dir / "precincts.csv"

    with pytest.raises(requests.RequestException, match="Content-Length"):
        client.download_dataset(URL, use_cache=True)

    assert not dest.exists()
    assert list(client.cache_dir.iterdir()) == []


@pytest.mark.parametrize("content_length", [len(CONTENT), None])
def test_complete_download_is_published_then_reused(client, content_length):
    dest = client.cache_dir / "precincts.csv"

    def complete_chunks():
        yield CONTENT[:8]
        assert not dest.exists()
        yield b""
        yield CONTENT[8:]
        assert not dest.exists()

    response_for(client, complete_chunks(), content_length)

    assert client.download_dataset(URL, use_cache=True) == dest
    assert dest.read_bytes() == CONTENT
    assert list(client.cache_dir.iterdir()) == [dest]
    assert client.download_dataset(URL, use_cache=True) == dest
    assert dest.read_bytes() == CONTENT
    client._session.get.assert_called_once()


def test_failed_refresh_preserves_complete_cached_file(client):
    dest = client.cache_dir / "precincts.csv"
    dest.write_bytes(CONTENT)
    response_for(client, [CONTENT[:8]], len(CONTENT))

    with pytest.raises(requests.RequestException, match="Content-Length"):
        client.download_dataset(URL, use_cache=False)

    assert dest.read_bytes() == CONTENT
    assert list(client.cache_dir.iterdir()) == [dest]

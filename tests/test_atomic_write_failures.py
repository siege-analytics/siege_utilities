"""Publication and cleanup guarantees for atomic cache writers (#1509)."""

import errno
import io
import os
from pathlib import Path
import stat
from unittest.mock import MagicMock
import zipfile

import pytest
import requests

from siege_utilities.files import operations


def response_with(chunks):
    response = MagicMock()
    response.__enter__.return_value = response
    response.iter_content.return_value = chunks
    response.headers = {}
    return response


def broken_chunks():
    yield b"first chunk"
    yield b"second chunk"
    raise requests.exceptions.ChunkedEncodingError("transfer interrupted")


@pytest.mark.parametrize("failure", [OSError("disk full"), KeyboardInterrupt()])
@pytest.mark.parametrize("existing", [True, False])
def test_atomic_write_cleans_up_and_preserves_target(tmp_path, failure, existing):
    target = tmp_path / "data.csv"
    if existing:
        target.write_bytes(b"original")
    with pytest.raises(type(failure)):
        with operations.atomic_write_path(target) as tmp:
            assert tmp.parent == target.parent
            tmp.write_bytes(b"partial")
            raise failure
    assert sorted(tmp_path.iterdir()) == ([target] if existing else [])
    if existing:
        assert target.read_bytes() == b"original"


def test_file_sync_precedes_replace_and_directory_sync_follows(tmp_path, monkeypatch):
    target = tmp_path / "data.csv"
    events = []
    real_fsync, real_replace = os.fsync, os.replace

    def sync(fd):
        events.append("directory" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file")
        real_fsync(fd)

    def replace(src, dst):
        assert target.read_bytes() == b"old"
        events.append("replace")
        real_replace(src, dst)

    target.write_bytes(b"old")
    monkeypatch.setattr(operations.os, "fsync", sync)
    monkeypatch.setattr(operations.os, "replace", replace)
    with operations.atomic_write_path(target) as tmp:
        tmp.write_bytes(b"new")
    assert events == (["file", "replace", "directory"] if os.name == "posix" else ["file", "replace"])
    assert target.read_bytes() == b"new"


@pytest.mark.parametrize("operation", ["fsync", "replace"])
def test_sync_or_replace_failure_does_not_publish(tmp_path, monkeypatch, operation):
    target = tmp_path / "data.csv"
    target.write_bytes(b"old")

    def fail(*args):
        raise OSError(errno.ENOSPC, "disk full")

    monkeypatch.setattr(operations.os, operation, fail)
    with pytest.raises(OSError):
        with operations.atomic_write_path(target) as tmp:
            tmp.write_bytes(b"new")
    assert target.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission semantics")
@pytest.mark.parametrize("mask", [0o002, 0o077])
def test_umask_applies_even_when_serializer_recreates_file(tmp_path, mask):
    target = tmp_path / "data.csv"
    target.write_bytes(b"old")
    target.chmod(0o600)
    previous = os.umask(mask)
    try:
        with operations.atomic_write_path(target) as tmp:
            tmp.unlink()
            tmp.write_bytes(b"new")
            tmp.chmod(0o600)
    finally:
        os.umask(previous)
    assert stat.S_IMODE(target.stat().st_mode) == 0o666 & ~mask


@pytest.mark.parametrize("writer", ["soi", "qcew", "pl"])
@pytest.mark.parametrize("failure", ["network", "size_cap"])
@pytest.mark.parametrize("existing", [False, True])
def test_stream_failure_preserves_existing_data(tmp_path, monkeypatch, writer, failure, existing):
    from siege_utilities.economic.irs.soi import IRSSOIFiles
    from siege_utilities.economic.bls.qcew import QCEWFiles
    from siege_utilities.geo.census_files.pl_downloader import _stream_download_to_file

    dest = tmp_path / "cached.bin"
    if existing:
        dest.write_bytes(b"original")
    response = response_with(broken_chunks())
    monkeypatch.setattr(requests, "get", MagicMock(return_value=response))
    if writer == "pl":
        def write():
            _stream_download_to_file("https://example.test/data", dest, timeout=5,
                                     max_bytes=1 if failure == "size_cap" else 1024)
    else:
        downloader = (IRSSOIFiles if writer == "soi" else QCEWFiles)(cache_dir=tmp_path, timeout=5)
        if failure == "size_cap":
            downloader._MAX_DOWNLOAD_BYTES = 1

        def write():
            downloader._stream_download_to_file("https://example.test/data", dest)

    with pytest.raises(ValueError if failure == "size_cap" else requests.exceptions.ChunkedEncodingError):
        write()
    if existing:
        assert dest.read_bytes() == b"original"
    assert list(tmp_path.iterdir()) == ([dest] if existing else [])


@pytest.mark.parametrize("fallback", [False, True])
def test_remote_download_failure_does_not_publish(tmp_path, monkeypatch, fallback):
    from siege_utilities.files.remote import download_file

    response = response_with(broken_chunks())
    get = MagicMock(return_value=response)
    if fallback:
        get.side_effect = [requests.exceptions.SSLError("TLS failed"), response]
    monkeypatch.setattr(requests, "get", get)
    dest = tmp_path / "download.bin"
    with pytest.raises(requests.exceptions.ChunkedEncodingError):
        download_file("https://example.test/data", dest, timeout=5,
                      allow_insecure_fallback=fallback)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("existing_empty", [False, True])
def test_nces_extraction_is_published_only_when_complete(tmp_path, monkeypatch, existing_empty):
    from siege_utilities.geo.providers.nces_download import NCESDownloader

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("schools.csv", "id\n1\n2\n")
    calls = []

    def download(url, destination, **kwargs):
        calls.append(destination)
        Path(destination).write_bytes(archive.getvalue())

    monkeypatch.setattr("siege_utilities.files.remote.download_file", download)
    downloader = NCESDownloader(cache_dir=str(tmp_path), timeout=5)
    final = tmp_path / "schools_2023"
    if existing_empty:
        final.mkdir()
    real_extractall = zipfile.ZipFile.extractall

    def interrupted_extract(self, path, *args, **kwargs):
        assert Path(path).parent == final.parent
        assert not final.exists() or not any(final.iterdir())
        (Path(path) / "schools.csv").write_text("id\n1\n")
        raise OSError(errno.ENOSPC, "disk full")

    monkeypatch.setattr(zipfile.ZipFile, "extractall", interrupted_extract)
    with pytest.raises(OSError):
        downloader._download_and_extract("https://example.test/schools.zip", "schools", 2023)
    assert not final.exists() or not any(final.iterdir())
    assert not list(tmp_path.glob("nces_extract_*"))

    monkeypatch.setattr(zipfile.ZipFile, "extractall", real_extractall)
    assert downloader._download_and_extract("https://example.test/schools.zip", "schools", 2023) == final
    assert (final / "schools.csv").read_text() == "id\n1\n2\n"
    assert len(calls) == 2
    assert downloader._download_and_extract("https://example.test/schools.zip", "schools", 2023) == final
    assert len(calls) == 2
    assert not list(tmp_path.glob("nces_extract_*"))

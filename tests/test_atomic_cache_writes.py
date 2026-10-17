"""Interrupted cache writes must never publish partial files (#1509)."""

import os
import stat
from unittest.mock import MagicMock

import pytest
import requests

from siege_utilities.economic.irs.soi import IRSSOIFiles
from siege_utilities.files.operations import atomic_write_path


def test_soi_interrupted_download_is_not_cached(tmp_path, monkeypatch):
    def interrupted_chunks():
        yield b"ZIPCODE,N1\n"
        yield b"78701,100\n"
        raise requests.exceptions.ChunkedEncodingError("interrupted transfer")

    response = MagicMock()
    response.__enter__.return_value = response
    response.iter_content.side_effect = [
        interrupted_chunks(),
        iter([b"ZIPCODE,N1\n78701,100\n78702,200\n"]),
    ]
    get = MagicMock(return_value=response)
    monkeypatch.setattr("siege_utilities.economic.irs.soi.requests.get", get)
    downloader = IRSSOIFiles(cache_dir=tmp_path, timeout=5)
    csv_path = tmp_path / "2020_tx_soi.csv"

    with pytest.raises(requests.exceptions.ChunkedEncodingError):
        downloader.download(2020, "tx")

    assert not csv_path.exists()
    assert list(tmp_path.iterdir()) == []
    assert downloader.download(2020, "tx") == csv_path
    assert get.call_count == 2
    assert csv_path.read_bytes() == b"ZIPCODE,N1\n78701,100\n78702,200\n"


@pytest.mark.skipif(os.name == "nt", reason="POSIX umask permissions")
def test_atomic_write_path_respects_umask(tmp_path):
    target = tmp_path / "shared.csv"
    previous = os.umask(0o022)
    try:
        with atomic_write_path(target) as temporary:
            temporary.write_text("complete\n")
    finally:
        os.umask(previous)

    assert stat.S_IMODE(target.stat().st_mode) == 0o644

"""Error-path coverage (SU-4b) for siege_utilities.economic.bls.qcew.

Forces both ValueError raises in QCEWFiles:
- the download-size cap in _stream_download_to_file
- the "No CSV found inside <zip>" guard in download()
"""

import zipfile

import pytest

from siege_utilities.economic.bls import qcew as qcew_mod
from siege_utilities.economic.bls.qcew import QCEWFiles


class _FakeResponse:
    """Minimal stand-in for the requests.Response streaming contract."""

    def __init__(self, chunks):
        self._chunks = chunks

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size=None):
        yield from self._chunks


def test_stream_download_enforces_size_cap(tmp_path, monkeypatch):
    files = QCEWFiles(cache_dir=tmp_path)
    files._MAX_DOWNLOAD_BYTES = 8  # shrink cap so a single chunk trips it
    oversized = b"x" * 64

    monkeypatch.setattr(
        qcew_mod.requests, "get",
        lambda *a, **k: _FakeResponse([oversized]),
    )

    dest = tmp_path / "big.zip"
    with pytest.raises(ValueError) as exc_info:
        files._stream_download_to_file("https://example.test/file.zip", dest)
    assert "exceeds" in str(exc_info.value)
    # The partially-written file must be cleaned up before raising.
    assert not dest.exists()


def test_download_raises_when_zip_has_no_csv(tmp_path, monkeypatch):
    files = QCEWFiles(cache_dir=tmp_path)

    def fake_stream(url, dest):
        # Write a real zip whose only member is a non-CSV file.
        with zipfile.ZipFile(dest, "w") as zf:
            zf.writestr("readme.txt", "no csv here")

    monkeypatch.setattr(files, "_stream_download_to_file", fake_stream)

    with pytest.raises(ValueError) as exc_info:
        files.download(2020)
    assert "No CSV found" in str(exc_info.value)

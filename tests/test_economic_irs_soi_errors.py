"""Error-path coverage (SU-4b) for siege_utilities.economic.irs.soi.

Forces the download-size-cap ValueError in IRSSOIFiles._stream_download_to_file.
"""

import pytest

from siege_utilities.economic.irs import soi as soi_mod
from siege_utilities.economic.irs.soi import IRSSOIFiles


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
    files = IRSSOIFiles(cache_dir=tmp_path)
    files._MAX_DOWNLOAD_BYTES = 8
    oversized = b"x" * 64

    monkeypatch.setattr(
        soi_mod.requests, "get",
        lambda *a, **k: _FakeResponse([oversized]),
    )

    dest = tmp_path / "big.csv"
    with pytest.raises(ValueError) as exc_info:
        files._stream_download_to_file("https://example.test/file.csv", dest)
    assert "exceeds" in str(exc_info.value)
    assert not dest.exists()

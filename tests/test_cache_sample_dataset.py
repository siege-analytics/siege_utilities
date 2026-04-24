"""Tests for siege_utilities.cache.ensure_sample_dataset."""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch

import pytest

from siege_utilities.cache import SampleDatasetError, ensure_sample_dataset


PAYLOAD = b"synthetic,dataset,payload\n1,2,3\n"
PAYLOAD_SHA = hashlib.sha256(PAYLOAD).hexdigest()


def _mock_urlopen(payload: bytes):
    """Return a context-manager mock that yields a fake HTTP response."""
    response = MagicMock()
    response.read.side_effect = [payload, b""]
    cm = MagicMock()
    cm.__enter__.return_value = response
    cm.__exit__.return_value = False
    return cm


class TestFirstRunDownload:
    def test_downloads_and_caches(self, tmp_path):
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(PAYLOAD)):
            path = ensure_sample_dataset(
                "sample.csv",
                "https://example.invalid/sample.csv",
                cache_dir=tmp_path,
            )
        assert path == tmp_path / "sample.csv"
        assert path.read_bytes() == PAYLOAD

    def test_second_call_does_not_fetch(self, tmp_path):
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(PAYLOAD)) as m:
            ensure_sample_dataset(
                "sample.csv", "https://example.invalid/sample.csv", cache_dir=tmp_path,
            )
            assert m.call_count == 1
            ensure_sample_dataset(
                "sample.csv", "https://example.invalid/sample.csv", cache_dir=tmp_path,
            )
            assert m.call_count == 1  # cache hit, no second fetch


class TestSha256Verification:
    def test_matching_sha_accepts(self, tmp_path):
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(PAYLOAD)):
            path = ensure_sample_dataset(
                "sample.csv",
                "https://example.invalid/sample.csv",
                cache_dir=tmp_path,
                sha256=PAYLOAD_SHA,
            )
        assert path.exists()

    def test_mismatched_sha_raises_and_removes(self, tmp_path):
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(PAYLOAD)):
            with pytest.raises(SampleDatasetError, match="sha256 mismatch"):
                ensure_sample_dataset(
                    "sample.csv",
                    "https://example.invalid/sample.csv",
                    cache_dir=tmp_path,
                    sha256="0" * 64,
                )
        # Corrupt file should not linger in cache
        assert not (tmp_path / "sample.csv").exists()


class TestErrorHandling:
    def test_network_failure_wrapped(self, tmp_path):
        with patch("urllib.request.urlopen", side_effect=OSError("network down")):
            with pytest.raises(SampleDatasetError, match="failed to download"):
                ensure_sample_dataset(
                    "sample.csv",
                    "https://example.invalid/sample.csv",
                    cache_dir=tmp_path,
                )

    def test_rejects_path_in_name(self, tmp_path):
        with pytest.raises(ValueError, match="single filename"):
            ensure_sample_dataset(
                "sub/sample.csv",
                "https://example.invalid/sample.csv",
                cache_dir=tmp_path,
            )


class TestEnvOverride:
    def test_env_var_used_when_cache_dir_not_given(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SIEGE_UTILITIES_CACHE_DIR", str(tmp_path))
        with patch("urllib.request.urlopen", return_value=_mock_urlopen(PAYLOAD)):
            path = ensure_sample_dataset(
                "sample.csv", "https://example.invalid/sample.csv",
            )
        assert path == tmp_path / "sample.csv"

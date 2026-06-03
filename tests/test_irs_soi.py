"""Tests for IRS SOI ZIP-code data helper (#539)."""

import csv
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from siege_utilities.economic.irs.soi import IRSSOIFiles, DEFAULT_CACHE_DIR


class TestIRSSOIFilesURL:
    """url_for builds the correct IRS download URL."""

    def test_default_url_pattern(self):
        files = IRSSOIFiles.__new__(IRSSOIFiles)
        url = files.url_for(2020, "tx")
        assert url == "https://www.irs.gov/pub/irs-soi/2020zpallagitx.csv"

    def test_uppercase_state_lowered(self):
        files = IRSSOIFiles.__new__(IRSSOIFiles)
        url = files.url_for(2021, "CA")
        assert "ca" in url

    def test_different_year(self):
        files = IRSSOIFiles.__new__(IRSSOIFiles)
        url = files.url_for(2019, "ny")
        assert "2019" in url
        assert "ny" in url


class TestIRSSOIFilesParse:
    """parse normalizes ZIP and FIPS codes."""

    def _write_csv(self, path, rows):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)

    def test_zero_pads_zipcode(self, tmp_path):
        csv_path = tmp_path / "soi.csv"
        self._write_csv(csv_path, [
            {"ZIPCODE": "1234", "STATEFIPS": "6", "N1": "100"},
        ])
        files = IRSSOIFiles(cache_dir=tmp_path)
        df = files.parse(csv_path)
        assert df["ZIPCODE"].iloc[0] == "01234"
        assert df["STATEFIPS"].iloc[0] == "06"

    def test_preserves_full_zip(self, tmp_path):
        csv_path = tmp_path / "soi.csv"
        self._write_csv(csv_path, [
            {"ZIPCODE": "78701", "STATEFIPS": "48", "N1": "200"},
        ])
        files = IRSSOIFiles(cache_dir=tmp_path)
        df = files.parse(csv_path)
        assert df["ZIPCODE"].iloc[0] == "78701"


class TestIRSSOIFilesDownload:
    """download caches and returns CSV path."""

    def test_returns_cached_path(self, tmp_path):
        cached = tmp_path / "2020_tx_soi.csv"
        cached.write_text("ZIPCODE,N1\n78701,100\n")
        files = IRSSOIFiles(cache_dir=tmp_path)
        result = files.download(2020, "tx")
        assert result == cached

    @patch("siege_utilities.economic.irs.soi.requests.get")
    def test_downloads_when_not_cached(self, mock_get, tmp_path):
        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [b"ZIPCODE,N1\n78701,100\n"]
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_get.return_value = mock_resp
        files = IRSSOIFiles(cache_dir=tmp_path)
        result = files.download(2020, "tx")
        assert result.exists()
        assert result.name == "2020_tx_soi.csv"
        mock_get.assert_called_once()


class TestIRSSOIFilesLoad:
    """load combines download + parse."""

    def test_load_returns_dataframe(self, tmp_path):
        cached = tmp_path / "2020_tx_soi.csv"
        cached.write_text("ZIPCODE,STATEFIPS,N1\n78701,48,100\n")
        files = IRSSOIFiles(cache_dir=tmp_path)
        df = files.load(2020, "tx")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df["ZIPCODE"].iloc[0] == "78701"


class TestIRSSOIFilesInit:
    """Constructor creates cache directory."""

    def test_default_cache_dir(self):
        files = IRSSOIFiles.__new__(IRSSOIFiles)
        assert DEFAULT_CACHE_DIR.name == "irs_soi"

    def test_custom_cache_dir(self, tmp_path):
        custom = tmp_path / "my_cache"
        files = IRSSOIFiles(cache_dir=custom)
        assert files.cache_dir == custom
        assert custom.exists()


class TestLazyImport:
    """IRSSOIFiles is accessible from economic package."""

    def test_import_from_economic(self):
        from siege_utilities.economic import IRSSOIFiles as Cls
        assert Cls is IRSSOIFiles

    def test_import_from_irs(self):
        from siege_utilities.economic.irs import IRSSOIFiles as Cls
        assert Cls is IRSSOIFiles

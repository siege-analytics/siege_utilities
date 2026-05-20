"""Tests for siege_utilities.economic.bls.qcew (SU#533)."""

import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

from siege_utilities.economic.bls.qcew import QCEWFiles, QCEW_FILE_URL


def _make_zip(tmp_path, year, csv_content):
    """Build a fake QCEW zip in tmp_path; return zip-bytes."""
    csv_path = tmp_path / f"{year}.qcew.csv"
    csv_path.write_text(csv_content)
    zip_path = tmp_path / "fake.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(csv_path, arcname=f"{year}.qcew.csv")
    return zip_path.read_bytes()


class TestParse:

    def test_parse_filters_by_quarter(self, tmp_path):
        csv = tmp_path / "data.csv"
        csv.write_text(
            "area_fips,own_code,industry_code,qtr,year,qtrly_estabs,month3_emplvl,total_qtrly_wages,avg_wkly_wage\n"
            "06037,5,10,1,2024,1,1000,100000,1500\n"
            "06037,5,10,3,2024,1,1100,110000,1550\n"
            "06037,5,10,4,2024,1,1200,120000,1600\n"
        )
        files = QCEWFiles(cache_dir=tmp_path)
        df = files.parse(csv, year=2024, quarter=3)
        assert len(df) == 1
        assert df.iloc[0]["qtr"] == 3

    def test_parse_filters_by_state(self, tmp_path):
        csv = tmp_path / "data.csv"
        csv.write_text(
            "area_fips,own_code,industry_code,qtr,year,qtrly_estabs,month3_emplvl,total_qtrly_wages,avg_wkly_wage\n"
            "06037,5,10,3,2024,1,1000,100000,1500\n"
            "48201,5,10,3,2024,1,2000,200000,1600\n"
        )
        files = QCEWFiles(cache_dir=tmp_path)
        df = files.parse(csv, year=2024, quarter=3, state_fips="06")
        assert len(df) == 1
        assert df.iloc[0]["area_fips"] == "06037"

    def test_parse_filters_by_naics_depth(self, tmp_path):
        csv = tmp_path / "data.csv"
        csv.write_text(
            "area_fips,own_code,industry_code,qtr,year,qtrly_estabs,month3_emplvl,total_qtrly_wages,avg_wkly_wage\n"
            "06037,5,10,3,2024,1,1000,100000,1500\n"
            "06037,5,238,3,2024,1,500,50000,1400\n"
        )
        files = QCEWFiles(cache_dir=tmp_path)
        df = files.parse(csv, year=2024, quarter=3, naics_depth=2)
        assert len(df) == 1
        assert df.iloc[0]["industry_code"] == "10"


class TestDownloadCache:

    def test_returns_cached_csv_when_present(self, tmp_path):
        # Pre-populate cache with the target CSV.
        (tmp_path / "2024.qcew.csv").write_text("placeholder")
        files = QCEWFiles(cache_dir=tmp_path)
        result = files.download(2024)
        assert result == tmp_path / "2024.qcew.csv"

    def test_download_writes_then_returns_csv(self, tmp_path):
        files = QCEWFiles(cache_dir=tmp_path)
        # Mock requests.get to return our fake zip.
        fake_zip_bytes = _make_zip(
            tmp_path, 2024,
            "area_fips,own_code,industry_code,qtr,year,qtrly_estabs,month3_emplvl,total_qtrly_wages,avg_wkly_wage\n",
        )
        # The fake CSV is one of multiple test setup steps; download() looks for
        # .csv in the zip but our _make_zip side-effect already wrote the csv to
        # tmp_path. Clean slate:
        (tmp_path / "2024.qcew.csv").unlink(missing_ok=True)

        with patch.object(__import__("siege_utilities.economic.bls.qcew", fromlist=["requests"]).requests, "get") as mock_get:
            mock_get.return_value = MagicMock(content=fake_zip_bytes, raise_for_status=lambda: None)
            result = files.download(2024)
        assert result.exists()
        assert result.name == "2024.qcew.csv"


def test_url_template_format():
    assert QCEW_FILE_URL.format(year=2024) == (
        "https://data.bls.gov/cew/data/files/2024/csv/2024_qtrly_singlefile.zip"
    )


def test_import_path():
    """The downstream-documented import path works."""
    from siege_utilities.economic.bls import QCEWFiles as q1
    from siege_utilities.economic.bls.qcew import QCEWFiles as q2

    assert q1 is q2

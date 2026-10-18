"""Tests for siege_utilities.economic.bls.qcew (SU#533)."""

import zipfile
from unittest.mock import patch, MagicMock

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


@pytest.fixture
def singlefile_probe(tmp_path):
    """Issue #1507's probe plus ownership, size-class and industry decoys."""
    csv = tmp_path / "probe.csv"
    csv.write_text(
        "area_fips,own_code,industry_code,agglvl_code,qtr,year,disclosure_code,month3_emplvl\n"
        "06000,0,10,50,1,2024,,1000\n"
        "06000,5,10,51,1,2024,,800\n"
        "06000,5,31-33,54,1,2024,,120\n"
        "06000,5,44-45,54,1,2024,,150\n"
        "06000,5,48-49,54,1,2024,,60\n"
        "06000,5,62,54,1,2024,,170\n"
        "06001,5,62,74,1,2024,N,0\n"
        "06000,1,62,54,1,2024,,20\n"
        "06000,2,62,54,1,2024,,30\n"
        "06000,3,62,54,1,2024,,40\n"
        "06001,3,62,74,1,2024,,10\n"
        "06000,5,1011,53,1,2024,,200\n"
        "06000,5,1021,53,1,2024,,300\n"
        "06000,5,62,64,1,2024,,50\n"
        "06000,5,311,55,1,2024,,100\n"
        "06000,5,3111,56,1,2024,,90\n"
        "06000,5,31111,57,1,2024,,80\n"
        "06000,5,311111,58,1,2024,,70\n"
        "48000,5,62,54,1,2024,,180\n"
        "US000,5,62,14,1,2024,,900\n"
        "C3108,5,62,44,1,2024,,190\n"
    )
    return csv


class TestParse:

    def test_parse_filters_by_quarter(self, tmp_path):
        csv = tmp_path / "data.csv"
        csv.write_text(
            "area_fips,own_code,industry_code,agglvl_code,qtr,year,disclosure_code,month3_emplvl\n"
            "06000,5,62,54,1,2024,,1000\n"
            "06000,5,62,54,3,2024,,1100\n"
            "06000,5,62,54,4,2024,,1200\n"
            "06000,5,62,54,3,2023,,1300\n"
        )
        files = QCEWFiles(cache_dir=tmp_path)
        df = files.parse(csv, year=2024, quarter=3)
        assert len(df) == 1
        assert df.iloc[0]["qtr"] == 3
        assert df.iloc[0]["year"] == 2024

    def test_parse_filters_by_state(self, tmp_path):
        csv = tmp_path / "data.csv"
        csv.write_text(
            "area_fips,own_code,industry_code,agglvl_code,qtr,year,disclosure_code,month3_emplvl\n"
            "06000,5,62,54,3,2024,,1000\n"
            "48000,5,62,54,3,2024,,2000\n"
        )
        files = QCEWFiles(cache_dir=tmp_path)
        df = files.parse(csv, year=2024, quarter=3, state_fips="06")
        assert len(df) == 1
        assert df.iloc[0]["area_fips"] == "06000"

    def test_parse_filters_by_naics_depth(self, tmp_path, singlefile_probe):
        files = QCEWFiles(cache_dir=tmp_path)
        df = files.parse(singlefile_probe, year=2024, quarter=1, state_fips="06", naics_depth=2)
        assert set(df["industry_code"]) == {"31-33", "44-45", "48-49", "62"}
        assert df["month3_emplvl"].sum() == 500

    def test_parse_defaults_select_one_ownership_and_aggregation(self, tmp_path, singlefile_probe):
        files = QCEWFiles(cache_dir=tmp_path)
        df = files.parse(singlefile_probe, year=2024, quarter=1, state_fips="06")
        assert set(df["own_code"]) == {5}
        assert set(df["agglvl_code"]) == {54}
        assert set(df["area_fips"]) == {"06000"}
        assert not df["industry_code"].duplicated().any()

    def test_parse_flags_suppressed_values(self, tmp_path):
        csv = tmp_path / "suppressed.csv"
        csv.write_text(
            "area_fips,own_code,industry_code,agglvl_code,qtr,year,disclosure_code,"
            "month3_emplvl,total_qtrly_wages,source_note\n"
            "06000,5,62,54,1,2024,N,0,0,suppressed\n"
            "48000,5,62,54,1,2024,,0,0,published zero\n"
        )
        df = QCEWFiles(cache_dir=tmp_path).parse(csv, year=2024, quarter=1)
        assert "is_suppressed" in df.columns
        assert df["is_suppressed"].dtype == bool
        assert df["is_suppressed"].tolist() == [True, False]
        # Preserve all source columns, including extensions and raw sentinels.
        assert df["source_note"].tolist() == ["suppressed", "published zero"]
        assert df["month3_emplvl"].tolist() == [0, 0]
        assert df["total_qtrly_wages"].tolist() == [0, 0]

    def test_parse_county_suppression_from_probe(self, tmp_path, singlefile_probe):
        df = QCEWFiles(cache_dir=tmp_path).parse(
            singlefile_probe, year=2024, quarter=1, state_fips="06", area_level="county",
        )
        assert df["area_fips"].tolist() == ["06001"]
        assert df["own_code"].tolist() == [5]
        assert df["agglvl_code"].tolist() == [74]
        assert df["is_suppressed"].tolist() == [True]

    @pytest.mark.parametrize("own_code", [1, 2, 3])
    def test_parse_selects_government_ownership(self, tmp_path, singlefile_probe, own_code):
        df = QCEWFiles(cache_dir=tmp_path).parse(
            singlefile_probe, year=2024, quarter=1, state_fips="06", own_code=own_code,
        )
        assert df["own_code"].tolist() == [own_code]
        assert df["agglvl_code"].tolist() == [54]
        assert df["industry_code"].tolist() == ["62"]

    @pytest.mark.parametrize("area_level, agglvl_code", [("national", 14), ("msa", 44)])
    def test_parse_selects_other_area_levels(self, tmp_path, singlefile_probe, area_level, agglvl_code):
        df = QCEWFiles(cache_dir=tmp_path).parse(
            singlefile_probe, year=2024, quarter=1, area_level=area_level,
        )
        assert df["agglvl_code"].tolist() == [agglvl_code]
        assert df["industry_code"].tolist() == ["62"]

    @pytest.mark.parametrize("depth, industry", [(3, "311"), (4, "3111"), (5, "31111"), (6, "311111")])
    def test_parse_detailed_industries_exclude_supersectors_and_ranges(
        self, tmp_path, singlefile_probe, depth, industry,
    ):
        df = QCEWFiles(cache_dir=tmp_path).parse(
            singlefile_probe, year=2024, quarter=1, state_fips="06", naics_depth=depth,
        )
        assert df["industry_code"].tolist() == [industry]
        assert df["agglvl_code"].tolist() == [52 + depth]

    def test_parse_keeps_all_twenty_sectors(self, tmp_path):
        sectors = [
            "11", "21", "22", "23", "31-33", "42", "44-45", "48-49", "51", "52",
            "53", "54", "55", "56", "61", "62", "71", "72", "81", "92",
        ]
        csv = tmp_path / "sectors.csv"
        csv.write_text(
            "area_fips,own_code,industry_code,agglvl_code,qtr,year,disclosure_code\n"
            + "".join(f"06000,5,{code},54,1,2024,\n" for code in sectors + ["99"])
        )
        df = QCEWFiles(cache_dir=tmp_path).parse(csv, year=2024, quarter=1)
        assert df["industry_code"].tolist() == sectors

    @pytest.mark.parametrize("kwargs, message", [
        ({"naics_depth": 1}, "naics_depth"),
        ({"naics_depth": 7}, "naics_depth"),
        ({"area_level": "all"}, "area_level"),
        ({"area_level": "national", "state_fips": "06"}, "state_fips"),
        ({"area_level": "msa", "state_fips": "06"}, "state_fips"),
        ({"state_fips": "6"}, "state_fips"),
    ])
    def test_parse_rejects_invalid_selection(self, tmp_path, singlefile_probe, kwargs, message):
        with pytest.raises(ValueError, match=message):
            QCEWFiles(cache_dir=tmp_path).parse(singlefile_probe, year=2024, quarter=1, **kwargs)


def test_load_forwards_selection(tmp_path, singlefile_probe):
    files = QCEWFiles(cache_dir=tmp_path)
    with patch.object(files, "download", return_value=singlefile_probe):
        df = files.load(year=2024, quarter=1, state_fips="06", area_level="county", own_code=3)
    assert df["area_fips"].tolist() == ["06001"]
    assert df["own_code"].tolist() == [3]
    assert df["agglvl_code"].tolist() == [74]


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

        # writing-tests:4 mock fidelity: download() streams via
        # `with requests.get(stream=True) as resp: resp.iter_content(...)`, so
        # the mock must expose the streaming context-manager interface (not a
        # plain `.content` attribute, which the streaming path never reads).
        import siege_utilities.economic.bls.qcew as qcew_mod
        with patch.object(qcew_mod.requests, "get") as mock_get:
            stream_resp = MagicMock()
            stream_resp.raise_for_status.return_value = None
            stream_resp.iter_content.return_value = [fake_zip_bytes]
            stream_resp.__enter__.return_value = stream_resp
            stream_resp.__exit__.return_value = False
            mock_get.return_value = stream_resp
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

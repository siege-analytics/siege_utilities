"""Further #1571 coverage: geography tokeniser, load_csv dtype, and the
RDHLoaderService GEOID-match paths. No network, no database."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from siege_utilities.geo.providers import redistricting_data_hub as rdh
from siege_utilities.geo.providers.redistricting_data_hub import (
    RDH_MAX_RESULTS, RDHClient, RDHDataset, _title_geography, fetch_cvap,
)


@pytest.fixture
def client(tmp_path):
    c = RDHClient(username="dummy-user", password="dummy-pass", cache_dir=tmp_path / "cache")
    c._session = MagicMock()
    yield c


class TestTitleGeography:

    @pytest.mark.parametrize("title, expected", [
        ("VA PL 94-171 2020 Block Group", "block group"),
        ("VA PL 94-171 2020 Block", "block"),
        ("VA_CVAP_block_group", "block group"),
        ("VA_CVAP_2021_tract_csv", "tract"),
        ("VA CVAP 2020 County", "county"),
        ("VA CVAP 2020", None),
        ("VA CVAP 2020 Tract and County", None),  # two levels: ambiguous
    ])
    def test_levels(self, title, expected):
        assert _title_geography(title) == expected

    def test_explicit_geography_metadata_wins_over_title(self, client):
        ds = RDHDataset("VA CVAP 2020 Tract", "https://x/t.csv", geography="block_group")
        with patch.object(client, "get_cvap_data", return_value=[ds]), \
             patch.object(client, "load_csv", side_effect=lambda d: d):
            assert fetch_cvap("VA", geography="block group", client=client) is ds
            with pytest.raises(FileNotFoundError):
                fetch_cvap("VA", geography="tract", client=client)

    def test_empty_geography_disables_filter(self, client):
        ds = RDHDataset("VA CVAP 2020 County", "https://x/c.csv")
        with patch.object(client, "get_cvap_data", return_value=[ds]), \
             patch.object(client, "load_csv", side_effect=lambda d: d):
            assert fetch_cvap("VA", geography=None, client=client) is ds


class TestLoadCSVSelection:

    def test_caller_dtype_is_honoured(self, client, tmp_path):
        csv = tmp_path / "al.csv"
        csv.write_text("GEOID20,CVAP_TOT\n01001020100,1234\n")
        df = client.load_csv(csv, dtype={"CVAP_TOT": str})
        assert df["GEOID20"].dtype.kind == "i"  # caller opted out of the default
        assert df.loc[0, "CVAP_TOT"] == "1234"

    def test_numeric_value_columns_stay_numeric(self, client, tmp_path):
        csv = tmp_path / "al.csv"
        csv.write_text("GEOID,TRACTCE20,CVAP_TOT,TOT_RACE\n01001020100,020100,1234,7\n")
        df = client.load_csv(csv)
        assert df.loc[0, "TRACTCE20"] == "020100"
        assert df["CVAP_TOT"].dtype.kind == "i" and df["TOT_RACE"].dtype.kind == "i"

    def test_single_csv_with_other_members_is_picked(self, client, tmp_path):
        d = tmp_path / "extracted"
        d.mkdir()
        (d / "readme.txt").write_text("not data")
        (d / "al_cvap.csv").write_text("GEOID\n01001\n")
        assert client.load_csv(d).loc[0, "GEOID"] == "01001"

    def test_ambiguous_csv_names_candidates(self, client, tmp_path):
        d = tmp_path / "extracted"
        d.mkdir()
        (d / "b.csv").write_text("GEOID\n1\n")
        (d / "a.csv").write_text("GEOID\n2\n")
        with pytest.raises(ValueError, match=r"\['a.csv', 'b.csv'\]"):
            client.load_csv(d)

    def test_cached_non_zip_still_returns_file(self, client, tmp_path):
        cached = tmp_path / "al.csv"
        cached.write_text("GEOID\n01001\n")
        assert client.download_dataset("https://x/al.csv", output_dir=tmp_path) == cached
        client._session.get.assert_not_called()


class TestListingCap:

    def test_below_cap_does_not_warn(self, client):
        resp = MagicMock()
        resp.json.return_value = [{"title": "VA d", "url": "https://x/0.csv"}] * (RDH_MAX_RESULTS - 1)
        client._session.get.return_value = resp
        with patch.object(rdh, "log_warning") as log_warning:
            client.list_datasets(states=["VA"])
        log_warning.assert_not_called()


# -- RDHLoaderService GEOID matching ------------------------------------------

try:
    from django.core.exceptions import ImproperlyConfigured
except ImportError:  # Django absent; the service import below raises ImportError
    ImproperlyConfigured = ImportError
try:
    from siege_utilities.geo.django.services.rdh_loader import RDHLoaderService

    HAS_GDAL = True
except (ImportError, ImproperlyConfigured, OSError):
    # GeoDjango without system libgdal raises ImproperlyConfigured (OSError for
    # an unloadable GDAL_LIBRARY_PATH). Narrowed so unrelated errors still fail.
    HAS_GDAL = False


def _service():
    return RDHLoaderService(client=MagicMock())


def _plan(*geoids):
    districts = [MagicMock(geoid=g, cvap=None) for g in geoids]
    plan = SimpleNamespace(state_fips="01", districts=MagicMock())
    plan.districts.all.return_value = districts
    return plan, districts


def _load_cvap(service, plan, **kwargs):
    # Bypass @transaction.atomic: the matching logic needs no database.
    return RDHLoaderService.load_cvap_for_plan.__wrapped__(service, plan, 2020, **kwargs)


@pytest.mark.requires_gdal
@pytest.mark.skipif(not HAS_GDAL, reason="GeoDjango/GDAL not available")
class TestLoaderCVAPMatch:

    def test_leading_zero_geoids_match(self, tmp_path):
        csv = tmp_path / "al_cvap_cd.csv"
        csv.write_text("GEOID,CVAP_EST\n0101,500000\n0102,510000\n")
        df = RDHClient(username="dummy-user", password="dummy-pass").load_csv(csv)
        plan, districts = _plan("0101", "0102")
        with patch.object(rdh, "fetch_cvap", return_value=df) as fetch:
            result = _load_cvap(_service(), plan, geography="congressional district")
        assert fetch.call_args.kwargs["geography"] == "congressional district"
        assert result.success and result.records_updated == 2
        assert [d.cvap for d in districts] == [500000, 510000]

    def test_numeric_geoid_column_is_an_error(self):
        df = pd.DataFrame({"GEOID": [101, 102], "CVAP_EST": [1, 2]})
        plan, districts = _plan("0101", "0102")
        with patch.object(rdh, "fetch_cvap", return_value=df):
            result = _load_cvap(_service(), plan)
        assert not result.success and "numeric" in result.errors[0]
        assert all(d.cvap is None for d in districts)

    def test_no_district_matching_is_an_error(self):
        df = pd.DataFrame({"GEOID": ["01001020100"], "CVAP_EST": [1]})
        plan, _ = _plan("0101", "0102")
        with patch.object(rdh, "fetch_cvap", return_value=df):
            result = _load_cvap(_service(), plan)
        assert not result.success and "No district matched" in result.errors[0]
        assert result.records_skipped == 2

    def test_partial_match_is_a_warning(self):
        df = pd.DataFrame({"GEOID": ["0101"], "CVAP_EST": [7]})
        plan, _ = _plan("0101", "0102")
        with patch.object(rdh, "fetch_cvap", return_value=df):
            result = _load_cvap(_service(), plan)
        assert result.success and result.records_updated == 1
        assert result.warnings and "0102" in result.warnings[0]

    def test_missing_geography_is_reported(self):
        plan, _ = _plan("0101")
        with patch.object(rdh, "fetch_cvap", side_effect=FileNotFoundError("available: [x]")):
            result = _load_cvap(_service(), plan)
        assert result.errors == ["available: [x]"]

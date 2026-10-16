"""Behavioral regressions for #1592, using the real ORM and PostGIS."""

import json
import logging
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.loader import MigrationLoader
from django.db.models import Sum
from shapely.geometry import Polygon

from siege_utilities.geo.django.models.redistricting import PrecinctElectionResult
from siege_utilities.geo.django.services.rdh_loader import RDHLoaderService
from siege_utilities.geo.providers import redistricting_data_hub as rdh


@pytest.fixture
def precinct_data():
    return gpd.GeoDataFrame(
        {
            "PRECINCT": ["001", "002"],
            "NAME": ["First precinct", "Second precinct"],
            "G20PREDBID": [100, 20],
            "G20PRERTRU": [80, 30],
            "G20PREOWRI": [5, 0],
        },
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 0)]), None],
        crs="EPSG:4326",
    )


@pytest.fixture
def loader(monkeypatch, precinct_data, tmp_path):
    monkeypatch.setattr(rdh, "fetch_precinct_results", lambda *args, **kwargs: precinct_data)
    with rdh.RDHClient(cache_dir=tmp_path) as client:
        yield RDHLoaderService(client=client)


@pytest.fixture
def vest_data(monkeypatch):
    def read(state, year):
        path = Path(__file__).parent / "fixtures" / "vest" / f"{state.lower()}_{year}.json"
        rows = json.loads(path.read_text())["rows"]
        frame = gpd.GeoDataFrame(rows, geometry=[None] * len(rows), crs="EPSG:4326")
        monkeypatch.setattr(rdh, "fetch_precinct_results", lambda *args, **kwargs: frame)
        return frame
    return read


@pytest.mark.postgis
@pytest.mark.django_db
class TestForwardFix:
    def test_ga_next_year_runoffs_load_distinctly_and_reload(self, loader, vest_data):
        frame = vest_data("GA", 2020)
        first = loader.load_precinct_results("GA", 2020)
        before = list(PrecinctElectionResult.objects.order_by("precinct_id", "election_year",
                      "election_type", "party_code", "candidate_name")
                      .values_list("precinct_id", "election_year", "election_type", "party_code",
                                   "candidate_name", "votes", "total_votes"))
        second = loader.load_precinct_results("GA", 2020)
        assert first.records_created == second.records_created
        assert before == list(PrecinctElectionResult.objects.order_by("precinct_id", "election_year",
                              "election_type", "party_code", "candidate_name")
                              .values_list("precinct_id", "election_year", "election_type", "party_code",
                                           "candidate_name", "votes", "total_votes"))
        senate = PrecinctElectionResult.objects.filter(office="senate")
        assert set(senate.values_list("election_year", "election_type")) == {
            (2020, "G"), (2020, "S"), (2021, "R"),
        }
        runoff = senate.filter(election_year=2021, election_type="R")
        assert set(runoff.values_list("candidate_name", flat=True)) == {"PER", "OSS", "LOE", "WAR"}
        assert runoff.count() == 8
        assert runoff.aggregate(n=Sum("votes"))["n"] == frame.filter(regex="^R21USS").sum().sum()
        assert all(any(col in w for w in first.warnings) for col in ["R21PSCRMCD", "R21PSCDBLA"])

    def test_runoff_reload_removes_missing_columns_and_preserves_other_scopes(self, loader, vest_data):
        frame = vest_data("GA", 2020)
        loader.load_precinct_results("GA", 2020)
        unrelated = PrecinctElectionResult.objects.create(
            state_fips="13", election_year=2021, election_type="G", precinct_id="other",
            office="senate", party_code="D", candidate_name="ABC", votes=9, data_source="rdh",
        )
        assert PrecinctElectionResult.objects.filter(election_year=2021, election_type="R").count() == 8
        frame.drop(columns=["R21USSRLOE", "R21USSDWAR"], inplace=True)
        loader.load_precinct_results("GA", 2020)
        runoff = PrecinctElectionResult.objects.filter(election_year=2021, election_type="R")
        assert not runoff.filter(candidate_name__in=["LOE", "WAR"]).exists()
        assert set(runoff.values_list("candidate_name", flat=True)) == {"PER", "OSS"}
        assert runoff.count() == 4
        assert PrecinctElectionResult.objects.get(pk=unrelated.pk).votes == 9

    def test_prior_year_reload_preserves_next_year_files_runoffs(self, loader, precinct_data, monkeypatch):
        """VEST la_2019 carries R19GOV/R19SOS; la_2018 has no R19 columns and must not delete them."""
        base = precinct_data[["PRECINCT", "NAME", "geometry"]]
        la_2019 = base.assign(G19GOVDEDW=[10, 1], R19GOVDEDW=[20, 2], R19GOVRRIS=[30, 3])
        la_2018 = base.assign(G18SOSRARD=[5, 4], R18SOSRARD=[6, 7])
        monkeypatch.setattr(rdh, "fetch_precinct_results", lambda *args, **kwargs: la_2019)
        loader.load_precinct_results("LA", 2019)
        assert PrecinctElectionResult.objects.filter(election_year=2019, election_type="R").count() == 4
        monkeypatch.setattr(rdh, "fetch_precinct_results", lambda *args, **kwargs: la_2018)
        loader.load_precinct_results("LA", 2018)
        assert PrecinctElectionResult.objects.filter(election_year=2019, election_type="R").count() == 4
        assert PrecinctElectionResult.objects.filter(election_year=2019).aggregate(n=Sum("votes"))["n"] == 66

    @pytest.mark.parametrize("column", ["G18PREDBID", "S22USSDWAR", "C21PREDBID", "P19PRE_TOTAL"])
    def test_other_year_omissions_are_warned(self, loader, precinct_data, column):
        precinct_data[column] = [1, 2]
        result = loader.load_precinct_results("VA", 2020)
        assert any(column in warning for warning in result.warnings)
        assert result.records_created == 6

    def test_dc_delegate_loads_as_house_and_shadow_offices_are_warned(self, loader, vest_data):
        frame = vest_data("DC", 2020)
        result = loader.load_precinct_results("DC", 2020)
        house = PrecinctElectionResult.objects.filter(office="house")
        assert house.filter(candidate_name="NOR", district="AL").count() == 2
        assert house.count() == 18
        assert house.aggregate(n=Sum("votes"))["n"] == frame.filter(regex="^G20DEL").sum().sum()
        assert not house.filter(candidate_name="OWO").exists()
        assert not PrecinctElectionResult.objects.filter(office="senate").exists()
        assert all(any(col in w and "shadow" in w for w in result.warnings)
                   for col in frame.filter(regex="^G20(?:USS|HAL)"))

    def test_dc_mapping_does_not_change_other_states(self, loader, vest_data):
        vest_data("DC", 2020)
        result = loader.load_precinct_results("DE", 2020)
        assert PrecinctElectionResult.objects.filter(office="house", candidate_name="OWO").count() == 2
        assert PrecinctElectionResult.objects.filter(office="senate", candidate_name="STR").count() == 2
        assert not PrecinctElectionResult.objects.filter(candidate_name="NOR").exists()
        assert any("G20DELDNOR" in w and "unmapped office" in w for w in result.warnings)

    @pytest.mark.parametrize("year,identities", [(2018, 23), (2020, 15)])
    def test_mn_vtdid_is_statewide_and_preserves_all_identities(self, loader, vest_data, year, identities):
        frame = vest_data("MN", year)
        first = loader.load_precinct_results("MN", year)
        frame.sort_values("VTDID", ascending=False, inplace=True)
        second = loader.load_precinct_results("MN", year)
        assert first.records_created == second.records_created == 2 * identities
        assert set(PrecinctElectionResult.objects.values_list("precinct_id", flat=True)) == {
            "270010005", "270010010",
        }
        assert PrecinctElectionResult.objects.filter(precinct_id="270010005").count() == identities
        assert PrecinctElectionResult.objects.aggregate(n=Sum("votes"))["n"] == (
            frame.filter(regex=r"^[GS]\d{2}(?:PRE|USS|GOV|SOS|ATG)").sum().sum()
        )

    def test_mn_2018_vtdid_governor_write_ins_remain_distinct(self, loader, vest_data):
        vest_data("MN", 2018)
        loader.load_precinct_results("MN", 2018)
        rows = PrecinctElectionResult.objects.filter(
            precinct_id="270010005", office="governor", candidate_name="WRI",
        )
        assert set(rows.values_list("party_code", flat=True)) == {"C", "O"}

    @pytest.mark.parametrize("column", ["GEOID16", "GEOID18", "VTDST16", "VTDST18"])
    def test_older_vest_id_variants_load(self, loader, precinct_data, column):
        precinct_data.rename(columns={"PRECINCT": column}, inplace=True)
        loader.load_precinct_results("VA", 2020)
        assert set(PrecinctElectionResult.objects.values_list("precinct_id", flat=True)) == {"001", "002"}

    @pytest.mark.parametrize("column", ["GEOID20", "PRECINCT"])
    def test_existing_id_precedes_added_vtdid(self, loader, precinct_data, column):
        precinct_data.rename(columns={"PRECINCT": column}, inplace=True)
        precinct_data["COUNTYFP"] = ["001", "003"]
        precinct_data["VTDID"] = ["270010005", "270010010"]
        loader.load_precinct_results("VA", 2020)
        expected = {"001", "002"} if column == "GEOID20" else {"001:001", "003:002"}
        assert set(PrecinctElectionResult.objects.values_list("precinct_id", flat=True)) == expected

    def test_mt_skips_three_blank_zero_vote_rows_and_preserves_sum(self, loader, vest_data):
        frame = vest_data("MT", 2020)
        first = loader.load_precinct_results("MT", 2020)
        second = loader.load_precinct_results("MT", 2020)
        assert first.records_created == second.records_created == 28
        assert first.records_skipped == second.records_skipped == 3
        assert any("3" in w and "blank" in w and "zero" in w for w in first.warnings)
        assert PrecinctElectionResult.objects.values("precinct_id").distinct().count() == 2
        assert PrecinctElectionResult.objects.aggregate(n=Sum("votes"))["n"] == (
            frame.filter(regex="^G20(?:PRE|USS|HAL|GOV|ATG|SOS)").sum().sum()
        )

    @pytest.mark.parametrize("column,value", [
        ("G20PREDBID", 1), ("G20AUDRDOW", 1), ("R21USSDWAR", 1),
        ("G19PREDBID", 1), ("G20PRE_TOTAL", "invalid"), ("G20PREDBID", 0.5),
    ])
    def test_blank_id_with_any_nonzero_or_invalid_vote_raises(self, loader, vest_data, column, value):
        frame = vest_data("MT", 2020)
        frame[column] = frame.get(column, pd.Series(0, index=frame.index)).astype(object)
        frame.loc[2, column] = value
        with pytest.raises(ValueError, match="Cannot resolve statewide precinct identifiers.*missing or blank"):
            loader.load_precinct_results("MT", 2020)
        assert not PrecinctElectionResult.objects.exists()

    def test_unknown_party_letters_warn_and_preserve_raw_identity(self, loader, vest_data, caplog):
        frame = vest_data("RI", 2020)
        with caplog.at_level(logging.WARNING, logger=RDHLoaderService.__module__):
            result = loader.load_precinct_results("RI", 2020)
        unknown = [col for col in frame if col.startswith("G20") and col[6] in "AOS"]
        assert {col[6] for col in unknown} == {"A", "O", "S"}
        assert all(any(col in w and repr(col[6]) in w and "unmapped party" in w
                       for w in result.warnings) for col in unknown)
        assert all(w in caplog.text for w in result.warnings)
        assert set(PrecinctElectionResult.objects.filter(party_code__in=["A", "O", "S"])
                   .values_list("party_code", flat=True)) == {"A", "O", "S"}
        assert PrecinctElectionResult.objects.aggregate(n=Sum("votes"))["n"] == frame.filter(regex="^G20").sum().sum()

    def test_complete_id_candidate_keeps_zero_vote_rows(self, loader, vest_data):
        frame = vest_data("MT", 2020)
        frame["VTDID"] = ["a", "b", "c", "d", "e"]
        result = loader.load_precinct_results("MT", 2020)
        assert result.records_created == 70
        assert result.records_skipped == 0
        assert set(PrecinctElectionResult.objects.values_list("precinct_id", flat=True)) == set("abcde")

    def test_zero_vote_omissions_keep_alignment_with_duplicate_dataframe_index(self, loader, vest_data):
        frame = vest_data("MT", 2020)
        frame.sort_values("SOSPRECINC", na_position="first", inplace=True)
        frame.index = [7] * len(frame)
        result = loader.load_precinct_results("MT", 2020)
        assert result.records_created == 28 and result.records_skipped == 3
        assert PrecinctElectionResult.objects.get(
            precinct_id="063:BONNER 89", candidate_name="BID",
        ).votes == 112

    def test_all_blank_zero_vote_ids_raise_and_preserve_prior_snapshot(self, loader, vest_data):
        frame = vest_data("MT", 2020)
        loader.load_precinct_results("MT", 2020)
        before = PrecinctElectionResult.objects.aggregate(n=Sum("votes"))["n"]
        frame.drop(index=[0, 1], inplace=True)
        with pytest.raises(ValueError, match="Cannot resolve statewide precinct identifiers"):
            loader.load_precinct_results("MT", 2020)
        assert PrecinctElectionResult.objects.count() == 28
        assert PrecinctElectionResult.objects.aggregate(n=Sum("votes"))["n"] == before


@pytest.mark.postgis
@pytest.mark.django_db
class TestPrecinctLoading:
    def test_vest_zero_z_boundary_loads_into_2d_postgis(self, loader, precinct_data):
        # VA 2020 VEST boundaries have Z=0; the model stores a 2D footprint.
        polygon = Polygon([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 0, 0)])
        precinct_data.loc[0, "geometry"] = polygon
        result = loader.load_precinct_results("VA", 2020)
        row = PrecinctElectionResult.objects.get(precinct_id="001", party="DEM")
        assert result.records_created == 6
        assert not row.geometry.hasz
        assert row.geometry.srid == 4326
        assert row.geometry[0].coords == (((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 0.0)),)

    def test_real_house_columns_retain_district_and_reload_idempotently(self, loader, precinct_data):
        precinct_data["G20HALRYOU"] = [40, 4]
        precinct_data["G20H01DSMI"] = [10, 1]
        precinct_data["G20H01RJON"] = [15, 2]
        precinct_data["G20H05DSMI"] = [30, 3]
        first = loader.load_precinct_results("VA", 2020)
        second = loader.load_precinct_results("VA", 2020)

        assert first.records_created == second.records_created == 14
        assert first.warnings == second.warnings
        assert len(first.warnings) == 1 and "G20PREOWRI" in first.warnings[0]
        assert PrecinctElectionResult.objects.count() == 14
        assert list(PrecinctElectionResult.objects.filter(precinct_id="001", office="house")
                    .order_by("district", "party_code")
                    .values_list("district", "party_code", "candidate_name", "votes", "total_votes")) == [
            ("01", "D", "SMI", 10, 25), ("01", "R", "JON", 15, 25),
            ("05", "D", "SMI", 30, 30), ("AL", "R", "YOU", 40, 40),
        ]
        assert PrecinctElectionResult.objects.get(
            precinct_id="001", district="01", party_code="D"
        ).vote_share == 0.4

    def test_mn_2018_governor_party_collision_preserves_raw_letters(self, loader, precinct_data):
        # VEST 2018 documentation.txt, Minnesota: all five governor columns.
        precinct_data["G18GOVDWAL"] = [100, 20]
        precinct_data["G18GOVRJOH"] = [80, 30]
        precinct_data["G18GOVLWEL"] = [3, 1]
        precinct_data["G18GOVCWRI"] = [7, 2]
        precinct_data["G18GOVOWRI"] = [5, 0]
        first = loader.load_precinct_results("MN", 2018)
        second = loader.load_precinct_results("MN", 2018)

        assert first.records_created == second.records_created == 10
        assert PrecinctElectionResult.objects.count() == 10
        assert list(PrecinctElectionResult.objects.filter(precinct_id="001", candidate_name="WRI")
                    .order_by("party_code").values_list("party_code", "party", "votes", "total_votes")) == [
            ("C", "C", 7, 195), ("O", "O", 5, 195),
        ]
        assert PrecinctElectionResult.objects.aggregate(total=Sum("votes"))["total"] == 248

    def test_special_and_general_senate_load_distinctly(self, loader, precinct_data):
        precinct_data["S20USSDWAR"] = [40, 4]
        precinct_data["G20USSDOSS"] = [60, 6]
        # Same candidate in both election types must also remain distinct.
        precinct_data["S20USSDOSS"] = [10, 1]
        first = loader.load_precinct_results("GA", 2020)
        second = loader.load_precinct_results("GA", 2020)

        assert first.records_created == second.records_created == 12
        assert first.warnings == second.warnings
        assert len(first.warnings) == 1 and "G20PREOWRI" in first.warnings[0]
        assert PrecinctElectionResult.objects.count() == 12
        assert list(PrecinctElectionResult.objects.filter(precinct_id="001", office="senate")
                    .order_by("election_type", "candidate_name")
                    .values_list("election_type", "candidate_name", "votes", "total_votes")) == [
            ("G", "OSS", 60, 60), ("S", "OSS", 10, 50), ("S", "WAR", 40, 50),
        ]

    @pytest.mark.parametrize("election_type", ["R", "C", "P"])
    def test_other_election_types_and_next_year_runoff_load_with_skip_warnings(
        self, loader, precinct_data, election_type, caplog
    ):
        """SU-1 and #1592 require next-year runoff columns to be observable."""
        precinct_data[f"{election_type}20PREDBID"] = [10, 1]
        malformed = f"{election_type}20PRE_TOTAL"
        unmapped = f"{election_type}20TREDABC"
        precinct_data[malformed] = [900, 90]
        precinct_data[unmapped] = [800, 80]
        precinct_data["R21USSDWAR"] = [700, 70]
        with caplog.at_level(logging.WARNING, logger=RDHLoaderService.__module__):
            result = loader.load_precinct_results("VA", 2020)
        assert result.records_created == 10
        row = PrecinctElectionResult.objects.get(
            precinct_id="001", election_type=election_type, election_year=2020,
        )
        assert (row.party_code, row.votes, row.total_votes) == ("D", 10, 10)
        assert PrecinctElectionResult.objects.get(
            precinct_id="001", election_year=2021, election_type="R",
        ).votes == 700
        skips = [warning for warning in result.warnings if warning.startswith("Skipping")]
        assert len(skips) == 2
        assert malformed in skips[0] and unmapped in skips[1]
        assert all(warning in caplog.text for warning in result.warnings)

    @pytest.mark.parametrize("column", ["GEOID20", "VTDST20", "PRECINCT_I", "SOSPRECINC", "WARDID"])
    def test_real_precinct_id_columns_resolve_statewide(self, loader, precinct_data, column):
        precinct_data.rename(columns={"PRECINCT": column}, inplace=True)
        result = loader.load_precinct_results("VA", 2020)
        assert result.records_created == 6
        assert set(PrecinctElectionResult.objects.values_list("precinct_id", flat=True)) == {"001", "002"}

    @pytest.mark.parametrize("column", ["PRECINCT", "PRECINCT_I", "SOSPRECINC", "VTDST20", "WARDID"])
    def test_county_qualifies_cross_county_duplicate_precincts(self, loader, precinct_data, column):
        precinct_data.rename(columns={"PRECINCT": column}, inplace=True)
        precinct_data[column] = ["001", "001"]
        precinct_data["COUNTYFP20"] = ["001", "003"]
        precinct_data.index = [7, 7]  # DataFrame index is not part of precinct identity.
        loader.load_precinct_results("VA", 2020)
        loader.load_precinct_results("VA", 2020)
        assert PrecinctElectionResult.objects.count() == 6
        assert set(PrecinctElectionResult.objects.values_list("precinct_id", flat=True)) == {
            "001:001", "003:001",
        }
        assert PrecinctElectionResult.objects.aggregate(total=Sum("votes"))["total"] == 235

    def test_geoid_preferred_over_county_local_precinct_and_vtd(self, loader, precinct_data):
        precinct_data["PRECINCT"] = ["001", "001"]
        precinct_data["VTDST20"] = ["ACWO01", "ACWO01"]
        precinct_data["GEOID20"] = ["33019ACWO01", "33017ACWO01"]
        precinct_data["COUNTYFP20"] = ["019", "017"]
        loader.load_precinct_results("NH", 2020)
        assert set(PrecinctElectionResult.objects.values_list("precinct_id", flat=True)) == {
            "33019ACWO01", "33017ACWO01",
        }

    def test_wisconsin_wards_include_municipality(self, loader, precinct_data):
        precinct_data.rename(columns={"PRECINCT": "WARDID"}, inplace=True)
        precinct_data["WARDID"] = ["0060", "0060"]
        precinct_data["CNTY_FIPS"] = ["55035", "55035"]
        precinct_data["MCD_FIPS"] = ["5503522300", "5503522301"]
        loader.load_precinct_results("WI", 2020)
        assert set(PrecinctElectionResult.objects.values_list("precinct_id", flat=True)) == {
            "55035:5503522300:0060", "55035:5503522301:0060",
        }

    def test_georgia_missing_precinct_code_uses_county_sos_id(self, loader, precinct_data):
        precinct_data.rename(columns={"PRECINCT": "PRECINCT_I"}, inplace=True)
        precinct_data["PRECINCT_I"] = [None, None]
        precinct_data["FIPS2"] = ["215", "053"]
        precinct_data["CTYSOSID"] = ["FTBEN2", "FTBEN2"]
        loader.load_precinct_results("GA", 2020)
        assert set(PrecinctElectionResult.objects.values_list("precinct_id", flat=True)) == {
            "215:FTBEN2", "053:FTBEN2",
        }

    @pytest.mark.parametrize("county", [None, "", "  "])
    def test_missing_county_identifier_raises_and_preserves_snapshot(self, loader, precinct_data, county):
        loader.load_precinct_results("VA", 2020)
        precinct_data["COUNTYFP"] = [county, "003"]
        with pytest.raises(ValueError, match="Cannot resolve statewide precinct identifiers.*missing or blank"):
            loader.load_precinct_results("VA", 2020)
        assert PrecinctElectionResult.objects.aggregate(total=Sum("votes"))["total"] == 235

    def test_duplicate_within_county_raises(self, loader, precinct_data):
        precinct_data["COUNTYFP"] = ["001", "001"]
        precinct_data["PRECINCT"] = ["001", "001"]
        with pytest.raises(ValueError, match="Cannot resolve statewide.*Duplicate precinct identifiers"):
            loader.load_precinct_results("VA", 2020)
        assert not PrecinctElectionResult.objects.exists()

    def test_overlong_statewide_identifier_raises(self, loader, precinct_data):
        precinct_data["PRECINCT"] = ["A" * 61, "002"]
        with pytest.raises(ValueError, match="Precinct identifiers exceed 60 characters"):
            loader.load_precinct_results("VA", 2020)
        assert not PrecinctElectionResult.objects.exists()

    def test_identifier_separator_does_not_merge_components(self, loader, precinct_data):
        precinct_data["COUNTY"] = ["a:b", "a"]
        precinct_data["PRECINCT"] = ["c", "b:c"]
        loader.load_precinct_results("VA", 2020)
        assert set(PrecinctElectionResult.objects.values_list("precinct_id", flat=True)) == {
            "a%3Ab:c", "a:b%3Ac",
        }

    def test_reloading_same_fixture_preserves_vote_sum(self, loader):
        first = loader.load_precinct_results("VA", 2020)
        before = PrecinctElectionResult.objects.aggregate(total=Sum("votes"))["total"]
        second = loader.load_precinct_results("VA", 2020)
        after = PrecinctElectionResult.objects.aggregate(total=Sum("votes"))["total"]

        assert first.success and second.success
        assert before == 235
        assert after == before
        assert PrecinctElectionResult.objects.count() == 6

    def test_2024_harris_column_creates_democratic_president_row(self, loader, precinct_data):
        precinct_data.drop(columns=["G20PREDBID", "G20PRERTRU", "G20PREOWRI"], inplace=True)
        precinct_data["G24PREDHAR"] = [110, 25]
        precinct_data["G24PRERTRU"] = [90, 35]
        result = loader.load_precinct_results("VA", 2024)

        assert result.records_created == 4
        harris = PrecinctElectionResult.objects.get(precinct_id="001", party="DEM")
        assert (harris.election_year, harris.office, harris.candidate_name) == (
            2024,
            "president",
            "HAR",
        )
        assert (harris.votes, harris.total_votes, harris.vote_share) == (110, 200, 0.55)
        assert harris.geometry.geom_type == "MultiPolygon"
        assert harris.geometry.srid == 4326

    @pytest.mark.parametrize(
        "year,column,office,party,candidate",
        [
            (2016, "G16PREDCLI", "president", "DEM", "CLI"),
            (2026, "G26GOVRSMI", "governor", "REP", "SMI"),
            (2024, "G24H01LDOE", "house", "LIB", "DOE"),
            (2024, "G24USSGDOE", "senate", "GRN", "DOE"),
            (2024, "g24sosidoe", "secretary_of_state", "IND", "DOE"),
            (2024, "G24ATGOWRI", "attorney_general", "O", "WRI"),
        ],
    )
    def test_discovers_requested_year_and_office(
        self, loader, precinct_data, year, column, office, party, candidate
    ):
        precinct_data[column] = [11, 7]
        loader.load_precinct_results("VA", year)
        assert list(
            PrecinctElectionResult.objects.order_by("precinct_id").values_list(
                "office",
                "party",
                "candidate_name",
                "votes",
                "total_votes",
            )
        ) == [(office, party, candidate, 11, 11), (office, party, candidate, 7, 7)]

    def test_office_totals_include_other_parties_without_mixing_offices(
        self, loader, precinct_data
    ):
        precinct_data["G20USSDWAR"] = [10, 5]
        precinct_data["G20USSRGAD"] = [15, 5]
        loader.load_precinct_results("VA", 2020)

        president = PrecinctElectionResult.objects.get(
            precinct_id="001", office="president", party="DEM"
        )
        senate = PrecinctElectionResult.objects.get(precinct_id="001", office="senate", party="DEM")
        write_in = PrecinctElectionResult.objects.get(precinct_id="001", candidate_name="WRI")
        assert president.total_votes == 185
        assert president.vote_share == pytest.approx(100 / 185)
        assert senate.total_votes == 25
        assert senate.vote_share == 0.4
        assert (write_in.party, write_in.votes) == ("O", 5)

    def test_digit_bearing_candidate_code_loads_with_positional_party_and_office(
        self, loader, precinct_data
    ):
        precinct_data["G20USSDSM2"] = [10, 5]
        precinct_data["G20USSDWAR"] = [15, 5]

        result = loader.load_precinct_results("VA", 2020)

        assert result.success
        assert len(result.warnings) == 1 and "G20PREOWRI" in result.warnings[0]
        assert result.records_created == 10
        assert list(
            PrecinctElectionResult.objects.filter(office="senate")
            .order_by("precinct_id", "candidate_name")
            .values_list("precinct_id", "party", "candidate_name", "votes", "total_votes")
        ) == [
            ("001", "DEM", "SM2", 10, 25),
            ("001", "DEM", "WAR", 15, 25),
            ("002", "DEM", "SM2", 5, 10),
            ("002", "DEM", "WAR", 5, 10),
        ]
        smith = PrecinctElectionResult.objects.get(precinct_id="001", candidate_name="SM2")
        assert smith.vote_share == 0.4

    @pytest.mark.parametrize("column", ["G20PREDEM", "G20XYZZZZZZ", "G20PRE_TOTAL"])
    def test_non_conforming_year_column_is_skipped_and_warned_without_losing_votes(
        self, loader, precinct_data, caplog, column
    ):
        precinct_data[column] = ["not a vote", 9000]

        with caplog.at_level(logging.WARNING, logger=RDHLoaderService.__module__):
            result = loader.load_precinct_results("VA", 2020)

        assert result.success
        assert result.errors == []
        assert result.records_created == 6
        assert len(result.warnings) == 2
        warning = next(w for w in result.warnings if w.startswith("Skipping"))
        assert f"Skipping non-conforming VEST vote column {column!r}" in warning
        assert "VA 2020" in warning
        assert (RDHLoaderService.__module__, logging.WARNING, warning) in caplog.record_tuples
        assert list(
            PrecinctElectionResult.objects.order_by("precinct_id", "candidate_name")
            .values_list("precinct_id", "candidate_name", "votes", "total_votes")
        ) == [
            ("001", "BID", 100, 185),
            ("001", "TRU", 80, 185),
            ("001", "WRI", 5, 185),
            ("002", "BID", 20, 50),
            ("002", "TRU", 30, 50),
            ("002", "WRI", 0, 50),
        ]

    @pytest.mark.parametrize("missing", [float("nan"), None, pd.NA, "", "  "])
    def test_missing_vote_cell_is_zero_without_losing_other_votes(
        self, loader, precinct_data, missing
    ):
        precinct_data["G20PREDBID"] = pd.Series([missing, 20], dtype=object)
        result = loader.load_precinct_results("VA", 2020)
        dem = PrecinctElectionResult.objects.get(precinct_id="001", party="DEM")
        assert result.success
        assert (dem.votes, dem.total_votes, dem.vote_share) == (0, 85, 0.0)
        assert PrecinctElectionResult.objects.aggregate(total=Sum("votes"))["total"] == 135

    def test_unknown_state_raises_without_storing_sentinel(self, loader):
        with pytest.raises(ValueError, match="Unknown state abbreviation: 'XX'"):
            loader.load_precinct_results("XX", 2020)
        assert not PrecinctElectionResult.objects.exists()

    def test_zero_office_total_has_no_vote_share(self, loader, precinct_data):
        precinct_data.loc[:, ["G20PREDBID", "G20PRERTRU", "G20PREOWRI"]] = 0
        loader.load_precinct_results("VA", 2020)
        assert (
            PrecinctElectionResult.objects.filter(votes=0, total_votes=0, vote_share=None).count()
            == 6
        )

    def test_candidates_with_same_party_remain_distinct(self, loader, precinct_data):
        precinct_data["G20PREDOTH"] = [9, 1]
        loader.load_precinct_results("VA", 2020)
        loader.load_precinct_results("VA", 2020)
        assert list(
            PrecinctElectionResult.objects.filter(precinct_id="001", party="DEM")
            .order_by(
                "candidate_name",
            )
            .values_list("candidate_name", "votes", "total_votes")
        ) == [("BID", 100, 194), ("OTH", 9, 194)]

    def test_reload_replaces_changed_and_removed_candidates_only_in_source_scope(
        self, loader, precinct_data
    ):
        unrelated = [
            PrecinctElectionResult.objects.create(
                state_fips=state,
                election_year=year,
                precinct_id="001",
                office="president",
                party="DEM",
                candidate_name="BID",
                votes=9,
                data_source=source,
            ).pk
            for state, year, source in [
                ("06", 2020, "rdh"),
                ("51", 2016, "rdh"),
                ("51", 2020, "local"),
            ]
        ]
        loader.load_precinct_results("VA", 2020)
        precinct_data.drop(columns=["G20PREOWRI"], inplace=True)
        precinct_data["G20PREDBID"] = [150, 25]
        loader.load_precinct_results("VA", 2020)

        results = PrecinctElectionResult.objects.filter(
            state_fips="51", election_year=2020, data_source="rdh"
        )
        assert results.count() == 4
        assert results.aggregate(total=Sum("votes"))["total"] == 285
        assert not results.filter(candidate_name="WRI").exists()
        assert PrecinctElectionResult.objects.filter(pk__in=unrelated, votes=9).count() == 3

    @pytest.mark.parametrize(
        "column,office_code",
        [("G20TREDABC", "TRE"), ("g20audrdef", "AUD"), ("G20XYZDABC", "XYZ")],
    )
    def test_unmapped_office_column_is_skipped_and_warned_without_losing_votes(
        self, loader, precinct_data, caplog, column, office_code
    ):
        """Under #1592 and SU-1, an unmapped office is an observable omission."""
        precinct_data[column] = [1, 2]

        with caplog.at_level(logging.WARNING, logger=RDHLoaderService.__module__):
            result = loader.load_precinct_results("VA", 2020)

        assert result.success
        assert result.errors == []
        assert result.records_created == 6
        assert len(result.warnings) == 2
        warning = next(w for w in result.warnings if w.startswith("Skipping"))
        assert f"Skipping VEST vote column {column!r}" in warning
        assert f"unmapped office {office_code!r}" in warning
        assert "VA 2020" in warning
        assert (RDHLoaderService.__module__, logging.WARNING, warning) in caplog.record_tuples
        assert list(
            PrecinctElectionResult.objects.order_by("precinct_id", "candidate_name")
            .values_list("precinct_id", "office", "candidate_name", "votes", "total_votes")
        ) == [
            ("001", "president", "BID", 100, 185),
            ("001", "president", "TRU", 80, 185),
            ("001", "president", "WRI", 5, 185),
            ("002", "president", "BID", 20, 50),
            ("002", "president", "TRU", 30, 50),
            ("002", "president", "WRI", 0, 50),
        ]

    @pytest.mark.parametrize("remaining_column", ["OTHER_COLUMN", "G20PRE_TOTAL", "G20TREDABC"])
    def test_missing_year_columns_raises_and_preserves_previous_load(
        self, loader, precinct_data, remaining_column
    ):
        loader.load_precinct_results("VA", 2020)
        precinct_data.drop(columns=["G20PREDBID", "G20PRERTRU", "G20PREOWRI"], inplace=True)
        precinct_data[remaining_column] = [185, 50]
        with pytest.raises(ValueError, match="No VEST vote columns for election year 2020"):
            loader.load_precinct_results("VA", 2020)
        assert PrecinctElectionResult.objects.aggregate(total=Sum("votes"))["total"] == 235

    @pytest.mark.parametrize("ids", [["001", "001"], ["001", " 001 "]])
    def test_duplicate_precincts_raise_without_inflating_votes(self, loader, precinct_data, ids):
        precinct_data["PRECINCT"] = ids
        with pytest.raises(ValueError, match="Duplicate precinct identifiers"):
            loader.load_precinct_results("VA", 2020)
        assert not PrecinctElectionResult.objects.exists()

    @pytest.mark.parametrize("missing", [None, "", "  "])
    def test_missing_precinct_identifier_raises(self, loader, precinct_data, missing):
        precinct_data.loc[0, "PRECINCT"] = missing
        with pytest.raises(ValueError, match="Precinct identifiers must not be missing or blank"):
            loader.load_precinct_results("VA", 2020)
        assert not PrecinctElectionResult.objects.exists()

    def test_missing_precinct_column_raises(self, loader, precinct_data):
        precinct_data.drop(columns=["PRECINCT"], inplace=True)
        with pytest.raises(ValueError, match="Could not identify a precinct identifier column"):
            loader.load_precinct_results("VA", 2020)

    def test_empty_input_raises(self, loader, precinct_data):
        precinct_data.drop(index=precinct_data.index, inplace=True)
        with pytest.raises(ValueError, match="No precinct results for VA 2020"):
            loader.load_precinct_results("VA", 2020)

    def test_insert_failure_rolls_back_replacement(self, loader, precinct_data):
        loader.load_precinct_results("VA", 2020)
        before = list(PrecinctElectionResult.objects.order_by("pk").values_list("pk", "votes"))
        precinct_data["g20predbid"] = [1, 2]
        with pytest.raises(IntegrityError, match="precinct_result_identity_uniq"):
            loader.load_precinct_results("VA", 2020)
        assert (
            list(PrecinctElectionResult.objects.order_by("pk").values_list("pk", "votes")) == before
        )

    def test_invalid_vote_value_raises_and_preserves_previous_load(self, loader, precinct_data):
        loader.load_precinct_results("VA", 2020)
        precinct_data["G20PREDBID"] = ["invalid", "20"]
        with pytest.raises(ValueError, match="invalid literal for int"):
            loader.load_precinct_results("VA", 2020)
        assert PrecinctElectionResult.objects.aggregate(total=Sum("votes"))["total"] == 235

    def test_missing_rdh_file_reports_failure_and_preserves_previous_load(
        self, loader, monkeypatch
    ):
        loader.load_precinct_results("VA", 2020)

        def missing_file(*args, **kwargs):
            raise FileNotFoundError("No precinct data found for VA year=2020")

        monkeypatch.setattr(rdh, "fetch_precinct_results", missing_file)
        result = loader.load_precinct_results("VA", 2020)
        assert not result.success
        assert result.errors == ["No precinct data found for VA year=2020"]
        assert result.total_processed == 0
        assert PrecinctElectionResult.objects.aggregate(total=Sum("votes"))["total"] == 235

    def test_database_rejects_duplicate_natural_key(self):
        fields = dict(
            state_fips="51",
            election_year=2024,
            precinct_id="001",
            office="president",
            party="DEM",
            candidate_name="HAR",
            votes=10,
            data_source="rdh",
        )
        PrecinctElectionResult.objects.create(**fields)
        with (
            pytest.raises(IntegrityError, match="precinct_result_identity_uniq"),
            transaction.atomic(),
        ):
            PrecinctElectionResult.objects.create(**fields)
        assert PrecinctElectionResult.objects.count() == 1

    def test_party_display_label_is_not_part_of_identity(self):
        fields = dict(
            state_fips="27", election_year=2018, election_type="G", precinct_id="001",
            office="governor", district="", party_code="C", candidate_name="WRI", votes=7,
        )
        PrecinctElectionResult.objects.create(**fields, party="C")
        with pytest.raises(IntegrityError, match="precinct_result_identity_uniq"), transaction.atomic():
            PrecinctElectionResult.objects.create(**fields, party="Grassroots-Legalize Cannabis")
        assert PrecinctElectionResult.objects.count() == 1


@pytest.mark.parametrize("column", ["G20PREDEM", "G20PR1DBID", "G20PRE1BID"])
def test_malformed_vote_column_parser_raises(column):
    with pytest.raises(ValueError, match="Invalid VEST vote column"):
        RDHLoaderService._parse_vote_column(column)


def test_unsupported_vote_column_office_parser_raises():
    """The parser retains its invariant; batch discovery skips unmapped offices."""
    with pytest.raises(ValueError, match="Unsupported VEST office 'XYZ' in column 'G20XYZDABC'"):
        RDHLoaderService._parse_vote_column("G20XYZDABC")


def test_precinct_unique_constraint_migration_state_matches_model():
    loader = MigrationLoader(None)
    state = loader.project_state(loader.graph.leaf_nodes("siege_geo"))
    constraints = state.models["siege_geo", "precinctelectionresult"].options["constraints"]
    assert len(constraints) == 1
    assert constraints == PrecinctElectionResult._meta.constraints
    assert constraints[0].fields == (
        "state_fips",
        "election_year",
        "election_type",
        "precinct_id",
        "office",
        "district",
        "party_code",
        "candidate_name",
        "data_source",
    )


@pytest.mark.postgis
@pytest.mark.parametrize("direction", ["apply", "unapply"])
def test_precinct_unique_migration_uses_reversible_concurrent_index(direction):
    loader = MigrationLoader(None)
    migration = loader.disk_migrations["siege_geo", "0015_precinct_result_identity"]
    state = loader.project_state(migration.dependencies)
    assert migration.atomic is False
    with connection.schema_editor(collect_sql=True, atomic=False) as editor:
        getattr(migration, direction)(state, editor)
    statements = [" ".join(sql.split()).replace(" ;", ";") for sql in editor.collected_sql]
    expected = {
        "apply": [
            'DROP INDEX CONCURRENTLY IF EXISTS "precinct_result_identity_idx";',
            'CREATE UNIQUE INDEX CONCURRENTLY "precinct_result_identity_idx" '
            'ON "siege_geo_precinctelectionresult" ("state_fips", "election_year", "election_type", "precinct_id", '
            '"office", "district", "party_code", "candidate_name", "data_source");',
            'ALTER TABLE "siege_geo_precinctelectionresult" ADD CONSTRAINT '
            '"precinct_result_identity_uniq" UNIQUE USING INDEX "precinct_result_identity_idx";',
        ],
        "unapply": [
            'ALTER TABLE "siege_geo_precinctelectionresult" DROP CONSTRAINT IF EXISTS "precinct_result_identity_uniq";',
            'DROP INDEX CONCURRENTLY IF EXISTS "precinct_result_identity_idx";',
        ],
    }
    # Column creation/backfill precede the concurrent index; reversal removes
    # those columns only after detaching the constraint.
    index_statements = [sql for sql in statements if "precinct_result_identity_" in sql]
    assert index_statements == expected[direction]


@pytest.fixture
def precinct_migration_without_constraint(transactional_db):
    loader = MigrationLoader(None)
    migration = loader.disk_migrations["siege_geo", "0015_precinct_result_identity"]
    state = loader.project_state(migration.dependencies)
    with connection.schema_editor(atomic=False) as editor:
        migration.unapply(state, editor)
    try:
        yield migration, state
    finally:
        state.apps.get_model("siege_geo", "PrecinctElectionResult").objects.all().delete()
        with connection.schema_editor(atomic=False) as editor:
            migration.unapply(state, editor)
        with connection.schema_editor(atomic=False) as editor:
            migration.apply(state, editor)


@pytest.mark.postgis
def test_migration_rejects_existing_duplicates_and_retries_after_reconciliation(
    precinct_migration_without_constraint,
):
    migration, state = precinct_migration_without_constraint
    legacy_model = state.apps.get_model("siege_geo", "PrecinctElectionResult")
    fields = dict(
        state_fips="51",
        election_year=2024,
        precinct_id="001",
        office="president",
        party="DEM",
        candidate_name="HAR",
        votes=10,
        data_source="rdh",
    )
    original = legacy_model.objects.create(**fields)
    duplicate = legacy_model.objects.create(**fields)

    with (
        pytest.raises(IntegrityError, match="could not create unique index"),
        connection.schema_editor(atomic=False) as editor,
    ):
        migration.apply(state, editor)
    assert PrecinctElectionResult.objects.count() == 2

    duplicate.delete()
    with connection.schema_editor(atomic=False) as editor:
        migration.apply(state, editor)
    assert PrecinctElectionResult.objects.get().pk == original.pk
    with pytest.raises(IntegrityError, match="precinct_result_identity_uniq"), transaction.atomic():
        PrecinctElectionResult.objects.create(**fields, party_code="D")

    with connection.schema_editor(atomic=False) as editor:
        migration.unapply(state, editor)
    assert legacy_model.objects.get().votes == 10
    legacy_model.objects.create(**fields)
    assert legacy_model.objects.count() == 2


@pytest.mark.postgis
def test_migration_backfills_legacy_party_without_guessing_unknown_letters(
    precinct_migration_without_constraint,
):
    migration, state = precinct_migration_without_constraint
    legacy_model = state.apps.get_model("siege_geo", "PrecinctElectionResult")
    fields = dict(
        state_fips="27", election_year=2018, precinct_id="001", office="governor",
        candidate_name="WRI", votes=7,
    )
    legacy_model.objects.bulk_create([
        legacy_model(**fields, party="DEM"),
        legacy_model(**fields, party="REP"),
        legacy_model(**fields, party="OTHER"),
        legacy_model(**fields, party="C"),
    ])
    with connection.schema_editor(atomic=False) as editor:
        migration.apply(state, editor)
    assert list(PrecinctElectionResult.objects.order_by("party_code")
                .values_list("election_type", "district", "party_code", "party", "votes")) == [
        ("G", "", "C", "C", 7), ("G", "", "D", "DEM", 7),
        ("G", "", "OTHER", "OTHER", 7), ("G", "", "R", "REP", 7),
    ]
    with connection.schema_editor(atomic=False) as editor:
        migration.unapply(state, editor)
    assert list(legacy_model.objects.order_by("party").values_list("party", "votes")) == [
        ("C", 7), ("DEM", 7), ("OTHER", 7), ("REP", 7),
    ]

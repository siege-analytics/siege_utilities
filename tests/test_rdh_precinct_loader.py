"""Behavioral regressions for #1592, using the real ORM and PostGIS."""

import logging

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


@pytest.mark.django_db
class TestPrecinctLoading:
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
            (2024, "G24USHLDOE", "house", "LIB", "DOE"),
            (2024, "G24USSGDOE", "senate", "GRN", "DOE"),
            (2024, "g24sosidoe", "secretary_of_state", "IND", "DOE"),
            (2024, "G24ATGOWRI", "attorney_general", "OTHER", "WRI"),
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
        assert (write_in.party, write_in.votes) == ("OTHER", 5)

    def test_digit_bearing_candidate_code_loads_with_positional_party_and_office(
        self, loader, precinct_data
    ):
        precinct_data["G20USSDSM2"] = [10, 5]
        precinct_data["G20USSDWAR"] = [15, 5]

        result = loader.load_precinct_results("VA", 2020)

        assert result.success
        assert result.warnings == []
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
        assert len(result.warnings) == 1
        warning = result.warnings[0]
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
        assert len(result.warnings) == 1
        warning = result.warnings[0]
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
        "precinct_id",
        "office",
        "party",
        "candidate_name",
        "data_source",
    )


@pytest.mark.parametrize("direction", ["apply", "unapply"])
def test_precinct_unique_migration_uses_reversible_concurrent_index(direction):
    loader = MigrationLoader(None)
    migration = loader.disk_migrations["siege_geo", "0014_precinct_result_identity"]
    state = loader.project_state(migration.dependencies)
    assert migration.atomic is False
    with connection.schema_editor(collect_sql=True, atomic=False) as editor:
        getattr(migration, direction)(state, editor)
    statements = [" ".join(sql.split()).replace(" ;", ";") for sql in editor.collected_sql]
    expected = {
        "apply": [
            'DROP INDEX CONCURRENTLY IF EXISTS "precinct_result_identity_idx";',
            'CREATE UNIQUE INDEX CONCURRENTLY "precinct_result_identity_idx" '
            'ON "siege_geo_precinctelectionresult" ("state_fips", "election_year", "precinct_id", '
            '"office", "party", "candidate_name", "data_source");',
            'ALTER TABLE "siege_geo_precinctelectionresult" ADD CONSTRAINT '
            '"precinct_result_identity_uniq" UNIQUE USING INDEX "precinct_result_identity_idx";',
        ],
        "unapply": [
            'ALTER TABLE "siege_geo_precinctelectionresult" DROP CONSTRAINT IF EXISTS "precinct_result_identity_uniq";',
            'DROP INDEX CONCURRENTLY IF EXISTS "precinct_result_identity_idx";',
        ],
    }
    assert statements == expected[direction]


@pytest.fixture
def precinct_migration_without_constraint(transactional_db):
    loader = MigrationLoader(None)
    migration = loader.disk_migrations["siege_geo", "0014_precinct_result_identity"]
    state = loader.project_state(migration.dependencies)
    with connection.schema_editor(atomic=False) as editor:
        migration.unapply(state, editor)
    try:
        yield migration, state
    finally:
        PrecinctElectionResult.objects.all().delete()
        with connection.schema_editor(atomic=False) as editor:
            migration.unapply(state, editor)
        with connection.schema_editor(atomic=False) as editor:
            migration.apply(state, editor)


def test_migration_rejects_existing_duplicates_and_retries_after_reconciliation(
    precinct_migration_without_constraint,
):
    migration, state = precinct_migration_without_constraint
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
    original = PrecinctElectionResult.objects.create(**fields)
    duplicate = PrecinctElectionResult.objects.create(**fields)

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
        PrecinctElectionResult.objects.create(**fields)

    with connection.schema_editor(atomic=False) as editor:
        migration.unapply(state, editor)
    assert PrecinctElectionResult.objects.get().votes == 10
    PrecinctElectionResult.objects.create(**fields)
    assert PrecinctElectionResult.objects.count() == 2

"""Tests for redistricting Django models and Pydantic schemas."""

from __future__ import annotations

from datetime import date

import pytest

from siege_utilities.geo.schemas.redistricting import (
    DistrictDemographicsSchema,
    PlanDistrictSchema,
    PrecinctElectionResultSchema,
    RedistrictingPlanSchema,
)


# ---------------------------------------------------------------------------
# RedistrictingPlanSchema
# ---------------------------------------------------------------------------


class TestRedistrictingPlanSchema:

    def test_basic_creation(self):
        schema = RedistrictingPlanSchema(
            state_fips="51",
            chamber="congress",
            cycle_year=2020,
            plan_name="VA_congress_2020_enacted",
            num_districts=11,
        )
        assert schema.state_fips == "51"
        assert schema.chamber == "congress"
        assert schema.cycle_year == 2020
        assert schema.plan_name == "VA_congress_2020_enacted"
        assert schema.plan_type == "enacted"
        assert schema.source == "rdh"
        assert schema.num_districts == 11
        assert schema.enacted_date is None
        assert schema.data_source == "rdh"

    def test_all_fields(self):
        schema = RedistrictingPlanSchema(
            state_fips="06",
            chamber="state_senate",
            cycle_year=2020,
            plan_name="CA_state_senate_2021",
            plan_type="commission",
            source="commission",
            source_url="https://example.com/plan.zip",
            num_districts=40,
            enacted_date=date(2021, 12, 20),
            data_source="commission",
        )
        assert schema.plan_type == "commission"
        assert schema.source == "commission"
        assert schema.enacted_date == date(2021, 12, 20)

    def test_cycle_year_validation(self):
        with pytest.raises(Exception):
            RedistrictingPlanSchema(
                state_fips="51",
                chamber="congress",
                cycle_year=1800,  # too early
                plan_name="test",
                num_districts=1,
            )


# ---------------------------------------------------------------------------
# PlanDistrictSchema
# ---------------------------------------------------------------------------


class TestPlanDistrictSchema:

    def test_basic_creation(self):
        schema = PlanDistrictSchema(
            geoid="5101",
            name="District 1",
            vintage_year=2020,
            district_number="01",
        )
        assert schema.geoid == "5101"
        assert schema.district_number == "01"
        assert schema.polsby_popper is None
        assert schema.total_population is None

    def test_with_compactness(self):
        schema = PlanDistrictSchema(
            geoid="5101",
            name="District 1",
            vintage_year=2020,
            district_number="01",
            polsby_popper=0.45,
            reock=0.38,
            convex_hull_ratio=0.72,
            schwartzberg=0.67,
        )
        assert schema.polsby_popper == 0.45
        assert schema.reock == 0.38
        assert schema.convex_hull_ratio == 0.72
        assert schema.schwartzberg == 0.67

    def test_with_population(self):
        schema = PlanDistrictSchema(
            geoid="5101",
            name="District 1",
            vintage_year=2020,
            district_number="01",
            total_population=761169,
            vap=600000,
            cvap=550000,
            deviation_pct=0.12,
        )
        assert schema.total_population == 761169
        assert schema.vap == 600000
        assert schema.cvap == 550000
        assert schema.deviation_pct == 0.12

    def test_geoid_syncs_to_feature_id(self):
        schema = PlanDistrictSchema(
            geoid="5101",
            name="District 1",
            vintage_year=2020,
            district_number="01",
        )
        assert schema.feature_id == "5101"
        assert schema.boundary_id == "5101"

    def test_compactness_validation_bounds(self):
        with pytest.raises(Exception):
            PlanDistrictSchema(
                geoid="5101",
                name="D1",
                vintage_year=2020,
                district_number="01",
                polsby_popper=1.5,  # > 1.0
            )

    def test_plan_id_field(self):
        schema = PlanDistrictSchema(
            geoid="5101",
            name="District 1",
            vintage_year=2020,
            district_number="01",
            plan_id=42,
        )
        assert schema.plan_id == 42


# ---------------------------------------------------------------------------
# DistrictDemographicsSchema
# ---------------------------------------------------------------------------


class TestDistrictDemographicsSchema:

    def test_basic_creation(self):
        schema = DistrictDemographicsSchema(
            district_id=1,
            dataset="acs5",
            year=2022,
        )
        assert schema.district_id == 1
        assert schema.dataset == "acs5"
        assert schema.year == 2022
        assert schema.pop_white is None
        assert schema.values == {}

    def test_with_race_data(self):
        schema = DistrictDemographicsSchema(
            district_id=1,
            dataset="acs5",
            year=2022,
            pop_white=500000,
            pop_black=150000,
            pop_hispanic=80000,
            pop_asian=45000,
        )
        assert schema.pop_white == 500000
        assert schema.pop_black == 150000

    def test_auto_populate_from_values(self):
        schema = DistrictDemographicsSchema(
            district_id=1,
            dataset="acs5",
            year=2022,
            values={
                "B02001_002E": 500000,
                "B02001_003E": 150000,
                "B19013_001E": 75000,
            },
        )
        assert schema.pop_white == 500000
        assert schema.pop_black == 150000
        assert schema.median_household_income == 75000

    def test_explicit_overrides_auto(self):
        schema = DistrictDemographicsSchema(
            district_id=1,
            dataset="acs5",
            year=2022,
            pop_white=999,
            values={"B02001_002E": 500000},
        )
        # Explicit value takes precedence — auto-populate only fills None
        assert schema.pop_white == 999

    def test_poverty_rate_validation(self):
        with pytest.raises(Exception):
            DistrictDemographicsSchema(
                district_id=1,
                dataset="acs5",
                year=2022,
                poverty_rate=150.0,  # > 100
            )

    def test_json_values(self):
        values = {"B01001_001E": 761169, "B01002_001E": 38.5}
        schema = DistrictDemographicsSchema(
            district_id=1,
            dataset="acs5",
            year=2022,
            values=values,
        )
        assert schema.values["B01001_001E"] == 761169
        assert schema.values["B01002_001E"] == 38.5


# ---------------------------------------------------------------------------
# PrecinctElectionResultSchema
# ---------------------------------------------------------------------------


class TestPrecinctElectionResultSchema:

    def test_basic_creation(self):
        schema = PrecinctElectionResultSchema(
            state_fips="51",
            precinct_id="510010001",
            election_year=2020,
            office="president",
            party="DEM",
            votes=1500,
        )
        assert schema.state_fips == "51"
        assert schema.precinct_id == "510010001"
        assert schema.election_year == 2020
        assert schema.office == "president"
        assert schema.party == "DEM"
        assert schema.votes == 1500
        assert schema.total_votes is None
        assert schema.vote_share is None
        assert schema.data_source == "rdh"

    def test_with_totals(self):
        schema = PrecinctElectionResultSchema(
            state_fips="51",
            precinct_id="510010001",
            election_year=2020,
            office="president",
            party="DEM",
            votes=1500,
            total_votes=3000,
            vote_share=0.5,
        )
        assert schema.total_votes == 3000
        assert schema.vote_share == 0.5

    def test_vote_share_validation(self):
        with pytest.raises(Exception):
            PrecinctElectionResultSchema(
                state_fips="51",
                precinct_id="510010001",
                election_year=2020,
                office="president",
                party="DEM",
                votes=1500,
                vote_share=1.5,  # > 1.0
            )

    def test_candidate_name(self):
        schema = PrecinctElectionResultSchema(
            state_fips="51",
            precinct_id="510010001",
            election_year=2020,
            office="president",
            party="DEM",
            candidate_name="Joe Biden",
            votes=1500,
        )
        assert schema.candidate_name == "Joe Biden"

    def test_from_attributes(self):
        """Test that model_config from_attributes is set."""
        assert PrecinctElectionResultSchema.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# Import checks
# ---------------------------------------------------------------------------


class TestImports:

    def test_models_importable(self):
        """Verify models can be imported from the package."""
        from siege_utilities.geo.django.models.redistricting import (
            DistrictDemographics,
            PlanDistrict,
            PrecinctElectionResult,
            RedistrictingPlan,
        )
        assert RedistrictingPlan is not None
        assert PlanDistrict is not None
        assert DistrictDemographics is not None
        assert PrecinctElectionResult is not None

    def test_schemas_importable_from_package(self):
        """Verify schemas importable from siege_utilities.geo.schemas."""
        from siege_utilities.geo.schemas import (
            DistrictDemographicsSchema,
            PlanDistrictSchema,
            PrecinctElectionResultSchema,
            RedistrictingPlanSchema,
        )
        assert RedistrictingPlanSchema is not None
        assert PlanDistrictSchema is not None
        assert DistrictDemographicsSchema is not None
        assert PrecinctElectionResultSchema is not None

    def test_models_in_package_init(self):
        """Verify models appear in __init__ __all__."""
        from siege_utilities.geo.django import models as geo_models
        assert "RedistrictingPlan" in geo_models.__all__
        assert "PlanDistrict" in geo_models.__all__
        assert "DistrictDemographics" in geo_models.__all__
        assert "PrecinctElectionResult" in geo_models.__all__

    def test_schemas_in_package_init(self):
        """Verify schemas appear in __init__ __all__."""
        from siege_utilities.geo import schemas as geo_schemas
        assert "RedistrictingPlanSchema" in geo_schemas.__all__
        assert "PlanDistrictSchema" in geo_schemas.__all__
        assert "DistrictDemographicsSchema" in geo_schemas.__all__
        assert "PrecinctElectionResultSchema" in geo_schemas.__all__


# ---------------------------------------------------------------------------
# RDH Loader Service (unit tests — no Django DB)
# ---------------------------------------------------------------------------


class TestRDHLoaderServiceHelpers:

    def test_state_abbr_to_fips(self):
        from siege_utilities.geo.django.services.rdh_loader import RDHLoaderService

        assert RDHLoaderService._state_abbr_to_fips("VA") == "51"
        assert RDHLoaderService._state_abbr_to_fips("CA") == "06"
        assert RDHLoaderService._state_abbr_to_fips("DC") == "11"
        assert RDHLoaderService._state_abbr_to_fips("XX") == "00"

    def test_fips_to_state_abbr(self):
        from siege_utilities.geo.django.services.rdh_loader import RDHLoaderService

        assert RDHLoaderService._fips_to_state_abbr("51") == "VA"
        assert RDHLoaderService._fips_to_state_abbr("06") == "CA"
        assert RDHLoaderService._fips_to_state_abbr("99") == "XX"

    def test_parse_vote_column(self):
        from siege_utilities.geo.django.services.rdh_loader import RDHLoaderService

        party, office = RDHLoaderService._parse_vote_column("G20PREDEM")
        assert party == "DEM"
        assert office == "president"

        party, office = RDHLoaderService._parse_vote_column("G20PREREP")
        assert party == "REP"
        assert office == "president"

        party, office = RDHLoaderService._parse_vote_column("G18GOVDEM")
        assert party == "DEM"
        assert office == "governor"

        party, office = RDHLoaderService._parse_vote_column("G20USSLIB")
        assert party == "LIB"
        assert office == "senate"

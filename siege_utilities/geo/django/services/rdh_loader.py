"""
Service for loading Redistricting Data Hub data into Django models.

Orchestrates fetching data from RDH (via the data client), computing
compactness scores, overlaying demographics, and persisting to the
redistricting Django models.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from django.db import transaction

if TYPE_CHECKING:
    import geopandas as gpd

logger = logging.getLogger(__name__)


@dataclass
class RDHLoadResult:
    """Result of an RDH load operation."""

    operation: str
    records_created: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        return self.records_created + self.records_updated + self.records_skipped

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class RDHLoaderService:
    """Loads RDH data into Django redistricting models.

    Example::

        from siege_utilities.geo.django.services.rdh_loader import RDHLoaderService

        service = RDHLoaderService()
        plan = service.load_enacted_plan("VA", "congress", 2020)
        service.compute_plan_compactness(plan)
        count = service.load_demographics_for_plan(plan, acs_year=2022)
    """

    def __init__(self, client=None):
        """
        Parameters
        ----------
        client : RDHClient, optional
            Pre-configured RDH client.  Created from env vars if omitted.
        """
        from siege_utilities.data.redistricting_data_hub import RDHClient

        self.client = client or RDHClient()

    @transaction.atomic
    def load_enacted_plan(
        self,
        state: str,
        chamber: str,
        cycle_year: int,
        year: Optional[str] = None,
    ):
        """Fetch and load an enacted redistricting plan with all districts.

        Parameters
        ----------
        state : str
            Two-letter state abbreviation.
        chamber : str
            ``"congress"``, ``"state_senate"``, or ``"state_house"``.
        cycle_year : int
            Redistricting cycle (e.g. 2020).
        year : str, optional
            Year filter for the RDH query.

        Returns
        -------
        RedistrictingPlan
            The created or updated plan instance.
        """
        from siege_utilities.data.redistricting_data_hub import fetch_enacted_plan
        from siege_utilities.geo.django.models.boundaries import State
        from siege_utilities.geo.django.models.redistricting import (
            PlanDistrict,
            RedistrictingPlan,
        )

        logger.info("Loading enacted %s plan for %s (cycle %d)", chamber, state, cycle_year)

        gdf = fetch_enacted_plan(state, chamber=chamber, year=year, client=self.client)

        # Resolve state FIPS
        state_fips = self._state_abbr_to_fips(state)

        # Find or resolve state FK
        state_obj = State.objects.filter(state_fips=state_fips).first()

        plan_name = f"{state}_{chamber}_{cycle_year}_enacted"

        plan, _created = RedistrictingPlan.objects.update_or_create(
            state_fips=state_fips,
            chamber=chamber,
            cycle_year=cycle_year,
            plan_name=plan_name,
            defaults={
                "state": state_obj,
                "plan_type": "enacted",
                "source": "rdh",
                "num_districts": len(gdf),
                "data_source": "rdh",
            },
        )

        # Determine GEOID and district number columns
        geoid_col = self._find_column(gdf, ["GEOID", "GEOID20", "GEOID10", "geoid"])
        district_col = self._find_column(
            gdf, ["DISTRICT", "NAMELSAD", "CD", "SLDUST", "SLDLST", "NAME", "District"]
        )

        created_count = 0
        for _, row in gdf.iterrows():
            geoid = str(row[geoid_col]) if geoid_col else ""
            district_number = str(row[district_col]) if district_col else str(_ + 1)

            geom = row.geometry
            # Ensure MultiPolygon
            from django.contrib.gis.geos import GEOSGeometry

            geos_geom = GEOSGeometry(geom.wkt, srid=4326)
            if geos_geom.geom_type == "Polygon":
                from django.contrib.gis.geos import MultiPolygon

                geos_geom = MultiPolygon(geos_geom, srid=4326)

            _district, dist_created = PlanDistrict.objects.update_or_create(
                plan=plan,
                district_number=district_number,
                defaults={
                    "geoid": geoid,
                    "state_fips": state_fips,
                    "name": district_number,
                    "feature_id": geoid,
                    "boundary_id": geoid,
                    "vintage_year": cycle_year,
                    "geometry": geos_geom,
                    "source": "RDH",
                },
            )
            if dist_created:
                created_count += 1

        logger.info(
            "Loaded plan %s with %d districts (%d new)",
            plan_name, len(gdf), created_count,
        )
        return plan

    @transaction.atomic
    def load_precinct_results(
        self,
        state: str,
        election_year: int,
        year: Optional[str] = None,
        plan=None,
    ) -> RDHLoadResult:
        """Fetch and load precinct election results.

        Parameters
        ----------
        state : str
            Two-letter state abbreviation.
        election_year : int
            Election year.
        year : str, optional
            Year filter for RDH query.
        plan : RedistrictingPlan, optional
            Link results to a specific plan.

        Returns
        -------
        RDHLoadResult
        """
        from siege_utilities.data.redistricting_data_hub import fetch_precinct_results
        from siege_utilities.geo.django.models.boundaries import State
        from siege_utilities.geo.django.models.redistricting import PrecinctElectionResult

        result = RDHLoadResult(operation="load_precinct_results")

        try:
            gdf = fetch_precinct_results(state, year=year or str(election_year), client=self.client)
        except FileNotFoundError as e:
            result.errors.append(str(e))
            return result

        state_fips = self._state_abbr_to_fips(state)
        state_obj = State.objects.filter(state_fips=state_fips).first()

        # Identify columns
        precinct_col = self._find_column(
            gdf, ["PRECINCT", "PREC_ID", "VTDST", "precinct_id", "VTD", "PCTNUM"]
        )
        name_col = self._find_column(
            gdf, ["PRECINCT_NAME", "PREC_NAME", "NAME", "precinct_name"]
        )

        # Find vote columns — look for party-prefixed columns
        vote_cols = [
            c for c in gdf.columns
            if any(
                c.upper().startswith(p)
                for p in ("G20PRE", "G18GOV", "G22GOV", "G20USS", "G22USS")
            )
        ]

        records = []
        for _, row in gdf.iterrows():
            precinct_id = str(row[precinct_col]) if precinct_col else str(_)
            precinct_name = str(row[name_col]) if name_col else ""

            geom = None
            if row.geometry is not None and not row.geometry.is_empty:
                from django.contrib.gis.geos import GEOSGeometry, MultiPolygon

                geos_geom = GEOSGeometry(row.geometry.wkt, srid=4326)
                if geos_geom.geom_type == "Polygon":
                    geos_geom = MultiPolygon(geos_geom, srid=4326)
                geom = geos_geom

            # Create a record for each vote column found
            if vote_cols:
                for col in vote_cols:
                    party, office = self._parse_vote_column(col)
                    votes = int(row[col]) if row[col] is not None else 0
                    records.append(PrecinctElectionResult(
                        plan=plan,
                        state=state_obj,
                        state_fips=state_fips,
                        precinct_id=precinct_id,
                        precinct_name=precinct_name,
                        geometry=geom,
                        election_year=election_year,
                        office=office,
                        party=party,
                        votes=votes,
                        data_source="rdh",
                    ))
            else:
                # Fallback: store as a single record with total votes
                total_col = self._find_column(gdf, ["TOTAL", "TOTVOTES", "total_votes"])
                total = int(row[total_col]) if total_col and row[total_col] is not None else 0
                records.append(PrecinctElectionResult(
                    plan=plan,
                    state=state_obj,
                    state_fips=state_fips,
                    precinct_id=precinct_id,
                    precinct_name=precinct_name,
                    geometry=geom,
                    election_year=election_year,
                    office="president",
                    party="TOTAL",
                    votes=total,
                    data_source="rdh",
                ))

        if records:
            PrecinctElectionResult.objects.bulk_create(records, batch_size=500)
            result.records_created = len(records)

        logger.info("Loaded %d precinct results for %s %d", len(records), state, election_year)
        return result

    @transaction.atomic
    def load_cvap_for_plan(self, plan, year: int) -> RDHLoadResult:
        """Overlay CVAP data onto plan districts via spatial join.

        Parameters
        ----------
        plan : RedistrictingPlan
            Plan whose districts will be updated.
        year : int
            CVAP data year.

        Returns
        -------
        RDHLoadResult
        """
        from siege_utilities.data.redistricting_data_hub import fetch_cvap

        result = RDHLoadResult(operation="load_cvap_for_plan")

        state = self._fips_to_state_abbr(plan.state_fips)
        try:
            cvap_df = fetch_cvap(state, year=str(year), client=self.client)
        except FileNotFoundError as e:
            result.errors.append(str(e))
            return result

        # Find CVAP total column
        cvap_col = self._find_column_df(
            cvap_df, ["CVAP_EST", "cvap_est", "CVAP", "cvap"]
        )
        geoid_col = self._find_column_df(
            cvap_df, ["GEOID", "geoid", "GEOID20"]
        )

        if not cvap_col or not geoid_col:
            result.errors.append("Could not identify CVAP or GEOID columns")
            return result

        cvap_lookup = dict(zip(cvap_df[geoid_col].astype(str), cvap_df[cvap_col]))

        updated = 0
        for district in plan.districts.all():
            if district.geoid in cvap_lookup:
                district.cvap = int(cvap_lookup[district.geoid])
                district.save(update_fields=["cvap"])
                updated += 1

        result.records_updated = updated
        logger.info("Updated CVAP for %d districts in plan %s", updated, plan)
        return result

    @transaction.atomic
    def load_demographics_for_plan(
        self,
        plan,
        acs_year: int,
        census_gdf: Optional["gpd.GeoDataFrame"] = None,
    ) -> RDHLoadResult:
        """Overlay ACS demographics onto plan districts via spatial join.

        Parameters
        ----------
        plan : RedistrictingPlan
            Plan to populate.
        acs_year : int
            ACS 5-year data year.
        census_gdf : GeoDataFrame, optional
            Pre-loaded Census data.  If omitted, fetches from RDH.

        Returns
        -------
        RDHLoadResult
        """
        from siege_utilities.data.redistricting_data_hub import (
            demographic_profile,
            fetch_demographic_summary,
        )
        from siege_utilities.geo.django.models.redistricting import DistrictDemographics
        from siege_utilities.geo.schemas.converters import orm_to_gdf

        result = RDHLoadResult(operation="load_demographics_for_plan")

        # Get plan districts as GeoDataFrame
        districts_qs = plan.districts.exclude(geometry__isnull=True)
        if not districts_qs.exists():
            result.errors.append("No districts with geometry found")
            return result

        plan_gdf = orm_to_gdf(districts_qs, geometry_field="geometry")

        # Identify the district column
        district_id_col = "geoid" if "geoid" in plan_gdf.columns else plan_gdf.columns[0]

        if census_gdf is None:
            state = self._fips_to_state_abbr(plan.state_fips)
            try:
                census_gdf = fetch_demographic_summary(
                    state, year=str(acs_year), client=self.client,
                )
            except FileNotFoundError as e:
                result.errors.append(str(e))
                return result

            # If it's a DataFrame (CSV), we can't do spatial join
            # Store what we can by GEOID match
            geoid_col = self._find_column_df(census_gdf, ["GEOID", "geoid", "GEOID20"])
            if geoid_col:
                for district in districts_qs:
                    row = census_gdf[census_gdf[geoid_col].astype(str) == district.geoid]
                    if row.empty:
                        result.records_skipped += 1
                        continue
                    row = row.iloc[0]
                    values = {
                        col: row[col]
                        for col in census_gdf.columns
                        if col != geoid_col and str(row[col]) != "nan"
                    }
                    DistrictDemographics.objects.update_or_create(
                        district=district,
                        dataset="acs5",
                        year=acs_year,
                        defaults={"values": values},
                    )
                    result.records_created += 1
                return result

        # Spatial join path (when census_gdf is a GeoDataFrame)
        try:
            profile_df = demographic_profile(
                plan_gdf, census_gdf, district_id_col=district_id_col,
            )
        except Exception as e:
            result.errors.append(f"Spatial join failed: {e}")
            return result

        for _, row in profile_df.iterrows():
            district = districts_qs.filter(geoid=str(row[district_id_col])).first()
            if not district:
                result.records_skipped += 1
                continue

            values = {
                col: row[col]
                for col in profile_df.columns
                if col != district_id_col
            }
            DistrictDemographics.objects.update_or_create(
                district=district,
                dataset="acs5",
                year=acs_year,
                defaults={"values": values},
            )
            result.records_created += 1

        logger.info(
            "Loaded demographics for %d districts in plan %s",
            result.records_created, plan,
        )
        return result

    def compute_plan_compactness(self, plan) -> None:
        """Compute and store compactness scores for all districts in a plan.

        Parameters
        ----------
        plan : RedistrictingPlan
            Plan whose districts will be scored.
        """
        from siege_utilities.data.redistricting_data_hub import (
            convex_hull_ratio as chr_fn,
            polsby_popper as pp_fn,
            reock as reock_fn,
            schwartzberg as sw_fn,
        )

        districts = plan.districts.exclude(geometry__isnull=True)
        updated = 0
        for district in districts:
            # Convert GEOS to Shapely for compactness functions
            from shapely import wkt

            shapely_geom = wkt.loads(district.geometry.wkt)
            district.polsby_popper = pp_fn(shapely_geom)
            district.reock = reock_fn(shapely_geom)
            district.convex_hull_ratio = chr_fn(shapely_geom)
            district.schwartzberg = sw_fn(shapely_geom)
            district.save(update_fields=[
                "polsby_popper", "reock", "convex_hull_ratio", "schwartzberg",
            ])
            updated += 1

        logger.info("Computed compactness for %d districts in plan %s", updated, plan)

    # -- Helpers --------------------------------------------------------------

    @staticmethod
    def _find_column(gdf, candidates: list[str]) -> Optional[str]:
        """Find first matching column name (case-insensitive)."""
        cols_upper = {c.upper(): c for c in gdf.columns}
        for candidate in candidates:
            if candidate.upper() in cols_upper:
                return cols_upper[candidate.upper()]
        return None

    @staticmethod
    def _find_column_df(df, candidates: list[str]) -> Optional[str]:
        """Find first matching column in a plain DataFrame."""
        cols_upper = {c.upper(): c for c in df.columns}
        for candidate in candidates:
            if candidate.upper() in cols_upper:
                return cols_upper[candidate.upper()]
        return None

    @staticmethod
    def _parse_vote_column(col: str) -> tuple[str, str]:
        """Parse a vote column name like G20PREDEM into (party, office)."""
        col_upper = col.upper()
        # Common patterns: G20PREDEM, G20PREREP, G18GOVDEM, G20USSDEM
        office_map = {
            "PRE": "president",
            "GOV": "governor",
            "USS": "senate",
            "USH": "house",
            "SOS": "secretary_of_state",
            "ATG": "attorney_general",
        }
        party = "OTHER"
        office = "president"
        if len(col_upper) >= 6:
            office_code = col_upper[3:6]
            office = office_map.get(office_code, "president")
        if col_upper.endswith("DEM"):
            party = "DEM"
        elif col_upper.endswith("REP"):
            party = "REP"
        elif col_upper.endswith("LIB"):
            party = "LIB"
        elif col_upper.endswith("GRN"):
            party = "GRN"
        elif col_upper.endswith("IND"):
            party = "IND"
        return party, office

    @staticmethod
    def _state_abbr_to_fips(abbr: str) -> str:
        """Convert state abbreviation to 2-digit FIPS code."""
        _map = {
            "AL": "01", "AK": "02", "AZ": "04", "AR": "05", "CA": "06",
            "CO": "08", "CT": "09", "DE": "10", "FL": "12", "GA": "13",
            "HI": "15", "ID": "16", "IL": "17", "IN": "18", "IA": "19",
            "KS": "20", "KY": "21", "LA": "22", "ME": "23", "MD": "24",
            "MA": "25", "MI": "26", "MN": "27", "MS": "28", "MO": "29",
            "MT": "30", "NE": "31", "NV": "32", "NH": "33", "NJ": "34",
            "NM": "35", "NY": "36", "NC": "37", "ND": "38", "OH": "39",
            "OK": "40", "OR": "41", "PA": "42", "RI": "44", "SC": "45",
            "SD": "46", "TN": "47", "TX": "48", "UT": "49", "VT": "50",
            "VA": "51", "WA": "53", "WV": "54", "WI": "55", "WY": "56",
            "DC": "11", "PR": "72",
        }
        return _map.get(abbr.upper(), "00")

    @staticmethod
    def _fips_to_state_abbr(fips: str) -> str:
        """Convert 2-digit FIPS code to state abbreviation."""
        _map = {
            "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
            "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
            "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
            "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
            "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
            "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
            "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
            "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
            "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
            "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
            "56": "WY", "72": "PR",
        }
        return _map.get(fips, "XX")

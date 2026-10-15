"""
Service for loading Redistricting Data Hub data into Django models.

Orchestrates fetching data from RDH (via the data client), computing
compactness scores, overlaying demographics, and persisting to the
redistricting Django models.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from django.db import transaction
from django.db.models import Q

if TYPE_CHECKING:
    import geopandas as gpd

logger = logging.getLogger(__name__)

_VEST_VOTE_COLUMN_RE = re.compile(r"^[GSRCP][0-9]{2}(?:[A-Z]{3}|H[0-9]{2})[A-Z][A-Z0-9]{3}$")
_VEST_VOTE_PREFIX_RE = re.compile(r"^[GSRCP][0-9]{2}")
_VEST_HOUSE_RE = re.compile(r"^H(?:[0-9]{2}|AL)$")
_VEST_PARTY_MAP = {"D": "DEM", "R": "REP", "L": "LIB", "G": "GRN", "I": "IND"}
_VEST_OFFICE_MAP = {
    "PRE": "president",
    "GOV": "governor",
    "USS": "senate",
    "SOS": "secretary_of_state",
    "ATG": "attorney_general",
}

__all__ = [
    'RDHLoadResult',
    'RDHLoaderService',
]


@dataclass
class RDHLoadResult:
    """Result of an RDH load operation; warnings describe recoverable omissions."""

    operation: str
    records_created: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

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
        from siege_utilities.geo.providers.redistricting_data_hub import RDHClient

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
        from siege_utilities.geo.providers.redistricting_data_hub import fetch_enacted_plan
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
            if geom is None or geom.is_empty:
                logger.warning(
                    "Skipping row %s: null or empty geometry", geoid or _
                )
                continue

            from django.contrib.gis.geos import GEOSGeometry

            geos_geom = GEOSGeometry(geom.wkt, srid=4326)
            if geos_geom.geom_type not in ("Polygon", "MultiPolygon"):
                logger.warning(
                    "Skipping row %s: expected Polygon/MultiPolygon, got %s",
                    geoid or _, geos_geom.geom_type,
                )
                continue
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
        """Replace RDH results for a state, election year and next-year runoffs.

        Read VEST vote columns (TYYOOOPCCC), including general, special, runoff,
        recount and primary elections. Store the raw election type, House
        district (two digits or AL), and party letter in the result identity.
        Next-year runoffs in the same file use their own election year (e.g.
        GA's R21 Senate columns in the 2020 file are stored as 2021). Other-year
        columns are skipped with warnings. Reload replaces the requested year
        and next-year runoff scope, including candidates removed from the file.
        In DC only, DEL is House/AL; USS and HAL are shadow offices, skipped
        with warnings. Known party display labels do not replace the source
        party code; unmapped letters are preserved and warned per column.
        Store the three-character alphanumeric candidate code in candidate_name;
        full surnames are not in the file. Skip non-conforming year-prefixed
        columns and columns with unmapped offices with logged warnings recorded
        in the result. Missing
        or blank vote cells count as zero. Totals include every conforming
        candidate column in each mapped office prefix, including unrecognized
        parties.
        Prefer existing GEOID and county-qualified precinct identifiers, then
        GEOID16/18, county-qualified VTDST16/18 and statewide VTDID alternatives.
        WARDID also needs its municipality when supplied.
        Every resolved identifier must be nonblank and unique within the state.
        Blank-ID rows may be skipped only when every vote-prefixed column is
        zero (missing vote cells count as zero), with the skipped count warned.
        Geometry is expected in WGS 84 (EPSG:4326) and stored as 2D boundaries.

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
            Number of replacement rows created, skipped blank-ID precincts,
            warnings for skipped columns and unknown parties,
            or errors if RDH has no file. Warnings do not mark the load failed.

        Raises
        ------
        ValueError
            If the state or precinct identifiers are invalid, or no conforming
            vote columns with mapped offices match election_year. Existing
            rows remain intact.
        """
        from siege_utilities.geo.providers.redistricting_data_hub import fetch_precinct_results
        from siege_utilities.geo.django.models.boundaries import State
        from siege_utilities.geo.django.models.redistricting import PrecinctElectionResult
        import pandas as pd

        result = RDHLoadResult(operation="load_precinct_results")
        state_fips = self._state_abbr_to_fips(state)

        try:
            gdf = fetch_precinct_results(state, year=year or str(election_year), client=self.client)
        except FileNotFoundError as e:
            result.errors.append(str(e))
            return result

        state_obj = State.objects.filter(state_fips=state_fips).first()

        # Identify columns
        name_col = self._find_column(
            gdf, ["PRECINCT_NAME", "PREC_NAME", "PRECINCT_N", "NAME20", "NAME", "precinct_name"]
        )

        if gdf.empty:
            raise ValueError(f"No precinct results for {state} {election_year}")
        vote_cols = []
        column_years = {}
        source_vote_cols = [col for col in gdf.columns if _VEST_VOTE_PREFIX_RE.match(col.upper())]
        for col in source_vote_cols:
            col_upper = col.upper()
            column_year = election_year if int(col_upper[1:3]) == election_year % 100 else None
            if col_upper.startswith(f"R{(election_year + 1) % 100:02d}"):
                column_year = election_year + 1
            if _VEST_VOTE_COLUMN_RE.fullmatch(col_upper) is None:
                warning = (
                    f"Skipping non-conforming VEST vote column {col!r} for "
                    f"{state} {election_year}; expected {_VEST_VOTE_COLUMN_RE.pattern}"
                )
            elif column_year is None:
                warning = (
                    f"Skipping VEST vote column {col!r} for {state} {election_year}; "
                    "outside the requested election year and next-year runoffs"
                )
            elif state_fips == "11" and col_upper[3:6] in {"USS", "HAL"}:
                warning = (
                    f"Skipping VEST vote column {col!r} for {state} {election_year}; "
                    f"DC shadow office {col_upper[3:6]!r}"
                )
            elif (
                col_upper[3:6] not in _VEST_OFFICE_MAP
                and _VEST_HOUSE_RE.fullmatch(col_upper[3:6]) is None
                and not (state_fips == "11" and col_upper[3:6] == "DEL")
            ):
                warning = (
                    f"Skipping VEST vote column {col!r} for {state} {election_year}; "
                    f"unmapped office {col_upper[3:6]!r}"
                )
            else:
                vote_cols.append(col)
                column_years[col] = column_year
                if col_upper[6] in _VEST_PARTY_MAP:
                    continue
                warning = (
                    f"Preserving unmapped party letter {col_upper[6]!r} in VEST vote column "
                    f"{col!r} for {state} {election_year}"
                )
            logger.warning(warning)
            result.warnings.append(warning)
        if not vote_cols:
            raise ValueError(f"No VEST vote columns for election year {election_year}")
        parsed_cols = {col: self._parse_vote_column(col, state_fips=state_fips) for col in vote_cols}

        # Include skipped offices, years and malformed columns in the zero test.
        # Invalid numeric text must not become evidence that a row has no votes.
        zero_vote_rows = gdf[source_vote_cols].apply(
            lambda col: pd.to_numeric(col, errors="coerce").eq(0)
            | col.isna() | col.astype(str).str.strip().eq("")
        ).all(axis=1)
        precinct_ids = self._resolve_precinct_ids(gdf, zero_vote_rows=zero_vote_rows)
        result.records_skipped = precinct_ids.count(None)
        if result.records_skipped:
            warning = (
                f"Skipping {result.records_skipped} precinct rows for {state} {election_year}: "
                "missing or blank identifiers and zero votes in every vote column"
            )
            logger.warning(warning)
            result.warnings.append(warning)

        records = []
        for precinct_id, (_, row) in zip(precinct_ids, gdf.iterrows()):
            if precinct_id is None:
                continue
            precinct_name = str(row[name_col]) if name_col else ""

            geom = None
            if row.geometry is not None and not row.geometry.is_empty:
                from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
                from shapely import force_2d

                geos_geom = GEOSGeometry(force_2d(row.geometry).wkt, srid=4326)
                if geos_geom.geom_type == "Polygon":
                    geos_geom = MultiPolygon(geos_geom, srid=4326)
                geom = geos_geom

            votes_by_col = {}
            totals = {}
            for col in vote_cols:
                raw = row[col]
                votes = 0 if pd.isna(raw) or (isinstance(raw, str) and not raw.strip()) else int(raw)
                votes_by_col[col] = votes
                prefix = col.upper()[:6]
                totals[prefix] = totals.get(prefix, 0) + votes

            for col, (party, office) in parsed_cols.items():
                votes = votes_by_col[col]
                total = totals[col.upper()[:6]]
                records.append(PrecinctElectionResult(
                    plan=plan,
                    state=state_obj,
                    state_fips=state_fips,
                    precinct_id=precinct_id,
                    precinct_name=precinct_name,
                    geometry=geom,
                    election_year=column_years[col],
                    election_type=col.upper()[0],
                    office=office,
                    district=("AL" if col.upper()[3:6] == "DEL" else col.upper()[4:6])
                    if office == "house" else "",
                    party=party,
                    party_code=col.upper()[6],
                    candidate_name=col.upper()[7:10],
                    votes=votes,
                    total_votes=total,
                    vote_share=votes / total if total else None,
                    data_source="rdh",
                ))

        # Replace the source snapshot only after all input has been parsed.
        # The transaction restores the previous snapshot if insertion fails.
        PrecinctElectionResult.objects.filter(
            Q(election_year=election_year) | Q(election_year=election_year + 1, election_type="R"),
            state_fips=state_fips, data_source="rdh",
        ).delete()
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
        from siege_utilities.geo.providers.redistricting_data_hub import fetch_cvap

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
                raw = cvap_lookup[district.geoid]
                if raw is None or (isinstance(raw, float) and raw != raw):
                    continue
                district.cvap = int(raw)
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
        from siege_utilities.geo.providers.redistricting_data_hub import (
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
        except (ValueError, TypeError, KeyError, AttributeError, OSError) as e:
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
        from siege_utilities.geo.providers.redistricting_data_hub import (
            convex_hull_ratio as chr_fn,
            polsby_popper as pp_fn,
            reock as reock_fn,
            schwartzberg as sw_fn,
        )

        districts = plan.districts.exclude(geometry__isnull=True)
        srid = districts.first().geometry.srid if districts.exists() else 4326
        updated = 0
        for district in districts:
            from shapely import wkt

            shapely_geom = wkt.loads(district.geometry.wkt)
            district.polsby_popper = pp_fn(shapely_geom, source_crs=f"EPSG:{srid}")
            district.reock = reock_fn(shapely_geom, source_crs=f"EPSG:{srid}")
            district.convex_hull_ratio = chr_fn(shapely_geom, source_crs=f"EPSG:{srid}")
            district.schwartzberg = sw_fn(shapely_geom, source_crs=f"EPSG:{srid}")
            district.save(update_fields=[
                "polsby_popper", "reock", "convex_hull_ratio", "schwartzberg",
            ])
            updated += 1

        logger.info("Computed compactness for %d districts in plan %s", updated, plan)

    # -- Helpers --------------------------------------------------------------

    @classmethod
    def _resolve_precinct_ids(cls, gdf, *, zero_vote_rows=None) -> list[Optional[str]]:
        """Resolve a complete statewide key from observed VEST identifier fields.

        Try whole-file alternatives, never row numbers or per-row substitutions.
        County-local VTDs are qualified even when this file happens to be unique.
        GA's CTYSOSID is an alternative when PRECINCT_I includes missing codes.
        Prefer a complete candidate over one requiring omission of zero-vote
        blank-ID rows. Return None at omitted positions to preserve row alignment.
        """
        county_col = cls._find_column(gdf, [
            "COUNTYFP20", "COUNTYFP10", "COUNTYFP", "CNTY_FIPS", "COUNTY_FIPS",
            "FIPS2", "CDE_COUNTY", "COUNTY", "CNTY", "CNTY_NAME", "LOCALITY",
        ])
        municipality_col = cls._find_column(gdf, ["MCD_FIPS", "MCD", "MCD_NAME"])
        candidates = []
        for name in [
            "GEOID20", "GEOID10", "GEOID", "VTDST20", "VTDST10", "PRECINCT",
            "PRECINCT_I", "SOSPRECINC", "WARDID", "CTYSOSID", "PREC_ID",
            "VTDST", "precinct_id", "VTD", "PCTNUM",
            "GEOID16", "GEOID18", "VTDST16", "VTDST18", "VTDID",
        ]:
            col = cls._find_column(gdf, [name])
            if col is None:
                continue
            parts = [col]
            if not name.startswith("GEOID") and name != "VTDID":
                if name == "WARDID" and municipality_col:
                    parts.insert(0, municipality_col)
                if county_col:
                    parts.insert(0, county_col)
            candidates.append(parts)
        if not candidates:
            raise ValueError("Could not identify a precinct identifier column")

        failures = []
        partial_ids = None
        for columns in candidates:
            parts = gdf[columns].astype(str).apply(lambda s: s.str.strip())
            missing = gdf[columns].isna().any(axis=1) | parts.eq("").any(axis=1)
            if missing.any():
                failures.append(f"{columns}: Precinct identifiers must not be missing or blank")
                if zero_vote_rows is None or not zero_vote_rows[missing].all() or missing.all():
                    continue
            # Escape the separator so component boundaries cannot alias.
            parts = parts.apply(
                lambda s: s.str.replace("%", "%25", regex=False).str.replace(":", "%3A", regex=False)
            )
            ids = parts.agg(":".join, axis=1)
            if ids[~missing].duplicated().any():
                failures.append(f"{columns}: Duplicate precinct identifiers")
                continue
            if ids[~missing].str.len().gt(60).any():
                failures.append(f"{columns}: Precinct identifiers exceed 60 characters")
                continue
            if not missing.any():
                logger.info("Resolved statewide precinct identifiers from %s", columns)
                return ids.tolist()
            if partial_ids is None:
                partial_ids = [None if absent else value for value, absent in zip(ids, missing)]
        if partial_ids is not None:
            return partial_ids
        raise ValueError("Cannot resolve statewide precinct identifiers; " + "; ".join(failures))

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
    def _parse_vote_column(col: str, state_fips: Optional[str] = None) -> tuple[str, str]:
        """Parse a VEST TYYOOOPCCC column into (party display label, office)."""
        col_upper = col.upper()
        if _VEST_VOTE_COLUMN_RE.fullmatch(col_upper) is None:
            raise ValueError(f"Invalid VEST vote column: {col!r}; expected TYYOOOPCCC")
        office_code = col_upper[3:6]
        office = "house" if _VEST_HOUSE_RE.fullmatch(office_code) else _VEST_OFFICE_MAP.get(office_code)
        if state_fips == "11":
            if office_code == "DEL":
                office = "house"
            elif office_code in {"USS", "HAL"}:
                office = None
        if office is None:
            raise ValueError(f"Unsupported VEST office {office_code!r} in column {col!r}")
        return _VEST_PARTY_MAP.get(col_upper[6], col_upper[6]), office

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
        normalized = abbr.strip().upper()
        if normalized not in _map:
            raise ValueError(f"Unknown state abbreviation: {abbr!r}")
        return _map[normalized]

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

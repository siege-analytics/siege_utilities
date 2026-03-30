"""
Redistricting plan models.

Stores redistricting plans, their component districts (with geometry and
compactness scores), per-district demographic overlays, and precinct-level
election results sourced from Redistricting Data Hub (RDH).

Model hierarchy:
    RedistrictingPlan (non-spatial grouping)
    ├── PlanDistrict (CensusTIGERBoundary — inherits GEOID + temporal geometry)
    │   └── DistrictDemographics (Census overlay per district)
    └── PrecinctElectionResult (precinct-level votes with optional geometry)
"""

from django.contrib.gis.db import models as gis_models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from .base import CensusTIGERBoundary
from .boundaries import State


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

CHAMBER_CHOICES = [
    ("congress", "U.S. Congress"),
    ("state_senate", "State Senate"),
    ("state_house", "State House"),
]

PLAN_TYPE_CHOICES = [
    ("enacted", "Enacted"),
    ("proposed", "Proposed"),
    ("alternative", "Alternative"),
    ("court_ordered", "Court-Ordered"),
    ("commission", "Commission"),
]

PLAN_SOURCE_CHOICES = [
    ("rdh", "Redistricting Data Hub"),
    ("census", "U.S. Census Bureau"),
    ("court", "Court"),
    ("legislature", "Legislature"),
    ("commission", "Commission"),
]

DATASET_CHOICES = [
    ("acs5", "American Community Survey 5-Year"),
    ("acs1", "American Community Survey 1-Year"),
    ("dec", "Decennial Census"),
    ("dec_pl", "Decennial Census P.L. 94-171"),
]

OFFICE_CHOICES = [
    ("president", "President"),
    ("senate", "U.S. Senate"),
    ("house", "U.S. House"),
    ("governor", "Governor"),
    ("state_senate", "State Senate"),
    ("state_house", "State House"),
    ("attorney_general", "Attorney General"),
    ("secretary_of_state", "Secretary of State"),
]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class RedistrictingPlan(models.Model):
    """A redistricting plan (enacted, proposed, or alternative).

    Non-spatial model that groups PlanDistrict records for a given
    state/chamber/cycle combination.
    """

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="redistricting_plans",
        null=True,
        help_text="Parent state",
    )
    state_fips = models.CharField(
        max_length=2,
        db_index=True,
        help_text="2-digit state FIPS code",
    )
    chamber = models.CharField(
        max_length=20,
        choices=CHAMBER_CHOICES,
        db_index=True,
    )
    cycle_year = models.PositiveSmallIntegerField(
        db_index=True,
        validators=[MinValueValidator(1960), MaxValueValidator(2040)],
        help_text="Redistricting cycle year (2010, 2020, 2030)",
    )
    plan_name = models.CharField(
        max_length=255,
        help_text="Plan identifier or title",
    )
    plan_type = models.CharField(
        max_length=20,
        choices=PLAN_TYPE_CHOICES,
        default="enacted",
    )
    source = models.CharField(
        max_length=20,
        choices=PLAN_SOURCE_CHOICES,
        default="rdh",
        help_text="Where this plan data came from",
    )
    source_url = models.URLField(
        blank=True,
        default="",
        help_text="URL to the original dataset",
    )
    num_districts = models.PositiveSmallIntegerField(
        help_text="Total number of districts in this plan",
    )
    enacted_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the plan was enacted (if applicable)",
    )
    data_source = models.CharField(
        max_length=100,
        default="rdh",
        help_text="Provenance tag for SourceAwareModel pattern",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Redistricting Plan"
        verbose_name_plural = "Redistricting Plans"
        unique_together = [("state_fips", "chamber", "cycle_year", "plan_name")]
        indexes = [
            models.Index(fields=["state_fips", "chamber"]),
            models.Index(fields=["cycle_year", "plan_type"]),
        ]

    def __str__(self):
        return f"{self.plan_name} ({self.state_fips} {self.chamber} {self.cycle_year})"


class PlanDistrict(CensusTIGERBoundary):
    """A single district within a redistricting plan.

    Inherits from CensusTIGERBoundary to get full GEOID, temporal geometry,
    and TIGER metadata infrastructure.
    """

    plan = models.ForeignKey(
        RedistrictingPlan,
        on_delete=models.CASCADE,
        related_name="districts",
        help_text="Parent redistricting plan",
    )
    district_number = models.CharField(
        max_length=10,
        db_index=True,
        help_text="District number or identifier within the plan",
    )

    # Compactness scores (computed on save or via service)
    polsby_popper = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Polsby-Popper compactness score (0–1)",
    )
    reock = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Reock compactness score (0–1)",
    )
    convex_hull_ratio = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Convex hull ratio (0–1)",
    )
    schwartzberg = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Schwartzberg compactness score (0–1)",
    )

    # Denormalized population fields for fast queries
    total_population = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Total population from Census overlay",
    )
    vap = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Voting age population",
    )
    cvap = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Citizen voting age population",
    )

    # Deviation from ideal district population
    deviation_pct = models.FloatField(
        null=True,
        blank=True,
        help_text="Percent deviation from ideal population",
    )

    class Meta:
        verbose_name = "Plan District"
        verbose_name_plural = "Plan Districts"
        unique_together = [("plan", "district_number")]
        indexes = [
            models.Index(fields=["plan", "district_number"]),
            models.Index(fields=["state_fips", "vintage_year"]),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        # Variable — district GEOIDs vary by chamber type
        return 20

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {
            "state_fips": geoid[:2],
            "district_number": geoid[2:],
        }

    def __str__(self):
        return f"District {self.district_number} ({self.plan})"


class DistrictDemographics(models.Model):
    """Demographic profile for a plan district from Census overlay.

    Stores explicit race/ethnicity and economic columns for fast queries,
    plus JSON blobs for the full variable set.
    """

    district = models.ForeignKey(
        PlanDistrict,
        on_delete=models.CASCADE,
        related_name="demographics",
        help_text="Parent plan district",
    )
    dataset = models.CharField(
        max_length=10,
        choices=DATASET_CHOICES,
        db_index=True,
        help_text="Census dataset source",
    )
    year = models.PositiveSmallIntegerField(
        db_index=True,
        validators=[MinValueValidator(1990), MaxValueValidator(2050)],
        help_text="Census/ACS year",
    )

    # Race/ethnicity
    pop_white = models.BigIntegerField(null=True, blank=True)
    pop_black = models.BigIntegerField(null=True, blank=True)
    pop_hispanic = models.BigIntegerField(null=True, blank=True)
    pop_asian = models.BigIntegerField(null=True, blank=True)
    pop_native = models.BigIntegerField(null=True, blank=True)
    pop_other = models.BigIntegerField(null=True, blank=True)
    pop_two_or_more = models.BigIntegerField(null=True, blank=True)

    # Economic
    median_household_income = models.IntegerField(
        null=True,
        blank=True,
        help_text="Median household income (B19013_001E)",
    )
    poverty_rate = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Poverty rate as percentage",
    )

    # Full variable set as JSON
    values = models.JSONField(
        default=dict,
        help_text="Variable code -> value mapping",
    )
    moe_values = models.JSONField(
        default=dict,
        blank=True,
        help_text="Variable code -> margin of error mapping",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "District Demographics"
        verbose_name_plural = "District Demographics"
        unique_together = [("district", "dataset", "year")]
        indexes = [
            models.Index(fields=["district", "dataset"]),
            models.Index(fields=["year", "dataset"]),
        ]

    def __str__(self):
        return f"{self.district} - {self.dataset} {self.year}"


class PrecinctElectionResult(models.Model):
    """Election results at precinct level from RDH.

    Stores per-candidate/party vote totals at precinct granularity,
    with optional geometry for spatial analysis.
    """

    plan = models.ForeignKey(
        RedistrictingPlan,
        on_delete=models.SET_NULL,
        related_name="precinct_results",
        null=True,
        blank=True,
        help_text="Optional link to redistricting plan",
    )
    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="precinct_election_results",
        null=True,
        help_text="Parent state",
    )
    state_fips = models.CharField(
        max_length=2,
        db_index=True,
        help_text="2-digit state FIPS code",
    )
    precinct_id = models.CharField(
        max_length=60,
        db_index=True,
        help_text="Precinct identifier (format varies by state)",
    )
    precinct_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )
    geometry = gis_models.MultiPolygonField(
        srid=4326,
        null=True,
        blank=True,
        help_text="Precinct boundary geometry (WGS 84)",
    )
    election_year = models.PositiveSmallIntegerField(
        db_index=True,
        validators=[MinValueValidator(1900), MaxValueValidator(2050)],
    )
    office = models.CharField(
        max_length=30,
        choices=OFFICE_CHOICES,
    )
    party = models.CharField(
        max_length=50,
        help_text="Political party (DEM, REP, LIB, GRN, IND, etc.)",
    )
    candidate_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
    )
    votes = models.IntegerField(
        help_text="Vote count for this candidate/party in this precinct",
    )
    total_votes = models.IntegerField(
        null=True,
        blank=True,
        help_text="Total votes cast in this precinct for this office",
    )
    vote_share = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Fraction of total votes (0.0–1.0)",
    )
    data_source = models.CharField(
        max_length=100,
        default="rdh",
        help_text="Provenance tag",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Precinct Election Result"
        verbose_name_plural = "Precinct Election Results"
        indexes = [
            models.Index(fields=["state_fips", "election_year"]),
            models.Index(fields=["precinct_id", "election_year"]),
            models.Index(fields=["office", "party"]),
            models.Index(fields=["election_year"]),
        ]

    def __str__(self):
        return (
            f"{self.precinct_id} {self.election_year} "
            f"{self.office} {self.party}: {self.votes}"
        )


class PlanDistrictAssignment(models.Model):
    """Maps a Seat to a boundary polygon within a RedistrictingPlan.

    Uses a Generic FK to point at any boundary model (CongressionalDistrict,
    StateLegislativeUpper, StateLegislativeLower, PlanDistrict, etc.)
    so that the same assignment model works for all chambers.

    This is the Phase C bridge: Plan → Seat → Boundary.
    """

    plan = models.ForeignKey(
        RedistrictingPlan,
        on_delete=models.CASCADE,
        related_name="district_assignments",
        help_text="Parent redistricting plan",
    )
    seat = models.ForeignKey(
        "temporal_political.Seat",
        on_delete=models.CASCADE,
        related_name="district_assignments",
        help_text="The political seat assigned to this boundary",
    )

    # Generic FK to boundary model
    boundary_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="Content type of the boundary model",
    )
    boundary_object_id = models.PositiveIntegerField(
        help_text="PK of the boundary instance",
    )
    boundary = GenericForeignKey("boundary_content_type", "boundary_object_id")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Plan District Assignment"
        verbose_name_plural = "Plan District Assignments"
        unique_together = [("plan", "seat")]
        indexes = [
            models.Index(fields=["plan", "seat"]),
            models.Index(
                fields=["boundary_content_type", "boundary_object_id"],
            ),
        ]

    def __str__(self):
        return f"{self.plan} → {self.seat}"

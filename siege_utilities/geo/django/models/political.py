"""
Political Census boundary models.

State legislative districts (upper/lower chambers), voting tabulation
districts (VTDs), and precincts.  All inherit from CensusTIGERBoundary.
"""

from django.db import models

from .base import CensusTIGERBoundary
from .boundaries import State, County, CongressionalDistrict


class StateLegislativeUpper(CensusTIGERBoundary):
    """
    State Legislative District — Upper Chamber (Senate).

    GEOID: 5 digits = state (2) + district (3)
    Example: "06001" for California State Senate District 1
    """

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="legislative_upper_districts",
        null=True,
        help_text="Parent state",
    )
    district_number = models.CharField(
        max_length=3,
        db_index=True,
        help_text="3-digit district number",
    )

    class Meta:
        verbose_name = "State Legislative District (Upper)"
        verbose_name_plural = "State Legislative Districts (Upper)"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "district_number"]),
            models.Index(fields=["state_fips", "vintage_year"]),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        return 5

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {
            "state_fips": geoid[:2],
            "district_number": geoid[2:5],
        }


class StateLegislativeLower(CensusTIGERBoundary):
    """
    State Legislative District — Lower Chamber (House/Assembly).

    GEOID: 5 digits = state (2) + district (3)
    Example: "06001" for California State Assembly District 1
    """

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="legislative_lower_districts",
        null=True,
        help_text="Parent state",
    )
    district_number = models.CharField(
        max_length=3,
        db_index=True,
        help_text="3-digit district number",
    )

    class Meta:
        verbose_name = "State Legislative District (Lower)"
        verbose_name_plural = "State Legislative Districts (Lower)"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "district_number"]),
            models.Index(fields=["state_fips", "vintage_year"]),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        return 5

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {
            "state_fips": geoid[:2],
            "district_number": geoid[2:5],
        }


class VTD(CensusTIGERBoundary):
    """
    Voting Tabulation District (VTD) boundary.

    VTDs are the smallest geographic units for which Census tabulates
    voting-age population data.  They approximate but don't exactly match
    election precincts.

    GEOID: 8 digits = state (2) + county (3) + VTD (3)
    Example: "06037001" for VTD 001 in LA County, CA

    Enhanced fields support enterprise-compatible workflows:
    - precinct_name/precinct_code for election data linkage
    - registered_voters for turnout analysis
    - data_source for provenance tracking
    - populate_parent_relationships() for FK resolution
    """

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="vtds",
        null=True,
        help_text="Parent state",
    )
    county = models.ForeignKey(
        County,
        on_delete=models.CASCADE,
        related_name="vtds",
        null=True,
        help_text="Parent county",
    )
    congressional_district = models.ForeignKey(
        CongressionalDistrict,
        on_delete=models.SET_NULL,
        related_name="vtds",
        null=True,
        blank=True,
        db_constraint=False,
        help_text="Containing congressional district (soft FK, resolved post-load)",
    )
    county_fips = models.CharField(
        max_length=3,
        db_index=True,
        help_text="3-digit county FIPS code",
    )
    vtd_code = models.CharField(
        max_length=6,
        db_index=True,
        help_text="VTD code (typically 3-6 characters)",
    )
    precinct_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Election precinct name (from election data, not Census)",
    )
    precinct_code = models.CharField(
        max_length=20,
        blank=True,
        default="",
        db_index=True,
        help_text="Election precinct code (from election data)",
    )
    registered_voters = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Registered voter count (from election data)",
    )
    data_source = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Source of non-Census fields (e.g. 'NC SBE 2024')",
    )

    class Meta:
        verbose_name = "Voting Tabulation District"
        verbose_name_plural = "Voting Tabulation Districts"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "county_fips", "vtd_code"]),
            models.Index(fields=["state_fips", "vintage_year"]),
            models.Index(fields=["precinct_code"]),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        return 8

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {
            "state_fips": geoid[:2],
            "county_fips": geoid[2:5],
            "vtd_code": geoid[5:],
        }

    def populate_parent_relationships(self):
        """
        Resolve parent FKs from FIPS codes.

        Call after bulk loading to link VTDs to their parent
        State, County, and (optionally) CongressionalDistrict records.
        """
        if not self.state_id and self.state_fips:
            self.state = (
                State.objects.filter(
                    state_fips=self.state_fips,
                    vintage_year=self.vintage_year,
                ).first()
            )
        if not self.county_id and self.state_fips and self.county_fips:
            self.county = (
                County.objects.filter(
                    state_fips=self.state_fips,
                    county_fips=self.county_fips,
                    vintage_year=self.vintage_year,
                ).first()
            )


class Precinct(CensusTIGERBoundary):
    """
    Election Precinct boundary.

    Precincts are the fundamental unit of election administration.  They
    may not align perfectly with Census VTDs.  Stored as TIGER boundaries
    when sourced from Census, but precinct_source tracks actual provenance.

    GEOID format varies by state; typically state (2) + county (3) + precinct code.
    """

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="precincts",
        null=True,
        help_text="Parent state",
    )
    county = models.ForeignKey(
        County,
        on_delete=models.CASCADE,
        related_name="precincts",
        null=True,
        help_text="Parent county",
    )
    county_fips = models.CharField(
        max_length=3,
        db_index=True,
        help_text="3-digit county FIPS code",
    )
    precinct_code = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Precinct identifier (format varies by state)",
    )
    precinct_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Human-readable precinct name",
    )
    precinct_source = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Data source for this precinct boundary",
    )

    class Meta:
        verbose_name = "Precinct"
        verbose_name_plural = "Precincts"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "county_fips"]),
            models.Index(fields=["state_fips", "vintage_year"]),
            models.Index(fields=["precinct_code"]),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        # Variable length — return max
        return 20

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {
            "state_fips": geoid[:2],
            "county_fips": geoid[2:5],
            "precinct_code": geoid[5:],
        }

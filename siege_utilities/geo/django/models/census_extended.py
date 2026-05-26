"""
Extended Census boundary models — non-nesting geographies.

CBSA, UrbanArea, PUMA, TribalArea, and CountySubdivision are Census-defined
boundaries that either don't nest in the standard state→county→tract hierarchy
or belong to parallel hierarchy branches.  All inherit from CensusTIGERBoundary.
"""

from django.db import models

from .base import CensusTIGERBoundary
from .boundaries import County, State


class CBSA(CensusTIGERBoundary):
    """
    Core Based Statistical Area (Metropolitan/Micropolitan).

    CBSAs are defined by OMB around urban cores of 10,000+ population.
    They consist of one or more counties (or county-equivalents).
    CBSAs do NOT nest in the Census hierarchy — they can span states.

    GEOID: 5 digits (CBSA FIPS code)
    Example: "31080" for Los Angeles-Long Beach-Anaheim, CA
    """

    CBSA_TYPE_CHOICES = [
        ("metro", "Metropolitan Statistical Area"),
        ("micro", "Micropolitan Statistical Area"),
    ]

    cbsa_type = models.CharField(
        max_length=5,
        choices=CBSA_TYPE_CHOICES,
        db_index=True,
        help_text="Metro or Micro statistical area",
    )
    csa_code = models.CharField(
        max_length=5,
        blank=True,
        default="",
        db_index=True,
        help_text="Combined Statistical Area code (if part of a CSA)",
    )
    csa_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Combined Statistical Area name",
    )
    principal_city = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Name of the principal city",
    )

    class Meta:
        verbose_name = "CBSA"
        verbose_name_plural = "CBSAs"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["cbsa_type"]),
            models.Index(fields=["csa_code"]),
            models.Index(fields=["vintage_year"]),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        return 5

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {
            # CBSAs don't have a state FIPS — can span states
            "state_fips": "",
        }


class UrbanArea(CensusTIGERBoundary):
    """
    Census Urban Area boundary.

    Urban Areas represent densely developed territory.  Two types:
    - Urbanized Area (UA): 50,000+ population
    - Urban Cluster (UC): 2,500–49,999 population

    Like CBSAs, Urban Areas can span county and state boundaries.

    GEOID: 5 digits (Urban Area code)
    Example: "51445" for Los Angeles—Long Beach—Anaheim, CA UA
    """

    UA_TYPE_CHOICES = [
        ("UA", "Urbanized Area (50,000+)"),
        ("UC", "Urban Cluster (2,500-49,999)"),
    ]

    ua_type = models.CharField(
        max_length=2,
        choices=UA_TYPE_CHOICES,
        db_index=True,
        help_text="Urbanized Area or Urban Cluster",
    )

    class Meta:
        verbose_name = "Urban Area"
        verbose_name_plural = "Urban Areas"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["ua_type"]),
            models.Index(fields=["vintage_year"]),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        return 5

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {
            "state_fips": "",
        }


class PUMA(CensusTIGERBoundary):
    """
    Public Use Microdata Area boundary.

    PUMAs are non-overlapping, statistical geographic areas of contiguous
    counties or census tracts containing ~100,000+ people. Used by ACS
    public-use microdata samples (PUMS) and small-area estimates.

    GEOID: 7 digits = state (2) + PUMA (5)
    Example: "0603701" for PUMA 03701 in California (Los Angeles area)
    """

    puma_code = models.CharField(
        max_length=5,
        db_index=True,
        help_text="5-digit PUMA code within a state",
    )

    class Meta:
        verbose_name = "PUMA"
        verbose_name_plural = "PUMAs"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "puma_code"]),
            models.Index(fields=["state_fips", "vintage_year"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(geoid__regex=r"^\d{7}$"),
                name="puma_geoid_7_digits",
            ),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        return 7

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {
            "state_fips": geoid[:2],
            "puma_code": geoid[2:7],
        }


class TribalArea(CensusTIGERBoundary):
    """
    American Indian / Alaska Native / Native Hawaiian Area boundary.

    TIGER layer: tl_YYYY_us_aiannh (national file, not per-state).
    GEOIDs vary in length (typically 4–5 digits); no fixed-length constraint.
    Tribal areas can span state boundaries.

    GEOID example: "0010" for Agua Caliente Indian Reservation
    """

    aiannhce = models.CharField(
        max_length=4,
        db_index=True,
        help_text="AIANNH Census code",
    )
    aiannhns = models.CharField(
        max_length=8,
        blank=True,
        default="",
        help_text="AIANNH ANSI code",
    )
    comptyp = models.CharField(
        max_length=2,
        blank=True,
        default="",
        help_text="Component type (R=Reservation, T=Trust land, etc.)",
    )

    class Meta:
        verbose_name = "Tribal Area"
        verbose_name_plural = "Tribal Areas"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["aiannhce"]),
            models.Index(fields=["vintage_year"]),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        return 4

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {
            "state_fips": "",
            "aiannhce": geoid[:4],
        }


class CountySubdivision(CensusTIGERBoundary):
    """
    County Subdivision (MCD/CCD) boundary.

    Minor Civil Divisions (MCDs) or Census County Divisions (CCDs) are the
    primary legal or statistical subdivision of a county. MCDs are used in
    28 states + DC; CCDs fill in where MCDs don't exist.

    TIGER layer: tl_YYYY_SS_cousub
    GEOID: 10 digits = state (2) + county (3) + cousub (5)
    Example: "2500109000" for Abington town, Plymouth County, MA
    """

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="county_subdivisions",
        null=True,
        help_text="Parent state",
    )
    county = models.ForeignKey(
        County,
        on_delete=models.CASCADE,
        related_name="county_subdivisions",
        null=True,
        help_text="Parent county",
    )
    county_fips = models.CharField(
        max_length=3,
        db_index=True,
        help_text="3-digit county FIPS code",
    )
    cousub_fips = models.CharField(
        max_length=5,
        db_index=True,
        help_text="5-digit county subdivision FIPS code",
    )
    cousub_type = models.CharField(
        max_length=1,
        blank=True,
        default="",
        help_text="Subdivision type (S=MCD, T=CCD, Z=unorganized territory, etc.)",
    )

    class Meta:
        verbose_name = "County Subdivision"
        verbose_name_plural = "County Subdivisions"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "county_fips", "cousub_fips"]),
            models.Index(fields=["state_fips", "vintage_year"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(geoid__regex=r"^\d{10}$"),
                name="cousub_geoid_10_digits",
            ),
        ]

    @classmethod
    def get_geoid_length(cls) -> int:
        return 10

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {
            "state_fips": geoid[:2],
            "county_fips": geoid[2:5],
            "cousub_fips": geoid[5:10],
        }

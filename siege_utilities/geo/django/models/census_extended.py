"""
Extended Census boundary models — non-nesting geographies.

CBSA (Core Based Statistical Area) and UrbanArea are Census-defined
boundaries that don't nest in the standard state→county→tract hierarchy.
Both inherit from CensusTIGERBoundary.
"""

from django.db import models

from .base import CensusTIGERBoundary


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

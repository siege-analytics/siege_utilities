"""
NCES School District boundary models.

Three types of school districts from Census TIGER/Line, enhanced with
NCES locale classification data (12-code urban-centric system).

All inherit from CensusTIGERBoundary.
"""

from django.db import models

from .base import CensusTIGERBoundary
from .boundaries import State


class SchoolDistrictBase(CensusTIGERBoundary):
    """
    Abstract base for NCES school district boundaries.

    Adds LEA (Local Education Agency) identifier and NCES locale
    classification fields.  Locale codes are denormalized here for
    query performance — the authoritative classification logic lives
    in siege_utilities.geo.locale.NCESLocaleClassifier.

    GEOID: 7 digits = state (2) + LEA (5)
    """

    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="%(class)s_districts",
        null=True,
        help_text="Parent state",
    )
    lea_id = models.CharField(
        max_length=7,
        db_index=True,
        help_text="NCES Local Education Agency ID",
    )
    district_type = models.CharField(
        max_length=2,
        blank=True,
        default="",
        help_text="District type code (e.g. 00=unified, 01=elementary, 02=secondary)",
    )
    locale_code = models.CharField(
        max_length=2,
        blank=True,
        default="",
        db_index=True,
        help_text="NCES 2-digit locale code (11-43)",
    )
    locale_category = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Locale category (City, Suburb, Town, Rural)",
    )
    locale_subcategory = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Locale subcategory (Large, Midsize, Small, Fringe, Distant, Remote)",
    )

    class Meta:
        abstract = True

    @classmethod
    def get_geoid_length(cls) -> int:
        return 7

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        return {
            "state_fips": geoid[:2],
            "lea_id": geoid[:7],
        }


class SchoolDistrictElementary(SchoolDistrictBase):
    """Elementary school district boundary."""

    class Meta:
        verbose_name = "School District (Elementary)"
        verbose_name_plural = "School Districts (Elementary)"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "vintage_year"]),
            models.Index(fields=["lea_id"]),
            models.Index(fields=["locale_code"]),
        ]


class SchoolDistrictSecondary(SchoolDistrictBase):
    """Secondary school district boundary."""

    class Meta:
        verbose_name = "School District (Secondary)"
        verbose_name_plural = "School Districts (Secondary)"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "vintage_year"]),
            models.Index(fields=["lea_id"]),
            models.Index(fields=["locale_code"]),
        ]


class SchoolDistrictUnified(SchoolDistrictBase):
    """Unified school district boundary (serves all grades)."""

    class Meta:
        verbose_name = "School District (Unified)"
        verbose_name_plural = "School Districts (Unified)"
        unique_together = [("geoid", "vintage_year")]
        indexes = [
            models.Index(fields=["state_fips", "vintage_year"]),
            models.Index(fields=["lea_id"]),
            models.Index(fields=["locale_code"]),
        ]

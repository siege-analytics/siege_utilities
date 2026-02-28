"""
NCES education models.

School district boundaries from Census TIGER/Line, enhanced with NCES
locale classification data (12-code urban-centric system).
Plus NCES-specific models for locale territory polygons and school locations.

School districts inherit from CensusTIGERBoundary.
NCESLocaleBoundary inherits from TemporalBoundary (not Census-specific).
SchoolLocation inherits from TemporalPointFeature.
"""

from django.db import models

from .base import CensusTIGERBoundary, TemporalBoundary, TemporalPointFeature
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


# -----------------------------------------------------------------------
# NCES-specific models (not Census TIGER)
# -----------------------------------------------------------------------


class NCESLocaleBoundary(TemporalBoundary):
    """NCES locale territory polygon.

    NCES publishes 12 locale territory polygons per year — one for each
    code (11=City-Large through 43=Rural-Remote). These are pre-classified
    boundaries that can be used for spatial joins without recomputing.

    Not a CensusTIGERBoundary because these are NCES-published, not TIGER.
    """

    locale_code = models.PositiveSmallIntegerField(
        db_index=True,
        help_text="NCES 2-digit locale code (11-43)",
    )
    locale_category = models.CharField(
        max_length=20,
        help_text="Major category: city, suburban, town, rural",
    )
    locale_subcategory = models.CharField(
        max_length=30,
        blank=True,
        default="",
        help_text="Full subcategory (e.g. city_large, rural_remote)",
    )
    nces_year = models.PositiveSmallIntegerField(
        db_index=True,
        help_text="NCES publication year for this boundary",
    )

    class Meta:
        verbose_name = "NCES Locale Boundary"
        verbose_name_plural = "NCES Locale Boundaries"
        unique_together = [("locale_code", "nces_year")]
        indexes = [
            models.Index(fields=["locale_category"]),
            models.Index(fields=["nces_year", "locale_code"]),
        ]

    def __str__(self):
        return f"{self.locale_category} ({self.locale_code}) [{self.nces_year}]"

    def save(self, *args, **kwargs):
        # Sync feature_id from locale code + year
        if not self.feature_id:
            self.feature_id = f"nces_locale_{self.locale_code}_{self.nces_year}"
        if not self.source:
            self.source = "NCES EDGE"
        super().save(*args, **kwargs)


class SchoolLocation(TemporalPointFeature):
    """Individual school geocoded point location.

    Downloaded from NCES EDGE school location data. Each row represents
    a school with its geocoded coordinates and NCES locale classification.
    """

    ncessch = models.CharField(
        max_length=12,
        db_index=True,
        help_text="NCES school ID (12-digit)",
    )
    school_name = models.CharField(
        max_length=255,
        help_text="School name from NCES",
    )
    lea_id = models.CharField(
        max_length=7,
        db_index=True,
        help_text="NCES LEA ID for parent district",
    )
    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name="school_locations",
        null=True,
        blank=True,
        help_text="Parent state",
    )
    locale_code = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="NCES 2-digit locale code (11-43)",
    )
    locale_category = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Major category: city, suburban, town, rural",
    )
    locale_subcategory = models.CharField(
        max_length=30,
        blank=True,
        default="",
        help_text="Full subcategory (e.g. city_large, rural_remote)",
    )

    class Meta:
        verbose_name = "School Location"
        verbose_name_plural = "School Locations"
        unique_together = [("ncessch", "vintage_year")]
        indexes = [
            models.Index(fields=["lea_id"]),
            models.Index(fields=["locale_code"]),
            models.Index(fields=["state", "vintage_year"]),
        ]

    def __str__(self):
        return f"{self.school_name} ({self.ncessch})"

    def save(self, *args, **kwargs):
        if not self.feature_id:
            self.feature_id = self.ncessch
        if not self.source:
            self.source = "NCES EDGE"
        super().save(*args, **kwargs)

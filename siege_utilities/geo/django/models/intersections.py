"""
Boundary intersection models — pre-computed spatial overlaps.

Generic BoundaryIntersection stores any pair of overlapping boundaries.
Typed convenience models (CountyCDIntersection, VTDCDIntersection,
TractCDIntersection) add FK constraints and dominant-boundary tracking
for the most commonly-queried intersection pairs.
"""

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from .boundaries import County, Tract, CongressionalDistrict
from .political import VTD


class BoundaryIntersection(models.Model):
    """
    Generic intersection between any two boundary types.

    Records the area overlap (intersection geometry is NOT stored — too
    expensive for millions of rows; use PostGIS ST_Intersection on the fly).
    Source/target types are string-typed for maximum flexibility.

    Example:
        BoundaryIntersection(
            source_type='county', source_boundary_id='06037',
            target_type='cd', target_boundary_id='0614',
            vintage_year=2020,
            intersection_area=12345678,
            pct_of_source=0.45,
            pct_of_target=0.72,
        )
    """

    source_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Geography type of source boundary",
    )
    source_boundary_id = models.CharField(
        max_length=60,
        db_index=True,
        help_text="Identifier of the source boundary",
    )
    target_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Geography type of target boundary",
    )
    target_boundary_id = models.CharField(
        max_length=60,
        db_index=True,
        help_text="Identifier of the target boundary",
    )
    vintage_year = models.PositiveSmallIntegerField(
        db_index=True,
        validators=[MinValueValidator(1790), MaxValueValidator(2100)],
        help_text="Vintage year for both boundaries",
    )
    intersection_area = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Area of intersection in square meters",
    )
    pct_of_source = models.DecimalField(
        max_digits=7,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Fraction of source boundary area in intersection (0-1)",
    )
    pct_of_target = models.DecimalField(
        max_digits=7,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Fraction of target boundary area in intersection (0-1)",
    )
    is_dominant = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if this is the largest intersection for the source",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Boundary Intersection"
        verbose_name_plural = "Boundary Intersections"
        unique_together = [
            (
                "source_type",
                "source_boundary_id",
                "target_type",
                "target_boundary_id",
                "vintage_year",
            )
        ]
        indexes = [
            models.Index(fields=["source_type", "source_boundary_id", "vintage_year"]),
            models.Index(fields=["target_type", "target_boundary_id", "vintage_year"]),
            models.Index(fields=["source_type", "target_type", "vintage_year"]),
            models.Index(fields=["is_dominant"]),
        ]

    def __str__(self):
        return (
            f"{self.source_type}:{self.source_boundary_id} ∩ "
            f"{self.target_type}:{self.target_boundary_id} "
            f"({self.vintage_year})"
        )


class CountyCDIntersection(models.Model):
    """
    Pre-computed County ↔ Congressional District intersection.

    Typed model with FKs for the most commonly-queried pair.
    Matches the enterprise pattern: pct_of_county, pct_of_cd, is_dominant.
    """

    county = models.ForeignKey(
        County,
        on_delete=models.CASCADE,
        related_name="cd_intersections",
        help_text="County boundary",
    )
    congressional_district = models.ForeignKey(
        CongressionalDistrict,
        on_delete=models.CASCADE,
        related_name="county_intersections",
        help_text="Congressional district boundary",
    )
    vintage_year = models.PositiveSmallIntegerField(
        db_index=True,
        help_text="Vintage year for both boundaries",
    )
    intersection_area = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Area of intersection in square meters",
    )
    pct_of_county = models.DecimalField(
        max_digits=7,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Fraction of county area in intersection",
    )
    pct_of_cd = models.DecimalField(
        max_digits=7,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Fraction of CD area in intersection",
    )
    is_dominant = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if this CD contains the most of this county",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "County-CD Intersection"
        verbose_name_plural = "County-CD Intersections"
        unique_together = [("county", "congressional_district", "vintage_year")]
        indexes = [
            models.Index(fields=["vintage_year"]),
        ]

    def __str__(self):
        return f"County {self.county_id} ∩ CD {self.congressional_district_id}"


class VTDCDIntersection(models.Model):
    """
    Pre-computed VTD ↔ Congressional District intersection.
    """

    vtd = models.ForeignKey(
        VTD,
        on_delete=models.CASCADE,
        related_name="cd_intersections",
        help_text="VTD boundary",
    )
    congressional_district = models.ForeignKey(
        CongressionalDistrict,
        on_delete=models.CASCADE,
        related_name="vtd_intersections",
        help_text="Congressional district boundary",
    )
    vintage_year = models.PositiveSmallIntegerField(
        db_index=True,
        help_text="Vintage year for both boundaries",
    )
    intersection_area = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Area of intersection in square meters",
    )
    pct_of_vtd = models.DecimalField(
        max_digits=7,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Fraction of VTD area in intersection",
    )
    pct_of_cd = models.DecimalField(
        max_digits=7,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Fraction of CD area in intersection",
    )
    is_dominant = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if this CD contains the most of this VTD",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "VTD-CD Intersection"
        verbose_name_plural = "VTD-CD Intersections"
        unique_together = [("vtd", "congressional_district", "vintage_year")]
        indexes = [
            models.Index(fields=["vintage_year"]),
        ]

    def __str__(self):
        return f"VTD {self.vtd_id} ∩ CD {self.congressional_district_id}"


class TractCDIntersection(models.Model):
    """
    Pre-computed Tract ↔ Congressional District intersection.
    """

    tract = models.ForeignKey(
        Tract,
        on_delete=models.CASCADE,
        related_name="cd_intersections",
        help_text="Tract boundary",
    )
    congressional_district = models.ForeignKey(
        CongressionalDistrict,
        on_delete=models.CASCADE,
        related_name="tract_intersections",
        help_text="Congressional district boundary",
    )
    vintage_year = models.PositiveSmallIntegerField(
        db_index=True,
        help_text="Vintage year for both boundaries",
    )
    intersection_area = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Area of intersection in square meters",
    )
    pct_of_tract = models.DecimalField(
        max_digits=7,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Fraction of tract area in intersection",
    )
    pct_of_cd = models.DecimalField(
        max_digits=7,
        decimal_places=6,
        null=True,
        blank=True,
        help_text="Fraction of CD area in intersection",
    )
    is_dominant = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if this CD contains the most of this tract",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tract-CD Intersection"
        verbose_name_plural = "Tract-CD Intersections"
        unique_together = [("tract", "congressional_district", "vintage_year")]
        indexes = [
            models.Index(fields=["vintage_year"]),
        ]

    def __str__(self):
        return f"Tract {self.tract_id} ∩ CD {self.congressional_district_id}"

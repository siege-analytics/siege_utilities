"""
Timezone boundary model.

Stores IANA timezone boundaries from the timezone-boundary-builder
(https://github.com/evansiroky/timezone-boundary-builder) as PostGIS
geometries with DST offset metadata.
"""

from django.db import models

from .base import TemporalBoundary


class TimezoneGeometry(TemporalBoundary):
    """
    IANA timezone boundary geometry.

    Data source: timezone-boundary-builder GeoJSON releases.
    Each record represents a single IANA timezone polygon for a given
    vintage year.

    Example:
        >>> tz = TimezoneGeometry.objects.get(timezone_id='America/New_York')
        >>> tz.utc_offset_std
        Decimal('-5.0')
    """

    timezone_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text="IANA timezone identifier (e.g. 'America/New_York')",
    )
    utc_offset_std = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="UTC offset during standard time (hours, e.g. -5.0)",
    )
    utc_offset_dst = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="UTC offset during daylight saving time (hours, e.g. -4.0)",
    )
    observes_dst = models.BooleanField(
        default=True,
        help_text="Whether this timezone observes daylight saving time",
    )

    class Meta:
        verbose_name = "Timezone Geometry"
        verbose_name_plural = "Timezone Geometries"
        unique_together = [("timezone_id", "vintage_year")]
        indexes = [
            models.Index(fields=["timezone_id"]),
            models.Index(fields=["vintage_year"]),
        ]

    def save(self, *args, **kwargs):
        if self.timezone_id and not self.feature_id:
            self.feature_id = self.timezone_id
            self.boundary_id = self.timezone_id
        if not self.source:
            self.source = "timezone-boundary-builder"
        if not self.name:
            self.name = self.timezone_id
        super().save(*args, **kwargs)

    def __str__(self):
        offset = self.utc_offset_std or "?"
        return f"{self.timezone_id} (UTC{offset:+})"

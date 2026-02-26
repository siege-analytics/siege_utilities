"""
Federal boundary models (non-Census).

These models inherit directly from TemporalBoundary (not CensusTIGERBoundary)
because they don't use Census GEOIDs or TIGER metadata.
"""

from django.db import models

from .base import TemporalBoundary


class NLRBRegion(TemporalBoundary):
    """
    National Labor Relations Board regional boundary.

    The NLRB divides the US into 26 regions (numbered, with some gaps).
    Boundaries change infrequently but do shift over time.
    """

    region_number = models.PositiveSmallIntegerField(
        db_index=True,
        help_text="NLRB region number (1-34, with gaps)",
    )
    region_office = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Regional office city (e.g. 'Boston', 'New York')",
    )
    states_covered = models.JSONField(
        default=list,
        blank=True,
        help_text="List of state FIPS codes or abbreviations covered",
    )

    class Meta:
        verbose_name = "NLRB Region"
        verbose_name_plural = "NLRB Regions"
        unique_together = [("feature_id", "vintage_year")]
        indexes = [
            models.Index(fields=["region_number"]),
            models.Index(fields=["vintage_year"]),
        ]

    def save(self, *args, **kwargs):
        if self.region_number and not self.feature_id:
            self.feature_id = f"NLRB-{self.region_number:02d}"
            self.boundary_id = self.feature_id
        if not self.source:
            self.source = "NLRB"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"NLRB Region {self.region_number} ({self.region_office})"


class FederalJudicialDistrict(TemporalBoundary):
    """
    US Federal Judicial District boundary.

    94 districts organized into 12 regional circuits (plus DC and Federal).
    District boundaries follow state lines and sometimes county lines.
    """

    district_code = models.CharField(
        max_length=10,
        db_index=True,
        help_text="District code (e.g. 'CACD' for Central District of California)",
    )
    district_name = models.CharField(
        max_length=100,
        help_text="Full district name",
    )
    circuit_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Circuit court number (1-11, plus DC=12, Federal=13)",
    )
    state_fips = models.CharField(
        max_length=2,
        blank=True,
        default="",
        db_index=True,
        help_text="Primary state FIPS code (some districts span states)",
    )

    class Meta:
        verbose_name = "Federal Judicial District"
        verbose_name_plural = "Federal Judicial Districts"
        unique_together = [("feature_id", "vintage_year")]
        indexes = [
            models.Index(fields=["district_code"]),
            models.Index(fields=["circuit_number"]),
            models.Index(fields=["state_fips"]),
            models.Index(fields=["vintage_year"]),
        ]

    def save(self, *args, **kwargs):
        if self.district_code and not self.feature_id:
            self.feature_id = self.district_code
            self.boundary_id = self.district_code
        if not self.source:
            self.source = "USCOURTS"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.district_name} ({self.district_code})"

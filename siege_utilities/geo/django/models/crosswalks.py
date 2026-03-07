"""
Temporal crosswalk and crosswalk dataset models.

TemporalCrosswalk stores relationships between geographic boundaries across
different vintage years, enabling longitudinal analysis when boundaries change.

BoundaryCrosswalk is kept as a deprecated alias for backwards compatibility.
"""


from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class TemporalCrosswalk(models.Model):
    """
    Crosswalk between geographic boundaries across different vintage years.

    When boundaries change between Census releases, this model stores the
    relationships needed to compare data across time.  Supports both Census
    and non-Census geographies via source_type/target_type fields.

    Relationship Types:
    - IDENTICAL: Boundary unchanged (weight=1.0, both directions)
    - SPLIT: Source split into multiple targets (source -> multiple targets)
    - MERGED: Multiple sources merged into target (multiple sources -> target)
    - PARTIAL: Partial overlap with weight indicating fraction
    - RENAMED: GEOID changed but boundary geometry unchanged

    Example:
        >>> # Tract 1001.00 in 2010 split into 1001.01 and 1001.02 in 2020
        >>> crosswalk = TemporalCrosswalk.objects.create(
        ...     source_boundary_id='06037100100',
        ...     target_boundary_id='06037100101',
        ...     source_vintage_year=2010,
        ...     target_vintage_year=2020,
        ...     source_type='tract',
        ...     target_type='tract',
        ...     relationship='SPLIT',
        ...     weight=0.6,
        ...     weight_type='population'
        ... )
    """

    RELATIONSHIP_CHOICES = [
        ("IDENTICAL", "Identical (no change)"),
        ("SPLIT", "Split (one-to-many)"),
        ("MERGED", "Merged (many-to-one)"),
        ("PARTIAL", "Partial overlap"),
        ("RENAMED", "Renamed (ID changed, boundary same)"),
    ]

    WEIGHT_TYPE_CHOICES = [
        ("population", "Population-weighted"),
        ("housing", "Housing unit-weighted"),
        ("area", "Area-weighted"),
        ("land_area", "Land area-weighted"),
    ]

    # Source boundary
    source_boundary_id = models.CharField(
        max_length=60,
        db_index=True,
        help_text="Identifier of the source (earlier vintage) boundary",
    )
    source_vintage_year = models.PositiveSmallIntegerField(
        db_index=True,
        validators=[MinValueValidator(1790), MaxValueValidator(2100)],
        help_text="Vintage year of the source boundary",
    )
    source_type = models.CharField(
        max_length=50,
        db_index=True,
        blank=True,
        default="",
        help_text="Geography type of source (e.g. tract, county, gadm_admin1)",
    )

    # Target boundary
    target_boundary_id = models.CharField(
        max_length=60,
        db_index=True,
        help_text="Identifier of the target (later vintage) boundary",
    )
    target_vintage_year = models.PositiveSmallIntegerField(
        db_index=True,
        validators=[MinValueValidator(1790), MaxValueValidator(2100)],
        help_text="Vintage year of the target boundary",
    )
    target_type = models.CharField(
        max_length=50,
        db_index=True,
        blank=True,
        default="",
        help_text="Geography type of target (e.g. tract, county, gadm_admin1)",
    )

    # Relationship metadata
    relationship = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_CHOICES,
        db_index=True,
        help_text="Type of relationship between boundaries",
    )

    # Allocation weights
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Allocation weight (0-1) for this relationship",
    )
    weight_type = models.CharField(
        max_length=20,
        choices=WEIGHT_TYPE_CHOICES,
        default="population",
        help_text="How the weight was calculated",
    )

    # State context (for filtering)
    state_fips = models.CharField(
        max_length=2,
        db_index=True,
        blank=True,
        help_text="State FIPS code (for filtering)",
    )

    # Additional metadata
    source_population = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Population in source boundary",
    )
    target_population = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Population in target boundary",
    )
    allocated_population = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Population allocated via this relationship",
    )
    area_sq_meters = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Area of intersection in square meters",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    data_source = models.CharField(
        max_length=100,
        blank=True,
        help_text="Source of this crosswalk data (e.g., Census Bureau file)",
    )

    class Meta:
        verbose_name = "Temporal Crosswalk"
        verbose_name_plural = "Temporal Crosswalks"
        unique_together = [
            (
                "source_boundary_id",
                "target_boundary_id",
                "source_vintage_year",
                "target_vintage_year",
                "weight_type",
            )
        ]
        indexes = [
            models.Index(fields=["source_boundary_id", "source_vintage_year"]),
            models.Index(fields=["target_boundary_id", "target_vintage_year"]),
            models.Index(fields=["source_type", "source_vintage_year", "target_vintage_year"]),
            models.Index(fields=["state_fips", "source_type"]),
            models.Index(fields=["relationship"]),
        ]

    def __str__(self):
        return (
            f"{self.source_boundary_id} ({self.source_vintage_year}) -> "
            f"{self.target_boundary_id} ({self.target_vintage_year}): "
            f"{self.weight:.4f}"
        )

    @property
    def is_unchanged(self) -> bool:
        """True if boundary is unchanged between vintages."""
        return self.relationship == "IDENTICAL" and self.weight == 1.0

    @property
    def is_one_to_one(self) -> bool:
        """True if this is a one-to-one mapping."""
        return self.relationship in ("IDENTICAL", "RENAMED")

    # --- Convenience aliases for old field names (backwards compat) ---

    @property
    def source_geoid(self) -> str:
        return self.source_boundary_id

    @property
    def target_geoid(self) -> str:
        return self.target_boundary_id

    @property
    def source_year(self) -> int:
        return self.source_vintage_year

    @property
    def target_year(self) -> int:
        return self.target_vintage_year

    @property
    def geography_type(self) -> str:
        return self.source_type

    @classmethod
    def get_forward_mappings(cls, boundary_id: str, source_year: int, target_year: int):
        """
        Get all target boundaries for a source boundary.

        Returns:
            QuerySet of crosswalk records mapping source to targets
        """
        return cls.objects.filter(
            source_boundary_id=boundary_id,
            source_vintage_year=source_year,
            target_vintage_year=target_year,
        ).order_by("-weight")

    @classmethod
    def get_reverse_mappings(cls, boundary_id: str, source_year: int, target_year: int):
        """
        Get all source boundaries for a target boundary.

        Returns:
            QuerySet of crosswalk records mapping sources to target
        """
        return cls.objects.filter(
            target_boundary_id=boundary_id,
            source_vintage_year=source_year,
            target_vintage_year=target_year,
        ).order_by("-weight")

    def allocate_value(self, value: float) -> float:
        """
        Allocate a value from source to target using this weight.

        Args:
            value: Value to allocate (e.g., population count)

        Returns:
            Allocated value = value * weight
        """
        return float(value) * float(self.weight)


# ---------------------------------------------------------------------------
# Deprecated alias
# ---------------------------------------------------------------------------
BoundaryCrosswalk = TemporalCrosswalk


class CrosswalkDataset(models.Model):
    """
    Metadata about a crosswalk dataset.

    Tracks the source, vintage, and coverage of loaded crosswalk data.
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Dataset name (e.g., '2010-2020 Tract Crosswalk')",
    )
    source_year = models.PositiveSmallIntegerField(
        help_text="Source (earlier) Census year",
    )
    target_year = models.PositiveSmallIntegerField(
        help_text="Target (later) Census year",
    )
    geography_type = models.CharField(
        max_length=20,
        help_text="Geography type covered",
    )
    source_url = models.URLField(
        blank=True,
        help_text="URL where data was downloaded from",
    )
    description = models.TextField(
        blank=True,
        help_text="Description of this dataset",
    )
    record_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of crosswalk records",
    )
    states_covered = models.JSONField(
        default=list,
        help_text="List of state FIPS codes included",
    )
    loaded_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this dataset was loaded",
    )

    class Meta:
        verbose_name = "Crosswalk Dataset"
        verbose_name_plural = "Crosswalk Datasets"

    def __str__(self):
        return f"{self.name} ({self.record_count} records)"

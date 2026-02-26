"""
Demographic data models for Census boundaries.

These models store demographic snapshots that can be attached to any
Census boundary type using Django's contenttypes framework.
"""

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class DemographicVariable(models.Model):
    """
    Reference table for Census variables.

    Stores metadata about Census variables for documentation
    and validation purposes.
    """

    DATASET_CHOICES = [
        ("acs5", "American Community Survey 5-Year"),
        ("acs1", "American Community Survey 1-Year"),
        ("dec", "Decennial Census"),
        ("dec_pl", "Decennial Census P.L. 94-171"),
    ]

    code = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Census variable code (e.g., B01001_001E)",
    )
    label = models.CharField(
        max_length=255,
        help_text="Human-readable label for this variable",
    )
    concept = models.CharField(
        max_length=255,
        blank=True,
        help_text="Census concept/table this variable belongs to",
    )
    dataset = models.CharField(
        max_length=10,
        choices=DATASET_CHOICES,
        db_index=True,
        help_text="Census dataset this variable is from",
    )
    predicate_type = models.CharField(
        max_length=20,
        blank=True,
        help_text="Data type (int, float, string)",
    )
    group = models.CharField(
        max_length=20,
        blank=True,
        db_index=True,
        help_text="Variable group code (e.g., B01001)",
    )
    universe = models.CharField(
        max_length=255,
        blank=True,
        help_text="Population universe for this variable",
    )

    class Meta:
        verbose_name = "Demographic Variable"
        verbose_name_plural = "Demographic Variables"
        unique_together = [("code", "dataset")]
        indexes = [
            models.Index(fields=["group", "dataset"]),
        ]

    def __str__(self):
        return f"{self.code}: {self.label}"

    @property
    def is_estimate(self) -> bool:
        """True if this is an estimate variable (ends in E)."""
        return self.code.endswith("E")

    @property
    def is_moe(self) -> bool:
        """True if this is a margin of error variable (ends in M)."""
        return self.code.endswith("M")

    @property
    def base_code(self) -> str:
        """Return the code without the E/M suffix."""
        if self.code.endswith(("E", "M")):
            return self.code[:-1]
        return self.code


class DemographicSnapshot(models.Model):
    """
    Demographic data snapshot for a Census boundary.

    Uses generic foreign key to attach to any boundary type.
    Stores values as JSON to allow flexible variable sets.

    Example:
        >>> snapshot = DemographicSnapshot.objects.create(
        ...     content_object=tract,
        ...     year=2022,
        ...     dataset='acs5',
        ...     values={'B01001_001E': 4521, 'B19013_001E': 75000},
        ...     moe_values={'B01001_001E': 150, 'B19013_001E': 5000}
        ... )
    """

    DATASET_CHOICES = [
        ("acs5", "American Community Survey 5-Year"),
        ("acs1", "American Community Survey 1-Year"),
        ("dec", "Decennial Census"),
        ("dec_pl", "Decennial Census P.L. 94-171"),
    ]

    # Generic foreign key to any boundary model
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={
            "app_label": "siege_geo",
            "model__in": [
                "state",
                "county",
                "tract",
                "blockgroup",
                "block",
                "place",
                "zcta",
                "congressionaldistrict",
                "statelegislativeupper",
                "statelegislativelower",
                "vtd",
                "precinct",
                "cbsa",
                "urbanarea",
                "schooldistrictelementary",
                "schooldistrictsecondary",
                "schooldistrictunified",
                "gadmcountry",
                "gadmadmin1",
                "gadmadmin2",
                "gadmadmin3",
                "gadmadmin4",
                "gadmadmin5",
                "nlrbregion",
                "federaljudicialdistrict",
            ],
        },
        help_text="Type of boundary this snapshot is for",
    )
    object_id = models.CharField(
        max_length=20,
        help_text="GEOID of the boundary",
    )
    content_object = GenericForeignKey("content_type", "object_id")

    # Snapshot metadata
    year = models.PositiveSmallIntegerField(
        db_index=True,
        validators=[MinValueValidator(1990), MaxValueValidator(2050)],
        help_text="Census/ACS year for this data",
    )
    dataset = models.CharField(
        max_length=10,
        choices=DATASET_CHOICES,
        db_index=True,
        help_text="Census dataset source",
    )
    vintage = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="API vintage year (may differ from data year)",
    )

    # Demographic values
    values = models.JSONField(
        default=dict,
        help_text="Variable code -> value mapping",
    )
    moe_values = models.JSONField(
        default=dict,
        blank=True,
        help_text="Variable code -> margin of error mapping",
    )

    # Computed summaries (optional, for common queries)
    total_population = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Total population (B01001_001E)",
    )
    median_household_income = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Median household income (B19013_001E)",
    )
    median_age = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Median age (B01002_001E)",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    source_url = models.URLField(
        blank=True,
        help_text="URL of the Census API call that provided this data",
    )

    class Meta:
        verbose_name = "Demographic Snapshot"
        verbose_name_plural = "Demographic Snapshots"
        unique_together = [("content_type", "object_id", "year", "dataset")]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["year", "dataset"]),
            models.Index(fields=["total_population"]),
        ]

    def __str__(self):
        return f"{self.content_type.model} {self.object_id} - {self.dataset} {self.year}"

    def get_value(self, variable_code: str, default=None):
        """
        Get a specific variable value.

        Args:
            variable_code: Census variable code (e.g., 'B01001_001E')
            default: Value to return if variable not present

        Returns:
            The variable value or default
        """
        return self.values.get(variable_code, default)

    def get_moe(self, variable_code: str, default=None):
        """
        Get margin of error for a specific variable.

        Args:
            variable_code: Census variable code (without M suffix)
            default: Value to return if MOE not present

        Returns:
            The margin of error or default
        """
        # Handle both with and without E suffix
        code = variable_code.rstrip("E")
        return self.moe_values.get(f"{code}M", self.moe_values.get(code, default))

    def save(self, *args, **kwargs):
        """Auto-populate summary fields from values if present."""
        if self.values:
            # Total population
            if "B01001_001E" in self.values:
                self.total_population = self.values["B01001_001E"]

            # Median household income
            if "B19013_001E" in self.values:
                self.median_household_income = self.values["B19013_001E"]

            # Median age
            if "B01002_001E" in self.values:
                try:
                    self.median_age = float(self.values["B01002_001E"])
                except (ValueError, TypeError):
                    pass

        super().save(*args, **kwargs)


class DemographicTimeSeries(models.Model):
    """
    Pre-computed time series for frequently-accessed demographic trends.

    This model stores aggregated time series data for performance,
    avoiding repeated joins across multiple DemographicSnapshot records.
    """

    # Generic foreign key
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="Type of boundary",
    )
    object_id = models.CharField(
        max_length=20,
        help_text="GEOID of the boundary",
    )
    content_object = GenericForeignKey("content_type", "object_id")

    # Series metadata
    variable_code = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Census variable code",
    )
    dataset = models.CharField(
        max_length=10,
        db_index=True,
        help_text="Census dataset",
    )
    start_year = models.PositiveSmallIntegerField(
        help_text="First year in series",
    )
    end_year = models.PositiveSmallIntegerField(
        help_text="Last year in series",
    )

    # Time series data
    years = models.JSONField(
        help_text="List of years",
    )
    values = models.JSONField(
        help_text="List of values corresponding to years",
    )
    moe_values = models.JSONField(
        default=list,
        blank=True,
        help_text="List of MOE values",
    )

    # Computed statistics
    mean_value = models.FloatField(
        null=True,
        blank=True,
        help_text="Mean value across all years",
    )
    std_dev = models.FloatField(
        null=True,
        blank=True,
        help_text="Standard deviation",
    )
    cagr = models.FloatField(
        null=True,
        blank=True,
        help_text="Compound annual growth rate",
    )
    trend_direction = models.CharField(
        max_length=20,
        blank=True,
        help_text="Trend direction (increasing, decreasing, stable)",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Demographic Time Series"
        verbose_name_plural = "Demographic Time Series"
        unique_together = [
            ("content_type", "object_id", "variable_code", "dataset", "start_year", "end_year")
        ]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["variable_code", "dataset"]),
        ]

    def __str__(self):
        return f"{self.variable_code} for {self.object_id} ({self.start_year}-{self.end_year})"

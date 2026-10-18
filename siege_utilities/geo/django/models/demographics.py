"""
Demographic data models for Census boundaries.

These models store demographic snapshots that can be attached to any
Census boundary type using Django's contenttypes framework.
"""

import warnings

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

__all__ = [
    'DemographicVariable',
    'DemographicSnapshot',
    'DemographicTimeSeries',
    'DemographicKeyArchive',
]


class _GEOIDBoundaryLink:
    """GEOID-native relation; ``object_id`` remains the ORM/storage field name.

    Retaining that name preserves loader filters, values_list and bulk writes.
    ``geoid`` is a read/write instance alias, also accepted by objects.create().
    This is not a GenericForeignKey and never resolves a boundary by its PK.
    """

    @property
    def geoid(self) -> str:
        return self.object_id

    @geoid.setter
    def geoid(self, value: str) -> None:
        self.object_id = value

    def get_boundary(self, vintage_year: int | None = None):
        """Return the GEOID boundary, or None if absent.

        Select the requested vintage exactly; otherwise select the newest
        available vintage (then highest PK as a deterministic tie breaker).
        Snapshot year is a data year, not an implicit boundary vintage.
        """
        if not self.content_type_id:
            return None
        model = self.content_type.model_class()
        if model is None:
            return None
        try:
            model._meta.get_field("geoid")
        except FieldDoesNotExist as error:
            raise ValueError("Demographic boundaries must have a GEOID field") from error
        boundaries = model._default_manager.using(self._state.db).filter(geoid=self.geoid)
        if vintage_year is not None:
            boundaries = boundaries.filter(vintage_year=vintage_year)
        return boundaries.order_by("-vintage_year", "-pk").first()

    @property
    def content_object(self):
        """Deprecated GEOID lookup; removed in v4.2.0. Use get_boundary()."""
        warnings.warn(
            "content_object is deprecated and will be removed in v4.2.0; "
            "use get_boundary() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get_boundary()

    @content_object.setter
    def content_object(self, boundary) -> None:
        warnings.warn(
            "content_object is deprecated and will be removed in v4.2.0; "
            "create with content_type and object_id=boundary.geoid instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if not isinstance(getattr(boundary, "geoid", None), str) or not boundary.geoid:
            raise ValueError("Demographic boundaries must have a nonempty string GEOID")
        self.content_type = ContentType.objects.db_manager(
            self._state.db or boundary._state.db
        ).get_for_model(boundary)
        self.geoid = boundary.geoid


class DemographicKeyArchive(models.Model):
    """Recovery copies from the GEOID migration; never queried as live data.

    Includes converted originals, quarantined keys and discarded duplicates.
    The migration's reverse operation restores them only if the migrated rows
    have not subsequently changed; otherwise it fails without overwriting data.
    """

    model_name = models.CharField(max_length=32)
    original_pk = models.PositiveBigIntegerField()
    reason = models.CharField(max_length=32)
    original_data = models.JSONField(encoder=DjangoJSONEncoder)
    migrated_data = models.JSONField(encoder=DjangoJSONEncoder, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["model_name", "original_pk"], name="demographic_archive_row_unique",
            ),
        ]


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


class DemographicSnapshot(_GEOIDBoundaryLink, models.Model):
    """
    Demographic data snapshot for a Census boundary.

    Uses (content_type, object_id/GEOID, dataset, year) as its identity.
    ``object_id`` is an indexed GEOID CharField, never a boundary PK.
    Stores values as JSON to allow flexible variable sets. The deprecated
    create(content_object=tract) convenience stores tract.geoid, not tract.pk,
    and will be removed in v4.2.0 alongside the content_object property.

    Example:
        >>> snapshot = DemographicSnapshot.objects.create(
        ...     content_type=ContentType.objects.get_for_model(tract),
        ...     object_id=tract.geoid,
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

    # Plain content type FK plus a GEOID; not a GenericForeignKey.
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
                "ncesLocaleboundary",
                "schoollocation",
            ],
        },
        help_text="Type of boundary this snapshot is for",
    )
    object_id = models.CharField(
        max_length=20,
        db_index=True,
        help_text="GEOID of the boundary (never its primary key)",
    )

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
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id", "dataset", "year"],
                name="demographic_snapshot_geoid_unique",
            ),
        ]
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


class DemographicTimeSeries(_GEOIDBoundaryLink, models.Model):
    """
    Pre-computed time series for frequently-accessed demographic trends.

    This model stores aggregated time series data for performance,
    avoiding repeated joins across multiple DemographicSnapshot records.
    As with snapshots, object_id is GEOID-only storage, with a geoid alias.
    """

    # Plain content type FK plus a GEOID; not a GenericForeignKey.
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="Type of boundary",
    )
    object_id = models.CharField(
        max_length=20,
        db_index=True,
        help_text="GEOID of the boundary (never its primary key)",
    )

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
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id", "variable_code", "dataset", "start_year", "end_year"],
                name="demographic_series_geoid_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["variable_code", "dataset"]),
        ]

    def __str__(self):
        return f"{self.variable_code} for {self.object_id} ({self.start_year}-{self.end_year})"

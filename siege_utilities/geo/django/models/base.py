"""Abstract base model for Census boundaries."""

from django.contrib.gis.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from siege_utilities.conf import settings


class CensusBoundary(models.Model):
    """
    Abstract base model for Census geographic boundaries.

    All Census boundary types share these common fields:
    - geoid: The full GEOID that uniquely identifies this geography
    - name: Human-readable name
    - geometry: MultiPolygon boundary (SRID from settings.STORAGE_CRS, default NAD83/4269)
    - census_year: The Census/ACS year this boundary represents
    - aland: Land area in square meters
    - awater: Water area in square meters

    GEOID Format by Geography Type:
    - State: 2 digits (e.g., "06" for California)
    - County: 5 digits = state (2) + county (3) (e.g., "06037")
    - Tract: 11 digits = state (2) + county (3) + tract (6) (e.g., "06037101100")
    - Block Group: 12 digits = tract (11) + block group (1) (e.g., "060371011001")
    - Block: 15 digits = tract (11) + block (4) (e.g., "060371011001001")
    - Place: 7 digits = state (2) + place (5) (e.g., "0644000")
    - ZCTA: 5 digits (ZIP Code Tabulation Area) (e.g., "90210")
    - CD: 4 digits = state (2) + district (2) (e.g., "0614")
    """

    geoid = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Full GEOID that uniquely identifies this geography",
    )
    name = models.CharField(
        max_length=255,
        help_text="Human-readable name of this geography",
    )
    # SRID resolves at class-definition time via settings.__getattr__.
    # Django model metaclass needs a concrete int for migrations.
    geometry = models.MultiPolygonField(
        srid=settings.STORAGE_CRS,
        help_text="Boundary geometry (SRID from siege_utilities.conf.settings.STORAGE_CRS)",
    )
    census_year = models.PositiveSmallIntegerField(
        db_index=True,
        validators=[MinValueValidator(1990), MaxValueValidator(2050)],
        help_text="Census or ACS year this boundary represents",
    )
    aland = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Land area in square meters",
    )
    awater = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Water area in square meters",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["geoid"]

    def __str__(self):
        return f"{self.name} ({self.geoid})"

    @property
    def total_area(self) -> int:
        """Total area (land + water) in square meters."""
        land = self.aland or 0
        water = self.awater or 0
        return land + water

    @property
    def land_percentage(self) -> float:
        """Percentage of total area that is land."""
        total = self.total_area
        if total == 0:
            return 0.0
        return (self.aland or 0) / total * 100

    @classmethod
    def get_geoid_length(cls) -> int:
        """Return the expected GEOID length for this geography type."""
        raise NotImplementedError("Subclasses must implement get_geoid_length()")

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        """
        Parse a GEOID into its component parts.

        Returns:
            Dictionary with component FIPS codes
        """
        raise NotImplementedError("Subclasses must implement parse_geoid()")

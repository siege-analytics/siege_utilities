"""
Abstract base models for temporal geographic features.

Hierarchy:
    TemporalGeographicFeature (root abstract — no geometry, pure temporal identity)
    ├── TemporalBoundary (abstract — MultiPolygon, area-based features)
    │   └── CensusTIGERBoundary (abstract — GEOID, FIPS codes, TIGER metadata)
    ├── TemporalLinearFeature (abstract — MultiLineString, e.g. roads, rivers)
    └── TemporalPointFeature (abstract — Point, e.g. addresses, facilities)
"""

import warnings

from django.contrib.gis.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class TemporalGeographicFeature(models.Model):
    """
    Root abstract model for all temporal geographic features.

    Every geographic feature — whether a polygon boundary, a road centerline,
    or a point address — has a temporal dimension: it was valid during some
    period and belongs to some vintage/edition of its source dataset.

    This base provides the identity, temporal, and metadata fields shared by
    ALL geographic feature types. Geometry is intentionally omitted — each
    geometry-type subclass (TemporalBoundary, TemporalLinearFeature,
    TemporalPointFeature) adds the appropriate geometry field.

    Fields:
        feature_id: Stable identifier unique within (feature_id, vintage_year).
                    Polygons sync this from geoid; points from address hash; etc.
        name: Human-readable label.
        vintage_year: The edition year of the source dataset (e.g. 2020 TIGER).
        valid_from / valid_to: Date range during which this feature was in effect.
                               NULL means open-ended (still valid / always valid).
        source: Provenance string (e.g. "TIGER/Line", "GADM", "OpenStreetMap").
    """

    feature_id = models.CharField(
        max_length=60,
        db_index=True,
        help_text="Stable identifier for this feature (unique per vintage_year)",
    )
    name = models.CharField(
        max_length=255,
        help_text="Human-readable name of this feature",
    )
    vintage_year = models.PositiveSmallIntegerField(
        db_index=True,
        validators=[MinValueValidator(1790), MaxValueValidator(2100)],
        help_text="Edition year of the source dataset",
    )
    valid_from = models.DateField(
        null=True,
        blank=True,
        help_text="Date this feature became effective (NULL = always valid)",
    )
    valid_to = models.DateField(
        null=True,
        blank=True,
        help_text="Date this feature ceased to be effective (NULL = still valid)",
    )
    source = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Provenance of this feature (e.g. TIGER/Line, GADM, OSM)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["feature_id"]

    def __str__(self):
        return f"{self.name} ({self.feature_id})"

    @property
    def is_current(self) -> bool:
        """True if this feature has no valid_to date (still in effect)."""
        return self.valid_to is None


class TemporalBoundary(TemporalGeographicFeature):
    """
    Abstract model for area/polygon-based geographic features.

    All boundary types (Census, GADM, NLRB regions, judicial districts, etc.)
    share these fields.  The geometry is always stored as MultiPolygon in
    WGS 84 (SRID 4326) for maximum interoperability.

    Fields inherited from TemporalGeographicFeature:
        feature_id, name, vintage_year, valid_from, valid_to, source

    Fields added here:
        boundary_id: Alias for feature_id, kept for readability in boundary contexts.
                     Automatically synced from feature_id in save().
        geometry: MultiPolygon, SRID 4326.
        area_land / area_water: Area in square meters (from TIGER ALAND/AWATER).
        internal_point: Representative point for labeling (INTPTLAT/INTPTLON).
    """

    boundary_id = models.CharField(
        max_length=60,
        db_index=True,
        help_text="Boundary identifier (synced from feature_id)",
    )
    geometry = models.MultiPolygonField(
        srid=4326,
        help_text="Boundary geometry (WGS 84)",
    )
    area_land = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Land area in square meters",
    )
    area_water = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Water area in square meters",
    )
    internal_point = models.PointField(
        srid=4326,
        null=True,
        blank=True,
        help_text="Representative interior point (INTPTLAT/INTPTLON)",
    )

    class Meta:
        abstract = True
        ordering = ["feature_id"]

    @property
    def total_area(self) -> int:
        """Total area (land + water) in square meters."""
        land = self.area_land or 0
        water = self.area_water or 0
        return land + water

    @property
    def land_percentage(self) -> float:
        """Percentage of total area that is land."""
        total = self.total_area
        if total == 0:
            return 0.0
        return (self.area_land or 0) / total * 100

    def save(self, *args, **kwargs):
        """Sync boundary_id from feature_id."""
        if self.feature_id and not self.boundary_id:
            self.boundary_id = self.feature_id
        super().save(*args, **kwargs)


class CensusTIGERBoundary(TemporalBoundary):
    """
    Abstract model for US Census TIGER/Line boundaries.

    Adds GEOID-based identity and TIGER-specific metadata fields that are
    common to ALL Census geography types (states, counties, tracts, etc.).

    The geoid is the authoritative identifier; feature_id and boundary_id
    are automatically synced from it in save().

    GEOID Format by Geography Type:
        State: 2 digits (e.g., "06" for California)
        County: 5 digits = state (2) + county (3) (e.g., "06037")
        Tract: 11 digits = state (2) + county (3) + tract (6)
        Block Group: 12 digits = tract (11) + block group (1)
        Block: 15 digits = tract (11) + block (4)
        Place: 7 digits = state (2) + place (5)
        ZCTA: 5 digits
        CD: 4 digits = state (2) + district (2)
    """

    geoid = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Full Census GEOID that uniquely identifies this geography",
    )
    state_fips = models.CharField(
        max_length=2,
        db_index=True,
        blank=True,
        default="",
        help_text="2-digit state FIPS code",
    )
    lsad = models.CharField(
        max_length=2,
        blank=True,
        default="",
        help_text="Legal/Statistical Area Description code",
    )
    mtfcc = models.CharField(
        max_length=5,
        blank=True,
        default="",
        help_text="MAF/TIGER Feature Class Code",
    )
    funcstat = models.CharField(
        max_length=1,
        blank=True,
        default="",
        help_text="Functional status code from TIGER/Line",
    )

    class Meta:
        abstract = True
        ordering = ["geoid"]

    def __str__(self):
        return f"{self.name} ({self.geoid})"

    def save(self, *args, **kwargs):
        """Sync feature_id and boundary_id from geoid."""
        if self.geoid:
            self.feature_id = self.geoid
            self.boundary_id = self.geoid
        if not self.source:
            self.source = "TIGER/Line"
        super().save(*args, **kwargs)

    @classmethod
    def get_geoid_length(cls) -> int:
        """Return the expected GEOID length for this geography type."""
        raise NotImplementedError("Subclasses must implement get_geoid_length()")

    @classmethod
    def parse_geoid(cls, geoid: str) -> dict:
        """Parse a GEOID into its component parts."""
        raise NotImplementedError("Subclasses must implement parse_geoid()")


class TemporalLinearFeature(TemporalGeographicFeature):
    """
    Abstract model for linear geographic features (roads, rivers, rail lines).

    These features have temporal validity — a highway may not have existed
    before a certain date, a road may be reclassified, a rail line may be
    decommissioned.

    Concrete subclasses (future): Road, RailLine, Waterway, etc.
    """

    geometry = models.MultiLineStringField(
        srid=4326,
        help_text="Linear geometry (WGS 84)",
    )
    length_meters = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Length in meters",
    )

    class Meta:
        abstract = True
        ordering = ["feature_id"]


class TemporalPointFeature(TemporalGeographicFeature):
    """
    Abstract model for point geographic features (addresses, facilities, landmarks).

    These features have temporal validity — a building may be demolished,
    a new address may be created, a facility may relocate.

    Concrete subclasses (future): Address, Facility, Landmark, etc.
    """

    geometry = models.PointField(
        srid=4326,
        help_text="Point geometry (WGS 84)",
    )

    class Meta:
        abstract = True
        ordering = ["feature_id"]


# ---------------------------------------------------------------------------
# Deprecated aliases — will be removed in v4.0.0
# ---------------------------------------------------------------------------

def _census_boundary_warning():
    warnings.warn(
        "CensusBoundary is deprecated. Use CensusTIGERBoundary instead.",
        DeprecationWarning,
        stacklevel=2,
    )


# CensusBoundary is kept as an alias pointing to CensusTIGERBoundary so that
# existing code like `class MyModel(CensusBoundary)` continues to work.
CensusBoundary = CensusTIGERBoundary

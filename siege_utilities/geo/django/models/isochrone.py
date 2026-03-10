"""
Isochrone result model.

Stores computed isochrone polygons (travel-time contours) in PostGIS
for caching, spatial joins, and historical analysis. Each record
represents a single isochrone polygon for a given origin point,
travel time, profile, and provider.
"""

from django.contrib.gis.db import models as gis_models
from django.db import models

from .base import TemporalBoundary


class IsochroneResult(TemporalBoundary):
    """
    Cached isochrone polygon from an external routing provider.

    Avoids repeated API calls by storing computed isochrones in PostGIS.
    Supports spatial queries like "which tracts are within 15 min of X?"

    Data source: OpenRouteService, Valhalla, or other isochrone providers.

    Example:
        >>> iso = IsochroneResult.objects.get(
        ...     travel_minutes=15,
        ...     profile="driving-car",
        ... )
        >>> iso.geometry  # MultiPolygon of the 15-min driving contour
    """

    origin_point = gis_models.PointField(
        srid=4326,
        help_text="Center point (lat/lon) from which the isochrone was computed",
    )
    travel_minutes = models.PositiveIntegerField(
        help_text="Travel time in minutes for this isochrone contour",
    )
    profile = models.CharField(
        max_length=50,
        default="driving-car",
        help_text="Routing profile (e.g. driving-car, foot-walking, cycling-regular)",
    )
    provider = models.CharField(
        max_length=50,
        default="openrouteservice",
        help_text="Isochrone provider (openrouteservice, valhalla)",
    )
    computed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this isochrone was computed",
    )

    class Meta:
        verbose_name = "Isochrone Result"
        verbose_name_plural = "Isochrone Results"
        unique_together = [
            ("origin_point", "travel_minutes", "profile", "vintage_year"),
        ]
        indexes = [
            models.Index(fields=["travel_minutes", "profile"]),
            models.Index(fields=["provider"]),
            models.Index(fields=["computed_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.feature_id:
            lat = self.origin_point.y
            lon = self.origin_point.x
            self.feature_id = f"iso_{lat:.4f}_{lon:.4f}_{self.travel_minutes}m_{self.profile}"
        if not self.boundary_id:
            self.boundary_id = self.feature_id
        if not self.source:
            self.source = self.provider
        if not self.name:
            self.name = f"{self.travel_minutes}min {self.profile} isochrone"
        super().save(*args, **kwargs)

    def __str__(self):
        lat = self.origin_point.y if self.origin_point else "?"
        lon = self.origin_point.x if self.origin_point else "?"
        return f"{self.travel_minutes}min {self.profile} @ ({lat:.4f}, {lon:.4f})"

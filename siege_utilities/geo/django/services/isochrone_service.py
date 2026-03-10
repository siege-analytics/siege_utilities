"""
Service for computing and caching isochrone results in PostGIS.

Wraps the siege_utilities.geo.isochrones module to fetch isochrone
polygons from routing providers and store them as IsochroneResult
model instances for spatial queries and historical analysis.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Point
from django.db import transaction
from django.utils import timezone

log = logging.getLogger(__name__)


@dataclass
class IsochroneComputeResult:
    """Result of an isochrone compute-and-store operation."""

    records_created: int = 0
    records_cached: int = 0
    errors: list = field(default_factory=list)

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class IsochroneComputeService:
    """
    Compute isochrones via external providers and cache in PostGIS.

    Example:
        >>> service = IsochroneComputeService()
        >>> result = service.compute_and_store(
        ...     latitude=41.8781, longitude=-87.6298,
        ...     travel_minutes=15, profile="driving-car",
        ... )
        >>> print(f"Created: {result.records_created}, Cached: {result.records_cached}")
    """

    def compute_and_store(
        self,
        latitude: float,
        longitude: float,
        travel_minutes: int,
        profile: str = "driving-car",
        provider: str = "openrouteservice",
        vintage_year: Optional[int] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        max_age_days: Optional[int] = None,
        **provider_kwargs,
    ) -> IsochroneComputeResult:
        """
        Fetch an isochrone from a provider and store it in PostGIS.

        If a cached result exists within ``max_age_days``, returns the
        cached record without making an API call.

        Args:
            latitude: Origin latitude.
            longitude: Origin longitude.
            travel_minutes: Travel time in minutes.
            profile: Routing profile (e.g. "driving-car", "foot-walking").
            provider: Isochrone provider ("openrouteservice" or "valhalla").
            vintage_year: Year to associate with this isochrone (default: current year).
            api_key: API key for the provider (if required).
            base_url: Custom base URL for self-hosted providers.
            max_age_days: If set, return cached result if younger than this many days.
            **provider_kwargs: Extra parameters forwarded to get_isochrone().

        Returns:
            IsochroneComputeResult with created/cached counts.
        """
        from siege_utilities.geo.django.models import IsochroneResult

        result = IsochroneComputeResult()
        vintage = vintage_year or datetime.now().year

        # Check cache first
        if max_age_days is not None:
            cutoff = timezone.now() - timedelta(days=max_age_days)
            cached = IsochroneResult.objects.filter(
                origin_point=Point(longitude, latitude, srid=4326),
                travel_minutes=travel_minutes,
                profile=profile,
                vintage_year=vintage,
                computed_at__gte=cutoff,
            ).first()
            if cached:
                result.records_cached = 1
                return result

        # Fetch from provider
        try:
            from siege_utilities.geo.isochrones import get_isochrone

            geojson = get_isochrone(
                latitude=latitude,
                longitude=longitude,
                travel_time_minutes=travel_minutes,
                provider=provider,
                profile=profile,
                api_key=api_key,
                base_url=base_url,
                **provider_kwargs,
            )
        except Exception as exc:
            result.errors.append(f"Provider error: {exc}")
            return result

        # Convert GeoJSON to GEOS geometry
        try:
            geometry = self._geojson_to_multipolygon(geojson)
        except Exception as exc:
            result.errors.append(f"Geometry conversion error: {exc}")
            return result

        # Store in PostGIS
        try:
            with transaction.atomic():
                IsochroneResult.objects.update_or_create(
                    origin_point=Point(longitude, latitude, srid=4326),
                    travel_minutes=travel_minutes,
                    profile=profile,
                    vintage_year=vintage,
                    defaults={
                        "geometry": geometry,
                        "provider": provider,
                        "source": provider,
                        "name": f"{travel_minutes}min {profile} isochrone",
                    },
                )
                result.records_created = 1
        except Exception as exc:
            result.errors.append(f"Database error: {exc}")

        return result

    def get_cached(
        self,
        latitude: float,
        longitude: float,
        travel_minutes: int,
        profile: str = "driving-car",
        max_age_days: Optional[int] = None,
    ):
        """
        Retrieve a cached isochrone result if available.

        Returns the IsochroneResult instance or None.
        """
        from siege_utilities.geo.django.models import IsochroneResult

        qs = IsochroneResult.objects.filter(
            origin_point=Point(longitude, latitude, srid=4326),
            travel_minutes=travel_minutes,
            profile=profile,
        )
        if max_age_days is not None:
            cutoff = timezone.now() - timedelta(days=max_age_days)
            qs = qs.filter(computed_at__gte=cutoff)
        return qs.order_by("-computed_at").first()

    @staticmethod
    def _geojson_to_multipolygon(geojson: dict) -> MultiPolygon:
        """Convert isochrone GeoJSON response to a MultiPolygon GEOS geometry."""
        features = geojson.get("features", [])
        if not features:
            raise ValueError("GeoJSON contains no features")

        polygons = []
        for feat in features:
            geom = GEOSGeometry(str(feat["geometry"]))
            if geom.geom_type == "Polygon":
                polygons.append(geom)
            elif geom.geom_type == "MultiPolygon":
                for poly in geom:
                    polygons.append(poly)

        if not polygons:
            raise ValueError("No polygon geometries found in GeoJSON features")

        return MultiPolygon(polygons, srid=4326)

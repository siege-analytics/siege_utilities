"""
Custom manager for temporal boundary models with spatial query helpers.
"""

from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point, GEOSGeometry
from django.contrib.gis.measure import D
from django.db import models


class BoundaryQuerySet(gis_models.QuerySet):
    """
    Custom QuerySet for boundary models with spatial queries.
    """

    def for_year(self, year: int):
        """Filter boundaries by vintage year."""
        return self.filter(vintage_year=year)

    def for_state(self, state_fips: str):
        """Filter boundaries by state FIPS code."""
        return self.filter(state_fips=state_fips)

    def current(self):
        """Filter to currently-valid boundaries (valid_to is NULL)."""
        return self.filter(valid_to__isnull=True)

    def valid_on(self, date):
        """Filter to boundaries valid on a specific date."""
        return self.filter(
            models.Q(valid_from__isnull=True) | models.Q(valid_from__lte=date),
            models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=date),
        )

    def containing_point(self, point: Point, srid: int = 4326):
        """
        Find boundaries containing a point.

        Args:
            point: A GEOS Point object or (lon, lat) tuple
            srid: Spatial reference ID (default: 4326 WGS 84)

        Returns:
            QuerySet filtered to boundaries containing the point
        """
        if isinstance(point, tuple):
            point = Point(point[0], point[1], srid=srid)
        return self.filter(geometry__contains=point)

    def intersecting(self, geometry: GEOSGeometry):
        """
        Find boundaries intersecting a geometry.

        Args:
            geometry: Any GEOS geometry

        Returns:
            QuerySet filtered to intersecting boundaries
        """
        return self.filter(geometry__intersects=geometry)

    def within_distance(self, point: Point, distance_meters: float):
        """
        Find boundaries within a distance of a point.

        Uses geodesic distance via PostGIS ST_DWithin(geography).

        Args:
            point: A GEOS Point object
            distance_meters: Distance in meters

        Returns:
            QuerySet filtered to boundaries within distance
        """
        return self.filter(geometry__dwithin=(point, D(m=distance_meters)))

    def nearest(self, point, max_distance_m=None, srid: int = 4326):
        """
        Find boundaries ordered by distance from a point (nearest first).

        Uses geodesic distance via PostGIS ST_Distance(geography).

        Args:
            point: A GEOS Point object or (lon, lat) tuple
            max_distance_m: Optional max distance in meters to filter results
            srid: Spatial reference ID for tuple input (default: 4326 WGS 84)

        Returns:
            QuerySet annotated with 'distance' and ordered nearest-first
        """
        from django.contrib.gis.db.models.functions import Distance

        if isinstance(point, tuple):
            point = Point(point[0], point[1], srid=srid)
        qs = self.annotate(distance=Distance("geometry", point)).order_by("distance")
        if max_distance_m is not None:
            qs = qs.filter(geometry__dwithin=(point, D(m=max_distance_m)))
        return qs

    def with_area(self):
        """
        Annotate each boundary with its calculated area.

        Returns:
            QuerySet with 'calculated_area' annotation (square meters)
        """
        from django.contrib.gis.db.models.functions import Area

        return self.annotate(calculated_area=Area("geometry"))

    def by_land_area(self, ascending: bool = True):
        """
        Order boundaries by land area.

        Args:
            ascending: True for smallest first, False for largest first

        Returns:
            Ordered QuerySet
        """
        order = "area_land" if ascending else "-area_land"
        return self.order_by(order)

    def by_population(self, year: int = None, ascending: bool = False):
        """
        Order boundaries by population.

        Requires DemographicSnapshot records to be joined.

        Args:
            year: Census year for population data
            ascending: True for smallest first, False for largest first

        Returns:
            Ordered QuerySet (may be empty if no demographics loaded)
        """
        # This requires a subquery to DemographicSnapshot
        from django.db.models import OuterRef, Subquery
        from ..models.demographics import DemographicSnapshot

        subquery = DemographicSnapshot.objects.filter(
            object_id=OuterRef("geoid"),
            **({"year": year} if year else {}),
        ).values("total_population")[:1]

        qs = self.annotate(population=Subquery(subquery))

        order = "population" if ascending else "-population"
        return qs.order_by(order)

    def geojson(self):
        """
        Return boundaries as GeoJSON Feature dicts.

        Returns:
            GeoJSON FeatureCollection dict
        """
        features = []
        for boundary in self.all():
            features.append(
                {
                    "type": "Feature",
                    "geometry": boundary.geometry.json,
                    "properties": {
                        "geoid": getattr(boundary, "geoid", boundary.feature_id),
                        "name": boundary.name,
                        "vintage_year": boundary.vintage_year,
                        "area_land": boundary.area_land,
                        "area_water": boundary.area_water,
                    },
                }
            )
        return {"type": "FeatureCollection", "features": features}


class BoundaryManager(gis_models.Manager):
    """
    Custom manager for temporal boundary models.

    Provides convenient methods for common spatial queries.

    Example:
        >>> from siege_utilities.geo.django.models import Tract
        >>> point = Point(-122.4194, 37.7749, srid=4326)
        >>> tract = Tract.objects.containing_point(point).for_year(2020).first()
    """

    def get_queryset(self):
        return BoundaryQuerySet(self.model, using=self._db)

    def for_year(self, year: int):
        """Filter boundaries by vintage year."""
        return self.get_queryset().for_year(year)

    def for_state(self, state_fips: str):
        """Filter boundaries by state FIPS code."""
        return self.get_queryset().for_state(state_fips)

    def current(self):
        """Filter to currently-valid boundaries."""
        return self.get_queryset().current()

    def valid_on(self, date):
        """Filter to boundaries valid on a specific date."""
        return self.get_queryset().valid_on(date)

    def containing_point(self, point, srid: int = 4326):
        """Find boundaries containing a point."""
        return self.get_queryset().containing_point(point, srid=srid)

    def intersecting(self, geometry):
        """Find boundaries intersecting a geometry."""
        return self.get_queryset().intersecting(geometry)

    def within_distance(self, point, distance_meters: float):
        """Find boundaries within a distance of a point."""
        return self.get_queryset().within_distance(point, distance_meters)

    def nearest(self, point, max_distance_m=None, srid: int = 4326):
        """Find boundaries ordered by distance from a point."""
        return self.get_queryset().nearest(point, max_distance_m, srid=srid)

    def get_by_geoid(self, geoid: str, year: int = None):
        """
        Get a single boundary by GEOID.

        Args:
            geoid: The full GEOID
            year: Optional vintage year (returns most recent if not specified)

        Returns:
            The boundary object

        Raises:
            DoesNotExist: If no matching boundary found
        """
        qs = self.filter(geoid=geoid)
        if year:
            qs = qs.filter(vintage_year=year)
        else:
            qs = qs.order_by("-vintage_year")
        return qs.first()

    def get_children(self, parent_geoid: str, year: int):
        """
        Get child boundaries for a parent GEOID.

        For example, get all counties in a state or all tracts in a county.

        Args:
            parent_geoid: GEOID of the parent boundary
            year: Vintage year

        Returns:
            QuerySet of child boundaries
        """
        return self.filter(geoid__startswith=parent_geoid, vintage_year=year).exclude(
            geoid=parent_geoid
        )

    def bulk_create_from_geodataframe(
        self, gdf, year: int, batch_size: int = 1000, srid: int = 4326
    ):
        """
        Bulk create boundaries from a GeoPandas GeoDataFrame.

        Args:
            gdf: GeoDataFrame with GEOID, NAME, geometry, and optionally ALAND/AWATER
            year: Vintage year for these boundaries
            batch_size: Number of records per batch
            srid: Spatial reference ID for the geometry (default: 4326 WGS 84)

        Returns:
            List of created boundary objects
        """
        from django.contrib.gis.geos import GEOSGeometry

        objects = []
        for _, row in gdf.iterrows():
            geom = GEOSGeometry(row.geometry.wkt, srid=srid)

            # Ensure MultiPolygon
            if geom.geom_type == "Polygon":
                from django.contrib.gis.geos import MultiPolygon

                geom = MultiPolygon(geom, srid=srid)

            # Build object kwargs
            kwargs = {
                "geoid": str(row.get("GEOID", row.get("geoid", ""))),
                "name": str(row.get("NAME", row.get("name", ""))),
                "geometry": geom,
                "vintage_year": year,
                "area_land": row.get("ALAND", row.get("aland", row.get("area_land"))),
                "area_water": row.get("AWATER", row.get("awater", row.get("area_water"))),
            }

            # Parse GEOID into component fields
            geoid = kwargs["geoid"]
            parsed = self.model.parse_geoid(geoid)
            kwargs.update(parsed)

            objects.append(self.model(**kwargs))

        # Bulk create in batches
        created = []
        for i in range(0, len(objects), batch_size):
            batch = objects[i : i + batch_size]
            created.extend(
                self.bulk_create(batch, ignore_conflicts=True, batch_size=batch_size)
            )

        return created

"""
Custom manager for Census boundary models with spatial query helpers.
"""

from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point, Polygon, GEOSGeometry
from django.db import models


class BoundaryQuerySet(gis_models.QuerySet):
    """
    Custom QuerySet for Census boundary models with spatial queries.
    """

    def for_year(self, year: int):
        """Filter boundaries by Census year."""
        return self.filter(census_year=year)

    def for_state(self, state_fips: str):
        """Filter boundaries by state FIPS code."""
        return self.filter(state_fips=state_fips)

    def containing_point(self, point: Point):
        """
        Find boundaries containing a point.

        Args:
            point: A GEOS Point object or (lon, lat) tuple

        Returns:
            QuerySet filtered to boundaries containing the point
        """
        if isinstance(point, tuple):
            point = Point(point[0], point[1], srid=4326)
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

        Args:
            point: A GEOS Point object
            distance_meters: Distance in meters

        Returns:
            QuerySet filtered to boundaries within distance
        """
        # Use dwithin for spherical distance on geographic coordinates
        return self.filter(geometry__dwithin=(point, distance_meters / 1000 / 111))

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
        order = "aland" if ascending else "-aland"
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
            List of GeoJSON Feature dictionaries
        """
        features = []
        for boundary in self.all():
            features.append(
                {
                    "type": "Feature",
                    "geometry": boundary.geometry.json,
                    "properties": {
                        "geoid": boundary.geoid,
                        "name": boundary.name,
                        "census_year": boundary.census_year,
                        "aland": boundary.aland,
                        "awater": boundary.awater,
                    },
                }
            )
        return {"type": "FeatureCollection", "features": features}


class BoundaryManager(gis_models.Manager):
    """
    Custom manager for Census boundary models.

    Provides convenient methods for common spatial queries.

    Example:
        >>> from siege_utilities.geo.django.models import Tract
        >>> point = Point(-122.4194, 37.7749, srid=4326)
        >>> tract = Tract.objects.containing_point(point).for_year(2020).first()
    """

    def get_queryset(self):
        return BoundaryQuerySet(self.model, using=self._db)

    def for_year(self, year: int):
        """Filter boundaries by Census year."""
        return self.get_queryset().for_year(year)

    def for_state(self, state_fips: str):
        """Filter boundaries by state FIPS code."""
        return self.get_queryset().for_state(state_fips)

    def containing_point(self, point):
        """Find boundaries containing a point."""
        return self.get_queryset().containing_point(point)

    def intersecting(self, geometry):
        """Find boundaries intersecting a geometry."""
        return self.get_queryset().intersecting(geometry)

    def within_distance(self, point, distance_meters: float):
        """Find boundaries within a distance of a point."""
        return self.get_queryset().within_distance(point, distance_meters)

    def get_by_geoid(self, geoid: str, year: int = None):
        """
        Get a single boundary by GEOID.

        Args:
            geoid: The full GEOID
            year: Optional Census year (returns most recent if not specified)

        Returns:
            The boundary object

        Raises:
            DoesNotExist: If no matching boundary found
        """
        qs = self.filter(geoid=geoid)
        if year:
            qs = qs.filter(census_year=year)
        else:
            qs = qs.order_by("-census_year")
        return qs.first()

    def get_children(self, parent_geoid: str, year: int):
        """
        Get child boundaries for a parent GEOID.

        For example, get all counties in a state or all tracts in a county.

        Args:
            parent_geoid: GEOID of the parent boundary
            year: Census year

        Returns:
            QuerySet of child boundaries
        """
        return self.filter(geoid__startswith=parent_geoid, census_year=year).exclude(
            geoid=parent_geoid
        )

    def bulk_create_from_geodataframe(self, gdf, year: int, batch_size: int = 1000):
        """
        Bulk create boundaries from a GeoPandas GeoDataFrame.

        Args:
            gdf: GeoDataFrame with GEOID, NAME, geometry, and optionally ALAND/AWATER
            year: Census year for these boundaries
            batch_size: Number of records per batch

        Returns:
            List of created boundary objects
        """
        from django.contrib.gis.geos import GEOSGeometry

        objects = []
        for _, row in gdf.iterrows():
            geom = GEOSGeometry(row.geometry.wkt, srid=4326)

            # Ensure MultiPolygon
            if geom.geom_type == "Polygon":
                from django.contrib.gis.geos import MultiPolygon

                geom = MultiPolygon(geom, srid=4326)

            # Build object kwargs
            kwargs = {
                "geoid": str(row.get("GEOID", row.get("geoid", ""))),
                "name": str(row.get("NAME", row.get("name", ""))),
                "geometry": geom,
                "census_year": year,
                "aland": row.get("ALAND", row.get("aland")),
                "awater": row.get("AWATER", row.get("awater")),
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

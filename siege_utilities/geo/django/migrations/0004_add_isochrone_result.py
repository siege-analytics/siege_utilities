"""Add IsochroneResult model for caching computed isochrone polygons."""

import django.contrib.gis.db.models.fields
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("siege_geo", "0003_add_timezone_geometry"),
    ]

    operations = [
        migrations.CreateModel(
            name="IsochroneResult",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "feature_id",
                    models.CharField(
                        db_index=True,
                        help_text="Stable identifier for this feature (unique per vintage_year)",
                        max_length=60,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Human-readable name of this feature",
                        max_length=255,
                    ),
                ),
                (
                    "vintage_year",
                    models.PositiveSmallIntegerField(
                        db_index=True,
                        help_text="Edition year of the source dataset",
                        validators=[
                            django.core.validators.MinValueValidator(1790),
                            django.core.validators.MaxValueValidator(2100),
                        ],
                    ),
                ),
                (
                    "valid_from",
                    models.DateField(
                        blank=True,
                        help_text="Date this feature became effective (NULL = always valid)",
                        null=True,
                    ),
                ),
                (
                    "valid_to",
                    models.DateField(
                        blank=True,
                        help_text="Date this feature ceased to be effective (NULL = still valid)",
                        null=True,
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Provenance of this feature (e.g. TIGER/Line, GADM, OSM)",
                        max_length=50,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "boundary_id",
                    models.CharField(
                        db_index=True,
                        help_text="Boundary identifier (synced from feature_id)",
                        max_length=60,
                    ),
                ),
                (
                    "geometry",
                    django.contrib.gis.db.models.fields.MultiPolygonField(
                        help_text="Boundary geometry (WGS 84)",
                        srid=4326,
                    ),
                ),
                (
                    "area_land",
                    models.BigIntegerField(
                        blank=True,
                        help_text="Land area in square meters",
                        null=True,
                    ),
                ),
                (
                    "area_water",
                    models.BigIntegerField(
                        blank=True,
                        help_text="Water area in square meters",
                        null=True,
                    ),
                ),
                (
                    "internal_point",
                    django.contrib.gis.db.models.fields.PointField(
                        blank=True,
                        help_text="Representative interior point (INTPTLAT/INTPTLON)",
                        null=True,
                        srid=4326,
                    ),
                ),
                (
                    "origin_point",
                    django.contrib.gis.db.models.fields.PointField(
                        help_text="Center point (lat/lon) from which the isochrone was computed",
                        srid=4326,
                    ),
                ),
                (
                    "travel_minutes",
                    models.PositiveIntegerField(
                        help_text="Travel time in minutes for this isochrone contour",
                    ),
                ),
                (
                    "profile",
                    models.CharField(
                        default="driving-car",
                        help_text="Routing profile (e.g. driving-car, foot-walking, cycling-regular)",
                        max_length=50,
                    ),
                ),
                (
                    "provider",
                    models.CharField(
                        default="openrouteservice",
                        help_text="Isochrone provider (openrouteservice, valhalla)",
                        max_length=50,
                    ),
                ),
                (
                    "computed_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="When this isochrone was computed",
                    ),
                ),
            ],
            options={
                "verbose_name": "Isochrone Result",
                "verbose_name_plural": "Isochrone Results",
                "unique_together": {
                    ("origin_point", "travel_minutes", "profile", "vintage_year"),
                },
                "indexes": [
                    models.Index(
                        fields=["travel_minutes", "profile"],
                        name="siege_geo_iso_travel_profile_idx",
                    ),
                    models.Index(
                        fields=["provider"],
                        name="siege_geo_iso_provider_idx",
                    ),
                    models.Index(
                        fields=["computed_at"],
                        name="siege_geo_iso_computed_idx",
                    ),
                ],
            },
        ),
    ]

"""SU#551: add TribalArea + CountySubdivision boundary models.

Completes the four missing Census TIGER boundary families flagged in
SW#305. PUMA and SpecialDistrict models were shipped in 0007; this
migration adds the remaining two.
"""

import django.contrib.gis.db.models.fields
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


def _tiger_fields():
    return [
        ("id", models.BigAutoField(
            auto_created=True, primary_key=True, serialize=False, verbose_name="ID",
        )),
        ("feature_id", models.CharField(
            db_index=True,
            help_text="Stable identifier for this feature (unique per vintage_year)",
            max_length=60,
        )),
        ("name", models.CharField(
            help_text="Human-readable name of this feature", max_length=255,
        )),
        ("vintage_year", models.PositiveSmallIntegerField(
            db_index=True,
            help_text="Edition year of the source dataset",
            validators=[
                django.core.validators.MinValueValidator(1790),
                django.core.validators.MaxValueValidator(2100),
            ],
        )),
        ("valid_from", models.DateField(
            blank=True,
            help_text="Date this feature became effective (NULL = always valid)",
            null=True,
        )),
        ("valid_to", models.DateField(
            blank=True,
            help_text="Date this feature ceased to be effective (NULL = still valid)",
            null=True,
        )),
        ("source", models.CharField(
            blank=True, default="",
            help_text="Provenance of this feature (e.g. TIGER/Line, GADM, OSM)",
            max_length=50,
        )),
        ("created_at", models.DateTimeField(auto_now_add=True)),
        ("updated_at", models.DateTimeField(auto_now=True)),
        ("boundary_id", models.CharField(
            db_index=True,
            help_text="Boundary identifier (synced from feature_id)",
            max_length=60,
        )),
        ("geometry", django.contrib.gis.db.models.fields.MultiPolygonField(
            help_text="Boundary geometry (WGS 84)", srid=4326,
        )),
        ("area_land", models.BigIntegerField(
            blank=True, help_text="Land area in square meters", null=True,
        )),
        ("area_water", models.BigIntegerField(
            blank=True, help_text="Water area in square meters", null=True,
        )),
        ("internal_point", django.contrib.gis.db.models.fields.PointField(
            blank=True,
            help_text="Representative interior point (INTPTLAT/INTPTLON)",
            null=True, srid=4326,
        )),
        ("geoid", models.CharField(
            db_index=True,
            help_text="Full Census GEOID that uniquely identifies this geography",
            max_length=20,
        )),
        ("state_fips", models.CharField(
            blank=True, default="", db_index=True,
            help_text="2-digit state FIPS code (empty for nation-level geographies)",
            max_length=2,
        )),
        ("lsad", models.CharField(
            blank=True, default="",
            help_text="Legal/Statistical Area Description code", max_length=2,
        )),
        ("mtfcc", models.CharField(
            blank=True, default="",
            help_text="MAF/TIGER Feature Class Code", max_length=5,
        )),
        ("funcstat", models.CharField(
            blank=True, default="",
            help_text="Functional status code", max_length=1,
        )),
    ]


class Migration(migrations.Migration):

    dependencies = [
        ("siege_geo", "0007_puma_and_special_districts"),
    ]

    operations = [
        # TribalArea — national-level AIANNH boundaries.
        migrations.CreateModel(
            name="TribalArea",
            fields=_tiger_fields() + [
                ("aiannhce", models.CharField(
                    db_index=True, max_length=4,
                    help_text="AIANNH Census code",
                )),
                ("aiannhns", models.CharField(
                    blank=True, default="", max_length=8,
                    help_text="AIANNH ANSI code",
                )),
                ("comptyp", models.CharField(
                    blank=True, default="", max_length=2,
                    help_text="Component type (R=Reservation, T=Trust land, etc.)",
                )),
            ],
            options={
                "verbose_name": "Tribal Area",
                "verbose_name_plural": "Tribal Areas",
                "unique_together": {("geoid", "vintage_year")},
            },
        ),
        migrations.AddIndex(
            model_name="tribalarea",
            index=models.Index(
                fields=["aiannhce"],
                name="siege_geo_tribal_ce_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="tribalarea",
            index=models.Index(
                fields=["vintage_year"],
                name="siege_geo_tribal_vy_idx",
            ),
        ),

        # CountySubdivision — MCD/CCD boundaries with state + county FK.
        migrations.CreateModel(
            name="CountySubdivision",
            fields=_tiger_fields() + [
                ("state", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="county_subdivisions",
                    to="siege_geo.state",
                    help_text="Parent state",
                )),
                ("county", models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="county_subdivisions",
                    to="siege_geo.county",
                    help_text="Parent county",
                )),
                ("county_fips", models.CharField(
                    db_index=True, max_length=3,
                    help_text="3-digit county FIPS code",
                )),
                ("cousub_fips", models.CharField(
                    db_index=True, max_length=5,
                    help_text="5-digit county subdivision FIPS code",
                )),
                ("cousub_type", models.CharField(
                    blank=True, default="", max_length=1,
                    help_text="Subdivision type (S=MCD, T=CCD, Z=unorganized territory, etc.)",
                )),
            ],
            options={
                "verbose_name": "County Subdivision",
                "verbose_name_plural": "County Subdivisions",
                "unique_together": {("geoid", "vintage_year")},
            },
        ),
        migrations.AddConstraint(
            model_name="countysubdivision",
            constraint=models.CheckConstraint(
                condition=models.Q(geoid__regex=r"^\d{10}$"),
                name="cousub_geoid_10_digits",
            ),
        ),
        migrations.AddIndex(
            model_name="countysubdivision",
            index=models.Index(
                fields=["state_fips", "county_fips", "cousub_fips"],
                name="siege_geo_cousub_fips_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="countysubdivision",
            index=models.Index(
                fields=["state_fips", "vintage_year"],
                name="siege_geo_cousub_st_vy_idx",
            ),
        ),
    ]

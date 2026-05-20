"""SU#535: add PUMA + 7 per-kind special-district boundary models.

Downstream SW#191 (template-readiness C-medium) already shipped the
Address-level cache fields for these types. This migration ships the
upstream boundary models so `assign_boundaries` can populate the
caches once data is loaded.
"""

import django.contrib.gis.db.models.fields
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


# Shared CensusTIGERBoundary fields. Every concrete model below carries
# this same field list (inherited from base). Defined once as a callable
# so each CreateModel can call it fresh.
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


# Shared special-district extras (added to base by SpecialDistrictBase).
def _special_district_extras():
    return [
        ("governing_body", models.CharField(
            blank=True, default="", max_length=255,
            help_text="Name of the special district's governing body.",
        )),
        ("function_code", models.CharField(
            blank=True, default="", db_index=True, max_length=10,
            help_text="Census-published function code distinguishing the district's purpose.",
        )),
    ]


_SPECIAL_DISTRICT_MODELS = [
    ("FireProtectionDistrict", "Fire Protection District"),
    ("WaterSupplyDistrict", "Water Supply District"),
    ("HospitalDistrict", "Hospital District"),
    ("LibraryDistrict", "Library District"),
    ("CemeteryDistrict", "Cemetery District"),
    ("MosquitoAbatementDistrict", "Mosquito Abatement District"),
    ("OtherSpecialDistrict", "Other Special District"),
]


def _make_special_district_create_model(model_name, verbose_name):
    return migrations.CreateModel(
        name=model_name,
        fields=_tiger_fields() + _special_district_extras(),
        options={
            "verbose_name": verbose_name,
            "verbose_name_plural": verbose_name + "s",
            "unique_together": {("geoid", "vintage_year")},
        },
    )


class Migration(migrations.Migration):

    dependencies = [
        ("siege_geo", "0006_redistrictingplan_missing_fields"),
    ]

    operations = [
        # PUMA — uses base TIGER fields + a 5-digit puma_code.
        migrations.CreateModel(
            name="PUMA",
            fields=_tiger_fields() + [
                ("puma_code", models.CharField(
                    db_index=True, max_length=5,
                    help_text="5-digit PUMA code within a state",
                )),
            ],
            options={
                "verbose_name": "PUMA",
                "verbose_name_plural": "PUMAs",
                "unique_together": {("geoid", "vintage_year")},
            },
        ),
        migrations.AddConstraint(
            model_name="puma",
            constraint=models.CheckConstraint(
                condition=models.Q(geoid__regex=r"^\d{7}$"),
                name="puma_geoid_7_digits",
            ),
        ),
        migrations.AddIndex(
            model_name="puma",
            index=models.Index(fields=["state_fips", "puma_code"], name="siege_geo_puma_st_pc_idx"),
        ),
        migrations.AddIndex(
            model_name="puma",
            index=models.Index(fields=["state_fips", "vintage_year"], name="siege_geo_puma_st_vy_idx"),
        ),

        # 7 per-kind special-district models, generated from the catalog.
        *[
            _make_special_district_create_model(name, verbose)
            for (name, verbose) in _SPECIAL_DISTRICT_MODELS
        ],

        # Per-model state_fips × vintage_year index (mirrors UrbanArea / Place pattern).
        *[
            migrations.AddIndex(
                model_name=name.lower(),
                index=models.Index(
                    fields=["state_fips", "vintage_year"],
                    name=f"siege_geo_{name[:8].lower()}_vy_idx",
                ),
            )
            for (name, _) in _SPECIAL_DISTRICT_MODELS
        ],
    ]

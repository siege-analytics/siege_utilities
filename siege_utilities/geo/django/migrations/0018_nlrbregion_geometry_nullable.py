"""Allow registry-only NLRB regions without a dissolved geometry (#1585)."""

from django.contrib.gis.db.models.fields import MultiPolygonField
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("siege_geo", "0017_cd112_geoid_format"),
    ]

    operations = [
        migrations.AlterField(
            model_name="nlrbregion",
            name="geometry",
            field=MultiPolygonField(
                help_text="Boundary geometry (WGS 84)", null=True, srid=4326,
            ),
        ),
    ]

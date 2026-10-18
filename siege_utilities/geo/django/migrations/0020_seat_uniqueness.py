from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("siege_geo", "0019_demographic_geoid_keys"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="seat",
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name="seat",
            constraint=models.UniqueConstraint(
                condition=models.Q(("senate_class__isnull", False)),
                fields=("office", "state", "district_label", "senate_class"),
                name="seat_identity_with_senate_class",
            ),
        ),
        migrations.AddConstraint(
            model_name="seat",
            constraint=models.UniqueConstraint(
                condition=models.Q(("senate_class__isnull", True)),
                fields=("office", "state", "district_label"),
                name="seat_identity_without_senate_class",
            ),
        ),
        migrations.AddConstraint(
            model_name="seat",
            constraint=models.UniqueConstraint(
                condition=models.Q(("office", "PRESIDENT")),
                fields=("office",),
                name="seat_president_singleton",
            ),
        ),
    ]

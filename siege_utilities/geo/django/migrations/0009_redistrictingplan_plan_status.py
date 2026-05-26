"""SU#552: add plan_status lifecycle field to RedistrictingPlan.

Six-choice lifecycle status (proposed/enacted/challenged/invalidated/
superseded/rejected) that lets for_date() and active() filter out plans
no longer in legal effect.  Default is "enacted" so existing rows
backfill correctly — all current production records represent enacted plans.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("siege_geo", "0008_tribalarea_and_countysubdivision"),
    ]

    operations = [
        migrations.AddField(
            model_name="redistrictingplan",
            name="plan_status",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("proposed", "Proposed"),
                    ("enacted", "Enacted / In Effect"),
                    ("challenged", "Challenged (under litigation)"),
                    ("invalidated", "Invalidated by Court"),
                    ("superseded", "Superseded by New Plan"),
                    ("rejected", "Rejected"),
                ],
                default="enacted",
                db_index=True,
                help_text="Lifecycle status of this plan",
            ),
        ),
    ]

"""Add the RedistrictingPlan fields declared on the model but absent from
migration 0005: `state` FK, `effective_from`, `effective_to`,
`superseded_by` self-FK, and `court_case`.

Fixes SU#527 — model declared the fields, schema didn't have the
columns, so `for_date()` and any `select_related("redistricting_plan")`
from downstream code crashed with UndefinedColumn.

All new columns are nullable / have safe defaults so existing rows
backfill cleanly. No data migration needed: existing rows simply have
NULL `state`, NULL `effective_from` / `effective_to`, NULL
`superseded_by`, and empty `court_case`.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("siege_geo", "0005_add_temporal_models_and_plan_assignment"),
    ]

    operations = [
        migrations.AddField(
            model_name="redistrictingplan",
            name="state",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="redistricting_plans",
                to="siege_geo.state",
                help_text="Parent state",
            ),
        ),
        migrations.AddField(
            model_name="redistrictingplan",
            name="effective_from",
            field=models.DateField(
                null=True,
                blank=True,
                db_index=True,
                help_text="Date this plan took legal effect (may differ from enacted_date)",
            ),
        ),
        migrations.AddField(
            model_name="redistrictingplan",
            name="effective_to",
            field=models.DateField(
                null=True,
                blank=True,
                db_index=True,
                help_text="Date this plan was superseded (NULL = still in effect)",
            ),
        ),
        migrations.AddField(
            model_name="redistrictingplan",
            name="superseded_by",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="supersedes",
                to="siege_geo.redistrictingplan",
                help_text="The plan that replaced this one (court order, new cycle, etc.)",
            ),
        ),
        migrations.AddField(
            model_name="redistrictingplan",
            name="court_case",
            field=models.CharField(
                max_length=255,
                blank=True,
                default="",
                help_text="Court case name if court-ordered (e.g., 'Allen v. Milligan')",
            ),
        ),
    ]

"""#977: Enforce that Seat.state is non-null unless office is PRESIDENT.

DB-level check constraint prevents House/Senate/Governor seats from
having a null state FK — only PRESIDENT is stateless.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("siege_geo", "0009_redistrictingplan_plan_status"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="seat",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(state__isnull=False)
                    | models.Q(office="PRESIDENT")
                ),
                name="seat_state_required_unless_president",
            ),
        ),
    ]

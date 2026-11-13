"""Seat identity includes Senate class; at most one PRESIDENT seat.

Of the constraints added here, only ``seat_president_singleton`` can reject
rows that were valid under 0019. The old ``(office, state, district_label)``
key already covers both identity constraints for rows with a state, and only
PRESIDENT rows may have no state. So before changing any constraint, a
read-only precheck counts the rows matching the singleton's own condition. If
there are duplicates, it fails with the total, a bounded list of their primary
keys and the constraint name. It never deletes, merges or reassigns rows. The
data owner resolves them and reruns the migration. A row inserted concurrently
between the precheck and ``AddConstraint`` is still rejected by the constraint.
"""

from django.db import migrations, models

PRESIDENT_SINGLETON = "seat_president_singleton"
DUPLICATE_SAMPLE_LIMIT = 20


def reject_duplicate_presidents(apps, schema_editor):
    """Raise RuntimeError if existing rows would violate the PRESIDENT singleton.

    Read-only: it uses the historical Seat model on the migrating connection's
    alias, and it only counts and lists primary keys.
    """
    alias = schema_editor.connection.alias
    seat = apps.get_model("siege_geo", "Seat")
    presidents = seat.objects.using(alias).filter(office="PRESIDENT")
    total = presidents.count()
    if total <= 1:
        return
    sample = list(
        presidents.order_by("pk").values_list("pk", flat=True)[:DUPLICATE_SAMPLE_LIMIT]
    )
    shown = ", ".join(str(pk) for pk in sample)
    raise RuntimeError(
        f"Cannot apply siege_geo 0020_seat_uniqueness: constraint {PRESIDENT_SINGLETON} "
        f"allows one PRESIDENT seat, but {total} exist (database alias {alias!r}). "
        f"Lowest primary keys, {len(sample)} of {total}: {shown}. "
        "This migration changed no rows or constraints. "
        "The application/data owner must reconcile these PRESIDENT seats, "
        "including rows that reference them, under their own authority, "
        "then rerun the migration."
    )


class Migration(migrations.Migration):

    dependencies = [
        ("siege_geo", "0019_demographic_geoid_keys"),
    ]

    operations = [
        # Read-only precheck: runs before any constraint change, reverses as a no-op.
        # The model_name hint lets database routers treat it like the Seat
        # operations below, so a router cannot skip the check but run them.
        migrations.RunPython(
            reject_duplicate_presidents,
            migrations.RunPython.noop,
            hints={"model_name": "seat"},
        ),
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

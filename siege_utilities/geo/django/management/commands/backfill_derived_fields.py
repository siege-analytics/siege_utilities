"""
Management command to backfill fields that bulk loaders left unset.

Before #1539, the loaders inserted rows with ``bulk_create``, which skips
``save()``. Boundary rows were stored with empty ``feature_id``,
``boundary_id`` and ``source``, and ``DemographicSnapshot`` rows with NULL
``total_population``, ``median_household_income`` and ``median_age``. Before
#1550, every snapshot also stored the Census API's ``NAME`` label as
``values["NAME"]``.

This command applies each model's ``prepare_for_bulk()`` to the affected
rows and writes the derived columns back. It is a one-off operator action
and never runs automatically; ``--dry-run`` reports what it would change.

Usage:
    python manage.py backfill_derived_fields --dry-run
    python manage.py backfill_derived_fields
    python manage.py backfill_derived_fields --only demographics --strip-name
"""

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

__all__ = ['Command']

# Fields TemporalGeographicFeature.prepare_for_bulk() implementations derive,
# and the subset whose emptiness marks a row the bulk loaders left unprepared.
_FEATURE_FIELDS = ("feature_id", "boundary_id", "source", "name")
_FEATURE_MARKERS = ("feature_id", "boundary_id", "source")
_SNAPSHOT_SOURCES = {
    "total_population": "B01001_001E",
    "median_household_income": "B19013_001E",
    "median_age": "B01002_001E",
}


class Command(BaseCommand):
    """Backfill save()-derived fields on rows inserted through bulk_create."""

    help = (
        "Backfill feature_id/boundary_id/source on boundary rows and the "
        "summary columns on DemographicSnapshot rows that bulk loaders left "
        "unset (#1539); optionally drop values['NAME'] (#1550)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Count the rows that would change without writing",
        )
        parser.add_argument(
            "--only",
            choices=("features", "demographics"),
            help="Backfill only geographic feature models or only DemographicSnapshot",
        )
        parser.add_argument(
            "--strip-name",
            action="store_true",
            help="Also remove the API's NAME label from DemographicSnapshot.values",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Rows per bulk_update (default: 1000)",
        )

    def handle(self, *args, **options):
        if options["batch_size"] < 1:
            raise CommandError("--batch-size must be at least 1")
        dry_run = options["dry_run"]
        total = 0
        if options["only"] != "demographics":
            for model in self._feature_models():
                total += self._backfill_features(model, dry_run, options["batch_size"])
        if options["only"] != "features":
            total += self._backfill_snapshots(
                dry_run, options["batch_size"], options["strip_name"]
            )
        verb = "would update" if dry_run else "updated"
        self.stdout.write(self.style.SUCCESS(f"Done: {verb} {total} rows."))

    @staticmethod
    def _feature_models():
        from siege_utilities.geo.django.models.base import TemporalGeographicFeature

        return [
            model
            for model in apps.get_app_config("siege_geo").get_models()
            if issubclass(model, TemporalGeographicFeature) and not model._meta.abstract
        ]

    def _backfill_features(self, model, dry_run, batch_size):
        field_names = {field.name for field in model._meta.concrete_fields}
        update_fields = [name for name in _FEATURE_FIELDS if name in field_names]
        empty = Q()
        for name in _FEATURE_MARKERS:
            if name in field_names:
                empty |= Q(**{name: ""})
        geometry_fields = [
            field.name for field in model._meta.concrete_fields if hasattr(field, "geom_type")
        ]
        queryset = model.objects.filter(empty).defer(*geometry_fields).order_by("pk")
        return self._apply(model, queryset, update_fields, dry_run, batch_size)

    def _backfill_snapshots(self, dry_run, batch_size, strip_name):
        from siege_utilities.geo.django.models import DemographicSnapshot

        missing = Q()
        for column, variable in _SNAPSHOT_SOURCES.items():
            missing |= Q(values__has_key=variable, **{f"{column}__isnull": True})
        update_fields = list(_SNAPSHOT_SOURCES)
        if strip_name:
            missing |= Q(values__has_key="NAME")
            update_fields.append("values")
        queryset = DemographicSnapshot.objects.filter(missing).order_by("pk")

        def prepare(snapshot):
            if strip_name:
                snapshot.values.pop("NAME", None)
            return snapshot.prepare_for_bulk()

        return self._apply(
            DemographicSnapshot, queryset, update_fields, dry_run, batch_size, prepare
        )

    def _apply(self, model, queryset, update_fields, dry_run, batch_size, prepare=None):
        """Prepare each candidate row; write back (or count) only rows that changed."""
        label = model._meta.label
        has_updated_at = any(f.name == "updated_at" for f in model._meta.concrete_fields)
        fields = update_fields + (["updated_at"] if has_updated_at else [])
        now = timezone.now()
        changed = 0
        batch = []

        def flush():
            if not dry_run:
                with transaction.atomic():
                    model.objects.bulk_update(batch, fields)

        for obj in queryset.iterator(chunk_size=batch_size):
            before = [_snapshot_value(getattr(obj, name)) for name in update_fields]
            obj = prepare(obj) if prepare else obj.prepare_for_bulk()
            if [getattr(obj, name) for name in update_fields] == before:
                continue  # nothing derivable (e.g. a model with no source default)
            if has_updated_at:
                # bulk_update bypasses auto_now=True; set updated_at explicitly.
                obj.updated_at = now
            batch.append(obj)
            changed += 1
            if len(batch) >= batch_size:
                flush()
                batch = []
        if batch:
            flush()
        verb = "would be updated" if dry_run else "updated"
        self.stdout.write(f"  {label}: {changed} rows {verb}")
        return changed


def _snapshot_value(value):
    """Copy mutable values (JSON dicts) so in-place edits register as changes."""
    return dict(value) if isinstance(value, dict) else value

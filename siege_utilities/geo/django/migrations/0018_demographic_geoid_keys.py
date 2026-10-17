"""Repurpose object_id as GEOID-only storage, preserving the ORM field name.

Existing GEOID matches and GEOID-shaped orphans stay unchanged. Only canonical
integers that cannot be GEOIDs of their content type can be legacy PKs.
Unresolvable keys and duplicates fail atomically unless the operator explicitly
sets SIEGE_DEMOGRAPHIC_GEOID_ALLOW_QUARANTINE=1. With that opt-in, dedupe by newest
updated_at, then highest PK. Recovery copies include every changed/deleted row,
so reversal can restore the original data.
"""

import logging
import os
import re
from collections import Counter
from datetime import date, datetime
from decimal import Decimal

import django.core.serializers.json
from django.core.exceptions import FieldDoesNotExist
from django.db import migrations, models, transaction
from django.db.models.functions import Length


logger = logging.getLogger(__name__)
# Index/constraint builds can take minutes on warehouse tables. Retain a short
# lock wait while allowing those statements up to 30 minutes in either direction.
TRANSACTION_LIMITS = "SET LOCAL lock_timeout = '5s'; SET LOCAL statement_timeout = '30min';"
QUARANTINE_OPT_IN = "SIEGE_DEMOGRAPHIC_GEOID_ALLOW_QUARANTINE"
KEYS = {
    "DemographicSnapshot": ("content_type_id", "object_id", "dataset", "year"),
    "DemographicTimeSeries": (
        "content_type_id", "object_id", "variable_code", "dataset", "start_year", "end_year",
    ),
}


def payload(row):
    """Serialize all fields without losing datetime microseconds or decimals."""
    result = {}
    for field in row._meta.concrete_fields:
        value = getattr(row, field.attname)
        if isinstance(value, (date, datetime)):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = str(value)
        result[field.attname] = value
    return result


def resolve_key(model, value, alias, geoid_lengths):
    """Return (GEOID, reason); a None reason leaves the live row unchanged."""
    if model is None:
        return None, "unsupported_content_type"
    boundaries = model.objects.using(alias)
    # Loaders already write GEOIDs. An unrelated integer PK is never evidence
    # against an exact GEOID match within this content type.
    if boundaries.filter(geoid=value).exists():
        return value, None
    # Loaders can write a valid GEOID before its boundary has been loaded.
    # str(pk) cannot have leading zeros; matching GEOID lengths are ambiguous
    # too, so preserve those orphans without converting or quarantining them.
    if (len(value) > 1 and value[0] == "0") or len(value) in geoid_lengths:
        return value, None
    pk_geoid = None
    if re.fullmatch(r"[1-9][0-9]*", value) and 0 < int(value) <= 9223372036854775807:
        pk_geoid = boundaries.filter(pk=int(value)).values_list("geoid", flat=True).first()
    if pk_geoid is not None:
        if not pk_geoid or len(pk_geoid) > 20:
            return None, "unresolvable_key"
        return pk_geoid, "converted_pk"
    return None, "unresolvable_key"


def normalize_keys(apps, schema_editor):
    """Commit conversions/removals together, or report every removal and roll back."""
    alias = schema_editor.connection.alias
    # Keep the same guarantee for direct invocations as MigrationExecutor gives
    # the surrounding schema operations. Counts cover both demographic tables.
    with transaction.atomic(using=alias):
        summaries = _normalize_keys(apps, schema_editor)
        removals = {
            name: {reason: count for reason, count in counts.items() if reason != "converted_pk"}
            for name, counts in summaries.items()
        }
        details = "; ".join(
            f"{name}: " + ", ".join(f"{reason}={count}" for reason, count in sorted(counts.items()))
            for name, counts in removals.items() if counts
        )
        if details and os.environ.get(QUARANTINE_OPT_IN) != "1":
            raise RuntimeError(
                f"GEOID migration would remove live rows ({details}). "
                "All changes rolled back. Load missing boundaries or reconcile keys and retry; "
                f"to explicitly allow archived removals, set {QUARANTINE_OPT_IN}=1."
            )
        for name, counts in summaries.items():
            logger.warning(
                "%s GEOID migration: converted=%d quarantined=%d deduplicated=%d; "
                "recovery copies in siege_geo_demographickeyarchive",
                name, counts["converted_pk"],
                sum(count for reason, count in counts.items() if reason not in {"converted_pk", "duplicate"}),
                counts["duplicate"],
            )


def _normalize_keys(apps, schema_editor):
    alias = schema_editor.connection.alias
    archive = apps.get_model("siege_geo", "DemographicKeyArchive").objects.using(alias)
    content_types = apps.get_model("contenttypes", "ContentType").objects.using(alias)
    boundary_models = {}
    for ct in content_types.all():
        try:
            model = apps.get_model(ct.app_label, ct.model)
            model._meta.get_field("geoid")
        except (LookupError, FieldDoesNotExist):
            model = None
        boundary_models[ct.pk] = model

    # Historical models have no get_geoid_length(). Cache the observed lengths
    # once per content type, shared by snapshots and time series in this run.
    geoid_lengths = {}
    summaries = {}
    for name, key_fields in KEYS.items():
        rows = apps.get_model("siege_geo", name).objects.using(alias)
        counts = summaries[name] = Counter()
        for row in rows.order_by("pk").iterator(chunk_size=1000):
            model = boundary_models.get(row.content_type_id)
            if row.content_type_id not in geoid_lengths:
                geoid_lengths[row.content_type_id] = set(
                    model.objects.using(alias).exclude(geoid="").exclude(geoid__isnull=True)
                    .order_by().annotate(geoid_length=Length("geoid"))
                    .values_list("geoid_length", flat=True).distinct()
                ) if model is not None else set()
            geoid, reason = resolve_key(model, row.object_id, alias, geoid_lengths[row.content_type_id])
            if reason is None:
                continue
            original = payload(row)
            if geoid is None:
                archive.create(model_name=name, original_pk=row.pk, reason=reason, original_data=original)
                rows.filter(pk=row.pk).delete()
            else:
                row.object_id = geoid
                archive.create(
                    model_name=name, original_pk=row.pk, reason=reason,
                    original_data=original, migrated_data=payload(row),
                )
                rows.filter(pk=row.pk).update(object_id=geoid)
            counts[reason] += 1

        duplicates = (
            rows.order_by().values(*key_fields).annotate(n=models.Count("pk")).filter(n__gt=1)
        )
        for group in duplicates.iterator(chunk_size=1000):
            key = {field: group[field] for field in key_fields}
            ordered = rows.filter(**key).order_by("-updated_at", "-pk")
            winner = ordered.values_list("pk", flat=True).first()
            for row in ordered.exclude(pk=winner).iterator(chunk_size=1000):
                recovery, _ = archive.get_or_create(
                    model_name=name, original_pk=row.pk,
                    defaults={"reason": "duplicate", "original_data": payload(row)},
                )
                archive.filter(pk=recovery.pk).update(reason="duplicate", migrated_data=None)
                rows.filter(pk=row.pk).delete()
                counts["duplicate"] += 1
    return summaries


def restore_keys(apps, schema_editor):
    alias = schema_editor.connection.alias
    archive = apps.get_model("siege_geo", "DemographicKeyArchive").objects.using(alias)
    # Check the entire archive before writing, so rollback never silently
    # overwrites a newer edit or a reused PK. The migration is atomic as well.
    for recovery in archive.order_by("pk").iterator(chunk_size=1000):
        model = apps.get_model("siege_geo", recovery.model_name)
        current = model.objects.using(alias).filter(pk=recovery.original_pk).first()
        if (payload(current) if current else None) != recovery.migrated_data:
            raise RuntimeError(
                f"Cannot restore {recovery.model_name} pk={recovery.original_pk}: "
                "row changed after GEOID migration; reconcile the archive first."
            )
    for recovery in archive.order_by("pk").iterator(chunk_size=1000):
        model = apps.get_model("siege_geo", recovery.model_name)
        original = {
            field.attname: field.to_python(recovery.original_data[field.attname])
            for field in model._meta.concrete_fields
        }
        rows = model.objects.using(alias)
        if recovery.migrated_data is not None:
            rows.filter(pk=recovery.original_pk).update(**original)
        else:
            # bulk_create runs DateTimeField.pre_save; restore exact timestamps
            # afterward, without auto_now/auto_now_add altering the originals.
            rows.bulk_create([model(**original)])
            rows.filter(pk=recovery.original_pk).update(**original)
    # Restored inserts queue deferred content-type FK checks. Drain those
    # before the following reverse DDL reinstates the old unique constraints.
    schema_editor.execute("SET CONSTRAINTS ALL IMMEDIATE")


class Migration(migrations.Migration):

    atomic = True

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("siege_geo", "0017_cd112_geoid_format"),
    ]

    operations = [
        migrations.RunSQL(
            TRANSACTION_LIMITS, reverse_sql=TRANSACTION_LIMITS,
        ),
        migrations.CreateModel(
            name="DemographicKeyArchive",
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
                ("model_name", models.CharField(max_length=32)),
                ("original_pk", models.PositiveBigIntegerField()),
                ("reason", models.CharField(max_length=32)),
                (
                    "original_data",
                    models.JSONField(
                        encoder=django.core.serializers.json.DjangoJSONEncoder
                    ),
                ),
                (
                    "migrated_data",
                    models.JSONField(
                        encoder=django.core.serializers.json.DjangoJSONEncoder,
                        null=True,
                    ),
                ),
            ],
        ),
        migrations.AlterUniqueTogether(
            name="demographicsnapshot",
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name="demographictimeseries",
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name="demographicsnapshot",
            name="object_id",
            field=models.CharField(
                db_index=True,
                help_text="GEOID of the boundary (never its primary key)",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="demographictimeseries",
            name="object_id",
            field=models.CharField(
                db_index=True,
                help_text="GEOID of the boundary (never its primary key)",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="plandistrictassignment",
            name="boundary_object_id",
            field=models.PositiveBigIntegerField(
                help_text="PK of the boundary instance"
            ),
        ),
        migrations.RunPython(normalize_keys, restore_keys),
        migrations.AddConstraint(
            model_name="demographicsnapshot",
            constraint=models.UniqueConstraint(
                fields=("content_type", "object_id", "dataset", "year"),
                name="demographic_snapshot_geoid_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="demographictimeseries",
            constraint=models.UniqueConstraint(
                fields=(
                    "content_type",
                    "object_id",
                    "variable_code",
                    "dataset",
                    "start_year",
                    "end_year",
                ),
                name="demographic_series_geoid_unique",
            ),
        ),
        migrations.AddConstraint(
            model_name="demographickeyarchive",
            constraint=models.UniqueConstraint(
                fields=("model_name", "original_pk"),
                name="demographic_archive_row_unique",
            ),
        ),
        # Last forwards means first backwards: bound DDL waits both ways.
        migrations.RunSQL(TRANSACTION_LIMITS, reverse_sql=TRANSACTION_LIMITS),
    ]

"""Repurpose object_id as GEOID-only storage, preserving the ORM field name.

Legacy PKs are converted only when their meaning is unambiguous. Conflicting
PK/GEOID interpretations and unresolvable keys are quarantined, not guessed.
After conversion, dedupe by newest updated_at, then highest PK. Recovery copies
include every changed/deleted row, so reversal can restore the original data.
"""

import logging
import re
from datetime import date, datetime
from decimal import Decimal

import django.core.serializers.json
from django.core.exceptions import FieldDoesNotExist
from django.db import migrations, models


logger = logging.getLogger(__name__)
TRANSACTION_LIMITS = "SET LOCAL lock_timeout = '5s'; SET LOCAL statement_timeout = '60s';"
KEYS = {
    "DemographicSnapshot": ("content_type_id", "object_id", "dataset", "year"),
    "DemographicTimeSeries": (
        "content_type_id", "object_id", "variable_code", "dataset", "start_year", "end_year",
    ),
}
# These models have no GEOID regex constraint in the historical state.
UNCONSTRAINED_PATTERNS = {
    "cbsa": r"[0-9]{5}",
    "urbanarea": r"[0-9]{5}",
    "tribalarea": r"[0-9]{4}",
    "schooldistrictelementary": r"[0-9]{7}",
    "schooldistrictsecondary": r"[0-9]{7}",
    "schooldistrictunified": r"[0-9]{7}",
    # Precinct formats vary; accept an existing GEOID, otherwise quarantine.
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


def geoid_pattern(model):
    for constraint in model._meta.constraints:
        condition = getattr(constraint, "condition", None)
        if condition is not None:
            for child in condition.children:
                if isinstance(child, tuple) and child[0] == "geoid__regex":
                    return child[1]
    return UNCONSTRAINED_PATTERNS.get(model._meta.model_name)


def resolve_key(model, value, alias):
    """Return (GEOID, reason); None means preserve the row in quarantine."""
    if model is None:
        return None, "unsupported_content_type"
    boundaries = model.objects.using(alias)
    geoid_exists = boundaries.filter(geoid=value).exists()
    pk_geoid = None
    if re.fullmatch(r"[0-9]+", value) and 0 < int(value) <= 9223372036854775807:
        pk_geoid = boundaries.filter(pk=int(value)).values_list("geoid", flat=True).first()
    if geoid_exists:
        if pk_geoid is not None and pk_geoid != value:
            return None, "ambiguous_pk_and_geoid"
        return value, None
    if pk_geoid is not None:
        if not pk_geoid or len(pk_geoid) > 20:
            return None, "unresolvable_key"
        return pk_geoid, "converted_pk"
    pattern = geoid_pattern(model)
    if pattern is not None and re.fullmatch(pattern, value, flags=re.ASCII):
        # GEOID-native snapshots may precede loading their boundaries.
        return value, None
    return None, "unresolvable_key"


def normalize_keys(apps, schema_editor):
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

    for name, key_fields in KEYS.items():
        rows = apps.get_model("siege_geo", name).objects.using(alias)
        converted = quarantined = deduplicated = 0
        for row in rows.order_by("pk").iterator(chunk_size=1000):
            geoid, reason = resolve_key(boundary_models.get(row.content_type_id), row.object_id, alias)
            if reason is None:
                continue
            original = payload(row)
            if geoid is None:
                archive.create(model_name=name, original_pk=row.pk, reason=reason, original_data=original)
                rows.filter(pk=row.pk).delete()
                quarantined += 1
            else:
                row.object_id = geoid
                archive.create(
                    model_name=name, original_pk=row.pk, reason=reason,
                    original_data=original, migrated_data=payload(row),
                )
                rows.filter(pk=row.pk).update(object_id=geoid)
                converted += 1

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
                deduplicated += 1
        logger.warning(
            "%s GEOID migration: converted=%d quarantined=%d deduplicated=%d; "
            "recovery copies in siege_geo_demographickeyarchive",
            name, converted, quarantined, deduplicated,
        )


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

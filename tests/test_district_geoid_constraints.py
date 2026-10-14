"""DB-free regression coverage for TIGER district GEOID constraints."""

import re

import pytest

pytest.importorskip("django", reason="Install siege-utilities[geodjango] to run model tests.")
from django.core.exceptions import ImproperlyConfigured

try:
    from django.contrib.gis.db import models as gis_models  # noqa: F401
except (ImportError, ImproperlyConfigured, OSError):
    pytest.skip(
        "Install GDAL/GEOS and configure GDAL_LIBRARY_PATH/GEOS_LIBRARY_PATH to run model tests.",
        allow_module_level=True,
    )

from siege_utilities.geo.django.models import (
    CongressionalDistrict,
    StateLegislativeLower,
    StateLegislativeUpper,
)


@pytest.mark.parametrize(
    "model,geoid",
    [
        (CongressionalDistrict, "2601"),
        (CongressionalDistrict, "2600"),
        (CongressionalDistrict, "26ZZ"),
        (StateLegislativeUpper, "06001"),
        (StateLegislativeUpper, "0200A"),
        (StateLegislativeUpper, "09ZZZ"),
        (StateLegislativeUpper, "501-1"),
        (StateLegislativeLower, "06001"),
        (StateLegislativeLower, "2701A"),
        (StateLegislativeLower, "2701B"),
        (StateLegislativeLower, "09ZZZ"),
        (StateLegislativeLower, "501-1"),
    ],
)
def test_district_geoid_constraint_accepts_tiger_codes(model, geoid):
    pattern = _geoid_pattern(model)
    assert re.fullmatch(pattern, geoid), (model.__name__, pattern, geoid)


@pytest.mark.parametrize(
    "model,geoid",
    [
        (CongressionalDistrict, "26zz"),
        (StateLegislativeUpper, "0200a"),
        (StateLegislativeLower, "2701a"),
    ],
)
def test_district_geoid_constraint_accepts_lowercase_codes(model, geoid):
    """Uppercase examples do not establish a Census letter-case restriction."""
    assert re.fullmatch(_geoid_pattern(model), geoid)


@pytest.mark.parametrize(
    "model,geoid",
    [
        (CongressionalDistrict, "260"),
        (CongressionalDistrict, "26001"),
        (CongressionalDistrict, "2AZZ"),
        (CongressionalDistrict, "261-"),
        (CongressionalDistrict, "26_1"),
        (StateLegislativeUpper, "020A"),
        (StateLegislativeUpper, "02000A"),
        (StateLegislativeUpper, "0A00A"),
        (StateLegislativeUpper, "020_A"),
        (StateLegislativeLower, "271A"),
        (StateLegislativeLower, "27001A"),
        (StateLegislativeLower, "2A01A"),
        (StateLegislativeLower, "2701!"),
    ],
)
def test_district_geoid_constraint_rejects_invalid_shape(model, geoid):
    assert re.fullmatch(_geoid_pattern(model), geoid) is None


def _geoid_pattern(model):
    patterns = [
        value
        for constraint in model._meta.constraints
        for lookup, value in constraint.condition.children
        if lookup == "geoid__regex"
    ]
    assert len(patterns) == 1
    return patterns[0]


@pytest.mark.parametrize(
    "model", [CongressionalDistrict, StateLegislativeUpper, StateLegislativeLower]
)
def test_district_migration_state_matches_model(model):
    from django.db.migrations.loader import MigrationLoader

    loader = MigrationLoader(None)
    state = loader.project_state(loader.graph.leaf_nodes("siege_geo"))
    constraints = state.models["siege_geo", model._meta.model_name].options["constraints"]
    assert constraints == model._meta.constraints


@pytest.mark.parametrize("direction", ["apply", "unapply"])
def test_district_migration_validates_after_constraint_swap(direction):
    from django.db import connection
    from django.db.migrations.loader import MigrationLoader

    loader = MigrationLoader(None)
    migration = loader.disk_migrations["siege_geo", "0014_district_geoid_charclass"]
    state = loader.project_state(migration.dependencies)
    assert migration.atomic is False
    with connection.schema_editor(collect_sql=True, atomic=False) as editor:
        getattr(migration, direction)(state, editor)

    assert len(editor.collected_sql) == 6
    models = [CongressionalDistrict, StateLegislativeUpper, StateLegislativeLower]
    old_names = ["cd_geoid_4_digits", "sldu_geoid_5_digits", "sldl_geoid_5_digits"]
    expected = list(zip(models, old_names))
    if direction == "unapply":
        expected.reverse()
    for offset, (model, old_name) in enumerate(expected):
        new_name = model._meta.constraints[0].name
        removed, added = (old_name, new_name) if direction == "apply" else (new_name, old_name)
        pattern = _geoid_pattern(model) if direction == "apply" else (
            r"^\d{4}$" if model is CongressionalDistrict else r"^\d{5}$"
        )
        swap, validate = editor.collected_sql[2 * offset:2 * offset + 2]
        assert f'ALTER TABLE "{model._meta.db_table}"' in swap
        assert f'DROP CONSTRAINT IF EXISTS "{removed}"' in swap
        assert f'DROP CONSTRAINT IF EXISTS "{added}"' in swap
        assert f'ADD CONSTRAINT "{added}"' in swap
        assert f'CHECK ("geoid" ~ \'{pattern}\') NOT VALID' in swap
        assert validate == (
            f'ALTER TABLE "{model._meta.db_table}" VALIDATE CONSTRAINT "{added}";'
        )

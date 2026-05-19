"""Regression test for SU#519: unity_catalog module is a deprecation
shim that re-exports the lakehouse_federation symbols and emits a
DeprecationWarning naming the new module path.

Behavior tests — no pytest.mark.databricks because the shim is pure
Python with no Databricks SDK calls.
"""

import importlib
import sys
import warnings


def _fresh_import(name):
    """Drop the module from sys.modules and re-import so the
    module-level DeprecationWarning fires under our catch_warnings."""
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def test_shim_emits_deprecation_warning_naming_su519():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _fresh_import("siege_utilities.databricks.unity_catalog")
    deps = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert deps, f"expected DeprecationWarning, got {[w.message for w in caught]}"
    msg = str(deps[0].message)
    assert "lakehouse_federation" in msg
    assert "SU#519" in msg


def test_shim_reexports_are_identity_equal_to_canonical():
    # Re-import freshly so the shim runs against a clean lakehouse_federation.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        sys.modules.pop("siege_utilities.databricks.unity_catalog", None)
        from siege_utilities.databricks import lakehouse_federation as canon
        from siege_utilities.databricks import unity_catalog as shim
    assert shim.build_foreign_table_sql is canon.build_foreign_table_sql
    assert shim.build_schema_and_table_sync_sql is canon.build_schema_and_table_sync_sql
    assert shim.quote_ident is canon.quote_ident


def test_package_import_does_not_emit_deprecation_warning():
    # `import siege_utilities.databricks` should resolve through
    # __init__.py without touching the shim.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sys.modules.pop("siege_utilities.databricks", None)
        importlib.import_module("siege_utilities.databricks")
    deps = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    su519_deps = [w for w in deps if "SU#519" in str(w.message)]
    assert not su519_deps, (
        f"package-level import unexpectedly triggered SU#519 shim warning: "
        f"{[str(w.message) for w in su519_deps]}"
    )


def test_lakehouse_federation_sql_unchanged():
    # Sanity: the SQL output post-rename is identical to the
    # documented pre-rename output.
    from siege_utilities.databricks.lakehouse_federation import (
        build_foreign_table_sql,
    )
    sql = build_foreign_table_sql(
        catalog="enterprise_dw_psql",
        schema="enterprise_dw",
        table="persons",
        connection_name="db_postgis_enterprise",
        source_schema="enterprise_dw",
    )
    assert "CREATE FOREIGN TABLE IF NOT EXISTS" in sql
    assert "`enterprise_dw_psql`.`enterprise_dw`.`persons`" in sql
    assert "USING CONNECTION `db_postgis_enterprise`" in sql
    assert "OPTIONS (table 'enterprise_dw.persons');" in sql

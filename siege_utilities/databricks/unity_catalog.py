"""Deprecated alias for :mod:`siege_utilities.databricks.lakehouse_federation`.

The helpers in this module generate ``CREATE FOREIGN TABLE ... USING
CONNECTION`` SQL, which is a Databricks Lakehouse Federation feature.
It does NOT work against the open-source Unity Catalog implementation
(unitycatalog.io). The old module name implied otherwise and burned
consumers planning OSS UC bridges. Renamed in SU#519.

Import from :mod:`siege_utilities.databricks.lakehouse_federation`
instead. This shim re-exports the public surface unchanged; importing
this module emits a single :class:`DeprecationWarning`.
"""

import warnings

from siege_utilities.databricks.lakehouse_federation import (  # noqa: F401
    build_foreign_table_sql,
    build_schema_and_table_sync_sql,
    quote_ident,
)

warnings.warn(
    "siege_utilities.databricks.unity_catalog is deprecated; "
    "import from siege_utilities.databricks.lakehouse_federation instead. "
    "The generated SQL is Databricks Lakehouse Federation only and does "
    "not work against OSS unitycatalog.io. (SU#519)",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "build_foreign_table_sql",
    "build_schema_and_table_sync_sql",
    "quote_ident",
]

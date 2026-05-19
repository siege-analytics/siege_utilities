"""Trino-dialect SQL helpers.

Trino is the OSS query engine commonly paired with the open-source
unitycatalog.io implementation when callers need live federation to a
foreign RDBMS — OSS UC itself has no native federation primitive (see
SU#519 / SU#521).

The first surface here is :mod:`siege_utilities.trino.federation`,
which generates ``CREATE VIEW`` statements that select through Trino's
``postgresql`` connector. This is the OSS analog of
:mod:`siege_utilities.databricks.lakehouse_federation` for the Databricks
Lakehouse Federation use case.
"""

from .federation import (
    build_trino_federation_view_sql,
    build_trino_schema_and_view_sync_sql,
    quote_ident,
)

__all__ = [
    "build_trino_federation_view_sql",
    "build_trino_schema_and_view_sync_sql",
    "quote_ident",
]

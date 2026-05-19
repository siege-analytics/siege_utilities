"""Helpers for the open-source Unity Catalog implementation (unitycatalog.io).

OSS Unity Catalog is the open-source reference catalog server published
at https://github.com/unitycatalog/unitycatalog (Docker image
``unitycatalog/unitycatalog``). It exposes a REST API for catalog /
schema / table metadata management. Unlike Databricks-managed Unity
Catalog it has no native query federation primitive — for live
federation to a foreign RDBMS see :mod:`siege_utilities.trino.federation`.

This package's first surface is
:mod:`siege_utilities.oss_unity_catalog.external_tables`, which
generates payloads for (and optionally POSTs) external table
registrations against the OSS UC REST endpoint
``POST /api/2.1/unity-catalog/tables``.

Filed under SU#521 (umbrella) following the SU#519 rename of the
Databricks-only helper.
"""

from .external_tables import (
    SUPPORTED_DATA_SOURCE_FORMATS,
    build_external_table_payload,
    register_external_table,
)

__all__ = [
    "SUPPORTED_DATA_SOURCE_FORMATS",
    "build_external_table_payload",
    "register_external_table",
]

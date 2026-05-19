"""External-table registration helpers for OSS Unity Catalog.

Generates payloads for (and optionally POSTs) external-table creation
against the OSS UC REST API endpoint
``POST /api/2.1/unity-catalog/tables``. Pure metadata: tells OSS UC
"a table named X exists at storage_location Y in format Z with these
columns." Readers (Spark, Trino, DuckDB) connect to UC, look up the
location, and read the files directly. No query federation is
involved — for live federation to a foreign RDBMS see
:mod:`siege_utilities.trino.federation`.

The payload builder is the load-bearing part — it is mock-friendly and
can be used standalone with any HTTP client. The thin
:func:`register_external_table` helper exists for the common case where
the caller wants a one-line ``requests.post`` against an OSS UC server.

See SU#521 (umbrella) and SU#519 (root context).
"""

from __future__ import annotations

from typing import Any, Mapping

import requests

from siege_utilities.core.sql_safety import validate_sql_identifier

# OSS UC v0.4.0 supported data source formats (from the proto schema).
# Update this set when OSS UC adds formats. Keys are upper-case because
# OSS UC's REST API requires upper-case format names.
SUPPORTED_DATA_SOURCE_FORMATS: frozenset[str] = frozenset({
    "DELTA",
    "PARQUET",
    "CSV",
    "JSON",
    "AVRO",
    "ORC",
    "TEXT",
})


def _validate_column(column: Mapping[str, Any], index: int) -> dict[str, Any]:
    """Validate one element of the columns list and return a clean dict.

    Required keys: ``name``, ``type_name``. Optional: ``type_text``,
    ``type_json``, ``nullable``, ``comment``, ``position``,
    ``partition_index``.
    """
    if not isinstance(column, Mapping):
        raise TypeError(
            f"columns[{index}] must be a Mapping; got {type(column).__name__}"
        )
    name = column.get("name")
    type_name = column.get("type_name")
    if not isinstance(name, str) or not name:
        raise ValueError(f"columns[{index}].name must be a non-empty string")
    if not isinstance(type_name, str) or not type_name:
        raise ValueError(f"columns[{index}].type_name must be a non-empty string")
    validate_sql_identifier(name, f"columns[{index}].name")

    cleaned: dict[str, Any] = {
        "name": name,
        "type_name": type_name,
        "nullable": bool(column.get("nullable", True)),
        "position": int(column.get("position", index)),
    }
    for optional_key in ("type_text", "type_json", "comment", "partition_index"):
        if optional_key in column and column[optional_key] is not None:
            cleaned[optional_key] = column[optional_key]
    return cleaned


def build_external_table_payload(
    catalog: str,
    schema: str,
    name: str,
    storage_location: str,
    data_source_format: str,
    columns: list[Mapping[str, Any]],
    *,
    properties: Mapping[str, str] | None = None,
    comment: str | None = None,
) -> dict[str, Any]:
    """Build the JSON payload for ``POST /api/2.1/unity-catalog/tables``.

    Args:
        catalog: Existing OSS UC catalog name.
        schema: Existing OSS UC schema within ``catalog``.
        name: Table name to create.
        storage_location: Absolute URI to the data location (e.g.
            ``"s3://bucket/path/persons"`` or ``"file:///srv/uc/data/persons"``).
        data_source_format: One of :data:`SUPPORTED_DATA_SOURCE_FORMATS`.
            Case-insensitive on input; normalized to upper case in the
            payload.
        columns: Ordered list of column specs. Each entry must be a
            Mapping with ``name`` (str) and ``type_name`` (str — one of
            OSS UC's typed column names like ``LONG``, ``STRING``,
            ``DOUBLE``). Optional per-column: ``type_text``, ``type_json``,
            ``nullable`` (default True), ``comment``, ``partition_index``.
            ``position`` defaults to the column's index in the list.
        properties: Optional table properties (key/value strings).
        comment: Optional human-readable table description.

    Returns:
        Plain dict ready to be passed to ``requests.post(..., json=payload)``.

    Raises:
        ValueError: identifier failed allow-list, format unsupported,
            or a column spec is malformed.
        TypeError: a column entry is not a Mapping.
    """
    validate_sql_identifier(catalog, "catalog")
    validate_sql_identifier(schema, "schema")
    validate_sql_identifier(name, "name")

    fmt = data_source_format.upper()
    if fmt not in SUPPORTED_DATA_SOURCE_FORMATS:
        raise ValueError(
            f"data_source_format={data_source_format!r} not in "
            f"{sorted(SUPPORTED_DATA_SOURCE_FORMATS)}"
        )

    if not isinstance(storage_location, str) or not storage_location:
        raise ValueError("storage_location must be a non-empty string")

    if not isinstance(columns, list) or not columns:
        raise ValueError("columns must be a non-empty list")

    cleaned_columns = [_validate_column(c, i) for i, c in enumerate(columns)]

    payload: dict[str, Any] = {
        "name": name,
        "catalog_name": catalog,
        "schema_name": schema,
        "table_type": "EXTERNAL",
        "data_source_format": fmt,
        "storage_location": storage_location,
        "columns": cleaned_columns,
    }
    if properties:
        payload["properties"] = dict(properties)
    if comment is not None:
        payload["comment"] = comment
    return payload


def register_external_table(
    uc_base_url: str,
    payload: Mapping[str, Any],
    *,
    auth_token: str | None = None,
    timeout: float = 30.0,
    session: requests.Session | None = None,
) -> dict[str, Any]:
    """POST ``payload`` to ``{uc_base_url}/api/2.1/unity-catalog/tables``.

    Thin convenience wrapper around :func:`requests.post`. Use this
    when you have the payload from :func:`build_external_table_payload`
    and want the one-call shape. Callers who prefer to manage their own
    HTTP client (retry policies, mTLS, proxies, etc.) should build the
    payload with :func:`build_external_table_payload` and POST it
    themselves.

    Args:
        uc_base_url: Base URL of the OSS UC server (e.g.
            ``"http://uc.internal:8080"``). Trailing slashes are
            tolerated.
        payload: A dict in the shape produced by
            :func:`build_external_table_payload`.
        auth_token: Optional bearer token. When set, sent as
            ``Authorization: Bearer <token>``.
        timeout: Per-request timeout in seconds.
        session: Optional :class:`requests.Session`. Useful for
            connection pooling across many registrations.

    Returns:
        Parsed JSON response from the server.

    Raises:
        requests.HTTPError: non-2xx response (via ``raise_for_status``).
    """
    url = uc_base_url.rstrip("/") + "/api/2.1/unity-catalog/tables"
    headers = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    poster = session.post if session is not None else requests.post
    response = poster(url, json=dict(payload), headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()

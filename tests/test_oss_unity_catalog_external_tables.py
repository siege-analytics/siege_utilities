"""Tests for siege_utilities.oss_unity_catalog.external_tables (SU#521 Shape A).

OSS UC external-table registration payload builder + REST helper.
Pure-payload tests run with no network; the REST helper test uses a
MagicMock session so no socket is opened.
"""

from unittest.mock import MagicMock

import pytest
import requests

from siege_utilities.oss_unity_catalog import (
    SUPPORTED_DATA_SOURCE_FORMATS,
    build_external_table_payload,
    register_external_table,
)


# ---- Payload builder --------------------------------------------------------


def _minimal_columns():
    return [
        {"name": "id", "type_name": "LONG"},
        {"name": "name", "type_name": "STRING", "nullable": False, "comment": "label"},
    ]


def test_payload_shape_minimal():
    payload = build_external_table_payload(
        catalog="main",
        schema="default",
        name="persons",
        storage_location="s3://bucket/path/persons",
        data_source_format="DELTA",
        columns=_minimal_columns(),
    )
    assert payload["name"] == "persons"
    assert payload["catalog_name"] == "main"
    assert payload["schema_name"] == "default"
    assert payload["table_type"] == "EXTERNAL"
    assert payload["data_source_format"] == "DELTA"
    assert payload["storage_location"] == "s3://bucket/path/persons"
    assert len(payload["columns"]) == 2
    assert payload["columns"][0]["name"] == "id"
    assert payload["columns"][0]["position"] == 0
    assert payload["columns"][0]["nullable"] is True
    assert payload["columns"][1]["nullable"] is False
    assert payload["columns"][1]["comment"] == "label"
    assert "properties" not in payload
    assert "comment" not in payload


def test_payload_includes_optional_properties_and_comment():
    payload = build_external_table_payload(
        catalog="main",
        schema="default",
        name="persons",
        storage_location="file:///srv/uc/data/persons",
        data_source_format="parquet",  # lower-case allowed, normalized
        columns=_minimal_columns(),
        properties={"owner": "alice", "freshness_sla": "P1D"},
        comment="Person registry",
    )
    assert payload["data_source_format"] == "PARQUET"
    assert payload["properties"] == {"owner": "alice", "freshness_sla": "P1D"}
    assert payload["comment"] == "Person registry"


@pytest.mark.parametrize("fmt", sorted(SUPPORTED_DATA_SOURCE_FORMATS))
def test_payload_accepts_every_supported_format(fmt):
    payload = build_external_table_payload(
        catalog="main",
        schema="default",
        name="t",
        storage_location="s3://b/p",
        data_source_format=fmt,
        columns=_minimal_columns(),
    )
    assert payload["data_source_format"] == fmt


def test_payload_rejects_unsupported_format():
    with pytest.raises(ValueError, match="data_source_format"):
        build_external_table_payload(
            catalog="main",
            schema="default",
            name="t",
            storage_location="s3://b/p",
            data_source_format="HUDI",  # not yet supported by OSS UC
            columns=_minimal_columns(),
        )


def test_payload_rejects_identifier_injection():
    with pytest.raises(ValueError, match="catalog"):
        build_external_table_payload(
            catalog="main; DROP TABLE x; --",
            schema="default",
            name="t",
            storage_location="s3://b/p",
            data_source_format="DELTA",
            columns=_minimal_columns(),
        )
    with pytest.raises(ValueError, match="schema"):
        build_external_table_payload(
            catalog="main",
            schema='evil"--',
            name="t",
            storage_location="s3://b/p",
            data_source_format="DELTA",
            columns=_minimal_columns(),
        )
    with pytest.raises(ValueError, match="name"):
        build_external_table_payload(
            catalog="main",
            schema="default",
            name="t; DROP",
            storage_location="s3://b/p",
            data_source_format="DELTA",
            columns=_minimal_columns(),
        )


def test_payload_rejects_empty_columns():
    with pytest.raises(ValueError, match="columns"):
        build_external_table_payload(
            catalog="main",
            schema="default",
            name="t",
            storage_location="s3://b/p",
            data_source_format="DELTA",
            columns=[],
        )


def test_payload_rejects_column_without_name():
    with pytest.raises(ValueError, match=r"columns\[0\]\.name"):
        build_external_table_payload(
            catalog="main",
            schema="default",
            name="t",
            storage_location="s3://b/p",
            data_source_format="DELTA",
            columns=[{"type_name": "LONG"}],
        )


def test_payload_rejects_column_with_bad_identifier_name():
    with pytest.raises(ValueError, match=r"columns\[0\]\.name"):
        build_external_table_payload(
            catalog="main",
            schema="default",
            name="t",
            storage_location="s3://b/p",
            data_source_format="DELTA",
            columns=[{"name": "id-1", "type_name": "LONG"}],  # hyphen rejected
        )


def test_payload_rejects_non_mapping_column_entry():
    with pytest.raises(TypeError, match=r"columns\[0\]"):
        build_external_table_payload(
            catalog="main",
            schema="default",
            name="t",
            storage_location="s3://b/p",
            data_source_format="DELTA",
            columns=["not a dict"],  # type: ignore[list-item]
        )


def test_payload_rejects_empty_storage_location():
    with pytest.raises(ValueError, match="storage_location"):
        build_external_table_payload(
            catalog="main",
            schema="default",
            name="t",
            storage_location="",
            data_source_format="DELTA",
            columns=_minimal_columns(),
        )


def test_payload_column_position_overrides_index_when_provided():
    payload = build_external_table_payload(
        catalog="main",
        schema="default",
        name="t",
        storage_location="s3://b/p",
        data_source_format="DELTA",
        columns=[
            {"name": "id", "type_name": "LONG", "position": 5},
            {"name": "name", "type_name": "STRING"},
        ],
    )
    assert payload["columns"][0]["position"] == 5  # explicit override
    assert payload["columns"][1]["position"] == 1  # index fallback


# ---- REST helper (mocked) ---------------------------------------------------


def test_register_external_table_posts_to_canonical_url_and_strips_trailing_slash():
    session = MagicMock(spec=requests.Session)
    response = MagicMock()
    response.json.return_value = {"name": "persons", "table_id": "abc-123"}
    response.raise_for_status.return_value = None
    session.post.return_value = response

    payload = {"name": "persons", "catalog_name": "main"}
    result = register_external_table(
        uc_base_url="http://uc.internal:8080/",  # trailing slash should be stripped
        payload=payload,
        session=session,
    )

    assert result == {"name": "persons", "table_id": "abc-123"}
    session.post.assert_called_once()
    args, kwargs = session.post.call_args
    assert args[0] == "http://uc.internal:8080/api/2.1/unity-catalog/tables"
    assert kwargs["json"] == payload
    assert kwargs["headers"]["Content-Type"] == "application/json"
    assert "Authorization" not in kwargs["headers"]  # no token, no header
    assert kwargs["timeout"] == 30.0


def test_register_external_table_sets_bearer_auth_when_token_given():
    session = MagicMock(spec=requests.Session)
    response = MagicMock()
    response.json.return_value = {}
    response.raise_for_status.return_value = None
    session.post.return_value = response

    register_external_table(
        uc_base_url="http://uc.internal:8080",
        payload={},
        auth_token="placeholder-token-not-a-real-secret",
        session=session,
    )

    _, kwargs = session.post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer placeholder-token-not-a-real-secret"


def test_register_external_table_raises_on_http_error():
    session = MagicMock(spec=requests.Session)
    response = MagicMock()
    response.raise_for_status.side_effect = requests.HTTPError("409 Conflict")
    session.post.return_value = response

    with pytest.raises(requests.HTTPError, match="Conflict"):
        register_external_table(
            uc_base_url="http://uc.internal:8080",
            payload={},
            session=session,
        )

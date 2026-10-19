"""Shared CRM field conversion contract for upsert payloads."""

import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from siege_utilities.connectors._protocol import ConnectorError, sanitize_record


@pytest.mark.parametrize("missing", [
    None, float("nan"), pd.NaT, pd.NA, np.float32("nan"), np.datetime64("NaT"),
])
def test_missing_fields_are_omitted_without_clearing_existing_values(missing):
    row = {"missing": missing, "zero": 0, "false": False, "empty": ""}

    result = sanitize_record(row)

    assert result == {"zero": 0, "false": False, "empty": ""}
    assert row["missing"] is missing
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize(("value", "expected"), [
    (pd.Timestamp("2026-10-18T12:34:56.123456789Z"), "2026-10-18T12:34:56.123456789+00:00"),
    (pd.Timestamp("2026-10-18"), "2026-10-18T00:00:00"),
    (datetime(2026, 10, 18, 12, 34, tzinfo=timezone.utc), "2026-10-18T12:34:00+00:00"),
    (date(2026, 10, 18), "2026-10-18"),
    (np.int64(42), 42),
    (np.uint64(2**63), 2**63),
    (np.float32(1.5), 1.5),
    (np.float64(2.5), 2.5),
    (np.bool_(True), True),
    (np.bool_(False), False),
    ("unchanged", "unchanged"),
    (42, 42),
    (1.5, 1.5),
    (True, True),
    (Decimal("12.50"), "12.50"),
    (b"bytes", "b'bytes'"),
    (float("inf"), "inf"),
    (float("-inf"), "-inf"),
])
def test_values_become_json_safe_native_types(value, expected):
    result = sanitize_record({"value": value})

    assert result == {"value": expected}
    assert type(result["value"]) is type(expected)
    assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_json_containers_are_preserved_and_nested_dates_use_iso8601():
    row = {
        "list": [1, None, "text"],
        "dict": {"active": False},
        "nested": {"date": date(2026, 10, 18)},
    }

    result = sanitize_record(row)

    assert result["list"] == [1, None, "text"]
    assert result["dict"] == {"active": False}
    assert result["nested"] == {"date": "2026-10-18"}
    assert row["nested"] == {"date": date(2026, 10, 18)}
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("missing", [
    None, float("nan"), pd.NaT, pd.NA, np.float32("nan"), np.datetime64("NaT"),
])
def test_nested_missing_values_omit_dict_children_and_preserve_list_positions(missing):
    child = {"missing": missing, "zero": np.int64(0), "false": np.bool_(False)}
    row = {"nested": [missing, {"child": child}, [missing, "last"]]}

    result = sanitize_record(row)

    assert result == {"nested": [None, {"child": {"zero": 0, "false": False}}, [None, "last"]]}
    assert type(result["nested"][1]["child"]["zero"]) is int
    assert result["nested"][1]["child"]["false"] is False
    assert child["missing"] is missing
    assert row["nested"][0] is missing
    json.dumps(result, allow_nan=False)


def test_nested_scalar_fallback_and_shared_containers():
    child = {"amount": Decimal("12.50"), "limit": float("inf")}
    row = {"left": child, "right": [child, (np.int64(7), pd.NaT)]}

    result = sanitize_record(row)

    expected = {"amount": "12.50", "limit": "inf"}
    assert result == {"left": expected, "right": [expected, [7, None]]}
    assert child == {"amount": Decimal("12.50"), "limit": float("inf")}
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("value", [{1, 2}, frozenset({1, 2}), np.array([1, 2])])
def test_unsupported_containers_raise_a_clear_error(value):
    with pytest.raises(ConnectorError, match="Unsupported.*container.*nested"):
        sanitize_record({"nested": {"value": value}})


@pytest.mark.parametrize("container", [{}, []])
def test_circular_containers_raise_a_clear_error(container):
    if isinstance(container, dict):
        container["self"] = container
    else:
        container.append(container)

    with pytest.raises(ConnectorError, match="Circular.*nested"):
        sanitize_record({"nested": container})


@pytest.mark.parametrize("key", [("invalid",), float("nan"), float("inf")])
def test_unsupported_dict_keys_raise_a_clear_error(key):
    with pytest.raises(ConnectorError, match="JSON object key.*nested"):
        sanitize_record({"nested": {key: "value"}})


def test_deeply_nested_values_preserve_structure_and_leaf_types():
    nested = np.int64(7)
    for _ in range(50):
        nested = [{"child": nested}]

    result = sanitize_record({"nested": nested})

    json.dumps(result, allow_nan=False)
    child = result["nested"]
    for _ in range(50):
        assert isinstance(child, list)
        assert isinstance(child[0], dict)
        child = child[0]["child"]
    assert child == 7
    assert type(child) is int


def test_excessive_nesting_raises_a_clear_error():
    nested = 7
    for _ in range(sys.getrecursionlimit() + 10):
        nested = [nested]

    with pytest.raises(ConnectorError, match="nesting.*recursion limit"):
        sanitize_record({"nested": nested})

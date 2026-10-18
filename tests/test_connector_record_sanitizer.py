"""Shared CRM field conversion contract for upsert payloads."""

import json
from datetime import date, datetime, timezone
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from siege_utilities.connectors._protocol import sanitize_record


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


def test_json_containers_are_preserved_and_unsupported_values_use_string_fallback():
    row = {
        "list": [1, None, "text"],
        "dict": {"active": False},
        "array": np.array([1, 2]),
        "unsupported_nested": {"date": date(2026, 10, 18)},
    }

    result = sanitize_record(row)

    assert result["list"] is row["list"]
    assert result["dict"] is row["dict"]
    assert result["array"] == str(row["array"])
    assert result["unsupported_nested"] == str(row["unsupported_nested"])
    json.dumps(result, allow_nan=False)

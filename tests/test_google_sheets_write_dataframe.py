"""Request-level regressions for DataFrame writes to Google Sheets (#1432)."""

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, call

import pytest

from siege_utilities.analytics.google_sheets import write_dataframe

pd = pytest.importorskip("pandas")
np = pytest.importorskip("numpy")


@pytest.fixture
def sheets_client():
    """Mock the service and enforce the real client's JSON serialization boundary."""
    client = Mock()
    values_api = client.sheets_service.return_value.spreadsheets.return_value.values.return_value
    values_api.update.return_value.execute.return_value = {"updatedCells": 4}

    def serialize_update(**kwargs):
        json.dumps(kwargs["body"], allow_nan=False)
        return values_api.update.return_value

    values_api.update.side_effect = serialize_update
    return client, values_api


@pytest.mark.parametrize("literal", ["007", "=1+1"])
@pytest.mark.parametrize("include_header", [True, False])
def test_strings_and_headers_are_written_verbatim(sheets_client, literal, include_header):
    client, values_api = sheets_client
    df = pd.DataFrame({literal: [literal], 42: [True]}, index=["not a cell"])

    result = write_dataframe(client, "ss_123", df, include_header=include_header)

    expected = [[literal, True]]
    if include_header:
        expected.insert(0, [literal, "42"])
    kwargs = values_api.update.call_args.kwargs
    assert kwargs["body"] == {"values": expected}
    assert kwargs["valueInputOption"] == "RAW"
    assert result == {"updatedCells": 4}


@pytest.mark.parametrize(
    "column, expected",
    [
        (pd.Series(pd.to_datetime(["2026-01-02 03:04:05"])), "2026-01-02T03:04:05"),
        (pd.Series([datetime(2026, 1, 2, 3, 4, 5)], dtype=object), "2026-01-02T03:04:05"),
        (pd.Series([date(2026, 1, 2)], dtype=object), "2026-01-02"),
        (
            pd.Series([pd.Timestamp(datetime(2026, 1, 2, tzinfo=timezone.utc))]),
            "2026-01-02T00:00:00+00:00",
        ),
    ],
    ids=["datetime64", "datetime", "date", "timestamp-with-timezone"],
)
def test_dates_are_json_serializable_iso_strings(sheets_client, column, expected):
    client, values_api = sheets_client

    write_dataframe(client, "ss_123", pd.DataFrame({"when": column}))

    assert values_api.update.call_args.kwargs["body"] == {"values": [["when"], [expected]]}


def test_numeric_columns_preserve_native_types_and_integer_precision(sheets_client):
    client, values_api = sheets_client
    df = pd.DataFrame({
        "id": np.array([9007199254740993], dtype=np.int64),
        "share": np.array([0.5], dtype=np.float64),
    })

    write_dataframe(client, "ss_123", df)

    row = values_api.update.call_args.kwargs["body"]["values"][1]
    assert row == [9007199254740993, 0.5]
    assert [type(value) for value in row] == [int, float]


def test_numpy_object_scalars_become_native_scalars(sheets_client):
    client, values_api = sheets_client
    df = pd.DataFrame({
        "value": pd.Series([np.int64(7), np.float32(0.5), np.float64(0.25), np.bool_(True)], dtype=object),
    })

    write_dataframe(client, "ss_123", df, include_header=False)

    rows = values_api.update.call_args.kwargs["body"]["values"]
    assert rows == [[7], [0.5], [0.25], [True]]
    assert [type(row[0]) for row in rows] == [int, float, float, bool]


def test_missing_values_are_empty_strings_in_raw_payload(sheets_client):
    client, values_api = sheets_client
    df = pd.DataFrame({
        "number": [float("nan")],
        "when": pd.to_datetime([None]),
        "object": [None],
        "nullable": pd.Series([pd.NA], dtype="Int64"),
    })

    write_dataframe(client, "ss_123", df, include_header=False)

    kwargs = values_api.update.call_args.kwargs
    assert kwargs["body"] == {"values": [["", "", "", ""]]}
    assert kwargs["valueInputOption"] == "RAW"


@pytest.mark.parametrize(
    "value", [Decimal("12.50"), [1, 2], {"a": 1}, np.array([1, 2])],
    ids=["decimal", "list", "dict", "array"],
)
def test_other_objects_are_stringified_as_single_cells(sheets_client, value):
    client, values_api = sheets_client
    df = pd.DataFrame({"value": pd.Series([value], dtype=object)})

    write_dataframe(client, "ss_123", df, include_header=False)

    assert values_api.update.call_args.kwargs["body"] == {"values": [[str(value)]]}


@pytest.mark.parametrize(
    "sheet_name, quoted_name",
    [("Sheet1", "'Sheet1'"), ("Monthly Data", "'Monthly Data'"),
     ("Owner's Data!", "'Owner''s Data!'"), ("A1", "'A1'")],
)
def test_entire_target_tab_is_cleared_before_update(sheets_client, sheet_name, quoted_name):
    client, values_api = sheets_client

    write_dataframe(client, "ss_123", pd.DataFrame({"id": [7]}), sheet_name=sheet_name, start_cell="C4")

    # Clear the entire named tab, including old data outside the new footprint.
    assert values_api.mock_calls == [
        call.clear(spreadsheetId="ss_123", range=quoted_name, body={}),
        call.clear().execute(),
        call.update(
            spreadsheetId="ss_123", range=f"{quoted_name}!C4",
            valueInputOption="RAW", body={"values": [["id"], [7]]},
        ),
        call.update().execute(),
    ]


def test_clear_failure_prevents_update(sheets_client):
    client, values_api = sheets_client
    values_api.clear.return_value.execute.side_effect = RuntimeError("Clear failed")

    with pytest.raises(RuntimeError, match="Clear failed"):
        write_dataframe(client, "ss_123", pd.DataFrame({"id": [7]}))

    values_api.update.assert_not_called()


@pytest.mark.parametrize("include_header", [True, False])
def test_empty_dataframe_still_clears_previous_values(sheets_client, include_header):
    client, values_api = sheets_client

    write_dataframe(client, "ss_123", pd.DataFrame(columns=["id"]), include_header=include_header)

    values_api.clear.assert_called_once_with(spreadsheetId="ss_123", range="'Sheet1'", body={})
    expected = [["id"]] if include_header else []
    assert values_api.update.call_args.kwargs["body"] == {"values": expected}

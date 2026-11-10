"""Ragged-sheet regressions for read_dataframe (#1432 item 4)."""

from unittest.mock import Mock

import pytest

from siege_utilities.analytics.google_sheets import read_dataframe

pd = pytest.importorskip("pandas")


def _client_returning(values):
    """Mock only the Sheets service; read_values and read_dataframe run for real."""
    client = Mock()
    values_api = client.sheets_service.return_value.spreadsheets.return_value.values.return_value
    values_api.get.return_value.execute.return_value = {"values": values}
    return client


def test_data_row_longer_than_header_extends_header():
    """The issue's probe: [["a","b"],["1","2","3"]] crashed on v4.0.0."""
    df = read_dataframe(_client_returning([["a", "b"], ["1", "2", "3"]]), "ss_123")

    assert list(df.columns) == ["a", "b", "column_3"]
    assert df.values.tolist() == [["1", "2", "3"]]


def test_short_data_rows_are_right_padded_with_empty_strings():
    """Sheets omits trailing empty cells, so short rows are padded on the right only."""
    values = [["a", "b", "c"], ["1"], ["4", "5", "6"], ["7", "8"]]

    df = read_dataframe(_client_returning(values), "ss_123")

    assert list(df.columns) == ["a", "b", "c"]
    assert df.values.tolist() == [["1", "", ""], ["4", "5", "6"], ["7", "8", ""]]


def test_generated_header_names_do_not_collide_with_existing_names():
    df = read_dataframe(_client_returning([["column_2"], ["1", "2"]]), "ss_123")

    assert list(df.columns) == ["column_2", "column_2_"]
    assert df.values.tolist() == [["1", "2"]]


def test_empty_header_row_with_data_gets_positional_names():
    df = read_dataframe(_client_returning([[], ["1", "2"]]), "ss_123")

    assert list(df.columns) == ["column_1", "column_2"]
    assert df.values.tolist() == [["1", "2"]]


def test_rectangular_sheet_is_unchanged():
    df = read_dataframe(_client_returning([["a", "b"], ["1", "2"], ["3", "4"]]), "ss_123")

    assert list(df.columns) == ["a", "b"]
    assert df.values.tolist() == [["1", "2"], ["3", "4"]]


def test_header_only_sheet_returns_empty_frame_with_columns():
    df = read_dataframe(_client_returning([["a", "b"]]), "ss_123")

    assert list(df.columns) == ["a", "b"]
    assert df.empty


def test_empty_sheet_returns_empty_frame():
    df = read_dataframe(_client_returning([]), "ss_123")

    assert df.empty
    assert list(df.columns) == []


def test_without_header_ragged_rows_keep_pandas_padding():
    """has_header=False is unchanged from v4.0.0: pandas pads with None."""
    df = read_dataframe(_client_returning([["1"], ["2", "3"]]), "ss_123", has_header=False)

    assert df.shape == (2, 2)
    assert df.iloc[0, 1] is None

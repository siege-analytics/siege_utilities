"""Tests for reporting table_utils (#973)."""

import pytest

from siege_utilities.reporting.table_utils import sort_table_data


class TestSortTableData:
    """sort_table_data sorts List[List] tables by column."""

    def test_sort_by_index_ascending(self):
        data = [["Name", "Score"], ["Charlie", "80"], ["Alice", "95"], ["Bob", "70"]]
        result = sort_table_data(data, sort_by=1, sort_order="asc")
        assert result[0] == ["Name", "Score"]
        assert result[1][0] == "Bob"
        assert result[3][0] == "Alice"

    def test_sort_by_index_descending(self):
        data = [["Name", "Score"], ["Charlie", "80"], ["Alice", "95"], ["Bob", "70"]]
        result = sort_table_data(data, sort_by=1, sort_order="desc")
        assert result[0] == ["Name", "Score"]
        assert result[1][0] == "Alice"
        assert result[3][0] == "Bob"

    def test_sort_by_header_name(self):
        data = [["City", "Pop"], ["Denver", "700000"], ["Austin", "950000"], ["Boise", "230000"]]
        result = sort_table_data(data, sort_by="Pop", sort_order="desc")
        assert result[1][0] == "Austin"
        assert result[3][0] == "Boise"

    def test_sort_preserves_header(self):
        data = [["H1", "H2"], ["b", "2"], ["a", "1"]]
        result = sort_table_data(data, sort_by=0)
        assert result[0] == ["H1", "H2"]

    def test_none_sort_by_preserves_order(self):
        data = [["H"], ["c"], ["a"], ["b"]]
        result = sort_table_data(data, sort_by=None)
        assert result == data

    def test_no_header_mode(self):
        data = [["c", "3"], ["a", "1"], ["b", "2"]]
        result = sort_table_data(data, sort_by=0, has_header=False)
        assert result[0][0] == "a"
        assert result[2][0] == "c"

    def test_formatted_numbers(self):
        """Commas and percent signs are stripped for numeric sort."""
        data = [["Item", "Value"], ["A", "1,200"], ["B", "900"], ["C", "3,100"]]
        result = sort_table_data(data, sort_by=1, sort_order="desc")
        assert result[1][1] == "3,100"
        assert result[3][1] == "900"

    def test_formatted_percentages(self):
        data = [["X", "Rate"], ["A", "15.2%"], ["B", "8.5%"], ["C", "22.0%"]]
        result = sort_table_data(data, sort_by="Rate", sort_order="asc")
        assert result[1][1] == "8.5%"
        assert result[3][1] == "22.0%"

    def test_empty_table(self):
        assert sort_table_data([], sort_by=0) == []

    def test_header_only(self):
        data = [["A", "B"]]
        result = sort_table_data(data, sort_by=0)
        assert result == [["A", "B"]]

    def test_invalid_sort_order(self):
        with pytest.raises(ValueError, match="sort_order"):
            sort_table_data([["H"], ["a"]], sort_by=0, sort_order="up")

    def test_invalid_column_name(self):
        with pytest.raises(ValueError, match="not found"):
            sort_table_data([["H1", "H2"], ["a", "b"]], sort_by="H3")

    def test_index_out_of_range(self):
        with pytest.raises(IndexError, match="out of range"):
            sort_table_data([["H1"], ["a"]], sort_by=5)

    def test_does_not_mutate_input(self):
        data = [["H", "V"], ["b", "2"], ["a", "1"]]
        original = [row[:] for row in data]
        sort_table_data(data, sort_by=0)
        assert data == original


class TestAddTableSectionSort:
    """ReportGenerator.add_table_section accepts sort_by/sort_order."""

    def test_sort_by_passed_through(self):
        from siege_utilities.reporting.report_generator import ReportGenerator

        gen = ReportGenerator.__new__(ReportGenerator)
        content = {"sections": []}
        result = gen.add_table_section(
            content, "Test",
            table_data=[["Name", "Val"], ["B", "2"], ["A", "1"]],
            sort_by=0,
        )
        rows = result["sections"][0]["content"]["data"]
        assert rows[0] == ["Name", "Val"]
        assert rows[1][0] == "A"

    def test_default_preserves_order(self):
        from siege_utilities.reporting.report_generator import ReportGenerator

        gen = ReportGenerator.__new__(ReportGenerator)
        content = {"sections": []}
        result = gen.add_table_section(
            content, "Test",
            table_data=[["Name", "Val"], ["B", "2"], ["A", "1"]],
        )
        rows = result["sections"][0]["content"]["data"]
        assert rows[1][0] == "B"


class TestAddTableSlideSort:
    """PowerPointGenerator.add_table_slide accepts sort_by/sort_order."""

    def test_sort_by_passed_through(self):
        from siege_utilities.reporting.powerpoint_generator import PowerPointGenerator

        gen = PowerPointGenerator.__new__(PowerPointGenerator)
        content = {"sections": []}
        result = gen.add_table_slide(
            content, "Test",
            table_data=[["Name", "Val"], ["B", "2"], ["A", "1"]],
            sort_by="Val", sort_order="desc",
        )
        rows = result["sections"][0]["content"]["data"]
        assert rows[0] == ["Name", "Val"]
        assert rows[1][0] == "B"

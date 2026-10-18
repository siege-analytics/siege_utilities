"""Tests for recency analysis (SU#631)."""

from __future__ import annotations

import pytest

from siege_utilities.geo.codification_recency import (
    TIGER_VINTAGES,
    AddressVintage,
    DictAddressVintageProvider,
    compute_recency,
)


def _av(input_id="0", first_vintage=2020, present_in=None):
    return AddressVintage(
        input_id=input_id,
        first_vintage=first_vintage,
        present_in=present_in or [2020],
    )


class TestAddressVintage:
    def test_defaults(self):
        v = AddressVintage()
        assert v.first_vintage is None
        assert not v.is_new_construction

    def test_is_new_construction(self):
        v = _av(first_vintage=2024, present_in=[2024])
        assert v.is_new_construction

    def test_not_new_construction(self):
        v = _av(first_vintage=2020, present_in=[2020, 2022, 2024])
        assert not v.is_new_construction


class TestDictAddressVintageProvider:
    def test_empty(self):
        p = DictAddressVintageProvider()
        assert p.get_vintages(["0"]) == []

    def test_add_and_get(self):
        p = DictAddressVintageProvider()
        p.add(_av(input_id="0"))
        result = p.get_vintages(["0"])
        assert len(result) == 1


class TestComputeRecency:
    def test_empty(self):
        r = compute_recency([])
        assert r.total_analyzed == 0

    def test_single_vintage(self):
        vintages = [_av(first_vintage=2020)] * 10
        r = compute_recency(vintages)
        assert r.total_analyzed == 10
        assert r.vintage_distribution == {2020: 10}
        assert r.vintage_pct[2020] == pytest.approx(1.0)
        assert r.new_construction_count == 0
        assert r.median_vintage == 2020

    def test_mixed_vintages(self):
        vintages = [
            _av(first_vintage=2016),
            _av(first_vintage=2016),
            _av(first_vintage=2018),
            _av(first_vintage=2024, present_in=[2024]),
            _av(first_vintage=2024, present_in=[2024]),
        ]
        r = compute_recency(vintages)
        assert r.total_analyzed == 5
        assert r.vintage_distribution[2016] == 2
        assert r.vintage_distribution[2018] == 1
        assert r.vintage_distribution[2024] == 2
        assert r.new_construction_count == 2
        assert r.new_construction_pct == pytest.approx(0.4)

    def test_median_odd(self):
        vintages = [_av(first_vintage=y) for y in [2010, 2016, 2020]]
        r = compute_recency(vintages)
        assert r.median_vintage == 2016

    def test_median_even(self):
        vintages = [_av(first_vintage=y) for y in [2010, 2016, 2020, 2022]]
        r = compute_recency(vintages)
        assert r.median_vintage == 2016

    def test_skips_none_vintage(self):
        vintages = [_av(first_vintage=2020), AddressVintage(input_id="1")]
        r = compute_recency(vintages)
        assert r.total_analyzed == 1

    def test_sorted_distribution(self):
        vintages = [_av(first_vintage=2020), _av(first_vintage=2010)]
        r = compute_recency(vintages)
        keys = list(r.vintage_distribution.keys())
        assert keys == [2010, 2020]


# ── Error path tests ──


class TestComputeRecencyErrorPaths:
    """Error and edge-case paths for compute_recency."""

    def test_empty_vintages_returns_empty_analysis(self):
        r = compute_recency([])
        assert r.total_analyzed == 0
        assert r.vintage_distribution == {}
        assert r.median_vintage is None
        assert r.new_construction_count == 0
        assert r.new_construction_pct == 0.0

    def test_all_none_first_vintage_returns_empty_analysis(self):
        vintages = [
            AddressVintage(input_id="0"),
            AddressVintage(input_id="1"),
            AddressVintage(input_id="2"),
        ]
        r = compute_recency(vintages)
        assert r.total_analyzed == 0
        assert r.vintage_distribution == {}
        assert r.median_vintage is None

    def test_single_vintage_edge_case(self):
        """A single address first appearing in the latest vintage is new."""
        latest = TIGER_VINTAGES[-1]
        vintages = [_av(first_vintage=latest, present_in=[latest])]
        r = compute_recency(vintages)
        assert r.total_analyzed == 1
        assert r.median_vintage == latest
        assert r.new_construction_count == 1
        assert r.new_construction_pct == pytest.approx(1.0)
        assert r.vintage_pct[latest] == pytest.approx(1.0)


class TestAddressVintageEdgeCases:
    """AddressVintage edge cases."""

    def test_negative_first_vintage_accepted(self):
        """No validation — negative vintage is stored as-is."""
        v = AddressVintage(input_id="0", first_vintage=-1, present_in=[-1])
        assert v.first_vintage == -1
        assert v.is_new_construction is False

    def test_negative_vintage_in_compute_recency(self):
        """Negative vintages flow through compute_recency without error."""
        vintages = [
            AddressVintage(input_id="0", first_vintage=-1, present_in=[-1]),
            AddressVintage(input_id="1", first_vintage=2020, present_in=[2020]),
        ]
        r = compute_recency(vintages)
        assert r.total_analyzed == 2
        assert -1 in r.vintage_distribution
        assert r.new_construction_count == 0

    def test_empty_present_in_not_new_construction(self):
        v = AddressVintage(input_id="0", first_vintage=2020, present_in=[])
        assert v.is_new_construction is False


class TestDictAddressVintageProviderMissing:
    """DictAddressVintageProvider for nonexistent addresses."""

    def test_missing_address_returns_empty(self):
        provider = DictAddressVintageProvider()
        result = provider.get_vintages(["NONEXISTENT"])
        assert result == []

    def test_partial_match_returns_only_found(self):
        provider = DictAddressVintageProvider()
        provider.add(_av(input_id="A"))
        result = provider.get_vintages(["A", "B", "C"])
        assert len(result) == 1
        assert result[0].input_id == "A"

    def test_empty_input_returns_empty(self):
        provider = DictAddressVintageProvider()
        provider.add(_av(input_id="A"))
        result = provider.get_vintages([])
        assert result == []


class TestRecencyMetricsRegression1492:
    @pytest.mark.parametrize("present_in", [[2010], TIGER_VINTAGES])
    def test_all_2010_area_has_no_new_construction(self, present_in):
        vintages = [
            AddressVintage(str(i), first_vintage=2010, present_in=present_in)
            for i in range(5)
        ]

        result = compute_recency(vintages)

        assert result.new_construction_pct == 0.0
        assert result.new_construction_count == 0
        assert result.total_analyzed == 5

    def test_address_new_construction_uses_latest_tiger_vintage(self):
        old = AddressVintage("x", first_vintage=2010, present_in=[2010])
        latest = TIGER_VINTAGES[-1]
        new = AddressVintage("new", first_vintage=latest, present_in=[latest])

        assert old.is_new_construction is False
        assert new.is_new_construction is True
        result = compute_recency([old, new])
        assert result.new_construction_count == 1
        assert result.new_construction_pct == 0.5

    def test_even_median_is_lower_observed_vintage(self):
        vintages = [
            AddressVintage(str(year), first_vintage=year, present_in=[year])
            for year in [2010, 2012]
        ]

        assert compute_recency(vintages).median_vintage == 2010

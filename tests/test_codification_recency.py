"""Tests for recency analysis (SU#631)."""

from __future__ import annotations

import pytest

from siege_utilities.geo.codification_recency import (
    AddressVintage,
    DictAddressVintageProvider,
    RecencyAnalysis,
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
        v = _av(first_vintage=2024, present_in=[2020, 2022, 2024])
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
        assert r.new_construction_count == 10
        assert r.median_vintage == 2020

    def test_mixed_vintages(self):
        vintages = [
            _av(first_vintage=2016),
            _av(first_vintage=2016),
            _av(first_vintage=2018),
            _av(first_vintage=2020),
            _av(first_vintage=2020),
        ]
        r = compute_recency(vintages)
        assert r.total_analyzed == 5
        assert r.vintage_distribution[2016] == 2
        assert r.vintage_distribution[2018] == 1
        assert r.vintage_distribution[2020] == 2
        assert r.new_construction_count == 2
        assert r.new_construction_pct == pytest.approx(0.4)

    def test_median_odd(self):
        vintages = [_av(first_vintage=y) for y in [2010, 2016, 2020]]
        r = compute_recency(vintages)
        assert r.median_vintage == 2016

    def test_median_even(self):
        vintages = [_av(first_vintage=y) for y in [2010, 2016, 2020, 2022]]
        r = compute_recency(vintages)
        assert r.median_vintage == 2018

    def test_skips_none_vintage(self):
        vintages = [_av(first_vintage=2020), AddressVintage(input_id="1")]
        r = compute_recency(vintages)
        assert r.total_analyzed == 1

    def test_sorted_distribution(self):
        vintages = [_av(first_vintage=2020), _av(first_vintage=2010)]
        r = compute_recency(vintages)
        keys = list(r.vintage_distribution.keys())
        assert keys == [2010, 2020]

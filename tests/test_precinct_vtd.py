"""Tests for precinct-VTD reconciliation (SU#635)."""

from __future__ import annotations

import pytest

from siege_utilities.geo.precinct_vtd import (
    ConfidenceLevel,
    DictNameMatchProvider,
    DictSpatialOverlapProvider,
    OfficialCrosswalkEntry,
    PrecinctVTDMapping,
    PrecinctVTDReconciler,
    ReconciliationMethod,
    ReconciliationResult,
    SpatialOverlap,
    _confidence_level,
    _name_similarity,
    _normalize_name,
    reconcile_names,
    reconcile_official,
    reconcile_spatial,
)


class TestConfidenceLevel:
    def test_high(self):
        assert _confidence_level(0.95) == ConfidenceLevel.HIGH
        assert _confidence_level(0.85) == ConfidenceLevel.HIGH

    def test_medium(self):
        assert _confidence_level(0.70) == ConfidenceLevel.MEDIUM
        assert _confidence_level(0.60) == ConfidenceLevel.MEDIUM

    def test_low(self):
        assert _confidence_level(0.50) == ConfidenceLevel.LOW
        assert _confidence_level(0.0) == ConfidenceLevel.LOW


class TestNormalizeName:
    def test_basic(self):
        assert _normalize_name("Precinct 1A") == "precinct 1a"

    def test_strips_punctuation(self):
        assert _normalize_name("Dist. #5 (North)") == "dist 5 north"

    def test_accented_characters(self):
        assert _normalize_name("Cañón") == "canon"
        assert _normalize_name("Précinct") == "precinct"
        assert _normalize_name("Müller") == "muller"
        assert _normalize_name("Señor García") == "senor garcia"

    def test_empty(self):
        assert _normalize_name("") == ""


class TestNameSimilarity:
    def test_identical(self):
        assert _name_similarity("Precinct 1", "Precinct 1") == pytest.approx(1.0)

    def test_similar(self):
        sim = _name_similarity("Precinct 001", "Precinct 1")
        assert sim > 0.7

    def test_different(self):
        sim = _name_similarity("North Ward", "South District")
        assert sim < 0.5

    def test_empty(self):
        assert _name_similarity("", "test") == 0.0
        assert _name_similarity("test", "") == 0.0


class TestPrecinctVTDMapping:
    def test_defaults(self):
        m = PrecinctVTDMapping()
        assert m.confidence == 0.0
        assert m.method == ReconciliationMethod.SPATIAL

    def test_to_dict(self):
        m = PrecinctVTDMapping(
            precinct_id="P1", vtd_geoid="V1",
            overlap_pct=0.95, confidence=0.95,
            confidence_level=ConfidenceLevel.HIGH,
            method=ReconciliationMethod.SPATIAL,
        )
        d = m.to_dict()
        assert d["precinct_id"] == "P1"
        assert d["confidence_level"] == "high"
        assert "name_similarity" not in d

    def test_to_dict_with_name(self):
        m = PrecinctVTDMapping(name_similarity=0.85, notes="matched")
        d = m.to_dict()
        assert d["name_similarity"] == 0.85
        assert d["notes"] == "matched"


class TestReconciliationResult:
    def test_empty(self):
        r = ReconciliationResult()
        assert r.match_rate == 0.0
        assert r.high_confidence_count == 0

    def test_match_rate(self):
        r = ReconciliationResult(total_precincts=10, matched_precincts=8)
        assert r.match_rate == pytest.approx(0.8)

    def test_high_confidence_count(self):
        r = ReconciliationResult(mappings=[
            PrecinctVTDMapping(confidence_level=ConfidenceLevel.HIGH),
            PrecinctVTDMapping(confidence_level=ConfidenceLevel.LOW),
            PrecinctVTDMapping(confidence_level=ConfidenceLevel.HIGH),
        ])
        assert r.high_confidence_count == 2

    def test_for_precinct(self):
        r = ReconciliationResult(mappings=[
            PrecinctVTDMapping(precinct_id="P1", vtd_geoid="V1"),
            PrecinctVTDMapping(precinct_id="P1", vtd_geoid="V2"),
            PrecinctVTDMapping(precinct_id="P2", vtd_geoid="V3"),
        ])
        assert len(r.for_precinct("P1")) == 2
        assert len(r.for_precinct("P2")) == 1

    def test_to_dict(self):
        r = ReconciliationResult(
            total_precincts=5, matched_precincts=4,
            unmatched_precincts=["P5"],
            method_counts={"spatial": 3, "name_match": 1},
        )
        d = r.to_dict()
        assert d["match_rate"] == 0.8
        assert d["unmatched_precincts"] == ["P5"]


class TestDictSpatialOverlapProvider:
    def test_empty(self):
        p = DictSpatialOverlapProvider()
        assert p.compute_overlaps(["P1"]) == []

    def test_filters_by_id(self):
        p = DictSpatialOverlapProvider()
        p.add(SpatialOverlap(precinct_id="P1", vtd_geoid="V1", overlap_pct=0.9))
        p.add(SpatialOverlap(precinct_id="P2", vtd_geoid="V2", overlap_pct=0.8))
        result = p.compute_overlaps(["P1"])
        assert len(result) == 1
        assert result[0].precinct_id == "P1"


class TestDictNameMatchProvider:
    def test_empty(self):
        p = DictNameMatchProvider()
        assert p.get_precinct_names(["P1"]) == {}
        assert p.get_vtd_names() == {}

    def test_add_and_get(self):
        p = DictNameMatchProvider()
        p.add_precinct("P1", "Ward 1")
        p.add_vtd("V1", "Ward One")
        assert p.get_precinct_names(["P1"]) == {"P1": "Ward 1"}
        assert "V1" in p.get_vtd_names()


class TestReconcileSpatial:
    def test_basic(self):
        overlaps = [
            SpatialOverlap(precinct_id="P1", vtd_geoid="V1", overlap_pct=0.95),
        ]
        mappings = reconcile_spatial(overlaps)
        assert len(mappings) == 1
        assert mappings[0].confidence == 0.95
        assert mappings[0].confidence_level == ConfidenceLevel.HIGH

    def test_filters_low_overlap(self):
        overlaps = [
            SpatialOverlap(precinct_id="P1", vtd_geoid="V1", overlap_pct=0.005),
        ]
        assert reconcile_spatial(overlaps) == []

    def test_split_precinct(self):
        overlaps = [
            SpatialOverlap(precinct_id="P1", vtd_geoid="V1", overlap_pct=0.60),
            SpatialOverlap(precinct_id="P1", vtd_geoid="V2", overlap_pct=0.40),
        ]
        mappings = reconcile_spatial(overlaps)
        assert len(mappings) == 2


class TestReconcileNames:
    def test_exact_match(self):
        mappings = reconcile_names(
            {"P1": "Precinct 1"}, {"V1": "Precinct 1"},
        )
        assert len(mappings) == 1
        assert mappings[0].name_similarity == pytest.approx(1.0)

    def test_fuzzy_match(self):
        mappings = reconcile_names(
            {"P1": "Precinct 001"}, {"V1": "Precinct 1", "V2": "District 99"},
        )
        assert len(mappings) == 1
        assert mappings[0].vtd_geoid == "V1"

    def test_no_match(self):
        mappings = reconcile_names(
            {"P1": "Alpha"}, {"V1": "Zulu"},
        )
        assert len(mappings) == 0

    def test_best_match_selected(self):
        mappings = reconcile_names(
            {"P1": "North Ward 5"},
            {"V1": "North Ward 5", "V2": "North Ward 6"},
        )
        assert mappings[0].vtd_geoid == "V1"


class TestReconcileOfficial:
    def test_basic(self):
        entries = [
            OfficialCrosswalkEntry(precinct_id="P1", vtd_geoid="V1", source="NC SBE 2022"),
        ]
        mappings = reconcile_official(entries)
        assert len(mappings) == 1
        assert mappings[0].confidence == 1.0
        assert mappings[0].method == ReconciliationMethod.OFFICIAL_CROSSWALK
        assert "NC SBE 2022" in mappings[0].notes

    def test_empty(self):
        assert reconcile_official([]) == []


class TestPrecinctVTDReconciler:
    def test_empty_input(self):
        rec = PrecinctVTDReconciler()
        result = rec.reconcile([])
        assert result.total_precincts == 0

    def test_spatial_only(self):
        sp = DictSpatialOverlapProvider()
        sp.add(SpatialOverlap(precinct_id="P1", vtd_geoid="V1", overlap_pct=0.90))
        sp.add(SpatialOverlap(precinct_id="P2", vtd_geoid="V2", overlap_pct=0.85))

        rec = PrecinctVTDReconciler(spatial_provider=sp)
        result = rec.reconcile(["P1", "P2"])
        assert result.total_precincts == 2
        assert result.matched_precincts == 2
        assert result.method_counts["spatial"] == 2

    def test_name_only(self):
        np = DictNameMatchProvider()
        np.add_precinct("P1", "Ward 1")
        np.add_vtd("V1", "Ward 1")

        rec = PrecinctVTDReconciler(name_provider=np)
        result = rec.reconcile(["P1"])
        assert result.matched_precincts == 1
        assert result.method_counts["name_match"] == 1

    def test_official_crosswalk(self):
        xw = [OfficialCrosswalkEntry(precinct_id="P1", vtd_geoid="V1")]
        rec = PrecinctVTDReconciler(official_crosswalk=xw)
        result = rec.reconcile(["P1"])
        assert result.matched_precincts == 1
        assert result.method_counts["official_crosswalk"] == 1

    def test_official_overrides_spatial(self):
        sp = DictSpatialOverlapProvider()
        sp.add(SpatialOverlap(precinct_id="P1", vtd_geoid="V_WRONG", overlap_pct=0.95))

        xw = [OfficialCrosswalkEntry(precinct_id="P1", vtd_geoid="V_RIGHT")]

        rec = PrecinctVTDReconciler(spatial_provider=sp, official_crosswalk=xw)
        result = rec.reconcile(["P1"])
        assert len(result.mappings) == 1
        assert result.mappings[0].vtd_geoid == "V_RIGHT"
        assert result.mappings[0].method == ReconciliationMethod.OFFICIAL_CROSSWALK

    def test_official_excludes_name_match(self):
        np = DictNameMatchProvider()
        np.add_precinct("P1", "Ward 1")
        np.add_vtd("V_WRONG", "Ward 1")

        xw = [OfficialCrosswalkEntry(precinct_id="P1", vtd_geoid="V_RIGHT")]

        rec = PrecinctVTDReconciler(name_provider=np, official_crosswalk=xw)
        result = rec.reconcile(["P1"])
        assert len(result.mappings) == 1
        assert result.mappings[0].vtd_geoid == "V_RIGHT"

    def test_combined_boost(self):
        sp = DictSpatialOverlapProvider()
        sp.add(SpatialOverlap(precinct_id="P1", vtd_geoid="V1", overlap_pct=0.80))

        np = DictNameMatchProvider()
        np.add_precinct("P1", "Ward 1")
        np.add_vtd("V1", "Ward 1")

        rec = PrecinctVTDReconciler(spatial_provider=sp, name_provider=np)
        result = rec.reconcile(["P1"])
        assert result.matched_precincts == 1
        combined = [m for m in result.mappings if m.method == ReconciliationMethod.COMBINED]
        assert len(combined) == 1
        assert combined[0].confidence > 0.80

    def test_unmatched_tracked(self):
        sp = DictSpatialOverlapProvider()
        sp.add(SpatialOverlap(precinct_id="P1", vtd_geoid="V1", overlap_pct=0.90))

        rec = PrecinctVTDReconciler(spatial_provider=sp)
        result = rec.reconcile(["P1", "P2", "P3"])
        assert result.matched_precincts == 1
        assert set(result.unmatched_precincts) == {"P2", "P3"}

    def test_split_precinct(self):
        sp = DictSpatialOverlapProvider()
        sp.add(SpatialOverlap(precinct_id="P1", vtd_geoid="V1", overlap_pct=0.60))
        sp.add(SpatialOverlap(precinct_id="P1", vtd_geoid="V2", overlap_pct=0.40))

        rec = PrecinctVTDReconciler(spatial_provider=sp)
        result = rec.reconcile(["P1"])
        assert result.matched_precincts == 1
        assert len(result.for_precinct("P1")) == 2

    def test_irrelevant_crosswalk_ignored(self):
        xw = [OfficialCrosswalkEntry(precinct_id="OTHER", vtd_geoid="V1")]
        rec = PrecinctVTDReconciler(official_crosswalk=xw)
        result = rec.reconcile(["P1"])
        assert result.matched_precincts == 0
        assert result.unmatched_precincts == ["P1"]

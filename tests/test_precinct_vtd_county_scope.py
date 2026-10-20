"""County-scoping regressions for precinct/VTD name matching (#1433)."""

import pytest

from siege_utilities.geo.precinct_vtd import (
    ConfidenceLevel,
    DictNameMatchProvider,
    DictSpatialOverlapProvider,
    MIN_OVERLAP_PCT,
    NAME_ONLY_MAX_CONFIDENCE,
    OfficialCrosswalkEntry,
    PrecinctVTDReconciler,
    ReconciliationMethod,
    SPATIAL_NAME_SUPPRESSION_PCT,
    SpatialOverlap,
    _county_candidates,
    reconcile_names,
)


LOCAL_VTD = "37001000001"
FOREIGN_VTD = "37999000001"
OFFICIAL_VTD = "37001000009"


def _county_names(vtd_names, *, county=None):
    provider = DictNameMatchProvider()
    provider.add_precinct("P1", "Downtown", county=county)
    for geoid, name in vtd_names.items():
        provider.add_vtd(geoid, name)
    return provider


def _crosswalk(county="37001", geoid=OFFICIAL_VTD):
    return [OfficialCrosswalkEntry(
        precinct_id="P1", vtd_geoid=geoid, county=county, source="County crosswalk",
    )]


def _name_mappings(result):
    assert result.errors == []
    return [m for m in result.mappings if m.method == ReconciliationMethod.NAME_MATCH]


class TestCountyScopedNameMatching:
    """Each scenario fails by assertion against the v4.0.0 implementation."""

    def test_identical_name_in_other_county_is_excluded(self):
        result = PrecinctVTDReconciler(
            name_provider=_county_names({FOREIGN_VTD: "Downtown"}),
            official_crosswalk=_crosswalk(),
        ).reconcile(["P1"])

        assert _name_mappings(result) == []
        assert all(m.vtd_geoid != FOREIGN_VTD for m in result.mappings)

    def test_same_county_fuzzy_match_beats_foreign_exact_match(self):
        spatial = DictSpatialOverlapProvider()
        spatial.add(SpatialOverlap(
            precinct_id="P1", vtd_geoid=OFFICIAL_VTD, overlap_pct=0.9,
        ))
        result = PrecinctVTDReconciler(
            spatial_provider=spatial,
            name_provider=_county_names({FOREIGN_VTD: "Downtown", LOCAL_VTD: "Downtown 1"}),
        ).reconcile(["P1"])

        matches = _name_mappings(result)
        assert [m.vtd_geoid for m in matches] == [LOCAL_VTD]
        assert 0.5 <= matches[0].name_similarity < 1.0

    def test_unknown_county_skips_name_matching(self):
        result = PrecinctVTDReconciler(
            name_provider=_county_names({FOREIGN_VTD: "Downtown", LOCAL_VTD: "Downtown"}),
        ).reconcile(["P1"])

        assert _name_mappings(result) == []
        assert result.high_confidence_count == 0
        assert result.unmatched_precincts == ["P1"]

    def test_legitimate_same_county_match_survives_foreign_name_tie(self):
        result = PrecinctVTDReconciler(
            name_provider=_county_names(
                {FOREIGN_VTD: "Downtown", LOCAL_VTD: "Downtown"}, county="37001",
            ),
        ).reconcile(["P1"])

        matches = _name_mappings(result)
        assert [m.vtd_geoid for m in matches] == [LOCAL_VTD]
        assert matches[0].name_similarity == pytest.approx(1.0)
        assert matches[0].confidence == NAME_ONLY_MAX_CONFIDENCE
        assert matches[0].confidence_level == ConfidenceLevel.MEDIUM

    def test_official_mapping_keeps_precedence_without_foreign_extra(self):
        spatial = DictSpatialOverlapProvider()
        spatial.add(SpatialOverlap(
            precinct_id="P1", vtd_geoid=LOCAL_VTD, overlap_pct=0.8,
        ))
        result = PrecinctVTDReconciler(
            spatial_provider=spatial,
            name_provider=_county_names({FOREIGN_VTD: "Downtown", LOCAL_VTD: "Downtown"}),
            official_crosswalk=_crosswalk(geoid=LOCAL_VTD),
        ).reconcile(["P1"])

        assert result.errors == []
        assert len(result.mappings) == 1
        mapping = result.mappings[0]
        assert mapping.vtd_geoid == LOCAL_VTD
        assert mapping.method == ReconciliationMethod.OFFICIAL_CROSSWALK
        assert mapping.confidence == 1.0
        assert mapping.overlap_pct == 1.0
        assert mapping.notes == "Official crosswalk: County crosswalk"


class TestCountyEvidence:
    @pytest.mark.parametrize("county,state,geoid", [
        ("37001", "", OFFICIAL_VTD),
        (" 37001 ", "", OFFICIAL_VTD),
        ("001", "", OFFICIAL_VTD),
        ("1", "", OFFICIAL_VTD),
        ("001", " nc ", "malformed"),
        ("001", "37", "malformed"),
    ])
    def test_official_fips_normalization(self, county, state, geoid):
        crosswalk = _crosswalk(county, geoid)
        crosswalk[0].state = state
        assert _county_candidates(crosswalk, []) == {"P1": {"37001"}}

    def test_full_county_fips_restores_leading_zero(self):
        assert _county_candidates(
            _crosswalk(county="1001", geoid="01001000009"), [],
        ) == {"P1": {"01001"}}

    def test_official_county_overrides_spatial_and_provider(self):
        spatial = DictSpatialOverlapProvider()
        spatial.add(SpatialOverlap("P1", LOCAL_VTD, overlap_pct=0.8))
        spatial.add(SpatialOverlap("P1", FOREIGN_VTD, overlap_pct=0.2))
        names = _county_names({FOREIGN_VTD: "Downtown", LOCAL_VTD: "Downtown 1"})
        names.add_precinct("P1", "Downtown", county="37999")
        result = PrecinctVTDReconciler(
            spatial_provider=spatial, name_provider=names, official_crosswalk=_crosswalk(),
        ).reconcile(["P1"])

        assert _name_mappings(result) == []
        assert [m.vtd_geoid for m in result.mappings if m.method == ReconciliationMethod.COMBINED] == [LOCAL_VTD]

    @pytest.mark.parametrize("overlap_pct", [0.005, MIN_OVERLAP_PCT, 0.9])
    def test_named_county_falls_back_to_spatial_before_provider(self, overlap_pct):
        spatial = DictSpatialOverlapProvider()
        spatial.add(SpatialOverlap("P1", LOCAL_VTD, overlap_pct=overlap_pct))
        names = _county_names({FOREIGN_VTD: "Downtown", LOCAL_VTD: "Downtown 1"})
        names.add_precinct("P1", "Downtown", county="37999")
        result = PrecinctVTDReconciler(
            spatial_provider=spatial, name_provider=names,
            official_crosswalk=_crosswalk(county="Alamance"),
        ).reconcile(["P1"])

        assert _name_mappings(result) == []
        confirmed = [m.vtd_geoid for m in result.mappings if m.method == ReconciliationMethod.COMBINED]
        assert confirmed == ([LOCAL_VTD] if overlap_pct >= MIN_OVERLAP_PCT else [])

    def test_sub_threshold_overlap_uses_provider_county(self):
        spatial = DictSpatialOverlapProvider()
        spatial.add(SpatialOverlap("P1", FOREIGN_VTD, overlap_pct=0.005))
        result = PrecinctVTDReconciler(
            spatial_provider=spatial,
            name_provider=_county_names(
                {FOREIGN_VTD: "Downtown", LOCAL_VTD: "Downtown"}, county="37001",
            ),
        ).reconcile(["P1"])

        assert [m.vtd_geoid for m in _name_mappings(result)] == [LOCAL_VTD]

    def test_provider_counties_are_scoped_per_precinct(self):
        names = _county_names({FOREIGN_VTD: "Downtown", LOCAL_VTD: "Downtown"})
        names.add_precinct("P1", "Downtown", county="37001")
        names.add_precinct("P2", "Downtown", county="37999")
        result = PrecinctVTDReconciler(
            name_provider=names,
        ).reconcile(["P1", "P2"])

        assert [(m.precinct_id, m.vtd_geoid) for m in _name_mappings(result)] == [
            ("P1", LOCAL_VTD), ("P2", FOREIGN_VTD),
        ]
        assert names.get_precinct_counties(["P2", "missing"]) == {"P2": "37999"}

    @pytest.mark.parametrize("source", ["official", "spatial"])
    def test_conflicting_counties_skip_names_despite_provider(self, source):
        spatial = DictSpatialOverlapProvider()
        crosswalk = []
        if source == "official":
            crosswalk = _crosswalk() + _crosswalk(county="37999", geoid=FOREIGN_VTD)
        else:
            spatial.add(SpatialOverlap("P1", OFFICIAL_VTD, overlap_pct=0.8))
            spatial.add(SpatialOverlap("P1", FOREIGN_VTD, overlap_pct=0.2))
        names = _county_names({LOCAL_VTD: "Downtown"})
        names.add_precinct("P1", "Downtown", county="37001")
        result = PrecinctVTDReconciler(
            spatial_provider=spatial, name_provider=names, official_crosswalk=crosswalk,
        ).reconcile(["P1"])

        assert _name_mappings(result) == []
        assert result.method_counts.get("combined", 0) == 0

    def test_neighbor_overlap_at_minimum_still_conflicts(self):
        spatial = DictSpatialOverlapProvider()
        spatial.add(SpatialOverlap("P1", LOCAL_VTD, overlap_pct=1.0 - MIN_OVERLAP_PCT))
        spatial.add(SpatialOverlap("P1", FOREIGN_VTD, overlap_pct=MIN_OVERLAP_PCT))
        result = PrecinctVTDReconciler(
            spatial_provider=spatial,
            name_provider=_county_names({LOCAL_VTD: "Downtown"}, county="37001"),
        ).reconcile(["P1"])

        assert result.errors == []
        assert result.method_counts == {"spatial": 2}

    def test_multiple_overlaps_in_one_county_are_unambiguous(self):
        spatial = DictSpatialOverlapProvider()
        spatial.add(SpatialOverlap("P1", OFFICIAL_VTD, overlap_pct=0.6))
        spatial.add(SpatialOverlap("P1", "37001000008", overlap_pct=0.4))
        result = PrecinctVTDReconciler(
            spatial_provider=spatial,
            name_provider=_county_names({FOREIGN_VTD: "Downtown", LOCAL_VTD: "Downtown 1"}),
        ).reconcile(["P1"])

        assert [m.vtd_geoid for m in _name_mappings(result)] == [LOCAL_VTD]

    def test_zero_overlap_is_not_county_evidence(self):
        spatial = DictSpatialOverlapProvider()
        spatial.add(SpatialOverlap("P1", FOREIGN_VTD, overlap_pct=0.0))
        result = PrecinctVTDReconciler(
            spatial_provider=spatial, name_provider=_county_names({FOREIGN_VTD: "Downtown"}),
        ).reconcile(["P1"])

        assert _name_mappings(result) == []

    def test_county_only_fips_without_state_is_unknown(self):
        result = PrecinctVTDReconciler(
            name_provider=_county_names({FOREIGN_VTD: "Downtown"}),
            official_crosswalk=_crosswalk(county="001", geoid="short"),
        ).reconcile(["P1"])

        assert _name_mappings(result) == []

    def test_legacy_provider_without_county_method_uses_spatial_county(self):
        class LegacyProvider:
            def get_precinct_names(self, precinct_ids):
                return {"P1": "Downtown"}

            def get_vtd_names(self):
                return {FOREIGN_VTD: "Downtown", LOCAL_VTD: "Downtown 1"}

        spatial = DictSpatialOverlapProvider()
        spatial.add(SpatialOverlap("P1", OFFICIAL_VTD, overlap_pct=0.9))
        result = PrecinctVTDReconciler(
            spatial_provider=spatial, name_provider=LegacyProvider(),
        ).reconcile(["P1"])

        assert [m.vtd_geoid for m in _name_mappings(result)] == [LOCAL_VTD]


class TestNameCandidateValidation:
    @pytest.mark.parametrize("geoid", [
        "", "3700", "37001", "370010", "3700100000", "370010000001",
        "XX001000001", "3700100000!", "37001000001\n", None, 37001000001,
    ])
    def test_malformed_vtd_candidate_is_skipped(self, geoid):
        result = PrecinctVTDReconciler(
            name_provider=_county_names(
                {geoid: "Downtown", LOCAL_VTD: "Downtown 1"}, county="37001",
            ),
        ).reconcile(["P1"])

        assert [m.vtd_geoid for m in _name_mappings(result)] == [LOCAL_VTD]

    @pytest.mark.parametrize("geoid", ["37001AB0001", "3700101-02A", "3700101/02."])
    def test_valid_nonnumeric_vtd_suffix_is_accepted(self, geoid):
        result = PrecinctVTDReconciler(
            name_provider=_county_names(
                {FOREIGN_VTD: "Downtown", geoid: "Downtown"}, county="37001",
            ),
        ).reconcile(["P1"])

        assert [m.vtd_geoid for m in _name_mappings(result)] == [geoid]

    def test_short_spatial_geoid_does_not_establish_county(self):
        spatial = DictSpatialOverlapProvider()
        spatial.add(SpatialOverlap("P1", "37001", overlap_pct=0.9))
        result = PrecinctVTDReconciler(
            spatial_provider=spatial, name_provider=_county_names({LOCAL_VTD: "Downtown"}),
        ).reconcile(["P1"])

        assert _name_mappings(result) == []

    @pytest.mark.parametrize("county", [None, {}, {"P1": "Alamance"}, {"P1": "001"}])
    def test_direct_matching_without_county_evidence_is_empty(self, county):
        assert reconcile_names(
            {"P1": "Downtown"}, {LOCAL_VTD: "Downtown"}, precinct_county=county,
        ) == []

    def test_direct_matching_defaults_to_no_county(self):
        assert reconcile_names({"P1": "Downtown"}, {LOCAL_VTD: "Downtown"}) == []


class TestNameMappingPrecedence:
    @pytest.mark.parametrize("overlap_pct,suppressed", [
        (SPATIAL_NAME_SUPPRESSION_PCT - 0.001, False),
        (SPATIAL_NAME_SUPPRESSION_PCT, True),
        (SPATIAL_NAME_SUPPRESSION_PCT + 0.001, True),
    ])
    def test_spatial_suppression_threshold(self, overlap_pct, suppressed):
        spatial = DictSpatialOverlapProvider()
        spatial.add(SpatialOverlap("P1", OFFICIAL_VTD, overlap_pct=overlap_pct))
        result = PrecinctVTDReconciler(
            spatial_provider=spatial, name_provider=_county_names({LOCAL_VTD: "Downtown"}),
        ).reconcile(["P1"])

        assert [m.vtd_geoid for m in _name_mappings(result)] == ([] if suppressed else [LOCAL_VTD])
        assert result.for_precinct("P1")[-1].vtd_geoid == OFFICIAL_VTD

    @pytest.mark.parametrize("overlap_pct", [SPATIAL_NAME_SUPPRESSION_PCT, 1.0])
    def test_name_confirmation_survives_spatial_suppression(self, overlap_pct):
        spatial = DictSpatialOverlapProvider()
        spatial.add(SpatialOverlap("P1", LOCAL_VTD, overlap_pct=overlap_pct))
        result = PrecinctVTDReconciler(
            spatial_provider=spatial, name_provider=_county_names({LOCAL_VTD: "Downtown"}),
        ).reconcile(["P1"])

        assert result.errors == []
        (mapping,) = result.mappings
        assert mapping.method == ReconciliationMethod.COMBINED
        assert mapping.name_similarity == 1.0
        assert mapping.confidence == pytest.approx(0.7 * overlap_pct + 0.3)
        assert mapping.confidence_level == ConfidenceLevel.HIGH

    @pytest.mark.parametrize("source", ["official", "spatial"])
    def test_name_suppression_is_scoped_per_precinct(self, source):
        names = _county_names({LOCAL_VTD: "Downtown"}, county="37001")
        names.add_precinct("P2", "Downtown", county="37001")
        spatial = DictSpatialOverlapProvider()
        crosswalk = []
        if source == "official":
            crosswalk = _crosswalk()
        else:
            spatial.add(SpatialOverlap("P1", OFFICIAL_VTD, overlap_pct=1.0))
        result = PrecinctVTDReconciler(
            spatial_provider=spatial, name_provider=names, official_crosswalk=crosswalk,
        ).reconcile(["P1", "P2"])

        assert [(m.precinct_id, m.vtd_geoid) for m in _name_mappings(result)] == [("P2", LOCAL_VTD)]
        assert [m.vtd_geoid for m in result.for_precinct("P1")] == [OFFICIAL_VTD]


def _names():
    nm = DictNameMatchProvider()
    nm.add_precinct("P1", "Precinct 1")
    nm.add_vtd("48201000001", "0001")
    nm.add_vtd("48201000077", "Precinct 1")  # same county, different VTD
    return nm


def test_no_name_only_mapping_beside_official_crosswalk():
    cw = [OfficialCrosswalkEntry("P1", "48201000001", state="TX", county="201", source="TX SOS")]
    r = PrecinctVTDReconciler(name_provider=_names(), official_crosswalk=cw).reconcile(["P1"])
    assert [m.vtd_geoid for m in r.mappings] == ["48201000001"]


def test_no_name_only_mapping_beside_full_spatial_overlap():
    sp = DictSpatialOverlapProvider()
    sp.add(SpatialOverlap("P1", "48201000001", overlap_pct=1.0))
    r = PrecinctVTDReconciler(spatial_provider=sp, name_provider=_names()).reconcile(["P1"])
    assert [m.vtd_geoid for m in r.mappings] == ["48201000001"]


def test_name_only_mapping_is_capped_below_high():
    nm = DictNameMatchProvider()
    nm.add_precinct("P1", "Precinct 1", county="48201")
    nm.add_vtd("48201000077", "Precinct 1")
    (m,) = PrecinctVTDReconciler(name_provider=nm).reconcile(["P1"]).mappings
    assert m.method == ReconciliationMethod.NAME_MATCH
    assert m.confidence_level != ConfidenceLevel.HIGH


def test_sub_threshold_sliver_does_not_block_name_confirmation():
    sp = DictSpatialOverlapProvider()
    sp.add(SpatialOverlap("P1", "48201000001", overlap_pct=0.995))
    sp.add(SpatialOverlap("P1", "48113000005", overlap_pct=0.005))  # < MIN_OVERLAP_PCT
    nm = DictNameMatchProvider()
    nm.add_precinct("P1", "Precinct 1")
    nm.add_vtd("48201000001", "Precinct 1")
    r = PrecinctVTDReconciler(spatial_provider=sp, name_provider=nm).reconcile(["P1"])
    assert r.method_counts.get("combined") == 1

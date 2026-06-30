"""Tests for siege_utilities.analytics.risk."""

import pytest

from siege_utilities.analytics.risk import (
    RiskAnalyzer,
    RiskAssessment,
    RiskSignal,
    RiskTier,
    RiskTierConfig,
    SignalType,
)


class TestSignalType:
    def test_all_types(self):
        assert SignalType.DECLINE.value == "decline"
        assert SignalType.THRESHOLD.value == "threshold"
        assert SignalType.ABSENCE.value == "absence"
        assert SignalType.ANOMALY.value == "anomaly"


class TestRiskSignal:
    def test_valid_signal(self):
        s = RiskSignal(name="polling", signal_type=SignalType.DECLINE, weight=50.0)
        assert s.name == "polling"
        assert s.signal_type == SignalType.DECLINE
        assert s.weight == 50.0

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name must not be empty"):
            RiskSignal(name="", signal_type=SignalType.DECLINE, weight=50.0)

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="must be a SignalType"):
            RiskSignal(name="x", signal_type="decline", weight=50.0)

    def test_zero_weight_raises(self):
        with pytest.raises(ValueError, match="weight must be in"):
            RiskSignal(name="x", signal_type=SignalType.DECLINE, weight=0)


class TestRiskTierConfig:
    def test_default_thresholds(self):
        c = RiskTierConfig()
        assert c.critical_min == 80.0
        assert c.high_min == 60.0
        assert c.medium_min == 40.0

    def test_classify_critical(self):
        c = RiskTierConfig()
        assert c.classify(90.0) == RiskTier.CRITICAL
        assert c.classify(80.0) == RiskTier.CRITICAL

    def test_classify_high(self):
        c = RiskTierConfig()
        assert c.classify(70.0) == RiskTier.HIGH
        assert c.classify(60.0) == RiskTier.HIGH

    def test_classify_medium(self):
        c = RiskTierConfig()
        assert c.classify(50.0) == RiskTier.MEDIUM
        assert c.classify(40.0) == RiskTier.MEDIUM

    def test_classify_low(self):
        c = RiskTierConfig()
        assert c.classify(30.0) == RiskTier.LOW
        assert c.classify(0.0) == RiskTier.LOW

    def test_invalid_order_raises(self):
        with pytest.raises(ValueError, match="must be ordered"):
            RiskTierConfig(critical_min=50.0, high_min=70.0, medium_min=40.0)


class TestRiskAnalyzer:
    @pytest.fixture
    def election_analyzer(self):
        return RiskAnalyzer(
            signals=[
                RiskSignal(name="polling_decline", signal_type=SignalType.DECLINE, weight=40.0),
                RiskSignal(name="fundraising_drop", signal_type=SignalType.DECLINE, weight=30.0),
                RiskSignal(name="endorsement_loss", signal_type=SignalType.ABSENCE, weight=30.0),
            ]
        )

    def test_empty_signals_raises(self):
        with pytest.raises(ValueError, match="At least one"):
            RiskAnalyzer(signals=[])

    def test_weights_not_100_raises(self):
        with pytest.raises(ValueError, match="weights must sum to 100"):
            RiskAnalyzer(
                signals=[
                    RiskSignal(name="a", signal_type=SignalType.DECLINE, weight=30.0),
                    RiskSignal(name="b", signal_type=SignalType.THRESHOLD, weight=30.0),
                ]
            )

    def test_happy_path(self, election_analyzer):
        result = election_analyzer.assess(
            entity_id="candidate-1",
            scores={
                "polling_decline": 80.0,
                "fundraising_drop": 60.0,
                "endorsement_loss": 40.0,
            },
        )
        assert isinstance(result, RiskAssessment)
        assert result.entity_id == "candidate-1"
        expected = 80.0 * 0.4 + 60.0 * 0.3 + 40.0 * 0.3
        assert result.composite_score == pytest.approx(expected)
        assert result.tier == RiskTier.HIGH
        assert result.signal_types["polling_decline"] == SignalType.DECLINE
        assert result.intervention is None

    def test_missing_signal_raises(self, election_analyzer):
        with pytest.raises(ValueError, match="Missing scores"):
            election_analyzer.assess(
                entity_id="e1",
                scores={"polling_decline": 80.0},
            )

    def test_unknown_signal_raises(self, election_analyzer):
        with pytest.raises(ValueError, match="Unknown signal"):
            election_analyzer.assess(
                entity_id="e1",
                scores={
                    "polling_decline": 80.0,
                    "fundraising_drop": 60.0,
                    "endorsement_loss": 40.0,
                    "bogus": 50.0,
                },
            )

    def test_score_out_of_range_raises(self, election_analyzer):
        with pytest.raises(ValueError, match="must be in"):
            election_analyzer.assess(
                entity_id="e1",
                scores={
                    "polling_decline": 110.0,
                    "fundraising_drop": 60.0,
                    "endorsement_loss": 40.0,
                },
            )

    def test_tier_boundary_critical(self):
        analyzer = RiskAnalyzer(
            signals=[RiskSignal(name="risk", signal_type=SignalType.ANOMALY, weight=100.0)]
        )
        result = analyzer.assess(entity_id="e1", scores={"risk": 80.0})
        assert result.tier == RiskTier.CRITICAL

    def test_tier_boundary_low(self):
        analyzer = RiskAnalyzer(
            signals=[RiskSignal(name="risk", signal_type=SignalType.ANOMALY, weight=100.0)]
        )
        result = analyzer.assess(entity_id="e1", scores={"risk": 10.0})
        assert result.tier == RiskTier.LOW

    def test_intervention_mapping(self):
        analyzer = RiskAnalyzer(
            signals=[RiskSignal(name="risk", signal_type=SignalType.DECLINE, weight=100.0)],
            interventions={
                RiskTier.CRITICAL: "immediate escalation",
                RiskTier.HIGH: "review within 24h",
                RiskTier.MEDIUM: "monitor weekly",
                RiskTier.LOW: "no action",
            },
        )
        result = analyzer.assess(entity_id="e1", scores={"risk": 85.0})
        assert result.intervention == "immediate escalation"

        result_low = analyzer.assess(entity_id="e2", scores={"risk": 10.0})
        assert result_low.intervention == "no action"

    def test_batch_assessment(self, election_analyzer):
        entities = [
            {
                "entity_id": "c1",
                "scores": {"polling_decline": 90.0, "fundraising_drop": 80.0, "endorsement_loss": 70.0},
            },
            {
                "entity_id": "c2",
                "scores": {"polling_decline": 10.0, "fundraising_drop": 20.0, "endorsement_loss": 15.0},
            },
        ]
        results = election_analyzer.assess_batch(entities)
        assert len(results) == 2
        assert results[0].tier == RiskTier.CRITICAL
        assert results[1].tier == RiskTier.LOW

    def test_batch_missing_keys_raises(self, election_analyzer):
        with pytest.raises(ValueError, match="must have"):
            election_analyzer.assess_batch([{"scores": {"polling_decline": 80.0}}])

    def test_signal_names_property(self, election_analyzer):
        assert election_analyzer.signal_names == [
            "polling_decline", "fundraising_drop", "endorsement_loss"
        ]

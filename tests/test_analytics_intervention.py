"""Tests for siege_utilities.analytics.intervention."""

import warnings

import pytest

from siege_utilities.analytics.intervention import (
    InterventionMapper,
    MappingRule,
)


class TestMappingRule:
    def test_valid_rule(self):
        r = MappingRule(signal="timeout", action="retry")
        assert r.signal == "timeout"
        assert r.action == "retry"
        assert r.priority == 0

    def test_empty_signal_raises(self):
        with pytest.raises(ValueError, match="Signal must not be empty"):
            MappingRule(signal="", action="retry")

    def test_empty_action_raises(self):
        with pytest.raises(ValueError, match="Action must not be empty"):
            MappingRule(signal="timeout", action="")

    def test_whitespace_signal_raises(self):
        with pytest.raises(ValueError, match="Signal must not be empty"):
            MappingRule(signal="   ", action="retry")

    def test_whitespace_action_raises(self):
        with pytest.raises(ValueError, match="Action must not be empty"):
            MappingRule(signal="timeout", action="   ")


class TestInterventionMapper:
    @pytest.fixture
    def geocoder_mapper(self):
        return InterventionMapper(
            rules=[
                MappingRule(signal="timeout", action="retry_with_backoff"),
                MappingRule(signal="not_found", action="fallback_provider"),
                MappingRule(signal="rate_limit", action="queue_and_wait"),
            ]
        )

    def test_empty_rules_raises(self):
        with pytest.raises(ValueError, match="At least one"):
            InterventionMapper(rules=[])

    def test_non_strict_without_default_raises(self):
        with pytest.raises(ValueError, match="default_action is required"):
            InterventionMapper(
                rules=[MappingRule(signal="a", action="b")],
                strict=False,
            )

    def test_happy_path(self, geocoder_mapper):
        assert geocoder_mapper.map("timeout") == "retry_with_backoff"
        assert geocoder_mapper.map("not_found") == "fallback_provider"
        assert geocoder_mapper.map("rate_limit") == "queue_and_wait"

    def test_unmapped_strict_raises(self, geocoder_mapper):
        with pytest.raises(ValueError, match="Unmapped signal"):
            geocoder_mapper.map("unknown_error")

    def test_unmapped_non_strict_warns(self):
        mapper = InterventionMapper(
            rules=[MappingRule(signal="a", action="b")],
            default_action="log_and_skip",
            strict=False,
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = mapper.map("unmapped")
            assert len(w) == 1
            assert "Unmapped signal" in str(w[0].message)
        assert result == "log_and_skip"

    def test_priority_ordering(self):
        mapper = InterventionMapper(
            rules=[
                MappingRule(signal="error", action="low_priority", priority=10),
                MappingRule(signal="error", action="high_priority", priority=1),
            ]
        )
        assert mapper.map("error") == "high_priority"

    def test_override_with_reason(self, geocoder_mapper):
        result = geocoder_mapper.map(
            "timeout",
            override_action="manual_fix",
            override_reason="known flaky endpoint",
        )
        assert result == "manual_fix"

    def test_override_without_reason_raises(self, geocoder_mapper):
        with pytest.raises(ValueError, match="override_reason is required"):
            geocoder_mapper.map("timeout", override_action="manual_fix")

    def test_override_whitespace_reason_raises(self, geocoder_mapper):
        with pytest.raises(ValueError, match="override_reason is required"):
            geocoder_mapper.map(
                "timeout", override_action="manual_fix", override_reason="   "
            )

    def test_empty_default_action_raises(self):
        with pytest.raises(ValueError, match="default_action must not be empty"):
            InterventionMapper(
                rules=[MappingRule(signal="a", action="b")],
                default_action="",
                strict=False,
            )

    def test_record_override_whitespace_reason_raises(self, geocoder_mapper):
        with pytest.raises(ValueError, match="override_reason is required"):
            geocoder_mapper.record_outcome(
                "timeout", "manual_fix", success=True,
                overridden=True, override_reason="   ",
            )

    def test_signals_property(self, geocoder_mapper):
        assert geocoder_mapper.signals == ["not_found", "rate_limit", "timeout"]

    def test_record_outcome(self, geocoder_mapper):
        geocoder_mapper.record_outcome("timeout", "retry_with_backoff", success=True)
        geocoder_mapper.record_outcome("timeout", "retry_with_backoff", success=False)
        reports = geocoder_mapper.effectiveness()
        assert len(reports) == 1
        assert reports[0].total == 2
        assert reports[0].successes == 1
        assert reports[0].success_rate == 0.5

    def test_record_override_without_reason_raises(self, geocoder_mapper):
        with pytest.raises(ValueError, match="override_reason is required"):
            geocoder_mapper.record_outcome(
                "timeout", "manual_fix", success=True, overridden=True
            )

    def test_effectiveness_no_outcomes_raises(self, geocoder_mapper):
        with pytest.raises(ValueError, match="No outcomes recorded"):
            geocoder_mapper.effectiveness()

    def test_effectiveness_multiple_actions(self, geocoder_mapper):
        geocoder_mapper.record_outcome("timeout", "retry_with_backoff", success=True)
        geocoder_mapper.record_outcome("timeout", "retry_with_backoff", success=True)
        geocoder_mapper.record_outcome("not_found", "fallback_provider", success=False)
        reports = geocoder_mapper.effectiveness()
        assert len(reports) == 2
        assert reports[0].success_rate < reports[1].success_rate

    def test_record_override_outcome(self, geocoder_mapper):
        geocoder_mapper.record_outcome(
            "timeout", "manual_fix", success=True,
            overridden=True, override_reason="testing",
        )
        reports = geocoder_mapper.effectiveness()
        assert reports[0].action == "manual_fix"

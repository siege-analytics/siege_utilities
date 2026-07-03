"""Tests for siege_utilities.analytics.pipeline."""

import warnings
from datetime import datetime, timedelta

import pytest

from siege_utilities.analytics.pipeline import (
    ConcentrationAlert,
    PipelineAnalyzer,
    PipelineItem,
    PipelineReport,
)


class TestPipelineItem:
    def test_valid_item(self):
        item = PipelineItem(item_id="i1", stage="prospect", value=1000.0)
        assert item.item_id == "i1"
        assert item.stage == "prospect"

    def test_empty_id_raises(self):
        with pytest.raises(ValueError, match="item_id must not be empty"):
            PipelineItem(item_id="", stage="prospect", value=100)

    def test_empty_stage_raises(self):
        with pytest.raises(ValueError, match="stage must not be empty"):
            PipelineItem(item_id="i1", stage="", value=100)

    def test_negative_value_raises(self):
        with pytest.raises(ValueError, match="value must be non-negative"):
            PipelineItem(item_id="i1", stage="prospect", value=-100)


class TestPipelineAnalyzer:
    @pytest.fixture
    def simple_analyzer(self):
        return PipelineAnalyzer(
            stages=["prospect", "qualified", "closed"],
            target=10000.0,
        )

    def test_empty_stages_raises(self):
        with pytest.raises(ValueError, match="At least one stage"):
            PipelineAnalyzer(stages=[])

    def test_duplicate_stages_raises(self):
        with pytest.raises(ValueError, match="must be unique"):
            PipelineAnalyzer(stages=["a", "b", "a"])

    def test_invalid_aging_threshold_raises(self):
        with pytest.raises(ValueError, match="aging_threshold must be positive"):
            PipelineAnalyzer(stages=["a"], aging_threshold=0)

    def test_invalid_concentration_threshold_raises(self):
        with pytest.raises(ValueError, match="concentration_threshold must be"):
            PipelineAnalyzer(stages=["a"], concentration_threshold=0)

    def test_empty_items_raises(self, simple_analyzer):
        with pytest.raises(ValueError, match="At least one pipeline item"):
            simple_analyzer.analyze([])

    def test_unknown_stage_raises(self, simple_analyzer):
        with pytest.raises(ValueError, match="Unknown stage"):
            simple_analyzer.analyze([
                PipelineItem(item_id="i1", stage="bogus", value=100),
            ])

    def test_happy_path(self, simple_analyzer):
        items = [
            PipelineItem(item_id="i1", stage="prospect", value=1000),
            PipelineItem(item_id="i2", stage="prospect", value=2000),
            PipelineItem(item_id="i3", stage="qualified", value=3000),
            PipelineItem(item_id="i4", stage="closed", value=4000),
        ]
        report = simple_analyzer.analyze(items)
        assert isinstance(report, PipelineReport)
        assert report.total_value == 10000
        assert report.coverage_ratio == 1.0
        assert len(report.stage_metrics) == 3
        assert report.stage_metrics[0].stage == "prospect"
        assert report.stage_metrics[0].count == 2

    def test_conversions(self, simple_analyzer):
        items = [
            PipelineItem(item_id="i1", stage="prospect", value=100),
            PipelineItem(item_id="i2", stage="prospect", value=100),
            PipelineItem(item_id="i3", stage="qualified", value=100),
        ]
        report = simple_analyzer.analyze(items)
        assert len(report.conversions) == 2
        assert report.conversions[0].from_stage == "prospect"
        assert report.conversions[0].to_stage == "qualified"
        assert report.conversions[0].rate == 0.5

    def test_coverage_ratio(self, simple_analyzer):
        items = [
            PipelineItem(item_id="i1", stage="prospect", value=30000),
        ]
        report = simple_analyzer.analyze(items)
        assert report.coverage_ratio == 3.0

    def test_no_target(self):
        analyzer = PipelineAnalyzer(stages=["a"])
        report = analyzer.analyze([
            PipelineItem(item_id="i1", stage="a", value=100),
        ])
        assert report.coverage_ratio is None

    def test_missing_timestamps_warns(self, simple_analyzer):
        items = [
            PipelineItem(item_id="i1", stage="prospect", value=100),
        ]
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            report = simple_analyzer.analyze(items)
            assert len(w) == 1
            assert "velocity metrics skipped" in str(w[0].message)
        assert report.velocity == []

    def test_velocity_with_timestamps(self, simple_analyzer):
        now = datetime(2026, 6, 29, 12, 0, 0)
        items = [
            PipelineItem(
                item_id="i1", stage="prospect", value=100,
                entered_stage=now - timedelta(days=5),
            ),
            PipelineItem(
                item_id="i2", stage="prospect", value=100,
                entered_stage=now - timedelta(days=3),
            ),
            PipelineItem(
                item_id="i3", stage="prospect", value=100,
                entered_stage=now - timedelta(days=30),
            ),
        ]
        report = simple_analyzer.analyze(items, as_of=now)
        assert len(report.velocity) >= 1
        prospect_v = report.velocity[0]
        assert prospect_v.stage == "prospect"
        assert prospect_v.avg_days > 0
        assert "i3" in prospect_v.aging_items

    def test_concentration_alert(self, simple_analyzer):
        items = [
            PipelineItem(item_id="big", stage="prospect", value=9000),
            PipelineItem(item_id="small", stage="prospect", value=1000),
        ]
        report = simple_analyzer.analyze(items)
        assert len(report.concentration_alerts) == 1
        assert report.concentration_alerts[0].item_id == "big"
        assert report.concentration_alerts[0].share == 0.9

    def test_no_concentration_alert(self, simple_analyzer):
        items = [
            PipelineItem(item_id="a", stage="prospect", value=100),
            PipelineItem(item_id="b", stage="prospect", value=100),
            PipelineItem(item_id="c", stage="prospect", value=100),
        ]
        report = simple_analyzer.analyze(items)
        assert report.concentration_alerts == []

    def test_zero_total_no_concentration(self, simple_analyzer):
        items = [
            PipelineItem(item_id="a", stage="prospect", value=0),
        ]
        report = simple_analyzer.analyze(items)
        assert report.concentration_alerts == []

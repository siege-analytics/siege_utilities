"""Tests for siege_utilities.analytics.scoring."""

import pytest

from siege_utilities.analytics.scoring import (
    Dimension,
    EntityScore,
    HealthScorer,
    ThresholdConfig,
)


class TestDimension:
    def test_valid_dimension(self):
        d = Dimension(name="quality", weight=50.0)
        assert d.name == "quality"
        assert d.weight == 50.0

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="name must not be empty"):
            Dimension(name="", weight=50.0)

    def test_zero_weight_raises(self):
        with pytest.raises(ValueError, match="weight must be in"):
            Dimension(name="quality", weight=0)

    def test_negative_weight_raises(self):
        with pytest.raises(ValueError, match="weight must be in"):
            Dimension(name="quality", weight=-10)

    def test_over_100_weight_raises(self):
        with pytest.raises(ValueError, match="weight must be in"):
            Dimension(name="quality", weight=101)


class TestThresholdConfig:
    def test_default_thresholds(self):
        t = ThresholdConfig()
        assert t.green_min == 70.0
        assert t.yellow_min == 40.0

    def test_classify_green(self):
        t = ThresholdConfig()
        assert t.classify(85.0) == "Green"
        assert t.classify(70.0) == "Green"

    def test_classify_yellow(self):
        t = ThresholdConfig()
        assert t.classify(55.0) == "Yellow"
        assert t.classify(40.0) == "Yellow"

    def test_classify_red(self):
        t = ThresholdConfig()
        assert t.classify(30.0) == "Red"
        assert t.classify(0.0) == "Red"

    def test_invalid_thresholds_raises(self):
        with pytest.raises(ValueError, match="yellow_min.*must be less"):
            ThresholdConfig(green_min=40.0, yellow_min=70.0)

    def test_equal_thresholds_raises(self):
        with pytest.raises(ValueError, match="yellow_min.*must be less"):
            ThresholdConfig(green_min=50.0, yellow_min=50.0)


class TestHealthScorer:
    @pytest.fixture
    def two_dim_scorer(self):
        return HealthScorer(
            dimensions=[
                Dimension(name="quality", weight=60.0),
                Dimension(name="engagement", weight=40.0),
            ]
        )

    def test_empty_dimensions_raises(self):
        with pytest.raises(ValueError, match="At least one dimension"):
            HealthScorer(dimensions=[])

    def test_weights_not_100_raises(self):
        with pytest.raises(ValueError, match="weights must sum to 100"):
            HealthScorer(
                dimensions=[
                    Dimension(name="a", weight=30.0),
                    Dimension(name="b", weight=30.0),
                ]
            )

    def test_happy_path(self, two_dim_scorer):
        result = two_dim_scorer.score(
            entity_id="entity-1",
            scores={"quality": 80.0, "engagement": 60.0},
        )
        assert isinstance(result, EntityScore)
        assert result.entity_id == "entity-1"
        assert result.composite_score == pytest.approx(72.0)
        assert result.tier == "Green"
        assert result.dimension_scores == {"quality": 80.0, "engagement": 60.0}
        assert result.segment is None
        assert result.trend is None

    def test_single_dimension(self):
        scorer = HealthScorer(
            dimensions=[Dimension(name="only", weight=100.0)]
        )
        result = scorer.score(entity_id="solo", scores={"only": 55.0})
        assert result.composite_score == pytest.approx(55.0)
        assert result.tier == "Yellow"

    def test_missing_dimension_raises(self, two_dim_scorer):
        with pytest.raises(ValueError, match="Missing scores"):
            two_dim_scorer.score(
                entity_id="e1",
                scores={"quality": 80.0},
            )

    def test_unknown_dimension_raises(self, two_dim_scorer):
        with pytest.raises(ValueError, match="Unknown dimension"):
            two_dim_scorer.score(
                entity_id="e1",
                scores={
                    "quality": 80.0,
                    "engagement": 60.0,
                    "bogus": 50.0,
                },
            )

    def test_score_out_of_range_raises(self, two_dim_scorer):
        with pytest.raises(ValueError, match="must be in"):
            two_dim_scorer.score(
                entity_id="e1",
                scores={"quality": 110.0, "engagement": 60.0},
            )

    def test_negative_score_raises(self, two_dim_scorer):
        with pytest.raises(ValueError, match="must be in"):
            two_dim_scorer.score(
                entity_id="e1",
                scores={"quality": -5.0, "engagement": 60.0},
            )

    def test_segment_thresholds(self):
        scorer = HealthScorer(
            dimensions=[Dimension(name="quality", weight=100.0)],
            segment_thresholds={
                "enterprise": ThresholdConfig(green_min=90.0, yellow_min=70.0),
            },
        )
        result = scorer.score(
            entity_id="e1",
            scores={"quality": 75.0},
            segment="enterprise",
        )
        assert result.tier == "Yellow"
        assert result.segment == "enterprise"

        result_default = scorer.score(
            entity_id="e2",
            scores={"quality": 75.0},
        )
        assert result_default.tier == "Green"

    def test_trend_improving(self, two_dim_scorer):
        result = two_dim_scorer.score(
            entity_id="e1",
            scores={"quality": 80.0, "engagement": 60.0},
            previous_score=60.0,
        )
        assert result.trend == pytest.approx(12.0)
        assert result.trend_direction == "improving"

    def test_trend_declining(self, two_dim_scorer):
        result = two_dim_scorer.score(
            entity_id="e1",
            scores={"quality": 40.0, "engagement": 30.0},
            previous_score=50.0,
        )
        assert result.trend < 0
        assert result.trend_direction == "declining"

    def test_trend_stable(self, two_dim_scorer):
        result = two_dim_scorer.score(
            entity_id="e1",
            scores={"quality": 80.0, "engagement": 55.0},
            previous_score=70.0,
        )
        assert result.trend == pytest.approx(0.0)
        assert result.trend_direction == "stable"

    def test_batch_scoring(self, two_dim_scorer):
        entities = [
            {"entity_id": "e1", "scores": {"quality": 80.0, "engagement": 60.0}},
            {"entity_id": "e2", "scores": {"quality": 30.0, "engagement": 20.0}},
        ]
        results = two_dim_scorer.score_batch(entities)
        assert len(results) == 2
        assert results[0].entity_id == "e1"
        assert results[1].entity_id == "e2"
        assert results[0].tier == "Green"
        assert results[1].tier == "Red"

    def test_batch_missing_keys_raises(self, two_dim_scorer):
        with pytest.raises(ValueError, match="must have"):
            two_dim_scorer.score_batch([{"scores": {"quality": 80.0}}])

    def test_dimension_names_property(self, two_dim_scorer):
        assert two_dim_scorer.dimension_names == ["quality", "engagement"]

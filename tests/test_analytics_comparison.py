"""Tests for siege_utilities.analytics.comparison."""

import pytest

from siege_utilities.analytics.comparison import (
    ComparativeAnalyzer,
    ComparisonResult,
    DimensionScore,
    FeatureMatrix,
)


class TestDimensionScore:
    def test_valid_score(self):
        ds = DimensionScore(score=4, evidence="benchmark report 2024")
        assert ds.score == 4
        assert ds.evidence == "benchmark report 2024"

    def test_score_below_range_raises(self):
        with pytest.raises(ValueError, match="must be an integer in"):
            DimensionScore(score=0, evidence="test")

    def test_score_above_range_raises(self):
        with pytest.raises(ValueError, match="must be an integer in"):
            DimensionScore(score=6, evidence="test")

    def test_float_score_raises(self):
        with pytest.raises(ValueError, match="must be an integer in"):
            DimensionScore(score=3.5, evidence="test")

    def test_empty_evidence_raises(self):
        with pytest.raises(ValueError, match="Evidence citation must not be empty"):
            DimensionScore(score=3, evidence="")

    def test_whitespace_evidence_raises(self):
        with pytest.raises(ValueError, match="Evidence citation must not be empty"):
            DimensionScore(score=3, evidence="   ")


class TestComparativeAnalyzer:
    @pytest.fixture
    def geocoder_analyzer(self):
        return ComparativeAnalyzer(
            dimensions=["accuracy", "coverage", "speed"],
            weights={"accuracy": 0.5, "coverage": 0.3, "speed": 0.2},
        )

    def test_empty_dimensions_raises(self):
        with pytest.raises(ValueError, match="At least one dimension"):
            ComparativeAnalyzer(dimensions=[])

    def test_duplicate_dimensions_raises(self):
        with pytest.raises(ValueError, match="must be unique"):
            ComparativeAnalyzer(dimensions=["a", "b", "a"])

    def test_missing_weights_raises(self):
        with pytest.raises(ValueError, match="Missing weights"):
            ComparativeAnalyzer(
                dimensions=["a", "b"],
                weights={"a": 0.5},
            )

    def test_extra_weights_raises(self):
        with pytest.raises(ValueError, match="unknown dimensions"):
            ComparativeAnalyzer(
                dimensions=["a"],
                weights={"a": 0.5, "b": 0.5},
            )

    def test_happy_path(self, geocoder_analyzer):
        result = geocoder_analyzer.compare({
            "Census": {
                "accuracy": DimensionScore(score=3, evidence="TIGER accuracy report"),
                "coverage": DimensionScore(score=5, evidence="full US coverage"),
                "speed": DimensionScore(score=2, evidence="batch processing benchmarks"),
            },
            "Google": {
                "accuracy": DimensionScore(score=5, evidence="Places API precision test"),
                "coverage": DimensionScore(score=4, evidence="global but gaps in rural"),
                "speed": DimensionScore(score=5, evidence="sub-100ms p95"),
            },
        })
        assert isinstance(result, ComparisonResult)
        assert len(result.entities) == 2
        assert "Census" in result.entities
        assert "Google" in result.entities
        assert result.weighted_totals["Google"] > result.weighted_totals["Census"]
        assert len(result.gap_analysis) == 3

    def test_single_entity(self, geocoder_analyzer):
        result = geocoder_analyzer.compare({
            "Census": {
                "accuracy": DimensionScore(score=3, evidence="report"),
                "coverage": DimensionScore(score=5, evidence="report"),
                "speed": DimensionScore(score=2, evidence="report"),
            },
        })
        assert len(result.entities) == 1
        assert all(v == 0.0 for _, v in result.gap_analysis)

    def test_missing_dimension_raises(self, geocoder_analyzer):
        with pytest.raises(ValueError, match="missing scores for"):
            geocoder_analyzer.compare({
                "Census": {
                    "accuracy": DimensionScore(score=3, evidence="report"),
                },
            })

    def test_no_entities_raises(self, geocoder_analyzer):
        with pytest.raises(ValueError, match="At least one entity"):
            geocoder_analyzer.compare({})

    def test_equal_weights_default(self):
        analyzer = ComparativeAnalyzer(dimensions=["a", "b"])
        result = analyzer.compare({
            "X": {
                "a": DimensionScore(score=4, evidence="e1"),
                "b": DimensionScore(score=2, evidence="e2"),
            },
        })
        assert result.weighted_totals["X"] == pytest.approx(3.0)

    def test_gap_analysis_ordering(self):
        analyzer = ComparativeAnalyzer(dimensions=["d1", "d2", "d3"])
        result = analyzer.compare({
            "A": {
                "d1": DimensionScore(score=1, evidence="e"),
                "d2": DimensionScore(score=3, evidence="e"),
                "d3": DimensionScore(score=5, evidence="e"),
            },
            "B": {
                "d1": DimensionScore(score=5, evidence="e"),
                "d2": DimensionScore(score=3, evidence="e"),
                "d3": DimensionScore(score=5, evidence="e"),
            },
        })
        assert result.gap_analysis[0][0] == "d1"
        assert result.gap_analysis[-1][0] in ("d2", "d3")


class TestFeatureMatrix:
    def test_happy_path(self):
        matrix = ComparativeAnalyzer.build_feature_matrix({
            "Census": {"geocoding": True, "reverse": True, "batch": False},
            "Google": {"geocoding": True, "reverse": True, "batch": True},
        })
        assert isinstance(matrix, FeatureMatrix)
        assert len(matrix.entities) == 2
        assert len(matrix.features) == 3
        assert matrix.coverage["Google"] == pytest.approx(100.0)
        assert matrix.coverage["Census"] == pytest.approx(66.67)

    def test_missing_feature_defaults_to_false(self):
        matrix = ComparativeAnalyzer.build_feature_matrix({
            "A": {"f1": True},
            "B": {"f1": True, "f2": True},
        })
        assert matrix.matrix["A"]["f2"] is False

    def test_no_entities_raises(self):
        with pytest.raises(ValueError, match="At least one entity"):
            ComparativeAnalyzer.build_feature_matrix({})

    def test_no_features_raises(self):
        with pytest.raises(ValueError, match="At least one feature"):
            ComparativeAnalyzer.build_feature_matrix({"A": {}})

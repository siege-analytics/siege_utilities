"""Tests for siege_utilities.survey.weights (SAL-65)."""
import pytest
import pandas as pd

try:
    import weightipy  # noqa: F401
    WEIGHTIPY_AVAILABLE = True
except ImportError:
    WEIGHTIPY_AVAILABLE = False

from siege_utilities.survey.weights import WeightingConvergenceError


class TestApplyRimWeightsImport:
    def test_import_error_without_weightipy(self, monkeypatch):
        """When weightipy is absent, apply_rim_weights raises ImportError."""
        import sys
        monkeypatch.setitem(sys.modules, "weightipy", None)
        from importlib import reload
        import siege_utilities.survey.weights as wmod
        with pytest.raises((ImportError, ModuleNotFoundError)):
            wmod.apply_rim_weights(
                pd.DataFrame({"age": ["18-34"], "gender": ["M"]}),
                targets={"age": {"18-34": 1.0}, "gender": {"M": 1.0}},
            )


class TestWeightingConvergenceError:
    def test_is_runtime_error_subclass(self):
        err = WeightingConvergenceError("test")
        assert isinstance(err, RuntimeError)

    def test_message(self):
        err = WeightingConvergenceError("did not converge")
        assert "converge" in str(err)


@pytest.mark.skipif(not WEIGHTIPY_AVAILABLE, reason="weightipy not installed")
class TestApplyRimWeightsWithWeightipy:
    def _sample_df(self):
        return pd.DataFrame({
            "age_group": ["18-34", "18-34", "35-54", "55+", "55+", "35-54"],
            "gender":    ["M", "F", "M", "F", "M", "F"],
        })

    def test_weight_col_added(self):
        from siege_utilities.survey.weights import apply_rim_weights
        df = self._sample_df()
        result = apply_rim_weights(
            df,
            targets={
                "age_group": {"18-34": 0.30, "35-54": 0.40, "55+": 0.30},
                "gender":    {"M": 0.50, "F": 0.50},
            },
        )
        assert "weight" in result.columns
        assert len(result) == len(df)

    def test_custom_weight_col_name(self):
        from siege_utilities.survey.weights import apply_rim_weights
        df = self._sample_df()
        result = apply_rim_weights(
            df,
            targets={
                "age_group": {"18-34": 0.30, "35-54": 0.40, "55+": 0.30},
                "gender":    {"M": 0.50, "F": 0.50},
            },
            weight_col="w",
        )
        assert "w" in result.columns

    def test_weights_are_positive(self):
        from siege_utilities.survey.weights import apply_rim_weights
        df = self._sample_df()
        result = apply_rim_weights(
            df,
            targets={
                "age_group": {"18-34": 0.30, "35-54": 0.40, "55+": 0.30},
                "gender":    {"M": 0.50, "F": 0.50},
            },
        )
        assert (result["weight"] > 0).all()

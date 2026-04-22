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


class TestApplyRimWeightsWithFakeWeightipy:
    """Success-path coverage that does NOT require weightipy to be installed.

    Runs even in the slim CI env. Catches API drift between our wrapper and
    weightipy's public surface (scheme_from_dict + weight_dataframe signatures).
    """

    def test_wrapper_calls_documented_api(self, monkeypatch):
        import sys
        import types

        calls = {}

        fake_wp = types.ModuleType("weightipy")

        def fake_scheme_from_dict(distributions, rim_params=None, name=None):
            calls["scheme_from_dict"] = {
                "distributions": distributions,
                "rim_params": rim_params,
                "name": name,
            }
            return {"_fake_scheme": True, "rim_params": rim_params}

        def fake_weight_dataframe(df, scheme, weight_column="weights", verbose=False):
            calls["weight_dataframe"] = {
                "df_shape": df.shape,
                "scheme": scheme,
                "weight_column": weight_column,
                "verbose": verbose,
            }
            out = df.copy()
            out[weight_column] = [1.0] * len(out)
            return out

        fake_wp.scheme_from_dict = fake_scheme_from_dict
        fake_wp.weight_dataframe = fake_weight_dataframe
        monkeypatch.setitem(sys.modules, "weightipy", fake_wp)

        from siege_utilities.survey.weights import apply_rim_weights
        df = pd.DataFrame({"age": ["18-34", "35+"], "gender": ["M", "F"]})
        result = apply_rim_weights(
            df,
            targets={"age": {"18-34": 0.5, "35+": 0.5}, "gender": {"M": 0.5, "F": 0.5}},
            weight_col="w",
            max_iterations=42,
            convergence=1e-8,
        )

        assert "w" in result.columns
        assert calls["scheme_from_dict"]["rim_params"] == {
            "max_iterations": 42,
            "convcrit": 1e-8,
        }
        assert calls["weight_dataframe"]["weight_column"] == "w"
        assert calls["weight_dataframe"]["df_shape"] == (2, 2)


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

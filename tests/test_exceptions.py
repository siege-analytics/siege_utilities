"""Tests for the unified exception hierarchy and on_error strategy."""

import warnings

import pytest

from siege_utilities.exceptions import (
    OnErrorStrategy,
    SiegeAPIError,
    SiegeConfigError,
    SiegeDataError,
    SiegeError,
    SiegeGeoError,
    handle_error,
)


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptionHierarchy:

    def test_base_is_exception(self):
        assert issubclass(SiegeError, Exception)

    def test_data_error_inherits(self):
        assert issubclass(SiegeDataError, SiegeError)

    def test_geo_error_inherits(self):
        assert issubclass(SiegeGeoError, SiegeError)

    def test_api_error_inherits(self):
        assert issubclass(SiegeAPIError, SiegeError)

    def test_config_error_inherits(self):
        assert issubclass(SiegeConfigError, SiegeError)

    def test_catch_family(self):
        """A single ``except SiegeError`` catches all domain errors."""
        for cls in (SiegeDataError, SiegeGeoError, SiegeAPIError, SiegeConfigError):
            with pytest.raises(SiegeError):
                raise cls("test")


# ---------------------------------------------------------------------------
# handle_error
# ---------------------------------------------------------------------------

class TestHandleError:

    def test_raise_mode(self):
        with pytest.raises(SiegeGeoError, match="boom"):
            handle_error(SiegeGeoError("boom"), on_error="raise")

    def test_warn_mode(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = handle_error(
                SiegeGeoError("oops"),
                on_error="warn",
                fallback=[],
                context="test op",
            )
            assert result == []
            assert len(w) == 1
            assert "test op: oops" in str(w[0].message)

    def test_skip_mode(self):
        result = handle_error(
            SiegeGeoError("silent"),
            on_error="skip",
            fallback="default",
        )
        assert result == "default"

    def test_skip_returns_none_by_default(self):
        result = handle_error(SiegeGeoError("x"), on_error="skip")
        assert result is None

    def test_context_in_raise(self):
        with pytest.raises(SiegeGeoError, match="boom"):
            handle_error(
                SiegeGeoError("boom"),
                on_error="raise",
                context="downloading boundaries",
            )

    def test_fallback_type_preserved(self):
        import pandas as pd
        fallback = pd.DataFrame()
        result = handle_error(
            SiegeAPIError("empty"),
            on_error="skip",
            fallback=fallback,
        )
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

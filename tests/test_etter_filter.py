"""Tests for the Etter natural-language geo-query connector.

Etter's actual parser calls an LLM, so the integration is mocked at the
upstream-parser level (we don't need a real network round-trip to verify
that *our* wrapper translates the upstream object correctly).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from siege_utilities.geo.providers import etter_filter as ef


# ---------------------------------------------------------------------------
# EtterFilter.from_geoquery (pure translation, no etter / no LLM)
# ---------------------------------------------------------------------------

class TestFromGeoQuery:
    def test_full_geoquery(self):
        gq = SimpleNamespace(
            spatial_relation="north_of",
            reference_location="Lausanne",
            buffer_config=SimpleNamespace(distance=5, unit="km"),
            overall_confidence=0.85,
        )
        f = ef.EtterFilter.from_geoquery("5 km north of Lausanne", gq)
        assert f.spatial_relation == "north_of"
        assert f.reference_location == "Lausanne"
        assert f.buffer_distance_m == 5000.0
        assert f.confidence == 0.85
        assert f.original_query == "5 km north of Lausanne"
        assert f.raw is gq

    def test_no_buffer(self):
        gq = SimpleNamespace(
            spatial_relation="in",
            reference_location="Alabama",
            buffer_config=None,
            overall_confidence=0.92,
        )
        f = ef.EtterFilter.from_geoquery("in Alabama", gq)
        assert f.buffer_distance_m is None

    def test_buffer_units_normalized(self):
        for unit, distance, expected in [
            ("m", 100, 100.0),
            ("km", 5, 5000.0),
            ("miles", 1, 1609.344),
            ("ft", 100, 30.48),
        ]:
            gq = SimpleNamespace(
                spatial_relation="near",
                reference_location="X",
                buffer_config=SimpleNamespace(distance=distance, unit=unit),
                overall_confidence=1.0,
            )
            f = ef.EtterFilter.from_geoquery("q", gq)
            assert f.buffer_distance_m == pytest.approx(expected)

    def test_unknown_unit_falls_back_to_meters(self):
        gq = SimpleNamespace(
            spatial_relation="near",
            reference_location="X",
            buffer_config=SimpleNamespace(distance=42, unit="parsec"),
            overall_confidence=1.0,
        )
        f = ef.EtterFilter.from_geoquery("q", gq)
        assert f.buffer_distance_m == 42.0  # treated as meters with warning

    def test_missing_overall_confidence_falls_back_to_breakdown(self):
        gq = SimpleNamespace(
            spatial_relation="near",
            reference_location="X",
            buffer_config=None,
            confidence_breakdown=SimpleNamespace(spatial=0.7, reference=0.5),
        )
        # No overall_confidence attr; fallback should pick min of the
        # numeric values from the breakdown (most conservative).
        gq.overall_confidence = None
        f = ef.EtterFilter.from_geoquery("q", gq)
        assert f.confidence == 0.5

    def test_missing_attrs_default_safely(self):
        # An empty namespace shouldn't crash — getattr defaults take over.
        gq = SimpleNamespace()
        gq.overall_confidence = None  # the from_geoquery code checks this branch
        f = ef.EtterFilter.from_geoquery("q", gq)
        assert f.spatial_relation is None
        assert f.reference_location is None
        assert f.buffer_distance_m is None
        assert f.confidence == 1.0

    def test_frozen(self):
        from dataclasses import FrozenInstanceError
        gq = SimpleNamespace(
            spatial_relation="in",
            reference_location="X",
            buffer_config=None,
            overall_confidence=1.0,
        )
        f = ef.EtterFilter.from_geoquery("q", gq)
        with pytest.raises(FrozenInstanceError):
            f.spatial_relation = "near"


# ---------------------------------------------------------------------------
# EtterParser (with mocked upstream)
# ---------------------------------------------------------------------------

class TestEtterParser:
    """The constructor refuses if etter is unavailable; once mocked, it
    delegates to the upstream parser and translates results."""

    def _patch_etter_available(self):
        """Force-enable the wrapper as if etter were installed."""
        upstream = MagicMock()
        upstream.parse.return_value = SimpleNamespace(
            spatial_relation="near",
            reference_location="Lausanne",
            buffer_config=SimpleNamespace(distance=5, unit="km"),
            overall_confidence=0.9,
        )
        return upstream

    def test_construction_requires_etter(self):
        with patch.object(ef, "ETTER_AVAILABLE", False):
            with pytest.raises(ImportError, match="etter"):
                ef.EtterParser(llm=MagicMock())

    def test_parse_translates_upstream(self):
        upstream = self._patch_etter_available()
        with patch.object(ef, "ETTER_AVAILABLE", True), \
             patch.object(ef, "_UpstreamParser", return_value=upstream):
            p = ef.EtterParser(llm=MagicMock())
            result = p.parse("5 km near Lausanne")
        assert isinstance(result, ef.EtterFilter)
        assert result.spatial_relation == "near"
        assert result.buffer_distance_m == 5000.0
        upstream.parse.assert_called_once_with("5 km near Lausanne")

    def test_parse_empty_query_raises(self):
        upstream = self._patch_etter_available()
        with patch.object(ef, "ETTER_AVAILABLE", True), \
             patch.object(ef, "_UpstreamParser", return_value=upstream):
            p = ef.EtterParser(llm=MagicMock())
            with pytest.raises(ef.EtterParseError, match="Empty"):
                p.parse("")
            with pytest.raises(ef.EtterParseError, match="Empty"):
                p.parse("   ")

    def test_upstream_failure_wraps_in_parse_error(self):
        upstream = MagicMock()
        upstream.parse.side_effect = RuntimeError("LLM hung up")
        with patch.object(ef, "ETTER_AVAILABLE", True), \
             patch.object(ef, "_UpstreamParser", return_value=upstream):
            p = ef.EtterParser(llm=MagicMock())
            with pytest.raises(ef.EtterParseError, match="LLM hung up"):
                p.parse("any query")

    def test_low_confidence_strict_raises(self):
        upstream = MagicMock()
        upstream.parse.return_value = SimpleNamespace(
            spatial_relation="near",
            reference_location="X",
            buffer_config=None,
            overall_confidence=0.4,
        )
        with patch.object(ef, "ETTER_AVAILABLE", True), \
             patch.object(ef, "_UpstreamParser", return_value=upstream):
            p = ef.EtterParser(llm=MagicMock(), confidence_threshold=0.6, strict_mode=True)
            with pytest.raises(ef.EtterLowConfidenceError, match=r"0\.40"):
                p.parse("q")

    def test_upstream_low_confidence_translated(self):
        """An upstream LowConfidenceError surfaces as our typed exception,
        even though we don't forward strict_mode to upstream — defends
        against the case where a future upstream version raises despite
        our local guard."""
        # Synthesize a class that *looks* like upstream's LowConfidenceError
        # (matched by class name, not isinstance — see comment in parse()).
        class LowConfidenceError(Exception):
            pass

        upstream = MagicMock()
        upstream.parse.side_effect = LowConfidenceError("0.42 < 0.6")
        with patch.object(ef, "ETTER_AVAILABLE", True), \
             patch.object(ef, "_UpstreamParser", return_value=upstream):
            p = ef.EtterParser(llm=MagicMock())
            with pytest.raises(ef.EtterLowConfidenceError, match="Upstream rejected"):
                p.parse("ambiguous query")

    def test_low_confidence_non_strict_returns_with_warning(self):
        upstream = MagicMock()
        upstream.parse.return_value = SimpleNamespace(
            spatial_relation="near",
            reference_location="X",
            buffer_config=None,
            overall_confidence=0.4,
        )
        with patch.object(ef, "ETTER_AVAILABLE", True), \
             patch.object(ef, "_UpstreamParser", return_value=upstream):
            p = ef.EtterParser(
                llm=MagicMock(), confidence_threshold=0.6, strict_mode=False,
            )
            result = p.parse("q")
            assert result.confidence == 0.4


# ---------------------------------------------------------------------------
# default_llm — verify the dispatch logic without actually constructing a model
# ---------------------------------------------------------------------------

class TestDefaultLlm:
    def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        # The langchain import itself may fail in the test env; skip if so.
        try:
            from langchain.chat_models import init_chat_model  # noqa: F401
        except ImportError:
            pytest.skip("langchain not installed")
        with pytest.raises(ef.EtterError, match="OPENAI_API_KEY"):
            ef.default_llm(model="gpt-4o")

    def test_explicit_api_key_bypasses_env_check(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        try:
            from langchain.chat_models import init_chat_model  # noqa: F401
        except ImportError:
            pytest.skip("langchain not installed")
        with patch("langchain.chat_models.init_chat_model") as mock_init:
            mock_init.return_value = MagicMock(name="llm")
            ef.default_llm(model="gpt-4o", api_key="sk-test")
            assert mock_init.called
            call_kwargs = mock_init.call_args.kwargs
            assert call_kwargs["api_key"] == "sk-test"

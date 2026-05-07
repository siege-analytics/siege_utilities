"""Natural-language geographic query parsing via Etter.

Wraps the upstream `etter <https://github.com/geoblocks/etter>`_ package
to parse natural-language geographic queries ("5 km north of Lausanne",
"donations near Birmingham", "tracts in Alabama") into structured
filters.

Why a thin wrapper?
-------------------
The upstream library hands you a Pydantic ``GeoQuery`` object. That's
good shape, but two practical problems for siege_utilities consumers:

1. Constructing the LLM (langchain ``ChatOpenAI``, ``ChatAnthropic``,
   etc.) is boilerplate that bleeds into every call site.
2. Consumers want a shape they can hand to a :class:`BoundaryProvider`
   or a :class:`DataFrameEngine` — not a Pydantic model from an
   unrelated lib.

This module hides both: :class:`EtterParser` gives you a default LLM
factory and a :class:`EtterFilter` dataclass that the rest of the
geo toolchain can act on.

The LLM dependency is opt-in via the ``[etter]`` extra. Etter calls
make a network round-trip per query, so this is **for ad-hoc
exploration / interactive UI / one-off ETL prep — not for batch
pipelines** where every donor address gets re-parsed.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

log = logging.getLogger(__name__)

try:
    from etter import GeoFilterParser as _UpstreamParser
    ETTER_AVAILABLE = True
except ImportError:
    _UpstreamParser = None  # type: ignore[assignment]
    ETTER_AVAILABLE = False
    log.info("etter not available — natural-language geo query parsing disabled")


__all__ = [
    "ETTER_AVAILABLE",
    "EtterError",
    "EtterParseError",
    "EtterLowConfidenceError",
    "EtterFilter",
    "EtterParser",
    "default_llm",
]


class EtterError(RuntimeError):
    """Base class for connector-side Etter failures."""


class EtterParseError(EtterError):
    """Etter failed to parse the query into a structured filter."""


class EtterLowConfidenceError(EtterError):
    """Parser succeeded but confidence is below the threshold."""


@dataclass(frozen=True)
class EtterFilter:
    """A normalized parsed query ready for downstream consumption.

    Wraps the upstream ``GeoQuery`` Pydantic model into a dataclass with
    the fields siege_utilities consumers actually need. The original
    upstream object is preserved on :attr:`raw` for callers that need
    full fidelity.

    Attributes:
        original_query: The natural-language input verbatim.
        spatial_relation: One of the relations Etter recognises —
            ``"in"``, ``"near"``, ``"north_of"``, ``"south_of"``,
            ``"east_of"``, ``"west_of"``, etc. ``None`` if the query
            doesn't carry a relation (e.g. a bare place name).
        reference_location: The place the relation hangs off — ``"Lausanne"``,
            ``"Lake Geneva"``, ``"Birmingham, AL"``.
        buffer_distance_m: Buffer distance in meters if the query had
            one (``"5 km"`` → 5000). ``None`` otherwise.
        confidence: Overall confidence score in ``[0, 1]``.
        raw: The upstream :class:`etter.GeoQuery` object, in case the
            consumer needs the full breakdown.
    """

    original_query: str
    spatial_relation: Optional[str]
    reference_location: Optional[str]
    buffer_distance_m: Optional[float] = None
    confidence: float = 1.0
    raw: Any = field(default=None, repr=False, compare=False)

    @classmethod
    def from_geoquery(cls, original_query: str, geo_query: Any) -> "EtterFilter":
        """Translate an upstream ``GeoQuery`` to an :class:`EtterFilter`.

        Tolerant of upstream field-name drift — uses ``getattr`` with
        defaults rather than positional unpacking.
        """
        # Buffer is published by upstream as a sub-model; flatten to meters.
        buffer = getattr(geo_query, "buffer_config", None)
        buffer_m: Optional[float] = None
        if buffer is not None:
            distance = getattr(buffer, "distance", None)
            unit = getattr(buffer, "unit", None) or "m"
            if distance is not None:
                buffer_m = _to_meters(float(distance), str(unit))

        # Confidence: upstream exposes a per-field breakdown plus an
        # overall score — pick whichever is present.
        confidence = getattr(geo_query, "overall_confidence", None)
        if confidence is None:
            breakdown = getattr(geo_query, "confidence_breakdown", None)
            if breakdown is not None:
                values = [
                    v for v in vars(breakdown).values() if isinstance(v, (int, float))
                ] if hasattr(breakdown, "__dict__") else []
                confidence = min(values) if values else 1.0
            else:
                confidence = 1.0

        return cls(
            original_query=original_query,
            spatial_relation=getattr(geo_query, "spatial_relation", None),
            reference_location=getattr(geo_query, "reference_location", None),
            buffer_distance_m=buffer_m,
            confidence=float(confidence),
            raw=geo_query,
        )


_UNIT_TO_METERS = {
    "m": 1.0, "meter": 1.0, "meters": 1.0,
    "km": 1000.0, "kilometer": 1000.0, "kilometers": 1000.0,
    "mi": 1609.344, "mile": 1609.344, "miles": 1609.344,
    "ft": 0.3048, "feet": 0.3048,
    "yd": 0.9144, "yard": 0.9144, "yards": 0.9144,
}


def _to_meters(distance: float, unit: str) -> float:
    """Convert *distance* in *unit* to meters; default to ``m`` on unknown."""
    factor = _UNIT_TO_METERS.get(unit.strip().lower())
    if factor is None:
        log.warning("Etter buffer unit %r not recognised; treating as meters", unit)
        return distance
    return distance * factor


def default_llm(
    *,
    model: str = "gpt-4o",
    temperature: float = 0.0,
    api_key: Optional[str] = None,
):
    """Return a langchain chat model suitable for :class:`EtterParser`.

    Picks the right adapter based on the model name. ``api_key`` falls
    back to the standard environment variable for the chosen provider
    (``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY``). Lazy-imports langchain
    so the rest of this module is importable without it.

    Args:
        model: Chat model name (e.g. ``"gpt-4o"``, ``"claude-3-5-sonnet-latest"``).
        temperature: Sampling temperature; default ``0.0`` for
            reproducibility — query parsing is not creative writing.
        api_key: Optional explicit API key; otherwise read from env.
    """
    try:
        from langchain.chat_models import init_chat_model
    except ImportError:
        raise ImportError(
            "default_llm requires langchain. Install with: "
            "pip install 'siege-utilities[etter]' "
            "(which pulls langchain via etter), or pass your own "
            "configured chat model directly to EtterParser."
        )

    name = model.lower()
    if "claude" in name:
        provider = "anthropic"
        env_var = "ANTHROPIC_API_KEY"
    elif "gpt" in name or "openai" in name:
        provider = "openai"
        env_var = "OPENAI_API_KEY"
    else:
        # Trust caller to know which provider; init_chat_model can infer.
        provider = None
        env_var = None

    kwargs: dict[str, Any] = {"temperature": temperature}
    if api_key:
        kwargs["api_key"] = api_key
    elif env_var and not os.environ.get(env_var):
        raise EtterError(
            f"No api_key passed and ${env_var} is unset. Cannot construct "
            f"the default LLM for model={model!r}."
        )

    if provider:
        return init_chat_model(model=model, model_provider=provider, **kwargs)
    return init_chat_model(model=model, **kwargs)


class EtterParser:
    """Wrap :class:`etter.GeoFilterParser` with a sensible default LLM.

    Usage::

        from siege_utilities.geo.providers.etter_filter import EtterParser

        # Defaults: gpt-4o, temperature=0, OPENAI_API_KEY from env.
        parser = EtterParser()
        result = parser.parse("5 km north of Lausanne")
        # result.spatial_relation == "north_of"
        # result.reference_location == "Lausanne"
        # result.buffer_distance_m == 5000.0

    Pass ``llm=`` to use a pre-built chat model (e.g. for tests or for
    pinning to a specific Anthropic / Azure deployment). All other
    constructor kwargs are forwarded to the upstream parser.
    """

    def __init__(
        self,
        *,
        llm: Any = None,
        confidence_threshold: float = 0.6,
        strict_mode: bool = False,
        **upstream_kwargs: Any,
    ) -> None:
        if not ETTER_AVAILABLE:
            raise ImportError(
                "EtterParser requires etter. Install with: "
                "pip install 'siege-utilities[etter]' or "
                "pip install 'etter>=0.1.0'."
            )
        if llm is None:
            llm = default_llm()
        self._parser = _UpstreamParser(
            llm=llm,
            confidence_threshold=confidence_threshold,
            strict_mode=strict_mode,
            **upstream_kwargs,
        )
        self._confidence_threshold = confidence_threshold
        self._strict_mode = strict_mode
        log.info("EtterParser initialised (threshold=%s)", confidence_threshold)

    def parse(self, query: str) -> EtterFilter:
        """Parse *query* into an :class:`EtterFilter`.

        Raises:
            EtterParseError: Upstream parser raised. The original
                exception is chained via ``__cause__``.
            EtterLowConfidenceError: Parser succeeded but confidence is
                below the threshold and ``strict_mode=True``. (When
                ``strict_mode`` is False, this case logs and returns
                normally; check :attr:`EtterFilter.confidence` if the
                caller needs to gate.)
        """
        if not query or not query.strip():
            raise EtterParseError("Empty query string")
        try:
            geo_query = self._parser.parse(query)
        except Exception as exc:
            raise EtterParseError(
                f"Etter failed to parse {query!r}: {exc}"
            ) from exc

        result = EtterFilter.from_geoquery(query, geo_query)

        if self._strict_mode and result.confidence < self._confidence_threshold:
            raise EtterLowConfidenceError(
                f"Etter parsed {query!r} with confidence "
                f"{result.confidence:.2f} < threshold "
                f"{self._confidence_threshold:.2f}"
            )
        if result.confidence < self._confidence_threshold:
            log.warning(
                "Etter parsed %r with low confidence %.2f (< %.2f). "
                "Result still returned; caller should verify.",
                query, result.confidence, self._confidence_threshold,
            )
        return result

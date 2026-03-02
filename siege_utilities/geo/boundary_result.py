"""
Structured diagnostics for Census boundary retrieval.

Provides typed exceptions and a result object so callers can programmatically
branch on failure reason without parsing free-text logs.

Usage::

    from siege_utilities.geo import fetch_geographic_boundaries

    result = fetch_geographic_boundaries(2020, 'county', state_fips='48')
    if result.success:
        gdf = result.geodataframe
    else:
        print(f"Failed at stage '{result.error_stage}': {result.message}")
        print(f"Context: {result.context}")
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any

try:
    import geopandas as gpd
except ImportError:
    gpd = None


# ---------------------------------------------------------------------------
# Typed Exceptions
# ---------------------------------------------------------------------------

class BoundaryRetrievalError(Exception):
    """Base exception for all boundary retrieval failures."""

    def __init__(self, message: str, stage: str, context: Optional[Dict[str, Any]] = None):
        self.stage = stage
        self.context = context or {}
        super().__init__(message)


class BoundaryInputError(BoundaryRetrievalError):
    """Invalid input parameters (state FIPS, year, geographic level)."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, stage="input_validation", context=context)


class BoundaryDiscoveryError(BoundaryRetrievalError):
    """Failed to discover available boundary types or construct a URL."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, stage="discovery", context=context)


class BoundaryUrlValidationError(BoundaryRetrievalError):
    """Constructed URL is not accessible (HTTP error, timeout, etc.)."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, stage="url_validation", context=context)


class BoundaryDownloadError(BoundaryRetrievalError):
    """Download succeeded but the file is corrupt or not a valid zip."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, stage="download", context=context)


class BoundaryParseError(BoundaryRetrievalError):
    """Downloaded data could not be parsed as a shapefile/GeoDataFrame."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, stage="parse", context=context)


class BoundaryConfigurationError(BoundaryRetrievalError):
    """Boundary type requires parameters that were not provided (e.g., state FIPS, congress number)."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, stage="configuration", context=context)


# ---------------------------------------------------------------------------
# Result Object
# ---------------------------------------------------------------------------

@dataclass
class BoundaryFetchResult:
    """Structured result from a boundary retrieval attempt.

    Attributes:
        success: Whether the retrieval succeeded.
        geodataframe: The resulting GeoDataFrame (None on failure).
        error_code: Machine-readable error code (None on success).
        error_stage: Pipeline stage where failure occurred (None on success).
            One of: input_validation, discovery, url_validation, download, parse.
        message: Human-readable description of the outcome.
        context: Diagnostic details (attempted URLs, year fallback, HTTP status, etc.).
    """

    success: bool
    geodataframe: Any = None  # Optional[gpd.GeoDataFrame]
    error_code: Optional[str] = None
    error_stage: Optional[str] = None
    message: str = ""
    context: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.success

    def raise_on_error(self) -> "BoundaryFetchResult":
        """Raise the appropriate typed exception if this result is a failure.

        Returns self on success so callers can chain::

            gdf = fetch_geographic_boundaries(...).raise_on_error().geodataframe
        """
        if self.success:
            return self

        exc_map = {
            "input_validation": BoundaryInputError,
            "discovery": BoundaryDiscoveryError,
            "configuration": BoundaryConfigurationError,
            "url_validation": BoundaryUrlValidationError,
            "download": BoundaryDownloadError,
            "parse": BoundaryParseError,
        }
        exc_cls = exc_map.get(self.error_stage, BoundaryRetrievalError)
        if exc_cls is BoundaryRetrievalError:
            raise exc_cls(self.message, stage=self.error_stage or "unknown", context=self.context)
        raise exc_cls(self.message, context=self.context)

    @classmethod
    def ok(cls, gdf, message: str = "", context: Optional[Dict[str, Any]] = None) -> "BoundaryFetchResult":
        """Construct a success result."""
        return cls(
            success=True,
            geodataframe=gdf,
            message=message or f"Retrieved {len(gdf)} features",
            context=context or {},
        )

    @classmethod
    def fail(
        cls,
        error_code: str,
        error_stage: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> "BoundaryFetchResult":
        """Construct a failure result."""
        return cls(
            success=False,
            error_code=error_code,
            error_stage=error_stage,
            message=message,
            context=context or {},
        )

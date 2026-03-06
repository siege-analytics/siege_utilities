"""Spatial runtime capability planning across Databricks/Spark/Python contexts."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple


@dataclass(frozen=True)
class SpatialRuntimePlan:
    """Execution plan for spatial operations with deterministic fallback order."""

    runtime: str
    native_spatial_available: bool
    sedona_available: bool
    loader_order: List[str]
    reason: str


def _parse_databricks_runtime_version(version: Optional[str]) -> Optional[Tuple[int, int]]:
    """Parse Databricks runtime version like `17.1.x-scala2.12`."""
    if not version:
        return None
    match = re.match(r"^\s*(\d+)\.(\d+)", str(version))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _detect_databricks_runtime() -> Optional[str]:
    """Read Databricks runtime version from environment when available."""
    return os.getenv("DATABRICKS_RUNTIME_VERSION")


def _infer_native_spatial_support(runtime_version: Optional[str]) -> bool:
    """
    Infer native Databricks spatial support from runtime version.

    Databricks SQL GEOGRAPHY/GEOMETRY support starts in Runtime 17.1+ (preview).
    """
    parsed = _parse_databricks_runtime_version(runtime_version)
    if parsed is None:
        return False
    major, minor = parsed
    return (major, minor) >= (17, 1)


def _detect_sedona_available() -> bool:
    """Best-effort Sedona availability detection via import."""
    try:
        import sedona  # type: ignore  # noqa: F401

        return True
    except Exception:
        return False


def resolve_spatial_runtime_plan(
    *,
    databricks_runtime_version: Optional[str] = None,
    native_spatial_available: Optional[bool] = None,
    sedona_available: Optional[bool] = None,
) -> SpatialRuntimePlan:
    """
    Resolve spatial runtime execution plan.

    Priority order:
    1. databricks_native
    2. sedona
    3. python
    """
    runtime_version = databricks_runtime_version or _detect_databricks_runtime()
    native_available = (
        _infer_native_spatial_support(runtime_version)
        if native_spatial_available is None
        else bool(native_spatial_available)
    )
    sedona_ready = _detect_sedona_available() if sedona_available is None else bool(sedona_available)

    if native_available:
        return SpatialRuntimePlan(
            runtime="databricks_native",
            native_spatial_available=True,
            sedona_available=sedona_ready,
            loader_order=["databricks_native", "sedona", "python"],
            reason="native Databricks spatial support available",
        )
    if sedona_ready:
        return SpatialRuntimePlan(
            runtime="sedona",
            native_spatial_available=False,
            sedona_available=True,
            loader_order=["sedona", "python"],
            reason="native Databricks spatial unavailable, Sedona available",
        )
    return SpatialRuntimePlan(
        runtime="python",
        native_spatial_available=False,
        sedona_available=False,
        loader_order=["python"],
        reason="no native Databricks spatial or Sedona support detected",
    )


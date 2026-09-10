"""Compatibility re-export for stdlib-only geocoding exceptions."""

from __future__ import annotations

from .geocoding_core import GeocodingError

__all__ = ["GeocodingError"]

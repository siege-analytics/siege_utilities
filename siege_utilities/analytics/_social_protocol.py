"""
Social media analytics protocol and shared types.

Defines the read-only contract that all social media analytics connectors
satisfy. Follows the ConnectorProtocol pattern from ``connectors/_protocol.py``:
narrow, runtime-checkable, intentionally minimal.

Social media connectors are analytics primitives — pull metrics and posts.
No publishing, no scheduling, no content management.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol, runtime_checkable

import pandas as pd

__all__ = [
    "SocialMediaProtocol",
    "SocialPost",
    "SocialMetric",
    "SocialMediaError",
    "SocialMediaAuthError",
    "SocialMediaRateLimitError",
]


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class SocialMediaError(Exception):
    """Base for all social media connector errors."""


class SocialMediaAuthError(SocialMediaError):
    """Authentication or authorization failure."""


class SocialMediaRateLimitError(SocialMediaError):
    """API rate limit exceeded."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class SocialPost:
    """A single social media post with engagement metrics."""

    id: str
    platform: str
    post_type: str
    text: str | None = None
    media_url: str | None = None
    published_at: datetime | None = None
    permalink: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class SocialMetric:
    """A single metric value for a time period."""

    name: str
    value: float
    period: str | None = None
    end_time: datetime | None = None


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SocialMediaProtocol(Protocol):
    """Read-only social media analytics contract.

    The protocol is intentionally narrow — seven methods, all read-only.
    Backends handle OAuth token refresh, rate-limit backoff, and
    pagination internally; callers just see this surface.

    Each connector may expose platform-specific methods beyond the
    protocol (e.g., ``InstagramConnector.get_stories()``). The protocol
    captures the shared shape that cross-platform reporting depends on.
    """

    @property
    def platform_name(self) -> str:
        """Platform identifier (``"instagram"``, ``"twitter"``, etc.)."""
        ...

    def authenticate(self) -> None:
        """Establish an authenticated session.

        Raises:
            SocialMediaAuthError: credentials invalid or auth flow failed.
        """
        ...

    def is_connected(self) -> bool:
        """Whether the connector has an active, authenticated session."""
        ...

    def get_account_info(self) -> dict[str, Any]:
        """Account-level metadata (followers, following, post count, etc.).

        Returns:
            Dict with at minimum ``followers_count`` and ``username``.

        Raises:
            SocialMediaAuthError: session expired or insufficient permissions.
            SocialMediaRateLimitError: API rate limit hit.
        """
        ...

    def get_account_insights(
        self,
        start_date: date,
        end_date: date,
        metrics: list[str] | None = None,
    ) -> pd.DataFrame:
        """Time-series account-level metrics.

        Args:
            start_date: Inclusive start of the reporting window.
            end_date: Inclusive end of the reporting window.
            metrics: Platform-specific metric names (e.g., ``"impressions"``,
                ``"reach"``). ``None`` for a sensible default set.

        Returns:
            DataFrame with at minimum ``date`` and one metric column.

        Raises:
            SocialMediaAuthError: session expired or insufficient permissions.
            SocialMediaRateLimitError: API rate limit hit.
        """
        ...

    def get_posts(
        self,
        start_date: date,
        end_date: date,
        *,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Posts published in the given window.

        Args:
            start_date: Inclusive start.
            end_date: Inclusive end.
            limit: Maximum posts to return. ``None`` for all.

        Returns:
            DataFrame with columns matching :class:`SocialPost` fields.

        Raises:
            SocialMediaAuthError: session expired or insufficient permissions.
            SocialMediaRateLimitError: API rate limit hit.
        """
        ...

    def get_post_insights(
        self,
        post_id: str,
        metrics: list[str] | None = None,
    ) -> pd.DataFrame:
        """Engagement metrics for a single post.

        Args:
            post_id: Platform-specific post identifier.
            metrics: Metric names to retrieve. ``None`` for all available.

        Returns:
            DataFrame with columns ``metric``, ``value``, and optionally
            ``period`` and ``end_time``.

        Raises:
            SocialMediaAuthError: session expired or insufficient permissions.
            SocialMediaRateLimitError: API rate limit hit.
        """
        ...

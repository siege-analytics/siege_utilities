"""Tabular Census retrieval with explicit fallback and provenance.

Compose ``DualSourceCensusClient(ApiSource(api), secondary, policy)`` with
sources accepting the keyword arguments of :meth:`CensusAPI.fetch_data`.
Every success returns the source's unchanged DataFrame and provenance;
failures raise. ``BulkFileSource`` defines the extension point for the ACS
Summary File parser deferred to #1385.
"""

from dataclasses import dataclass, replace
import logging
from typing import Any, Protocol

import pandas as pd
from requests.exceptions import Timeout

from siege_utilities.geo.census_api_client import (
    CensusAPIError,
    CensusRateLimitError,
)
from .api import CensusAPI

__all__ = [
    "Provenance",
    "CensusDataSource",
    "ApiSource",
    "BulkFileSource",
    "AlternationPolicy",
    "DualSourceCensusClient",
]

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Provenance:
    """Origin and retrieval history for one returned frame.

    ``source`` is ``"api"`` or ``"bulk"``. ``url_or_path`` is None when the
    source does not expose its location. ``attempts`` counts source-level
    fetch calls for this request, including failed calls across both sources;
    transport retries and cache access inside a source are not counted.
    ``degraded`` indicates that the secondary source served the request.
    """

    source: str
    url_or_path: str | None
    attempts: int
    degraded: bool


class CensusDataSource(Protocol):
    """A tabular source accepting CensusAPI.fetch_data keyword arguments."""

    name: str

    def fetch(self, **request: Any) -> tuple[pd.DataFrame, Provenance]:
        """Return a frame and its provenance, or raise a retrieval error."""
        ...


class ApiSource:
    """Adapt an injected CensusAPI without adding transport retries."""

    name: str = "api"

    def __init__(self, api: CensusAPI) -> None:
        self.api = api

    def fetch(self, **request: Any) -> tuple[pd.DataFrame, Provenance]:
        """Forward the request and report one source call, or raise its error.

        CensusAPI wraps exhausted transport timeouts in CensusAPIError.
        Expose that Timeout cause so the default fallback policy recognizes
        it; other API errors propagate unchanged. The API does not expose
        the served URL/cache path, so ``url_or_path`` is None.
        """
        log.debug("Fetching Census tabular data through the API source")
        try:
            frame = self.api.fetch_data(**request)
        except CensusAPIError as error:
            if isinstance(error.__cause__, Timeout):
                raise error.__cause__ from None
            raise
        return frame, Provenance(
            source="api", url_or_path=None, attempts=1, degraded=False,
        )


class BulkFileSource:
    """Extension point for the ACS Summary File tabular source (#1385)."""

    name: str = "bulk"

    def fetch(self, **request: Any) -> tuple[pd.DataFrame, Provenance]:
        """Raise until the ACS Summary File parser is implemented in #1385."""
        raise NotImplementedError(
            "ACS Summary File bulk source not yet implemented; see #1385"
        )


@dataclass(frozen=True)
class AlternationPolicy:
    """Pure configuration for a bounded primary-then-secondary attempt order.

    ``max_api_attempts`` is a positive source-call budget for the primary.
    Only ``fallback_on`` errors consume that retry budget; other errors
    propagate immediately. An empty tuple disables retries and fallback.
    ``alternate_under_sustained_pressure`` defaults to False and is reserved
    for a future cross-request scheduling policy. This framework does not
    track pressure across requests; each fetch starts with the primary.
    """

    max_api_attempts: int = 3
    fallback_on: tuple[type[Exception], ...] = (CensusRateLimitError, Timeout)
    alternate_under_sustained_pressure: bool = False

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_api_attempts, bool)
            or not isinstance(self.max_api_attempts, int)
            or self.max_api_attempts < 1
        ):
            raise ValueError("max_api_attempts must be a positive integer")


class DualSourceCensusClient:
    """Retry the primary on configured errors, then try the secondary once.

    The last retrieval error propagates if no source succeeds, including
    BulkFileSource's NotImplementedError until #1385 is implemented. Each
    return includes provenance with this request's total source-call count.
    Source frames, source names, and locations are preserved.
    """

    def __init__(
        self,
        primary: CensusDataSource,
        secondary: CensusDataSource,
        policy: AlternationPolicy | None = None,
    ) -> None:
        self.primary = primary
        self.secondary = secondary
        self.policy = policy if policy is not None else AlternationPolicy()

    def fetch(self, **request: Any) -> tuple[pd.DataFrame, Provenance]:
        """Return an unchanged source frame and provenance, or raise.

        Forward the same CensusAPI.fetch_data keyword arguments to each
        attempted source. Secondary errors propagate without retrying.
        """
        attempt = 0
        while True:
            attempt += 1
            log.debug(
                "Fetching Census data from %s (attempt %s/%s)",
                self.primary.name, attempt, self.policy.max_api_attempts,
            )
            try:
                frame, provenance = self.primary.fetch(**request)
            except self.policy.fallback_on as error:
                log.warning(
                    "Census source %s attempt %s/%s failed (%s)",
                    self.primary.name, attempt, self.policy.max_api_attempts,
                    type(error).__name__,
                )
                if attempt == self.policy.max_api_attempts:
                    log.warning(
                        "Falling back to Census source %s",
                        self.secondary.name,
                    )
                    frame, provenance = self.secondary.fetch(**request)
                    return frame, replace(
                        provenance, attempts=attempt + 1, degraded=True,
                    )
            else:
                return frame, replace(provenance, attempts=attempt)

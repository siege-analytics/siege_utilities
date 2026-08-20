"""siege wrapper for ``parsons.VAN`` (NGP VAN / EveryAction).

Ships :class:`SiegeVAN` — a :class:`~siege_utilities.connectors._protocol.ConnectorProtocol`
implementation that wraps ``parsons.VAN``. Callers see ``pd.DataFrame``
in / out and typed :class:`~siege_utilities.connectors._protocol.ConnectorError`
subclasses on failure. No direct ``parsons`` import needed downstream.

Usage — inline credentials::

    from siege_utilities.integrations.parsons.van import SiegeVAN

    van = SiegeVAN(api_key="…")
    events = van.get_objects("Events", limit=100)   # -> pd.DataFrame

Usage — siege credential profile bridge::

    van = SiegeVAN(profile="acme")
    # api_key resolved from siege CredentialManager via bridge_credentials

EveryAction: pass ``db="EveryAction"`` to the constructor, or use the
:class:`SiegeEveryAction` alias which hardcodes it.

The wrapper is deliberately thin. Every method routes through either
:func:`~siege_utilities.integrations.parsons._adapter.parsons_table_to_dataframe`
(read) or the underlying ``parsons.VAN`` call (write), decorated with
:func:`~siege_utilities.integrations.parsons._errors.translate_errors`.

Object-type surface (``get_objects``): ``"People"``, ``"Events"``,
``"ActivistCodes"``, ``"SavedLists"``, ``"SurveyQuestions"``. Others
raise :class:`ConnectorNotFoundError`. Add here as needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pandas as pd

from ...connectors._protocol import (
    ConnectorAuthError,
    ConnectorError,
    ConnectorNotFoundError,
)
from ._adapter import parsons_table_to_dataframe
from ._auth import bridge_credentials
from ._errors import translate_errors

if TYPE_CHECKING:
    from parsons import VAN as _ParsonsVAN


__all__ = [
    "SiegeVAN",
    "SiegeEveryAction",
    "SUPPORTED_OBJECT_TYPES",
]


# Object-type keys accepted by :meth:`SiegeVAN.get_objects`. Extending the
# surface: add the key here + a branch in :meth:`_dispatch_get_objects`.
SUPPORTED_OBJECT_TYPES: tuple[str, ...] = (
    "People",
    "Events",
    "ActivistCodes",
    "SavedLists",
    "SurveyQuestions",
)


class SiegeVAN:
    """VAN / EveryAction wrapper implementing ``ConnectorProtocol``.

    Args:
        api_key: VAN API key. If ``None``, resolved from ``profile`` via
            :func:`bridge_credentials`. Exactly one of ``api_key`` or
            ``profile`` must produce a usable key.
        db: VAN database. ``None`` uses the connector's default;
            ``"EveryAction"`` targets EveryAction; ``"MyVoters"`` /
            ``"MyCampaign"`` / ``"MyMembers"`` target their respective
            databases. See ``parsons.VAN`` docs.
        profile: siege credential profile name for bridging. Ignored if
            ``api_key`` is given directly.
        _van_factory: Optional injectable factory for the underlying
            connector (test hook; defaults to ``parsons.VAN``).

    Raises:
        ConnectorAuthError: no API key available (neither ``api_key``
            argument nor a resolvable profile) or the credential bridge
            failed.
        ConnectorError: the ``parsons`` package is not installed
            (install ``siege_utilities[parsons-van]``).
    """

    def __init__(
        self,
        api_key: str | None = None,
        db: str | None = None,
        *,
        profile: str | None = None,
        _van_factory: Any | None = None,
    ) -> None:
        if _van_factory is None:
            try:
                from parsons import VAN as _VAN
                _van_factory = _VAN
            except ImportError as exc:
                raise ConnectorError(
                    "parsons.VAN is not installed. "
                    "Install siege_utilities[parsons-van]."
                ) from exc

        if api_key is None:
            kwargs = bridge_credentials("van", profile=profile)
            api_key = kwargs["api_key"]

        if not api_key:
            raise ConnectorAuthError(
                "SiegeVAN requires an api_key (direct or via profile)."
            )

        try:
            self._van = _van_factory(api_key=api_key, db=db)
        except Exception as exc:  # noqa: BLE001
            # Constructor doesn't hit the network (per P0-4 matrix) but
            # can still raise on bad arg shapes. Wrap for a clean contract.
            raise ConnectorError(f"Failed to construct parsons.VAN: {exc}") from exc

        self._db = db

    # ------------------------------------------------------------------
    # ConnectorProtocol
    # ------------------------------------------------------------------

    @property
    def provider_name(self) -> str:
        if self._db == "EveryAction":
            return "everyaction"
        return "van"

    def authenticate(self) -> None:
        """No-op — parsons.VAN authenticates lazily on first API call.

        Kept for ConnectorProtocol conformance. If the API key is invalid,
        the first :meth:`get_objects` (or similar) will raise
        :class:`ConnectorAuthError` per the HTTP-401 mapping in
        :func:`map_parsons_exception`.
        """
        return None

    def is_connected(self) -> bool:
        """Whether the underlying connector has an API key bound.

        Returns ``True`` if construction succeeded and an api_key is
        present. Does NOT probe the API — call :meth:`get_objects` with
        a small limit for a live check.
        """
        return getattr(self._van, "api_key", None) not in (None, "")

    @translate_errors("van")
    def list_object_types(self) -> list[str]:
        """Return the object types this wrapper knows how to fetch."""
        return list(SUPPORTED_OBJECT_TYPES)

    @translate_errors("van")
    def get_objects(
        self,
        object_type: str,
        *,
        fields: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Fetch records of ``object_type`` as a DataFrame.

        Args:
            object_type: One of :data:`SUPPORTED_OBJECT_TYPES`.
            fields: Ignored for VAN — the upstream get_* methods do not
                take a projection argument. Accepted for
                :class:`ConnectorProtocol` conformance; caller can slice
                the returned DataFrame.
            filters: Passed as keyword arguments to the underlying VAN
                get_ method. Interpretation depends on ``object_type``
                (e.g., ``{"event_type_ids": [123]}`` for Events).
            limit: Truncates the returned DataFrame after conversion.
                None returns all records.

        Raises:
            ConnectorNotFoundError: ``object_type`` is not in
                :data:`SUPPORTED_OBJECT_TYPES`.
            ConnectorAuthError: API key rejected (HTTP 401/403).
            ConnectorRateLimitError: rate limit exceeded (HTTP 429).
            ConnectorError: any other transport / parsons failure.
        """
        table = self._dispatch_get_objects(object_type, filters or {})
        df = parsons_table_to_dataframe(table)
        if fields:
            missing = [f for f in fields if f not in df.columns]
            if missing:
                # Not fatal — the caller may only want a subset that
                # doesn't exist yet. Filter to available columns.
                fields = [f for f in fields if f in df.columns]
            if fields:
                df = df[fields]
        if limit is not None:
            df = df.head(limit)
        return df

    # ------------------------------------------------------------------
    # ConnectorProtocol write methods — VAN wrapper is READ-focused
    # ------------------------------------------------------------------
    # The upstream parsons.VAN has extensive write methods (bulk_upsert_*,
    # apply_*, create_*, delete_*). Wrapping them is out of scope for the
    # P2 first-connector-proof — the goal here is to prove the pattern
    # (adapter + errors + auth) end-to-end for the READ path. Write
    # wrappers ship in a follow-up (see #1148 Phase 3 fan-out).

    def create_record(self, object_type: str, data: dict[str, Any]) -> str:
        raise NotImplementedError(
            "SiegeVAN.create_record: VAN write surface not yet wrapped. "
            "See #1148 Phase 3 fan-out. Use self._van directly for now."
        )

    def update_record(
        self, object_type: str, record_id: str, data: dict[str, Any]
    ) -> None:
        raise NotImplementedError(
            "SiegeVAN.update_record: VAN write surface not yet wrapped. "
            "See #1148 Phase 3 fan-out. Use self._van directly for now."
        )

    def delete_record(self, object_type: str, record_id: str) -> None:
        raise NotImplementedError(
            "SiegeVAN.delete_record: VAN write surface not yet wrapped. "
            "See #1148 Phase 3 fan-out. Use self._van directly for now."
        )

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def _dispatch_get_objects(
        self, object_type: str, filters: dict[str, Any]
    ) -> Any:
        """Route ``object_type`` to the underlying ``parsons.VAN`` method.

        Returns the raw ``parsons.Table``; caller converts.
        """
        if object_type == "People":
            # There is no bulk "list_people" — People is fetched via find_person
            # or export jobs. For the ConnectorProtocol shape, use
            # get_saved_list_people if a saved_list_id filter is present;
            # otherwise raise a clear error naming the required filter.
            saved_list_id = filters.get("saved_list_id")
            if saved_list_id is None:
                raise ConnectorNotFoundError(
                    "SiegeVAN.get_objects('People'): VAN has no bulk-list "
                    "people endpoint. Provide filters={'saved_list_id': N} "
                    "to fetch a saved list's people, or use "
                    "self._van.find_person(...) directly."
                )
            return self._van.download_saved_list(saved_list_id)
        if object_type == "Events":
            return self._van.get_events(**filters)
        if object_type == "ActivistCodes":
            return self._van.get_activist_codes(**filters)
        if object_type == "SavedLists":
            return self._van.get_saved_lists(**filters)
        if object_type == "SurveyQuestions":
            return self._van.get_survey_questions(**filters)

        raise ConnectorNotFoundError(
            f"SiegeVAN.get_objects: unknown object_type {object_type!r}. "
            f"Supported: {SUPPORTED_OBJECT_TYPES}."
        )

    # ------------------------------------------------------------------
    # Escape hatch — direct access to parsons.VAN for unwrapped surface
    # ------------------------------------------------------------------

    @property
    def raw(self) -> "_ParsonsVAN":
        """Underlying ``parsons.VAN`` instance.

        Escape hatch for methods the siege wrapper does not yet expose
        (write methods, bulk import, target exports). Using ``.raw`` opts
        the caller out of siege's error contract — exceptions from raw
        methods are Parsons's, not ``ConnectorError``.
        """
        return self._van


class SiegeEveryAction(SiegeVAN):
    """EveryAction alias — same as ``SiegeVAN(db='EveryAction')``.

    Convenience for consumers who model EveryAction as a distinct
    connector even though upstream Parsons uses the same class.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        profile: str | None = None,
        _van_factory: Any | None = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            db="EveryAction",
            profile=profile,
            _van_factory=_van_factory,
        )

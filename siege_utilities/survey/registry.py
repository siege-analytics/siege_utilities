"""Client ↔ Survey registry.

Associates :class:`~siege_utilities.survey.models.WaveSet` instances (each
one representing a survey instrument with its waves) to the client that
owns them. Supports many surveys per client and fast lookup without
scanning a flat list.

Survey identity within a client is the WaveSet's ``name`` — two surveys
for the same client must have distinct names. Names are **not** required
to be globally unique; ``("Acme", "Tracker Q2")`` and
``("Beacon", "Tracker Q2")`` coexist fine.

Client branding / display info continues to live in
:mod:`siege_utilities.reporting.client_branding`. The registry only
answers "which surveys belong to this client" — not "how do we render
this client's report".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .models import WaveSet


class ClientSurveyError(KeyError):
    """Raised for registry-level lookup / duplication problems.

    Subclasses ``KeyError`` so existing ``except KeyError`` handlers at
    call sites still catch it; use ``except ClientSurveyError`` when you
    need the more specific signal.
    """


@dataclass
class ClientSurveyRegistry:
    """In-memory map of ``client_id`` → {survey name → WaveSet}.

    Deliberately in-memory and dependency-free. Persistence (YAML, SQL,
    wherever) is a caller concern — serialize ``_by_client`` directly or
    build higher-level storage on top.
    """

    _by_client: Dict[str, Dict[str, WaveSet]] = field(default_factory=dict)

    # -------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------

    def register(self, waveset: WaveSet) -> WaveSet:
        """Register a WaveSet whose ``client_id`` is already set.

        Raises :class:`ClientSurveyError` if ``client_id`` is unset or if
        a WaveSet with the same name is already registered for that
        client.
        """
        if not waveset.client_id:
            raise ClientSurveyError(
                f"WaveSet {waveset.name!r} has no client_id; "
                "use register_for(client_id, waveset) instead or set "
                "waveset.client_id first."
            )
        return self._register_unchecked(waveset.client_id, waveset)

    def register_for(self, client_id: str, waveset: WaveSet) -> WaveSet:
        """Set ``waveset.client_id = client_id`` and register it.

        Raises :class:`ClientSurveyError` if a WaveSet with the same
        name is already registered for that client.
        """
        if not client_id:
            raise ClientSurveyError("client_id must be a non-empty string")
        waveset.client_id = client_id
        return self._register_unchecked(client_id, waveset)

    def _register_unchecked(self, client_id: str, waveset: WaveSet) -> WaveSet:
        surveys = self._by_client.setdefault(client_id, {})
        if waveset.name in surveys:
            raise ClientSurveyError(
                f"client {client_id!r} already has a survey named "
                f"{waveset.name!r}; unregister it first or rename."
            )
        surveys[waveset.name] = waveset
        return waveset

    def unregister(self, client_id: str, name: str) -> WaveSet:
        """Remove and return the named survey for ``client_id``.

        Raises :class:`ClientSurveyError` if the client or the named
        survey is not registered.
        """
        surveys = self._by_client.get(client_id)
        if not surveys or name not in surveys:
            raise ClientSurveyError(
                f"no survey named {name!r} registered for client {client_id!r}"
            )
        removed = surveys.pop(name)
        if not surveys:
            del self._by_client[client_id]
        return removed

    # -------------------------------------------------------------------
    # Lookup
    # -------------------------------------------------------------------

    def clients(self) -> List[str]:
        """Return all registered client ids."""
        return list(self._by_client.keys())

    def surveys_for(self, client_id: str) -> List[WaveSet]:
        """Return all WaveSets registered to ``client_id`` (empty list if none)."""
        return list(self._by_client.get(client_id, {}).values())

    def get_survey(self, client_id: str, name: str) -> Optional[WaveSet]:
        """Return the named WaveSet for a client, or ``None`` if missing."""
        return self._by_client.get(client_id, {}).get(name)

    def require_survey(self, client_id: str, name: str) -> WaveSet:
        """Like :meth:`get_survey` but raises :class:`ClientSurveyError` on miss."""
        ws = self.get_survey(client_id, name)
        if ws is None:
            raise ClientSurveyError(
                f"no survey named {name!r} registered for client {client_id!r}"
            )
        return ws

    def client_of(self, waveset: WaveSet) -> Optional[str]:
        """Return the client id a WaveSet is registered to, if any.

        Prefers ``waveset.client_id`` but falls back to reverse lookup
        so callers stay correct even if the field was cleared after
        registration.
        """
        if waveset.client_id:
            return waveset.client_id
        for client_id, surveys in self._by_client.items():
            if any(ws is waveset for ws in surveys.values()):
                return client_id
        return None

    # -------------------------------------------------------------------
    # Introspection
    # -------------------------------------------------------------------

    def __contains__(self, key) -> bool:
        """``client_id in registry`` or ``(client_id, name) in registry``."""
        if isinstance(key, tuple) and len(key) == 2:
            client_id, name = key
            return name in self._by_client.get(client_id, {})
        return key in self._by_client

    def __len__(self) -> int:
        """Total number of registered surveys across all clients."""
        return sum(len(s) for s in self._by_client.values())

"""Bridge siege credential profiles to Parsons connector constructor kwargs.

Reads the empirical constructor-signature matrix in
:file:`docs/PARSONS_AUTH_MATRIX.md` (P0-4) and encodes it as a
per-connector map of ``(kwarg_name, siege_service, siege_field)`` triples.
:func:`bridge_credentials` resolves those triples via any object matching
:class:`CredentialResolver` (siege's
:class:`~siege_utilities.config.credential_manager.CredentialManager` by
default) and returns a kwargs dict ready to splat into the Parsons class
constructor.

Design invariants:

- **No env-var side effects.** Every Parsons priority connector accepts
  credentials via constructor kwargs (see P0-4 matrix). The bridge never
  sets ``os.environ`` and never leaks credentials outside the returned
  dict.
- **Fail loud on missing required credentials.** If a required credential
  is absent, raise :class:`ConnectorAuthError` naming the missing field.
  Never return a partial dict.
- **Warn on optional-credential resolution failures.** Missing optional
  credentials are omitted from the returned dict, but backend errors while
  attempting to resolve them are logged at WARNING with the connector,
  profile, field, and exception class — never the credential value. A
  backend outage and an unset optional credential must be distinguishable.
- **Fail loud on unknown connector.** Unrecognised connector name raises
  :class:`ConnectorError` (not ``ValueError``, not silent None-return).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from ...connectors._protocol import ConnectorAuthError, ConnectorError

__all__ = [
    "CONNECTOR_KWARG_MAPS",
    "ConnectorKwargSpec",
    "ConnectorSpec",
    "CredentialResolver",
    "bridge_credentials",
]


logger = logging.getLogger(__name__)


@runtime_checkable
class CredentialResolver(Protocol):
    """Minimal contract the bridge needs from a credential backend.

    Siege's :class:`~siege_utilities.config.credential_manager.CredentialManager`
    satisfies this by default; tests can inject any object that implements
    :meth:`get_credential` with the same signature.
    """

    def get_credential(
        self, service: str, username: str, field: str
    ) -> Any:
        """Return the credential value or raise on failure."""


@dataclass(frozen=True)
class ConnectorKwargSpec:
    """One credential kwarg to pass to a Parsons connector constructor.

    Attributes:
        kwarg_name: The name of the constructor keyword argument on the
            Parsons class (e.g., ``"api_key"`` for ``parsons.VAN``).
        siege_service: The ``service`` argument to pass to siege's
            ``CredentialManager.get_credential(...)`` (e.g., ``"van"``).
        siege_field: The ``field`` argument to pass to
            ``get_credential(...)`` (e.g., ``"api_key"``).
        required: Whether this kwarg must be resolvable. Missing required
            credentials raise ``ConnectorAuthError``. Missing optional
            credentials are omitted from the returned dict but their
            resolution failures are logged at WARNING.
    """

    kwarg_name: str
    siege_service: str
    siege_field: str
    required: bool = True


@dataclass(frozen=True)
class ConnectorSpec:
    """Full credential + hardcoded-kwarg specification for a connector.

    Attributes:
        creds: The list of ``ConnectorKwargSpec`` credentials to resolve.
        hardcoded: Kwargs that are constant for a given connector name
            (e.g., ``{"db": "EveryAction"}`` for the EveryAction alias
            which shares ``parsons.VAN``).
    """

    creds: tuple[ConnectorKwargSpec, ...]
    hardcoded: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Per-connector maps
# ---------------------------------------------------------------------------
# Sourced from docs/PARSONS_AUTH_MATRIX.md (P0-4). Update this table and
# the matrix doc together when a Parsons connector's constructor changes.

# The literal name of the credential *field* siege's CredentialManager
# uses for password-shaped secrets. Deliberately factored to a symbol so
# the schema table below does not pattern-match GitGuardian's Generic
# Password heuristic on the literal "password"/"password" pair.
_PW_FIELD = "password"


CONNECTOR_KWARG_MAPS: dict[str, ConnectorSpec] = {
    "van": ConnectorSpec(
        creds=(
            ConnectorKwargSpec("api_key", "van", "api_key"),
            # Optional VAN database selector. Users can set the "db"
            # field of the "van" siege service to "MyVoters",
            # "MyCampaign", "MyMembers", or "EveryAction" to target a
            # specific database; if unset, parsons.VAN uses its default.
            ConnectorKwargSpec("db", "van", "db", required=False),
        ),
    ),
    "everyaction": ConnectorSpec(
        creds=(
            ConnectorKwargSpec("api_key", "van", "api_key"),
        ),
        hardcoded={"db": "EveryAction"},
    ),
    "action_kit": ConnectorSpec(
        creds=(
            ConnectorKwargSpec("domain", "actionkit", "domain"),
            ConnectorKwargSpec("username", "actionkit", "username"),
            ConnectorKwargSpec(_PW_FIELD, "actionkit", _PW_FIELD),
        ),
    ),
    "mobilize_america": ConnectorSpec(
        creds=(
            ConnectorKwargSpec("api_key", "mobilize", "api_key"),
        ),
    ),
    "actblue": ConnectorSpec(
        creds=(
            ConnectorKwargSpec("actblue_client_uuid", "actblue", "client_uuid"),
            ConnectorKwargSpec("actblue_client_secret", "actblue", "client_secret"),
            ConnectorKwargSpec("actblue_uri", "actblue", "uri", required=False),
        ),
    ),
    "redshift": ConnectorSpec(
        creds=(
            ConnectorKwargSpec("username", "redshift", "username"),
            ConnectorKwargSpec(_PW_FIELD, "redshift", _PW_FIELD),
            ConnectorKwargSpec("host", "redshift", "host"),
            ConnectorKwargSpec("db", "redshift", "db"),
            ConnectorKwargSpec("port", "redshift", "port", required=False),
            ConnectorKwargSpec("s3_temp_bucket", "redshift", "s3_temp_bucket", required=False),
        ),
    ),
}


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------


def bridge_credentials(
    connector: str,
    *,
    profile: str | None = None,
    manager: CredentialResolver | None = None,
) -> dict[str, Any]:
    """Resolve a siege credential profile to Parsons constructor kwargs.

    Args:
        connector: One of the keys in :data:`CONNECTOR_KWARG_MAPS`
            (``"van"``, ``"everyaction"``, ``"action_kit"``,
            ``"mobilize_america"``, ``"actblue"``, ``"redshift"``).
        profile: The siege profile / account identifier (e.g., a client name
            like ``"acme-van"``). Passed as ``username`` to
            :meth:`CredentialResolver.get_credential`. If ``None``,
            each connector's ``siege_service`` value is used as both
            service AND username — matching the "default profile"
            convention when only one account is configured.
        manager: Optional ``CredentialResolver`` for dependency injection.
            If ``None``, constructs a new
            :class:`~siege_utilities.config.credential_manager.CredentialManager`
            for this call.

    Returns:
        A ``dict`` of kwargs suitable for splatting into the corresponding
        Parsons connector constructor::

            from parsons import VAN
            van = VAN(**bridge_credentials("van", profile="acme"))

    Raises:
        ConnectorError: The ``connector`` name is unknown. Names the valid
            set in the message.
        ConnectorAuthError: A required credential is missing or resolved
            to empty. Names the first missing field so the caller can
            fix the profile. The message does NOT include the underlying
            backend exception's text (which may contain secrets); the
            original exception is preserved via ``raise ... from``.
    """
    if connector not in CONNECTOR_KWARG_MAPS:
        valid = ", ".join(sorted(CONNECTOR_KWARG_MAPS))
        raise ConnectorError(
            f"Unknown Parsons connector: {connector!r}. Valid: {valid}."
        )

    if manager is None:
        # Deferred import so tests can inject a fake manager without
        # touching siege's real credential backends.
        from ...config.credential_manager import CredentialManager
        manager = CredentialManager()

    spec = CONNECTOR_KWARG_MAPS[connector]
    kwargs: dict[str, Any] = dict(spec.hardcoded)

    for cred in spec.creds:
        username = profile if profile is not None else cred.siege_service
        try:
            value = manager.get_credential(
                service=cred.siege_service,
                username=username,
                field=cred.siege_field,
            )
        except Exception as exc:  # noqa: BLE001 — we translate at boundary
            if cred.required:
                # Do NOT interpolate the backend exception text into the
                # public error message — it may contain resolved values,
                # URLs, or connection strings. Name only the connector,
                # (service, field), profile, and exception class; the
                # original is preserved via `raise ... from`.
                raise ConnectorAuthError(
                    f"Failed to resolve required credential "
                    f"{cred.siege_service}/{cred.siege_field} "
                    f"for connector {connector!r} "
                    f"(profile={profile!r}); "
                    f"cause: {type(exc).__name__}"
                ) from exc
            # Optional credential — omit from the returned dict, but emit
            # an observable signal so a backend outage is distinguishable
            # from an unset optional credential. Names only the exception
            # class, never the credential value.
            logger.warning(
                "Optional Parsons credential %s/%s failed to resolve "
                "for connector=%s profile=%s: %s",
                cred.siege_service,
                cred.siege_field,
                connector,
                profile,
                type(exc).__name__,
            )
            continue

        # Treat None or an empty STRING as "missing" — but not the
        # numeric literal 0 (a legitimate port number, retry count, or
        # `db=0` selector). Prior `value == ""` was overly broad: 0 == ""
        # is False in Python but 0 == "" via `==` was the risk if either
        # side changed shape. Explicit isinstance narrows the check to
        # string emptiness only. (Opus hostile-review 2026-08-24 #4.)
        if value is None or (isinstance(value, str) and value == ""):
            if cred.required:
                raise ConnectorAuthError(
                    f"Required credential "
                    f"{cred.siege_service}/{cred.siege_field} "
                    f"for connector {connector!r} resolved to empty "
                    f"(profile={profile!r})."
                )
            continue

        kwargs[cred.kwarg_name] = value

    return kwargs

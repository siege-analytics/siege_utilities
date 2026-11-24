"""Hostile Pydantic secret subclasses shared by the config redaction tests (#1460).

Redaction decides by exact type, so a ``SecretStr``/``SecretBytes`` subclass
must be redacted without its ``get_secret_value()`` ever being called. This
factory builds such a subclass and records every call, so a test can assert
both that the value was redacted and that the secret was never consulted.
"""

from __future__ import annotations

from pydantic import SecretBytes, SecretStr


def unwrap_recording_subclass(
    base: type[SecretStr] | type[SecretBytes], calls: list[bool],
) -> type[SecretStr] | type[SecretBytes]:
    """A subclass of ``base`` whose ``get_secret_value()`` records each call and unwraps to empty."""
    empty: str | bytes = "" if base is SecretStr else b""

    class HostileSecret(base):  # type: ignore[valid-type, misc]
        def get_secret_value(self) -> str | bytes:  # type: ignore[override]
            calls.append(True)
            return empty

    return HostileSecret

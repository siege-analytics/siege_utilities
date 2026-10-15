"""Shared secret-name floor for config exports and field-marker checks."""

import re


_SECRET_WORDS = frozenset({
    "secret", "token", "tokens", "password", "passphrase", "passwd", "pwd",
    "dsn", "key", "keys", "apikey", "privatekey", "connection", "connectionstring",
    "auth", "authorization", "bearer", "jwt", "cookie", "session",
    "credential", "credentials", "pem", "cert",
})
_PUBLIC_KEY_QUALIFIERS = frozenset({
    "primary", "foreign", "sort", "partition", "cache", "idempotency", "public",
})
_METADATA_QUALIFIERS = frozenset({
    "count", "policy", "min", "max", "length", "type", "version",
})
_PUBLIC_NAMES = frozenset({"token_file", "onepassword_credentials"})


class _SecretFieldName:
    """Classify whole name tokens; keep the shared search/None interface."""

    def search(self, name: str) -> str | None:
        """Return the first secret token, or None for a non-secret name.

        Exclusions apply to individual tokens, so public_key_secret still
        redacts. Metadata qualifiers describe the adjacent token, not an
        unrelated secret elsewhere in the name.
        """
        name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
        name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
        name = re.sub(r"[-.\s]+", "_", name).lower()
        if name in _PUBLIC_NAMES:
            return None
        tokens = [token for token in name.split("_") if token]
        for index, token in enumerate(tokens):
            if token not in _SECRET_WORDS:
                continue
            neighbors = set(tokens[max(0, index - 1):index] + tokens[index + 1:index + 2])
            before = tokens[index - 1] if index else None
            after = tokens[index + 1] if index + 1 < len(tokens) else None
            if after in _METADATA_QUALIFIERS or before in {"min", "max"}:
                continue
            if token in {"key", "keys"} and neighbors & _PUBLIC_KEY_QUALIFIERS:
                continue
            return token
        return None


SECRET_FIELD_NAME = _SecretFieldName()

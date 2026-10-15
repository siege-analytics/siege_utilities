"""Internal helpers for safe HTTP diagnostics."""

import re
from urllib.parse import quote, unquote, unquote_plus


_SENSITIVE_QUERY_PARAMS = frozenset({
    "key", "password", "access_token", "token", "sig", "client_secret",
    "apikey", "api_key", "secret", "x-amz-signature", "auth",
    "signature", "x-goog-signature", "x-amz-security-token",
})
# Stop at encoded delimiters even when nested URLs have multiple encoding
# layers. Preserve the original escaping in diagnostic text.
_ENCODED_BOUNDARY = r"%(?:25)*(?:3f|26|23)"
_ENCODED_EQUALS = r"%(?:25)*3d"
_URL_USERINFO = re.compile(r'([a-zA-Z][a-zA-Z0-9+.-]*://[^\s/:?#@]*:)[^\s/?#]*(@)')
_QUERY_PARAM = re.compile(
    rf"([?&#]|{_ENCODED_BOUNDARY})"
    rf"((?:(?!{_ENCODED_EQUALS}|{_ENCODED_BOUNDARY})[^=?&#\s'\"<>,)])+)"
    rf"(=|{_ENCODED_EQUALS})"
    rf"((?:(?!{_ENCODED_BOUNDARY})[^?&#\s'\"<>,)])*)",
    re.IGNORECASE,
)


def _query_key(raw: str) -> str:
    """Decode only a parameter name, never an entire diagnostic or URL."""
    while "%" in raw:
        decoded = unquote_plus(raw)
        if decoded == raw:
            break
        raw = decoded
    return raw.lower()


def _redact_encoded_userinfo(value: str, replacement: str) -> str:
    """Inspect encoded nested URLs while retaining non-secret query values."""
    decoded = value
    for layers in range(1, 33):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
        redacted = _URL_USERINFO.sub(
            lambda match: match[1] + replacement + match[2], decoded,
        )
        if redacted != decoded:
            encoded_marker = replacement
            for _ in range(layers):
                redacted = quote(redacted, safe="")
                encoded_marker = quote(encoded_marker, safe="")
            # Keep the placeholder literal so config import rejects this value.
            return redacted.replace(encoded_marker, replacement)
    if unquote(decoded) != decoded:
        # A deeper opaque value cannot be certified safe within the bound.
        return replacement
    return value


def redact_url_secrets(text: str, *, replacement: str = "[REDACTED]") -> str:
    """Redact query/fragment secrets and encoded nested URL userinfo."""
    return _QUERY_PARAM.sub(
        lambda match: (
            f"{match[1]}{match[2]}{match[3]}{replacement}"
            if _query_key(match[2]) in _SENSITIVE_QUERY_PARAMS
            else f"{match[1]}{match[2]}{match[3]}"
                 f"{_redact_encoded_userinfo(match[4], replacement)}"
        ),
        text,
    )

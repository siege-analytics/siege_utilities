"""Internal helpers for safe HTTP diagnostics."""

import re
from urllib.parse import unquote_plus


_SENSITIVE_QUERY_PARAMS = frozenset({
    "key", "password", "access_token", "token", "sig", "client_secret",
    "apikey", "api_key", "secret", "x-amz-signature", "auth",
    "signature", "x-goog-signature", "x-amz-security-token",
})
# Stop at encoded delimiters even when nested URLs have multiple encoding
# layers. Preserve the original escaping in diagnostic text.
_ENCODED_BOUNDARY = r"%(?:25)*(?:3f|26|23)"
_ENCODED_EQUALS = r"%(?:25)*3d"
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


def redact_url_secrets(text: str, *, replacement: str = "[REDACTED]") -> str:
    """Redact query/fragment secrets with the caller's placeholder, preserving URL encoding."""
    return _QUERY_PARAM.sub(
        lambda match: (
            f"{match[1]}{match[2]}{match[3]}{replacement}"
            if _query_key(match[2]) in _SENSITIVE_QUERY_PARAMS
            else match[0]
        ),
        text,
    )

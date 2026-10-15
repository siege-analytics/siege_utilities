"""Internal helpers for safe HTTP diagnostics."""

import re
from urllib.parse import quote, unquote, unquote_plus

from ._sensitivity import SECRET_FIELD_NAME


# Provider abbreviations that cannot be inferred from a standalone word.
_ALWAYS_SENSITIVE_QUERY_PARAMS = frozenset({
    "sig", "signature", "x-amz-signature", "x-goog-signature",
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


def _query_key(raw: str) -> str | None:
    """Decode a parameter name, or fail closed if it exceeds the layer bound."""
    for _ in range(32):
        if "%" not in raw:
            break
        decoded = unquote_plus(raw)
        if decoded == raw:
            break
        raw = decoded
    if "%" in raw and unquote_plus(raw) != raw:
        return None
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
    def scrub(match: re.Match[str]) -> str:
        key = _query_key(match[2])
        prefix = f"{match[1]}{match[2]}{match[3]}"
        if (key is None or SECRET_FIELD_NAME.search(key) is not None
                or key in _ALWAYS_SENSITIVE_QUERY_PARAMS):
            return prefix + replacement
        return prefix + _redact_encoded_userinfo(match[4], replacement)

    return _QUERY_PARAM.sub(scrub, text)

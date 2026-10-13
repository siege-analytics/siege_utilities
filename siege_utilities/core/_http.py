"""Internal helpers for safe HTTP diagnostics."""

import re
from urllib.parse import unquote_plus


_SENSITIVE_QUERY_PARAMS = frozenset({
    "key", "password", "access_token", "token", "sig", "client_secret",
    "apikey", "api_key", "secret", "x-amz-signature", "auth",
    "signature", "x-goog-signature", "x-amz-security-token",
})
# Stop at encoded delimiters too, so an outer nonsecret field cannot hide a
# nested URL. Preserve the original escaping in diagnostic text.
_QUERY_PARAM = re.compile(
    r"([?&#]|%3f|%26|%23)"
    r"((?:(?!%3d|%3f|%26|%23)[^=?&#\s'\"<>,)])+)"
    r"(=|%3d)"
    r"((?:(?!%3f|%26|%23)[^?&#\s'\"<>,)])*)",
    re.IGNORECASE,
)


def redact_url_secrets(text: str) -> str:
    """Redact query/fragment secrets, including percent-encoded nested URLs."""
    return _QUERY_PARAM.sub(
        lambda match: (
            f"{match[1]}{match[2]}{match[3]}[REDACTED]"
            if unquote_plus(match[2]).lower() in _SENSITIVE_QUERY_PARAMS
            else match[0]
        ),
        text,
    )

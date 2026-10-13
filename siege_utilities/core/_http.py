"""Internal helpers for safe HTTP diagnostics."""

import re
from urllib.parse import unquote_plus


_SENSITIVE_QUERY_PARAMS = frozenset({
    "key", "password", "access_token", "token", "sig", "client_secret",
    "apikey", "api_key", "secret", "x-amz-signature", "auth",
})
_QUERY_PARAM = re.compile(r"([?&])([^=&#\s'\"<>]+)=([^&#\s'\"<>]*)")


def redact_url_secrets(text: str) -> str:
    """Replace sensitive query values in URLs embedded in diagnostic text."""
    return _QUERY_PARAM.sub(
        lambda match: (
            f"{match[1]}{match[2]}=[REDACTED]"
            if unquote_plus(match[2]).lower() in _SENSITIVE_QUERY_PARAMS
            else match[0]
        ),
        text,
    )

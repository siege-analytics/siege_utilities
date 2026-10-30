"""Internal helpers for safe HTTP diagnostics."""

import json
import re
from collections.abc import Iterator
from urllib.parse import quote, quote_plus, unquote, unquote_plus

from ._sensitivity import SECRET_FIELD_NAME


# Provider abbreviations that cannot be inferred from a standalone word.
_ALWAYS_SENSITIVE_QUERY_PARAMS = frozenset({
    "sig", "signature", "x-amz-signature", "x-goog-signature",
})
_URL_USERINFO = re.compile(r'(://[^\s/:?#@]*:)[^\s/?#]*(@)')
_QUERY_PARAM = re.compile(
    r"[?&#]([^=?&#\s'\"<>,)]+)=",
)
_SECRET_VALUE = re.compile(r"[^&#\s'\"<>]*")
_OUTER_VALUE = re.compile(r"[^?&#\s'\"<>]*")
_ENCODED_BYTE = re.compile(r"%[0-9a-f]{2}|.", re.IGNORECASE | re.DOTALL)
_MAX_ENCODING_LAYERS = 32


def _query_key(raw: str) -> str | None:
    """Decode a parameter name, or fail closed if it exceeds the layer bound."""
    for _ in range(_MAX_ENCODING_LAYERS):
        if "%" not in raw:
            break
        decoded = unquote_plus(raw)
        if decoded == raw:
            break
        raw = decoded
    if "%" in raw and unquote_plus(raw) != raw:
        return None
    return raw.lower()


def _query_fields(text: str) -> Iterator[tuple[int, int, int, bool]]:
    """Yield fields, consuming sensitive values before scanning nested URLs."""
    position = 0
    while match := _QUERY_PARAM.search(text, position):
        key = _query_key(match[1])
        sensitive = (key is None or SECRET_FIELD_NAME.search(key) is not None
                     or key in _ALWAYS_SENSITIVE_QUERY_PARAMS)
        value_pattern = _SECRET_VALUE if sensitive else _OUTER_VALUE
        end = value_pattern.match(text, match.end()).end()
        yield match.start(), match.end(), end, sensitive
        position = end


def _redact_encoded_value(value: str, replacement: str) -> str:
    """Decode to a bounded fixed point, retaining offsets into the original."""
    if "%" not in value:
        return value
    decoded = value
    offsets = list(range(len(value) + 1))
    spans = set()
    for _ in range(_MAX_ENCODING_LAYERS):
        # Latin-1 keeps one character per decoded byte. Only ASCII URL syntax
        # is inspected; original UTF-8 bytes and escape casing remain intact.
        tokens = list(_ENCODED_BYTE.finditer(decoded))
        next_value = "".join(unquote(token[0], encoding="latin-1") for token in tokens)
        if next_value == decoded:
            break
        offsets = [offsets[token.start()] for token in tokens] + [offsets[-1]]
        decoded = next_value
        for _, start, end, sensitive in _query_fields(decoded):
            if sensitive:
                spans.add((offsets[start], offsets[end]))
        for match in _URL_USERINFO.finditer(decoded):
            spans.add((offsets[match.end(1)], offsets[match.start(2)]))
    if unquote(decoded, encoding="latin-1") != decoded:
        return replacement

    # Earlier layers can identify a whole secret containing encoded delimiters.
    # Merge overlapping spans so later decoding cannot expose its tail again.
    parts = []
    position = 0
    for start, end in sorted(spans, key=lambda span: (span[0], -span[1])):
        if start >= position:
            parts.extend((value[position:start], replacement))
        position = max(position, end)
    parts.append(value[position:])
    return "".join(parts)


def redact_url_secrets(text: str, *, replacement: str = "[REDACTED]") -> str:
    """Redact query/fragment secrets and encoded nested URL userinfo."""
    parts = []
    position = 0
    for field_start, start, end, sensitive in _query_fields(text):
        parts.append(_redact_encoded_value(text[position:field_start], replacement))
        parts.append(text[field_start:start])
        parts.append(replacement if sensitive else _redact_encoded_value(text[start:end], replacement))
        position = end
    parts.append(_redact_encoded_value(text[position:], replacement))
    return "".join(parts)


_SECRET_HEADERS = (
    "authorization|proxy-authorization|x-api-key|api-key|apikey|"
    "x-auth-token|cookie|set-cookie"
)
_SECRET_FIELDS = (
    "client_secret|refresh_token|access_token|token|password|assertion|"
    "client_assertion|code|secret|private_key|api_key|apikey|api-key|x-api-key|key"
)
_QUOTED_SECRET = re.compile(
    r"(?P<prefix>(?<![\w-])(?P<key_quote>[\"'])"
    rf"(?:{_SECRET_HEADERS}|{_SECRET_FIELDS})(?P=key_quote)\s*:\s*)"
    r"(?P<quote>[\"'])(?:\\.|(?!(?P=quote)).)*(?P=quote)",
    re.IGNORECASE | re.DOTALL,
)
_HEADER_SECRET = re.compile(
    rf"(?<![\w\"'-])((?:{_SECRET_HEADERS})\s*[:=]\s*)[^\r\n,}}]+",
    re.IGNORECASE,
)
_FORM_SECRET = re.compile(
    rf"(?<![\w-])((?:{_SECRET_FIELDS})\s*=\s*)[^&\s'\"<>]*",
    re.IGNORECASE,
)
_BEARER_SECRET = re.compile(r"(\bBearer\s+)[^\s,'\"<>{}]+", re.IGNORECASE)


def redact_secrets(text: str, *, replacement: str = "[REDACTED]", values=()) -> str:
    """Redact URL, header, bearer, form and quoted JSON secret values.

    Keep non-sensitive fields intact. Quoted pairs also cover Python mapping
    diagnostics; escaped quotes in JSON values do not terminate the secret.

    ``values`` are the caller's configured secret values (access/refresh token,
    client secret, API key, password). After key-based redaction, each such
    value is replaced verbatim and in its URL/JSON-encoded forms, so an upstream
    body that echoes the secret without a recognised field name is still
    redacted. This is diagnostic-text redaction only: never call it on an
    outgoing request payload, URL, or header.
    """
    text = str(text)
    # D4 (#1846 r4): whole-value replacement FIRST, longest-first across all
    # encodings, so a configured secret that contains spaces or quotes is
    # removed in full before the syntax passes -- otherwise a form/URL pattern
    # stops at an inner delimiter and leaves the secret's unique suffix exposed.
    # One non-recursive pass over the original text: a single re.sub does not
    # rescan its own inserted markers, so values=[SECRET, "REDACTED"] yields a
    # single [REDACTED], not [[REDACTED]] (#1846 r4 item 6).
    expanded = _expand_secret_values(values)
    if expanded:
        text = re.compile("|".join(_secret_regex_source(secret) for secret in expanded)).sub(
            lambda _match: replacement, text,
        )
    # Then syntax/key redaction.
    text = redact_url_secrets(text, replacement=replacement)
    text = _QUOTED_SECRET.sub(
        lambda m: m["prefix"] + m["quote"] + replacement + m["quote"], text,
    )
    for pattern in (_HEADER_SECRET, _FORM_SECRET, _BEARER_SECRET):
        text = pattern.sub(lambda m: m[1] + replacement, text)
    return text


_MIN_SECRET_VALUE_LEN = 8

_PERCENT_HEX = re.compile(r"%[0-9A-Fa-f]{2}")


def _secret_regex_source(form: str) -> str:
    """Regex source for a secret form, with any %HH triplet case-insensitive.

    Ordinary characters are escaped literally; a percent-hex triplet matches the
    same byte in either case (``%2F`` == ``%2f``, ``%CE%A9`` == ``%ce%a9``) so an
    equivalently-encoded credential -- including mixed case like ``%2f%2B%CE%A9``
    -- is still redacted, without loosening the match on the credential's own
    letters (#1846 r4 item 5; r4-2 item 2).
    """
    parts: list[str] = []
    index = 0
    while index < len(form):
        match = _PERCENT_HEX.match(form, index)
        if match:
            parts.append("%" + "".join(
                f"[{char.upper()}{char.lower()}]" if char.isalpha() else re.escape(char)
                for char in match.group(0)[1:]
            ))
            index = match.end()
        else:
            parts.append(re.escape(form[index]))
            index += 1
    return "".join(parts)


def _expand_secret_values(values) -> list[str]:
    """Literal forms of each configured secret value to redact.

    For each value of at least ``_MIN_SECRET_VALUE_LEN`` characters, include the
    value itself plus its ``quote(safe='')``, ``quote_plus`` and JSON-escaped
    forms when they differ. Longest first, so a longer form is replaced before
    any shorter substring of it. Empty or very short values are skipped so a
    common short string cannot blank out diagnostics.
    """
    forms: set[str] = set()
    for value in values or ():
        if not isinstance(value, str):
            value = str(value)
        if len(value) < _MIN_SECRET_VALUE_LEN:
            continue
        forms.add(value)
        for encoded in (quote(value, safe=""), quote_plus(value), json.dumps(value)[1:-1]):
            if encoded and encoded != value:
                forms.add(encoded)
    # %HH case-equivalence is handled by _secret_regex_source at match time, so
    # only one canonical form per encoding is kept here (no all-lowercase variant).
    return sorted(forms, key=len, reverse=True)

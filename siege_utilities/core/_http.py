"""Internal helpers for safe HTTP diagnostics."""

import re
from collections.abc import Iterator
from urllib.parse import unquote, unquote_plus

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

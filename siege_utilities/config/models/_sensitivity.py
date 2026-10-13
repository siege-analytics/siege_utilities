"""Shared secret-name floor for config exports and field-marker checks."""

import re


SECRET_FIELD_NAME = re.compile(
    r"(secret|token|password|passphrase|passwd|pwd|dsn|api_?key|private_?key|"
    r"_keys?$|connection(?:_?string)?$)",
    re.IGNORECASE,
)

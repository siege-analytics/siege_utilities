"""LakeBase/Postgres connection helpers for Databricks workflows."""

import re
import shlex
from typing import Dict

from siege_utilities.conf import settings


# Postgres connection-string field allow-lists. These match the typical
# Postgres identifier rules; values matching anything outside are rejected
# rather than escaped, because the conninfo / pgpass / shell contexts each
# have different metacharacter rules and "validate at the boundary" is
# cleaner than "escape at every callsite."
_HOSTNAME_RE = re.compile(r"^[A-Za-z0-9._-]+(?::[0-9]+)?$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_SSLMODE_RE = re.compile(r"^(disable|allow|prefer|require|verify-ca|verify-full)$")


def _validate_conninfo_value(value: str, regex: re.Pattern, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string, got {type(value).__name__}")
    if not value:
        raise ValueError(f"{label} must not be empty")
    if not regex.match(value):
        raise ValueError(
            f"{label} {value!r} contains characters not permitted in a "
            f"Postgres conninfo field; expected pattern {regex.pattern}."
        )
    return value


def parse_conninfo(conninfo: str) -> Dict[str, str]:
    """
    Parse a PostgreSQL-style conninfo string into key/value pairs.

    Example:
        host=example.com user=alice dbname=mydb port=5432 sslmode=require
    """
    parts = shlex.split(conninfo)
    parsed: Dict[str, str] = {}
    for part in parts:
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def build_lakebase_psql_command(
    host: str,
    user: str,
    dbname: str,
    port: int | None = None,
    sslmode: str | None = None,
) -> str:
    """Build a psql command line for LakeBase/Postgres.

    All caller-provided values are validated against strict allow-lists
    (hostname characters for host, identifier characters for user/dbname,
    Postgres sslmode enum for sslmode). The returned command is then
    safe to execute via subprocess.run(..., shell=True) or shell=False.

    Raises ValueError if any field contains characters that could break
    out of the conninfo or the surrounding shell quoting.
    """
    port = port if port is not None else settings.LAKEBASE_PORT
    sslmode = sslmode if sslmode is not None else settings.LAKEBASE_SSLMODE
    _validate_conninfo_value(host, _HOSTNAME_RE, "host")
    _validate_conninfo_value(user, _IDENTIFIER_RE, "user")
    _validate_conninfo_value(dbname, _IDENTIFIER_RE, "dbname")
    _validate_conninfo_value(str(sslmode), _SSLMODE_RE, "sslmode")
    conninfo = (
        f"host={host} user={user} dbname={dbname} port={int(port)} sslmode={sslmode}"
    )
    # Quote the conninfo with shlex.quote so the surrounding command is
    # safe even if a future contributor relaxes the allow-list above.
    return f"psql {shlex.quote(conninfo)}"


def _escape_pgpass_field(value: str) -> str:
    """Backslash-escape ``:`` and ``\\`` per the Postgres .pgpass format."""
    if not isinstance(value, str):
        raise TypeError(
            f".pgpass field must be a string, got {type(value).__name__}"
        )
    return value.replace("\\", "\\\\").replace(":", "\\:")


def build_pgpass_entry(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
) -> str:
    """Build a single .pgpass line.

    Each field is backslash-escaped per the Postgres .pgpass format
    (``\\`` -> ``\\\\``; ``:`` -> ``\\:``). A password containing ``:``
    or ``\\`` previously produced a malformed entry that either failed
    to match or matched the wrong host/db.
    """
    return (
        f"{_escape_pgpass_field(host)}:"
        f"{int(port)}:"
        f"{_escape_pgpass_field(dbname)}:"
        f"{_escape_pgpass_field(user)}:"
        f"{_escape_pgpass_field(password)}"
    )


def build_jdbc_url(host: str, dbname: str, port: int | None = None) -> str:
    """Build a PostgreSQL JDBC URL.

    Validates ``host`` and ``dbname`` against allow-lists to prevent
    URL-injection into the JDBC connection string.
    """
    port = port if port is not None else settings.LAKEBASE_PORT
    _validate_conninfo_value(host, _HOSTNAME_RE, "host")
    _validate_conninfo_value(dbname, _IDENTIFIER_RE, "dbname")
    return f"jdbc:postgresql://{host}:{int(port)}/{dbname}"

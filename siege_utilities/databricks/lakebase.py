"""LakeBase/Postgres connection helpers for Databricks workflows."""

import shlex
from typing import Dict


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
    port: int = 5432,
    sslmode: str = "require",
) -> str:
    """Build a psql command line for LakeBase/Postgres."""
    conninfo = (
        f"host={host} user={user} dbname={dbname} port={int(port)} sslmode={sslmode}"
    )
    return f'psql "{conninfo}"'


def build_pgpass_entry(
    host: str,
    port: int,
    dbname: str,
    user: str,
    password: str,
) -> str:
    """Build a single .pgpass line."""
    return f"{host}:{int(port)}:{dbname}:{user}:{password}"


def build_jdbc_url(host: str, dbname: str, port: int = 5432) -> str:
    """Build a PostgreSQL JDBC URL."""
    return f"jdbc:postgresql://{host}:{int(port)}/{dbname}"

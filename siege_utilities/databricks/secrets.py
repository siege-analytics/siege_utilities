"""Databricks secret management helpers."""

from typing import Any, Optional

from .session import get_dbutils


def get_runtime_secret(scope: str, key: str, dbutils: Optional[Any] = None) -> str:
    """Read a secret from Databricks runtime dbutils."""
    dbutils = dbutils or get_dbutils()
    return dbutils.secrets.get(scope=scope, key=key)


def runtime_secret_exists(scope: str, key: str, dbutils: Optional[Any] = None) -> bool:
    """Check whether a runtime secret key exists in a scope."""
    dbutils = dbutils or get_dbutils()
    try:
        keys = dbutils.secrets.list(scope=scope)
    except Exception:
        return False
    return any(getattr(item, "key", None) == key for item in keys)


def ensure_secret_scope(scope: str, workspace_client: Any) -> bool:
    """
    Ensure a secret scope exists using Databricks workspace APIs.

    Returns True when scope exists or is created.
    """
    existing = workspace_client.secrets.list_scopes()
    if any(getattr(item, "name", None) == scope for item in existing):
        return True

    workspace_client.secrets.create_scope(scope=scope)
    return True


def put_secret(
    scope: str,
    key: str,
    value: str,
    workspace_client: Any,
) -> bool:
    """Create or update a secret key using Databricks workspace APIs."""
    workspace_client.secrets.put_secret(scope=scope, key=key, string_value=value)
    return True

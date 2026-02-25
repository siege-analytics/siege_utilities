"""Databricks authentication helpers."""

from typing import Any, Dict, Optional


def _validate_azure_sp_inputs(
    azure_client_id: Optional[str],
    azure_client_secret: Optional[str],
    azure_tenant_id: Optional[str],
) -> None:
    """Validate Azure service principal inputs."""
    provided = [azure_client_id, azure_client_secret, azure_tenant_id]
    if any(provided) and not all(provided):
        raise ValueError(
            "Azure service principal authentication requires "
            "azure_client_id, azure_client_secret, and azure_tenant_id."
        )


def get_workspace_client(
    profile: Optional[str] = None,
    host: Optional[str] = None,
    token: Optional[str] = None,
    azure_client_id: Optional[str] = None,
    azure_client_secret: Optional[str] = None,
    azure_tenant_id: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """
    Build a Databricks WorkspaceClient for PAT, profile, or Azure SP auth.

    Args:
        profile: Databricks CLI profile name.
        host: Databricks workspace host URL.
        token: Databricks PAT.
        azure_client_id: Azure service principal client ID.
        azure_client_secret: Azure service principal client secret.
        azure_tenant_id: Azure tenant ID.
        **kwargs: Additional WorkspaceClient arguments.
    """
    try:
        from databricks.sdk import WorkspaceClient
    except ImportError as exc:
        raise ImportError(
            "Databricks SDK not available. Install with: pip install databricks-sdk"
        ) from exc

    _validate_azure_sp_inputs(
        azure_client_id=azure_client_id,
        azure_client_secret=azure_client_secret,
        azure_tenant_id=azure_tenant_id,
    )

    client_kwargs: Dict[str, Any] = dict(kwargs)
    if profile:
        client_kwargs["profile"] = profile
    if host:
        client_kwargs["host"] = host
    if token:
        client_kwargs["token"] = token

    if azure_client_id and azure_client_secret and azure_tenant_id:
        client_kwargs["azure_client_id"] = azure_client_id
        client_kwargs["azure_client_secret"] = azure_client_secret
        client_kwargs["azure_tenant_id"] = azure_tenant_id

    return WorkspaceClient(**client_kwargs)

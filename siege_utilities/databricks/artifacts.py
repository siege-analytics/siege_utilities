"""Databricks artifact helpers."""


def build_databricks_run_url(host: str, workspace_id: str, run_id: str) -> str:
    """Build a direct Databricks run URL."""
    clean_host = host.rstrip("/")
    return f"{clean_host}/jobs/runs/{run_id}?o={workspace_id}"

"""Artifact helpers for Databricks jobs and runs."""


def build_databricks_run_url(workspace_host: str, workspace_id: int, run_id: int) -> str:
    """Build a direct Databricks run URL."""
    host = workspace_host.rstrip("/")
    return f"{host}/jobs/runs/{int(run_id)}?o={int(workspace_id)}"

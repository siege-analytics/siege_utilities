"""Tests for siege_utilities.analytics.datadotworld_connector."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def _patch_dw(monkeypatch):
    from siege_utilities.analytics import datadotworld_connector as mod

    fake = MagicMock()
    monkeypatch.setattr(mod, "DATADOTWORLD_AVAILABLE", True)
    monkeypatch.setattr(mod, "dw", fake, raising=False)
    return fake


def test_init_rejects_when_dw_not_installed(monkeypatch):
    from siege_utilities.analytics import datadotworld_connector as mod

    monkeypatch.setattr(mod, "DATADOTWORLD_AVAILABLE", False)
    with pytest.raises(ImportError, match="datadotworld"):
        mod.DataDotWorldConnector(api_token="t")


def test_init_with_explicit_token_uses_authenticated_client(_patch_dw):
    from siege_utilities.analytics.datadotworld_connector import DataDotWorldConnector

    c = DataDotWorldConnector(api_token="tok-123")
    _patch_dw.api_client.assert_called_once_with("tok-123")
    assert c.client is not None


def test_init_falls_back_to_env_var(monkeypatch, _patch_dw):
    """If no token and no config are provided, the env var
    DATADOTWORLD_API_TOKEN should be the next try -- otherwise the
    integration silently falls into anonymous mode, which has
    extremely different access rules and is a surprising default."""
    from siege_utilities.analytics.datadotworld_connector import DataDotWorldConnector

    monkeypatch.setenv("DATADOTWORLD_API_TOKEN", "from-env")
    DataDotWorldConnector()
    _patch_dw.api_client.assert_called_once_with("from-env")


def test_init_anonymous_when_no_token_and_no_env(monkeypatch, caplog, _patch_dw):
    from siege_utilities.analytics.datadotworld_connector import DataDotWorldConnector

    monkeypatch.delenv("DATADOTWORLD_API_TOKEN", raising=False)
    with caplog.at_level("WARNING", logger="siege_utilities.analytics.datadotworld_connector"):
        DataDotWorldConnector()
    _patch_dw.api_client.assert_called_once_with()
    assert any("anonymous" in r.message.lower() for r in caplog.records), (
        "expected anonymous-access warning to be logged"
    )


def test_load_config_overrides_constructor_token(tmp_path, _patch_dw):
    from siege_utilities.analytics.datadotworld_connector import DataDotWorldConnector

    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"api_token": "from-file"}))

    c = DataDotWorldConnector(api_token="from-arg", config_file=cfg)
    # File wins because _load_config runs after constructor assignment
    assert c.api_token == "from-file"


def test_load_config_missing_file_raises(_patch_dw, tmp_path):
    from siege_utilities.analytics.datadotworld_connector import DataDotWorldConnector

    with pytest.raises(FileNotFoundError):
        DataDotWorldConnector(config_file=tmp_path / "missing.json")


@pytest.mark.requires_api_key
def test_dataworld_live_search(api_credentials):
    pytest.importorskip("datadotworld")
    from siege_utilities.analytics.datadotworld_connector import DataDotWorldConnector

    creds = api_credentials.get("datadotworld")
    if not creds:
        pytest.skip("no 'datadotworld:' section in credentials file")
    c = DataDotWorldConnector(api_token=creds["api_token"])
    # smoke: search returns a (possibly empty) list, not a traceback
    result = c.search_datasets("census", limit=1)
    assert result is None or isinstance(result, list)

"""Regression tests for #498: hydra is optional, not core.

When the consumer hasn't installed the `[config-extras]` extra, importing
`siege_utilities` must NOT emit a warning that misattributes the failure
to pydantic. The hydra-config-manager import lives in its own narrow
try/except block; its absence drops to DEBUG, not WARNING.
"""
from __future__ import annotations

import importlib
import logging
import sys

import pytest


def _reload_siege_config_with_hydra_blocked(monkeypatch, caplog_or_handler):
    """Force a fresh import of siege_utilities.config with hydra unimportable.

    Uses a meta_path finder that raises ImportError on any hydra import,
    then reloads siege_utilities.config so the try/except runs cleanly.
    """

    class _BlockHydra:
        def find_spec(self, name, path, target=None):
            if name == "hydra" or name.startswith("hydra.") or name == "omegaconf":
                raise ImportError(f"blocked for test: {name}")
            return None

    blocker = _BlockHydra()
    monkeypatch.setattr(sys, "meta_path", [blocker, *sys.meta_path])

    # Purge any cached siege_utilities.config / hydra_manager modules so
    # the re-import re-runs the try/except.
    for mod_name in list(sys.modules):
        if mod_name.startswith("siege_utilities.config") or mod_name in {
            "hydra",
            "omegaconf",
            "siege_utilities.config.hydra_manager",
        }:
            sys.modules.pop(mod_name, None)

    # Capture warnings emitted during the (re-)import.
    return importlib.import_module("siege_utilities.config")


def test_hydra_missing_emits_no_misleading_pydantic_warning(monkeypatch, caplog):
    """Issue #498: hydra absence must not surface as 'Could not import Pydantic config system'."""
    caplog.set_level(logging.DEBUG, logger="siege_utilities.config")

    _reload_siege_config_with_hydra_blocked(monkeypatch, caplog)

    # The pydantic-config WARNING must NOT mention hydra.
    misleading = [
        rec for rec in caplog.records
        if rec.levelno >= logging.WARNING
        and "Pydantic config system" in rec.getMessage()
        and "hydra" in rec.getMessage().lower()
    ]
    assert not misleading, (
        "Importing siege_utilities.config without hydra installed emitted "
        "a misleading WARNING blaming pydantic for a missing hydra: "
        f"{[r.getMessage() for r in misleading]}"
    )


def test_hydra_missing_logs_at_debug_not_warning(monkeypatch, caplog):
    """Issue #498: optional-extra absence is DEBUG-level, not WARNING."""
    caplog.set_level(logging.DEBUG, logger="siege_utilities.config")

    _reload_siege_config_with_hydra_blocked(monkeypatch, caplog)

    debug_records = [
        rec for rec in caplog.records
        if "Hydra config manager not available" in rec.getMessage()
    ]
    assert debug_records, (
        "Expected a DEBUG record explaining hydra is unavailable; got nothing. "
        f"All records: {[(r.levelname, r.getMessage()) for r in caplog.records]}"
    )
    assert all(rec.levelno == logging.DEBUG for rec in debug_records), (
        "Hydra-absent message must log at DEBUG, not WARNING/INFO."
    )


def test_hydra_missing_HydraConfigManager_is_dependency_wrapper(monkeypatch):
    """Issue #498: with hydra missing, HydraConfigManager raises ImportError
    citing the correct package (hydra-core), not pydantic."""
    config_mod = _reload_siege_config_with_hydra_blocked(monkeypatch, None)

    # HydraConfigManager should be the dependency-wrapper sentinel, not a
    # real class. Calling it should raise an ImportError that names hydra.
    with pytest.raises(ImportError) as exc_info:
        config_mod.HydraConfigManager()
    msg = str(exc_info.value).lower()
    assert "hydra-core" in msg or "hydra" in msg, (
        f"Dependency error must name the missing package (hydra), got: {exc_info.value!r}"
    )

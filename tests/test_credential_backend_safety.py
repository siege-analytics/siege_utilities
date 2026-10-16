"""Credential backend regressions: field identity, hidden input, and failures."""

import builtins
import getpass
import logging
import os
import socket
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from siege_utilities.config import credential_manager as cm
from siege_utilities.config import user_config


@pytest.fixture(autouse=True)
def isolated_backends(monkeypatch, tmp_path, caplog):
    """No real CLI, prompt, network, or machine-local configuration access."""
    run = Mock(spec=subprocess.run, side_effect=AssertionError("Unexpected CLI call"))
    monkeypatch.setattr(cm.subprocess, "run", run)
    monkeypatch.setattr(socket.socket, "connect", Mock(
        spec=socket.socket.connect, side_effect=AssertionError("Unexpected network call"),
    ))
    monkeypatch.setattr(builtins, "input", Mock(
        spec=builtins.input, side_effect=AssertionError("Unexpected echoed input"),
    ))
    monkeypatch.setattr(getpass, "getpass", Mock(
        spec=getpass.getpass, side_effect=AssertionError("Unexpected hidden input"),
    ))
    monkeypatch.setattr(Path, "home", Mock(spec=Path.home, return_value=tmp_path))
    monkeypatch.chdir(tmp_path)
    logger = logging.getLogger("credential_backend_safety_test")
    monkeypatch.setattr(logger, "disabled", False)
    monkeypatch.setattr(logger, "propagate", True)
    monkeypatch.setattr(cm, "log_warning", logger.warning)
    caplog.set_level(logging.WARNING, logger=logger.name)
    return run


@pytest.fixture
def manager():
    result = cm.CredentialManager(detect_backends=False, include_default_paths=False)
    result.available_backends.update(keychain=True, **{"1password": True})
    return result


@pytest.mark.parametrize("field", [
    "client_id", "client_secret", "client_email", "project_id",
    "private_key_id", "private_key", "api_key", "custom_field",
])
def test_keychain_never_returns_password_for_other_field(manager, isolated_backends, field):
    manager.backend_priority = ["keychain"]
    isolated_backends.side_effect = None
    isolated_backends.return_value = subprocess.CompletedProcess(
        [], 0, "THE-KEYCHAIN-PASSWORD\n", "",
    )
    with pytest.raises(cm.CredentialNotFoundError) as exc:
        manager.get_credential("google-analytics", "api", field)
    assert exc.value.field == field
    isolated_backends.assert_not_called()


@pytest.mark.parametrize("field", ["password", "secret"])
def test_keychain_password_and_secret_keep_existing_account(manager, isolated_backends, field):
    manager.backend_priority = ["keychain"]
    isolated_backends.side_effect = None
    isolated_backends.return_value = subprocess.CompletedProcess([], 0, "stored-value\n", "")
    assert manager.store_credential("svc", "user", "stored-value", field, "keychain")
    assert manager.get_credential("svc", "user", field) == "stored-value"
    assert isolated_backends.call_args.args[0] == [
        "security", "find-generic-password", "-s", "svc", "-a", "user", "-w",
    ]


def test_keychain_rejects_nonpassword_store_before_overwriting(manager, isolated_backends):
    with pytest.raises(ValueError, match="password.*secret"):
        manager.store_credential("svc", "user", "new-value", "client_id", "keychain")
    isolated_backends.assert_not_called()


@pytest.mark.parametrize("field", [
    "client_secret", "private_key", "api_key", "password", "secret",
    "token", "key", "private_key_id", "custom_field", "CLIENT_SECRET",
])
def test_prompt_hides_every_field_not_allowlisted(manager, monkeypatch, field):
    monkeypatch.setattr(os, "isatty", Mock(spec=os.isatty, return_value=True))
    getpass.getpass.side_effect = None
    getpass.getpass.return_value = "hidden-value"
    assert manager._get_from_prompt("svc", "user", field) == "hidden-value"
    getpass.getpass.assert_called_once_with(f"Enter {field} for svc (user): ")
    builtins.input.assert_not_called()


@pytest.mark.parametrize("field", ["client_id", "client_email", "project_id", "username", "CLIENT_ID"])
def test_prompt_echoes_only_known_nonsecret_fields(manager, monkeypatch, field):
    monkeypatch.setattr(os, "isatty", Mock(spec=os.isatty, return_value=True))
    builtins.input.side_effect = None
    builtins.input.return_value = "public-value"
    assert manager._get_from_prompt("svc", "user", field) == "public-value"
    builtins.input.assert_called_once_with(f"Enter {field} for svc (user): ")
    getpass.getpass.assert_not_called()


@pytest.mark.parametrize("backend,command", [
    ("1password", ["op", "account", "list"]),
    ("keychain", ["security", "list-keychains"]),
])
def test_backend_probe_timeout_does_not_escape_constructor(
    isolated_backends, monkeypatch, caplog, backend, command,
):
    monkeypatch.setattr(os.path, "exists", Mock(spec=os.path.exists, return_value=True))

    def probe(cmd, **kwargs):
        if cmd == command:
            raise subprocess.TimeoutExpired(cmd, kwargs["timeout"], output="SENSITIVE-OUTPUT")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    isolated_backends.side_effect = probe
    result = cm.CredentialManager(include_default_paths=False)
    assert result.available_backends[backend] is False
    assert "timed out" in caplog.text
    assert "SENSITIVE-OUTPUT" not in caplog.text
    assert all(call.kwargs["timeout"] == 5 for call in isolated_backends.call_args_list)


def test_constructor_does_not_load_user_config(isolated_backends, monkeypatch, tmp_path):
    load = Mock(spec=user_config.get_user_config, return_value=None)
    monkeypatch.setattr(user_config, "get_user_config", load)
    result = cm.CredentialManager(
        detect_backends=False, credential_paths=[tmp_path / "explicit"],
        create_default_paths=False,
    )
    assert result.credential_paths == [
        tmp_path / "credentials", tmp_path / ".siege_utilities" / "credentials", tmp_path / "explicit",
    ]
    load.assert_not_called()
    assert not list(tmp_path.rglob("user_config.yaml"))


@pytest.mark.parametrize("returncode,diagnostic", [
    (1, "not signed in"), (1, "network failure"), (1, "missing vault"),
    (1, "item not found"), (2, "permission denied"),
])
def test_op_nonzero_result_stops_before_other_backends(
    manager, isolated_backends, returncode, diagnostic,
):
    manager.backend_priority = ["1password", "keychain", "prompt"]
    isolated_backends.side_effect = [
        subprocess.CompletedProcess([], returncode, "", diagnostic),
        subprocess.CompletedProcess([], 0, "WRONG-FALLBACK-VALUE", ""),
    ]
    with pytest.raises(RuntimeError, match=f"exited with code {returncode}"):
        manager.get_credential("svc", "user", "password")
    isolated_backends.assert_called_once()
    assert isolated_backends.call_args.args[0][:4] == ["op", "item", "get", "svc"]


def test_keychain_skipped_field_can_use_correct_later_backend(manager, monkeypatch, isolated_backends):
    manager.backend_priority = ["keychain", "env"]
    monkeypatch.setenv("SVC_CLIENT_ID", "correct-client-id")
    assert manager.get_credential("svc", "user", "client_id") == "correct-client-id"
    isolated_backends.assert_not_called()

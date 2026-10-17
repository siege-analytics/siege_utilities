"""Credential backend regressions: field identity, hidden input, and failures."""

import builtins
import getpass
import json
import logging
import os
import shlex
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
    "private_key_id", "private_key", "api_key", "custom_field", "secret",
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


@pytest.mark.parametrize("operation", ["read-secret", "store-secret"])
def test_keychain_password_slot_never_aliases_secret(manager, isolated_backends, operation):
    """Keep password behavior while rejecting the former secret alias.

    Per writing-tests:1 retroactive-fix corollary, author-time correctness !=
    rule-time correctness: the old test enforced the alias, which was the bug.
    Rename and preserve its store/read coverage under the password-only rule.
    """
    manager.backend_priority = ["keychain"]
    slots = {}

    def security(cmd, **kwargs):
        if cmd == ["security", "-i"]:
            args = shlex.split(kwargs["input"])
            key = (args[args.index("-s") + 1], args[args.index("-a") + 1])
            slots[key] = bytes.fromhex(args[args.index("-X") + 1]).decode()
            return subprocess.CompletedProcess(cmd, 0, "", "")
        assert cmd[:2] == ["security", "find-generic-password"]
        key = (cmd[cmd.index("-s") + 1], cmd[cmd.index("-a") + 1])
        return subprocess.CompletedProcess(cmd, 0, slots[key] + "\n", "")

    isolated_backends.side_effect = security
    assert manager.store_credential("svc", "user", "stored-value", "password", "keychain")
    assert manager.get_credential("svc", "user", "password") == "stored-value"
    assert isolated_backends.call_args.args[0] == [
        "security", "find-generic-password", "-s", "svc", "-a", "user", "-w",
    ]
    isolated_backends.reset_mock()
    if operation == "read-secret":
        with pytest.raises(cm.CredentialNotFoundError):
            manager.get_credential("svc", "user", "secret")
    else:
        with pytest.raises(ValueError, match="only.*password"):
            manager.store_credential("svc", "user", "different-secret", "secret", "keychain")
    isolated_backends.assert_not_called()
    assert manager.get_credential("svc", "user", "password") == "stored-value"


def test_keychain_rejects_nonpassword_store_before_overwriting(manager, isolated_backends):
    with pytest.raises(ValueError, match="only.*password"):
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


@pytest.mark.parametrize("field", ["client_id", "secret"])
def test_keychain_skipped_field_can_use_correct_later_backend(
    manager, monkeypatch, isolated_backends, field,
):
    manager.backend_priority = ["keychain", "env"]
    monkeypatch.setenv(f"SVC_{field.upper()}", "correct-field-value")
    assert manager.get_credential("svc", "user", field) == "correct-field-value"
    isolated_backends.assert_not_called()


@pytest.fixture
def op_item_store(isolated_backends):
    """Model exact title/ID lookups and persist stdin writes without live op.

    Item shape comes from the existing sanitized op create --dry-run capture.
    Listing exposes metadata only; field reads come from the stored item.
    """
    items = {}
    template = json.loads((Path(__file__).parent / "data" / "op_api_credential_dry_run.json").read_text())

    def op(cmd, **kwargs):
        assert cmd[:2] == ["op", "item"]
        action = cmd[2]
        if action == "list":
            output = [{"id": item["id"], "title": item["title"]} for item in items.values()]
        elif action == "get":
            item = next((item for item in items.values() if cmd[3] in (item["id"], item["title"])), None)
            if item is None:
                return subprocess.CompletedProcess(cmd, 1, "", "item not found")
            if "--format=json" not in cmd:
                field = next(arg.split("=", 1)[1] for arg in cmd if arg.startswith("--field="))
                value = next(entry["value"] for entry in item["fields"] if entry["id"] == field)
                return subprocess.CompletedProcess(cmd, 0, value + "\n", "")
            output = item
        elif action == "create":
            output = dict(template, **json.loads(kwargs["input"]))
            output["title"] = next(arg.split("=", 1)[1] for arg in cmd if arg.startswith("--title="))
            items[output["id"]] = output
        elif action == "edit":
            assert cmd[3] in items
            output = json.loads(kwargs["input"])
            items[cmd[3]] = output
        else:
            pytest.fail(f"Unexpected op action: {action}")
        return subprocess.CompletedProcess(cmd, 0, json.dumps(output), "")

    isolated_backends.side_effect = op
    return items, template


@pytest.mark.parametrize("initial_title", [
    None, "test-svc", "test-svc API", "test-svc Credentials",
    "Test Svc API", "Test Svc Credentials",
], ids=["create-exact", "edit-exact", "legacy-api", "legacy-credentials",
        "legacy-titled-api", "legacy-titled-credentials"])
def test_op_store_read_round_trip_or_refuses_legacy_title(
    manager, isolated_backends, op_item_store, initial_title,
):
    """A successful store must be readable by the same service, or refuse before writing."""
    items, template = op_item_store
    if initial_title is not None:
        items[template["id"]] = dict(template, title=initial_title)
    before = json.loads(json.dumps(items))
    manager.backend_priority = ["1password"]
    scope = {"vault": "round-trip-vault", "account": "round-trip-account"}

    if initial_title not in (None, "test-svc"):
        with pytest.raises(cm.SiegeConfigError, match="Use the exact item title or ID"):
            manager.store_credential("test-svc", "user", "new-value", "password", "1password", **scope)
        assert items == before
        assert [call.args[0][2] for call in isolated_backends.call_args_list] == ["get", "list"]
        # Following the guidance restores the round-trip for the legacy item.
        isolated_backends.reset_mock()
        service = initial_title
    else:
        service = "test-svc"

    assert manager.store_credential(service, "user", "new-value", "password", "1password", **scope)
    assert manager.get_credential(service, "user", "password", **scope) == "new-value"
    assert len(items) == 1
    assert items[template["id"]]["title"] == service
    assert isolated_backends.call_args.args[0] == [
        "op", "item", "get", service, "--field=password", "--reveal",
        "--vault=round-trip-vault", "--account=round-trip-account",
    ]
    assert all("--vault=round-trip-vault" in call.args[0] and
               "--account=round-trip-account" in call.args[0]
               for call in isolated_backends.call_args_list)


@pytest.mark.parametrize("returncode,output", [(1, ""), (2, ""), (0, "invalid-json")])
def test_op_store_listing_failure_stops_before_create(manager, isolated_backends, returncode, output):
    isolated_backends.side_effect = [
        subprocess.CompletedProcess([], 1, "", "item not found"),
        subprocess.CompletedProcess([], returncode, output, ""),
    ]
    assert manager.store_credential("svc", "user", "new-value", backend="1password") is False
    assert [call.args[0][2] for call in isolated_backends.call_args_list] == ["get", "list"]


@pytest.mark.parametrize("output", ["{}", "[null]"])
def test_op_store_invalid_listing_shape_refuses_create(manager, isolated_backends, output):
    isolated_backends.side_effect = [
        subprocess.CompletedProcess([], 1, "", "item not found"),
        subprocess.CompletedProcess([], 0, output, ""),
    ]
    with pytest.raises(cm.SiegeConfigError, match="invalid item list JSON"):
        manager.store_credential("svc", "user", "new-value", backend="1password")
    assert [call.args[0][2] for call in isolated_backends.call_args_list] == ["get", "list"]

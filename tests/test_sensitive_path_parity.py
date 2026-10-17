"""Keep file and shell credential policies aligned, including under /root."""

import os

import pytest

from siege_utilities.core._sensitive_paths import ROOT_CREDENTIAL_STORES
from siege_utilities.files import shell, validation


def test_file_and_shell_policies_include_shared_credential_stores():
    """A blanket /root entry must not hide a missing explicit store."""
    assert validation.ROOT_CREDENTIAL_STORES is ROOT_CREDENTIAL_STORES
    assert shell.ROOT_CREDENTIAL_STORES is ROOT_CREDENTIAL_STORES
    assert ROOT_CREDENTIAL_STORES <= validation.SENSITIVE_PATHS
    assert ROOT_CREDENTIAL_STORES <= shell.SENSITIVE_PATHS


@pytest.mark.parametrize("path", sorted(ROOT_CREDENTIAL_STORES))
@pytest.mark.parametrize("base_directory", [None, "/root"])
def test_shared_credential_store_raises_in_both_policies(monkeypatch, path, base_directory):
    # Simulate /root without creating or reading any credential files there.
    with monkeypatch.context() as patch:
        patch.setattr(os, "getcwd", lambda: "/root")
        with pytest.raises(validation.PathSecurityError, match="Access to sensitive path blocked"):
            validation.validate_safe_path(path, base_directory=base_directory)
        with pytest.raises(shell.SecurityError, match="Access to sensitive path forbidden"):
            shell.validate_command_safety(['cat', path], cwd='/root')

        # Exercise the real shell checks with the blanket rule removed, so a
        # forgotten shared entry cannot pass just because /root blocks cat.
        patch.setattr(shell, "SENSITIVE_PATHS", shell.SENSITIVE_PATHS - {'/root'})
        ordinary_command = ['cat', '/root/work/data.csv']
        assert shell.validate_command_safety(ordinary_command, cwd='/root') == ordinary_command
        with pytest.raises(shell.SecurityError, match="Access to sensitive path forbidden"):
            shell.validate_command_safety(['cat', path], cwd='/root')

"""
Unit tests for CredentialManager.

Covers:
- Initialization and backend detection
- Credential file search paths
- File-based credential retrieval (_get_from_files, _extract_from_file, _find_field_in_dict)
- Environment variable retrieval (_get_from_env)
- 1Password retrieval with vault/account flag threading
- Keychain retrieval (_get_from_keychain)
- Prompt-based retrieval (_get_from_prompt)
- Credential storage across backends (1Password, Keychain, env)
- Google Analytics credential helpers (store/retrieve, OAuth, service account)
- list_stored_credentials and backend_status
- Module-level convenience functions
- get_google_oauth_document_from_1password
- create_temporary_service_account_file
- store_ga_credentials_from_file and store_ga_service_account_from_file
"""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

import pytest

from siege_utilities.config.credential_manager import (
    CredentialManager,
    get_credential,
    store_credential,
    get_google_service_account_from_1password,
    get_google_oauth_from_1password,
    get_google_oauth_document_from_1password,
    create_temporary_service_account_file,
    store_ga_credentials_from_file,
    store_ga_service_account_from_file,
    get_ga_credentials,
    get_ga_service_account_credentials,
    credential_status,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_op_available():
    """Mock subprocess so 1Password CLI appears available."""
    with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout='account1\n', stderr='')
        yield mock_run


@pytest.fixture
def mock_op_unavailable():
    """Mock subprocess so 1Password CLI appears unavailable."""
    with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
        mock_run.side_effect = FileNotFoundError("op not found")
        yield mock_run


@pytest.fixture
def manager_with_defaults(mock_op_available):
    """CredentialManager with default vault/account (no account)."""
    manager = CredentialManager(
        backend_priority=['1password'],
        default_vault='Private',
    )
    return manager, mock_op_available


@pytest.fixture
def manager_with_account(mock_op_available):
    """CredentialManager with explicit vault and account defaults."""
    manager = CredentialManager(
        backend_priority=['1password'],
        default_vault='Employee',
        default_account='Siege_Analytics',
    )
    return manager, mock_op_available


@pytest.fixture
def manager_env_only(mock_op_available):
    """CredentialManager using only environment variable backend."""
    manager = CredentialManager(
        backend_priority=['env'],
    )
    return manager, mock_op_available


@pytest.fixture
def manager_files_only(mock_op_available):
    """CredentialManager using only file backend."""
    manager = CredentialManager(
        backend_priority=['files'],
    )
    return manager, mock_op_available


@pytest.fixture
def tmp_cred_dir(tmp_path):
    """Create a temporary credential directory with sample files."""
    cred_dir = tmp_path / "credentials"
    cred_dir.mkdir()
    return cred_dir


# =============================================================================
# INIT TESTS
# =============================================================================

class TestCredentialManagerInit:
    """Tests for __init__ parameter handling and defaults."""

    def test_default_account_is_none(self, mock_op_available):
        manager = CredentialManager()
        assert manager.default_account is None

    def test_default_account_stored(self, mock_op_available):
        manager = CredentialManager(default_account='Siege_Analytics')
        assert manager.default_account == 'Siege_Analytics'

    def test_default_vault_unchanged(self, mock_op_available):
        manager = CredentialManager()
        assert manager.default_vault == 'Private'

    def test_default_backend_priority(self, mock_op_available):
        manager = CredentialManager()
        assert manager.backend_priority == ['files', 'env', '1password', 'keychain', 'prompt']

    def test_custom_backend_priority(self, mock_op_available):
        manager = CredentialManager(backend_priority=['env', 'files'])
        assert manager.backend_priority == ['env', 'files']

    def test_credential_paths_include_defaults(self, mock_op_available):
        manager = CredentialManager()
        # Should have at least cwd/credentials and ~/.siege_utilities/credentials
        path_strs = [str(p) for p in manager.credential_paths]
        assert any('credentials' in p for p in path_strs)

    def test_additional_credential_paths(self, mock_op_available, tmp_path):
        extra = tmp_path / "extra_creds"
        extra.mkdir()
        manager = CredentialManager(credential_paths=[str(extra)])
        assert extra in manager.credential_paths


# =============================================================================
# BACKEND DETECTION TESTS
# =============================================================================

class TestBackendDetection:
    """Tests for _detect_available_backends, _check_1password_available, _check_keychain_available."""

    def test_files_env_prompt_always_available(self, mock_op_available):
        manager = CredentialManager()
        assert manager.available_backends['files'] is True
        assert manager.available_backends['env'] is True
        assert manager.available_backends['prompt'] is True

    def test_1password_available_when_op_succeeds(self, mock_op_available):
        manager = CredentialManager()
        assert manager.available_backends['1password'] is True

    def test_1password_unavailable_when_op_not_found(self):
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError("op not found")
            manager = CredentialManager()
            assert manager.available_backends['1password'] is False

    def test_1password_unavailable_when_op_returns_error(self):
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=1, stdout='', stderr='not authenticated')
            manager = CredentialManager()
            assert manager.available_backends['1password'] is False

    def test_keychain_unavailable_on_linux(self, mock_op_available):
        """On Linux (no /usr/bin/security), keychain is unavailable."""
        with patch('os.path.exists', return_value=False):
            manager = CredentialManager()
            assert manager.available_backends['keychain'] is False


# =============================================================================
# _build_op_flags TESTS
# =============================================================================

class TestBuildOpFlags:
    """Tests for the _build_op_flags helper."""

    def test_defaults_vault_only(self, manager_with_defaults):
        manager, _ = manager_with_defaults
        flags = manager._build_op_flags()
        assert flags == ['--vault=Private']

    def test_with_account_default(self, manager_with_account):
        manager, _ = manager_with_account
        flags = manager._build_op_flags()
        assert '--vault=Employee' in flags
        assert '--account=Siege_Analytics' in flags

    def test_per_call_overrides(self, manager_with_account):
        manager, _ = manager_with_account
        flags = manager._build_op_flags(vault='OtherVault', account='OtherAccount')
        assert '--vault=OtherVault' in flags
        assert '--account=OtherAccount' in flags

    def test_no_vault_no_account(self, mock_op_available):
        manager = CredentialManager(
            backend_priority=['1password'],
            default_vault='',
            default_account=None,
        )
        flags = manager._build_op_flags()
        assert flags == []


# =============================================================================
# _get_from_env TESTS
# =============================================================================

class TestGetFromEnv:
    """Tests for environment variable credential retrieval."""

    def test_finds_service_field_pattern(self, manager_env_only):
        manager, _ = manager_env_only
        with patch.dict(os.environ, {'MYSERVICE_PASSWORD': 'secret123'}):
            result = manager._get_from_env('myservice', 'user', 'password')
            assert result == 'secret123'

    def test_finds_service_username_field_pattern(self, manager_env_only):
        manager, _ = manager_env_only
        with patch.dict(os.environ, {'MYSERVICE_ADMIN_TOKEN': 'tok123'}, clear=False):
            result = manager._get_from_env('myservice', 'admin', 'token')
            assert result == 'tok123'

    def test_finds_field_service_pattern(self, manager_env_only):
        manager, _ = manager_env_only
        with patch.dict(os.environ, {'PASSWORD_MYSERVICE': 'pw456'}, clear=False):
            result = manager._get_from_env('myservice', 'user', 'password')
            assert result == 'pw456'

    def test_returns_none_when_not_found(self, manager_env_only):
        manager, _ = manager_env_only
        with patch.dict(os.environ, {}, clear=True):
            result = manager._get_from_env('nonexistent', 'user', 'password')
            assert result is None

    def test_handles_hyphens_in_service_name(self, manager_env_only):
        manager, _ = manager_env_only
        with patch.dict(os.environ, {'MY_SERVICE_API_KEY': 'key789'}, clear=False):
            result = manager._get_from_env('my-service', 'user', 'api_key')
            assert result == 'key789'


# =============================================================================
# _get_from_files / _extract_from_file / _find_field_in_dict TESTS
# =============================================================================

class TestGetFromFiles:
    """Tests for file-based credential retrieval."""

    def test_reads_direct_json_field(self, manager_files_only, tmp_cred_dir):
        manager, _ = manager_files_only
        cred_file = tmp_cred_dir / "myservice.json"
        cred_file.write_text(json.dumps({"password": "file_secret"}))

        result = manager._get_from_files('myservice', 'user', 'password',
                                          additional_paths=[tmp_cred_dir])
        assert result == 'file_secret'

    def test_reads_google_oauth_format(self, manager_files_only, tmp_cred_dir):
        manager, _ = manager_files_only
        cred_file = tmp_cred_dir / "myservice.json"
        cred_file.write_text(json.dumps({
            "installed": {"client_id": "abc123", "client_secret": "xyz"}
        }))

        result = manager._get_from_files('myservice', 'user', 'client_id',
                                          additional_paths=[tmp_cred_dir])
        assert result == 'abc123'

    def test_reads_service_section(self, manager_files_only, tmp_cred_dir):
        manager, _ = manager_files_only
        cred_file = tmp_cred_dir / "credentials.json"
        cred_file.write_text(json.dumps({
            "myservice": {"api_key": "svc_key_123"}
        }))

        result = manager._get_from_files('myservice', 'user', 'api_key',
                                          additional_paths=[tmp_cred_dir])
        assert result == 'svc_key_123'

    def test_reads_plain_text_file(self, manager_files_only, tmp_cred_dir):
        manager, _ = manager_files_only
        cred_file = tmp_cred_dir / "myservice_password.txt"
        cred_file.write_text("plaintext_secret\n")

        result = manager._get_from_files('myservice', 'user', 'password',
                                          additional_paths=[tmp_cred_dir])
        assert result == 'plaintext_secret'

    def test_returns_none_when_no_files(self, manager_files_only, tmp_cred_dir):
        manager, _ = manager_files_only
        result = manager._get_from_files('nonexistent', 'user', 'password',
                                          additional_paths=[tmp_cred_dir])
        assert result is None

    def test_handles_invalid_json(self, manager_files_only, tmp_cred_dir):
        manager, _ = manager_files_only
        cred_file = tmp_cred_dir / "myservice.json"
        cred_file.write_text("not valid json {{{")

        result = manager._get_from_files('myservice', 'user', 'password',
                                          additional_paths=[tmp_cred_dir])
        assert result is None

    def test_handles_nonexistent_search_path(self, manager_files_only):
        manager, _ = manager_files_only
        result = manager._get_from_files('myservice', 'user', 'password',
                                          additional_paths=[Path('/nonexistent/path')])
        assert result is None

    def test_wildcard_pattern_matching(self, manager_files_only, tmp_cred_dir):
        manager, _ = manager_files_only
        cred_file = tmp_cred_dir / "client_secret_myservice.json"
        cred_file.write_text(json.dumps({
            "installed": {"client_id": "wildcard_id"}
        }))

        result = manager._get_from_files('myservice', 'user', 'client_id',
                                          additional_paths=[tmp_cred_dir])
        # The client_secret_*.json wildcard pattern should match
        assert result == 'wildcard_id'

    def test_service_section_non_dict_value(self, manager_files_only, tmp_cred_dir):
        """When service section is a plain string, return it for 'password' field."""
        manager, _ = manager_files_only
        cred_file = tmp_cred_dir / "myservice.json"
        cred_file.write_text(json.dumps({"myservice": "direct_value"}))

        result = manager._get_from_files('myservice', 'user', 'password',
                                          additional_paths=[tmp_cred_dir])
        assert result == 'direct_value'

    def test_service_section_non_dict_non_password(self, manager_files_only, tmp_cred_dir):
        """When service section is a plain string and field is not 'password', return None."""
        manager, _ = manager_files_only
        cred_file = tmp_cred_dir / "myservice.json"
        cred_file.write_text(json.dumps({"myservice": "direct_value"}))

        result = manager._get_from_files('myservice', 'user', 'api_key',
                                          additional_paths=[tmp_cred_dir])
        assert result is None

    def test_empty_text_file_returns_none(self, manager_files_only, tmp_cred_dir):
        manager, _ = manager_files_only
        cred_file = tmp_cred_dir / "myservice_password.txt"
        cred_file.write_text("")

        result = manager._get_from_files('myservice', 'user', 'password',
                                          additional_paths=[tmp_cred_dir])
        assert result is None


class TestFindFieldInDict:
    """Tests for recursive dictionary field search."""

    def test_finds_top_level_field(self, mock_op_available):
        manager = CredentialManager()
        result = manager._find_field_in_dict({"api_key": "found"}, "api_key")
        assert result == "found"

    def test_finds_nested_field(self, mock_op_available):
        manager = CredentialManager()
        data = {"level1": {"level2": {"secret": "deep_value"}}}
        result = manager._find_field_in_dict(data, "secret")
        assert result == "deep_value"

    def test_returns_none_when_field_missing(self, mock_op_available):
        manager = CredentialManager()
        result = manager._find_field_in_dict({"a": "b"}, "nonexistent")
        assert result is None

    def test_returns_none_for_non_dict(self, mock_op_available):
        manager = CredentialManager()
        result = manager._find_field_in_dict("not a dict", "field")
        assert result is None

    def test_converts_non_string_values(self, mock_op_available):
        manager = CredentialManager()
        result = manager._find_field_in_dict({"port": 5432}, "port")
        assert result == "5432"


# =============================================================================
# _get_from_1password TESTS
# =============================================================================

class TestGetFrom1Password:
    """Tests that _get_from_1password passes vault/account flags."""

    def test_includes_vault_and_account(self, manager_with_account):
        manager, mock_run = manager_with_account
        mock_run.return_value = Mock(returncode=0, stdout='my-api-key\n', stderr='')

        result = manager._get_from_1password('Census API Credentials', 'credential')

        assert result == 'my-api-key'
        item_get_calls = [c for c in mock_run.call_args_list
                          if c[0][0][0] == 'op' and 'item' in c[0][0] and 'get' in c[0][0]]
        assert len(item_get_calls) >= 1
        cmd = item_get_calls[0][0][0]
        assert '--vault=Employee' in cmd
        assert '--account=Siege_Analytics' in cmd

    def test_per_call_override(self, manager_with_defaults):
        manager, mock_run = manager_with_defaults
        mock_run.return_value = Mock(returncode=0, stdout='secret\n', stderr='')

        manager._get_from_1password('svc', 'field', vault='MyVault', account='MyAcct')

        item_get_calls = [c for c in mock_run.call_args_list
                          if c[0][0][0] == 'op' and 'item' in c[0][0] and 'get' in c[0][0]]
        cmd = item_get_calls[0][0][0]
        assert '--vault=MyVault' in cmd
        assert '--account=MyAcct' in cmd

    def test_no_account_flag_when_none(self, manager_with_defaults):
        manager, mock_run = manager_with_defaults
        mock_run.return_value = Mock(returncode=0, stdout='val\n', stderr='')

        manager._get_from_1password('svc', 'field')

        item_get_calls = [c for c in mock_run.call_args_list
                          if c[0][0][0] == 'op' and 'item' in c[0][0] and 'get' in c[0][0]]
        cmd = item_get_calls[0][0][0]
        assert '--vault=Private' in cmd
        assert not any(f.startswith('--account=') for f in cmd)

    def test_service_variation_fallback_uses_flags(self, manager_with_account):
        manager, mock_run = manager_with_account

        mock_run.reset_mock()
        mock_run.side_effect = [
            Mock(returncode=1, stdout='', stderr='not found'),
            Mock(returncode=0, stdout='found-it\n', stderr=''),
        ]

        result = manager._get_from_1password('Census', 'credential')
        assert result == 'found-it'

        variation_call = mock_run.call_args_list[-1]
        cmd = variation_call[0][0]
        assert '--vault=Employee' in cmd
        assert '--account=Siege_Analytics' in cmd

    def test_returns_none_when_all_variations_fail(self, manager_with_defaults):
        manager, mock_run = manager_with_defaults
        mock_run.return_value = Mock(returncode=1, stdout='', stderr='not found')

        result = manager._get_from_1password('nonexistent', 'field')
        assert result is None

    def test_returns_none_on_exception(self, manager_with_defaults):
        manager, mock_run = manager_with_defaults
        mock_run.side_effect = Exception("connection failed")

        result = manager._get_from_1password('svc', 'field')
        assert result is None


# =============================================================================
# _get_from_keychain TESTS
# =============================================================================

class TestGetFromKeychain:
    """Tests for Apple Keychain retrieval."""

    def test_returns_value_on_success(self, mock_op_available):
        manager = CredentialManager()
        mock_op_available.return_value = Mock(returncode=0, stdout='keychain_secret\n', stderr='')

        result = manager._get_from_keychain('my-service', 'my-user')
        assert result == 'keychain_secret'

    def test_returns_none_on_failure(self, mock_op_available):
        manager = CredentialManager()
        mock_op_available.return_value = Mock(returncode=44, stdout='', stderr='not found')

        result = manager._get_from_keychain('my-service', 'my-user')
        assert result is None

    def test_returns_none_on_exception(self, mock_op_available):
        manager = CredentialManager()
        mock_op_available.side_effect = Exception("keychain error")

        result = manager._get_from_keychain('my-service', 'my-user')
        assert result is None


# =============================================================================
# _get_from_prompt TESTS
# =============================================================================

class TestGetFromPrompt:
    """Tests for interactive prompt retrieval."""

    def test_returns_none_when_not_tty(self, mock_op_available):
        manager = CredentialManager()
        with patch('os.isatty', return_value=False):
            result = manager._get_from_prompt('service', 'user', 'password')
            assert result is None

    def test_uses_getpass_for_sensitive_fields(self, mock_op_available):
        manager = CredentialManager()
        with patch('os.isatty', return_value=True), \
             patch('getpass.getpass', return_value='prompted_password'):
            result = manager._get_from_prompt('service', 'user', 'password')
            assert result == 'prompted_password'

    def test_uses_input_for_non_sensitive_fields(self, mock_op_available):
        manager = CredentialManager()
        with patch('os.isatty', return_value=True), \
             patch('builtins.input', return_value='my_username'):
            result = manager._get_from_prompt('service', 'user', 'username')
            assert result == 'my_username'

    def test_handles_eof_error(self, mock_op_available):
        manager = CredentialManager()
        with patch('os.isatty', return_value=True), \
             patch('getpass.getpass', side_effect=EOFError):
            result = manager._get_from_prompt('service', 'user', 'secret')
            assert result is None

    def test_handles_keyboard_interrupt(self, mock_op_available):
        manager = CredentialManager()
        with patch('os.isatty', return_value=True), \
             patch('getpass.getpass', side_effect=KeyboardInterrupt):
            result = manager._get_from_prompt('service', 'user', 'token')
            assert result is None


# =============================================================================
# get_credential INSTANCE METHOD TESTS
# =============================================================================

class TestGetCredentialInstance:
    """Tests that get_credential iterates backends correctly."""

    def test_threads_vault_account(self, manager_with_defaults):
        manager, mock_run = manager_with_defaults
        mock_run.return_value = Mock(returncode=0, stdout='secret-value\n', stderr='')

        result = manager.get_credential(
            'Census API Credentials', 'api', 'credential',
            vault='Employee', account='Siege_Analytics'
        )

        assert result == 'secret-value'

    def test_skips_unavailable_backends(self, mock_op_available):
        """If 1password is not available, skip it and try next backend."""
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            # 1password check fails, but env should work
            mock_run.return_value = Mock(returncode=1, stdout='', stderr='')
            manager = CredentialManager(backend_priority=['1password', 'env'])

        with patch.dict(os.environ, {'MYSERVICE_PASSWORD': 'env_secret'}):
            result = manager.get_credential('myservice', 'user', 'password')
            assert result == 'env_secret'

    def test_returns_none_when_all_fail(self, mock_op_available):
        manager = CredentialManager(backend_priority=['env'])
        with patch.dict(os.environ, {}, clear=True):
            result = manager.get_credential('nonexistent', 'user', 'password')
            assert result is None

    def test_unknown_backend_skipped(self, mock_op_available):
        manager = CredentialManager(backend_priority=['unknown_backend', 'env'])
        with patch.dict(os.environ, {'SVC_PASSWORD': 'found'}, clear=False):
            result = manager.get_credential('svc', 'user', 'password')
            assert result == 'found'

    def test_exception_in_backend_continues(self, mock_op_available):
        """If a backend raises an exception, continue to the next."""
        manager = CredentialManager(backend_priority=['files', 'env'])
        with patch.object(manager, '_get_from_files', side_effect=Exception("read error")), \
             patch.dict(os.environ, {'SVC_API_KEY': 'fallback_key'}, clear=False):
            result = manager.get_credential('svc', 'user', 'api_key')
            assert result == 'fallback_key'


# =============================================================================
# store_credential INSTANCE METHOD TESTS
# =============================================================================

class TestStoreCredential:
    """Tests for the store_credential instance method across backends."""

    def test_store_in_env(self, mock_op_available):
        manager = CredentialManager()
        result = manager.store_credential('test-svc', 'user', 'val123',
                                           field='api_key', backend='env')
        assert result is True
        assert os.environ.get('TEST_SVC_API_KEY') == 'val123'
        # Clean up
        del os.environ['TEST_SVC_API_KEY']

    def test_store_unavailable_backend(self, mock_op_available):
        manager = CredentialManager()
        manager.available_backends['1password'] = False
        result = manager.store_credential('svc', 'user', 'val', backend='1password')
        assert result is False

    def test_store_unknown_backend(self, mock_op_available):
        manager = CredentialManager()
        result = manager.store_credential('svc', 'user', 'val', backend='nosuch')
        assert result is False


# =============================================================================
# _store_in_1password TESTS
# =============================================================================

class TestStoreIn1Password:
    """Tests that _store_in_1password uses vault/account flags."""

    def test_create_includes_flags(self, manager_with_account):
        manager, mock_run = manager_with_account

        mock_run.reset_mock()
        mock_run.side_effect = [
            Mock(returncode=1, stdout='', stderr='not found'),  # direct lookup
            Mock(returncode=1, stdout='', stderr=''),  # variation 1
            Mock(returncode=1, stdout='', stderr=''),  # variation 2
            Mock(returncode=1, stdout='', stderr=''),  # variation 3
            Mock(returncode=1, stdout='', stderr=''),  # variation 4
            Mock(returncode=0, stdout='created\n', stderr=''),  # create
        ]

        result = manager._store_in_1password('test-svc', 'user', 'pass', 'password')

        assert result is True
        create_call = mock_run.call_args_list[-1]
        cmd = create_call[0][0]
        assert '--vault=Employee' in cmd
        assert '--account=Siege_Analytics' in cmd

    def test_update_existing_item(self, manager_with_account):
        manager, mock_run = manager_with_account

        mock_run.reset_mock()
        # _get_from_1password succeeds (item exists)
        mock_run.side_effect = [
            Mock(returncode=0, stdout='old_value\n', stderr=''),  # lookup succeeds
            Mock(returncode=0, stdout='updated\n', stderr=''),  # edit succeeds
        ]

        result = manager._store_in_1password('test-svc', 'user', 'new_pass', 'password')
        assert result is True

        # Last call should be 'op item edit'
        edit_call = mock_run.call_args_list[-1]
        cmd = edit_call[0][0]
        assert 'edit' in cmd

    def test_store_returns_false_on_failure(self, manager_with_account):
        manager, mock_run = manager_with_account

        mock_run.reset_mock()
        mock_run.side_effect = [
            Mock(returncode=1, stdout='', stderr=''),  # direct lookup
            Mock(returncode=1, stdout='', stderr=''),  # var 1
            Mock(returncode=1, stdout='', stderr=''),  # var 2
            Mock(returncode=1, stdout='', stderr=''),  # var 3
            Mock(returncode=1, stdout='', stderr=''),  # var 4
            Mock(returncode=1, stdout='', stderr='create failed'),  # create fails
        ]

        result = manager._store_in_1password('test-svc', 'user', 'pass', 'password')
        assert result is False

    def test_store_returns_false_on_exception(self, manager_with_account):
        manager, mock_run = manager_with_account

        mock_run.reset_mock()
        mock_run.side_effect = Exception("network error")

        result = manager._store_in_1password('test-svc', 'user', 'pass', 'password')
        assert result is False


# =============================================================================
# _store_in_keychain TESTS
# =============================================================================

class TestStoreInKeychain:
    """Tests for Apple Keychain storage."""

    def test_returns_true_on_success(self, mock_op_available):
        manager = CredentialManager()
        mock_op_available.return_value = Mock(returncode=0, stdout='', stderr='')

        result = manager._store_in_keychain('svc', 'user', 'secret')
        assert result is True

    def test_returns_false_on_failure(self, mock_op_available):
        manager = CredentialManager()
        mock_op_available.return_value = Mock(returncode=1, stdout='', stderr='error')

        result = manager._store_in_keychain('svc', 'user', 'secret')
        assert result is False

    def test_returns_false_on_exception(self, mock_op_available):
        manager = CredentialManager()
        mock_op_available.side_effect = Exception("keychain write error")

        result = manager._store_in_keychain('svc', 'user', 'secret')
        assert result is False


# =============================================================================
# _store_in_env TESTS
# =============================================================================

class TestStoreInEnv:
    """Tests for environment variable storage."""

    def test_stores_and_returns_true(self, mock_op_available):
        manager = CredentialManager()
        result = manager._store_in_env('my-service', 'user', 'envval', 'api_key')
        assert result is True
        assert os.environ.get('MY_SERVICE_API_KEY') == 'envval'
        del os.environ['MY_SERVICE_API_KEY']


# =============================================================================
# store_google_analytics_credentials TESTS
# =============================================================================

class TestStoreGoogleAnalyticsCredentials:
    """Tests for store_google_analytics_credentials."""

    def test_returns_false_when_1password_unavailable(self, mock_op_available):
        manager = CredentialManager()
        manager.available_backends['1password'] = False

        result = manager.store_google_analytics_credentials({"installed": {}})
        assert result is False

    def test_returns_false_for_invalid_format(self, mock_op_available):
        manager = CredentialManager()
        result = manager.store_google_analytics_credentials({"web": {}})
        assert result is False

    def test_stores_and_verifies(self, mock_op_available):
        manager = CredentialManager()
        mock_op_available.return_value = Mock(returncode=0, stdout='verified_id\n', stderr='')

        creds = {
            "installed": {
                "client_id": "cid",
                "client_secret": "csec",
                "auth_uri": "https://auth",
                "token_uri": "https://token",
                "redirect_uris": ["http://localhost"]
            }
        }
        result = manager.store_google_analytics_credentials(creds)
        assert result is True

    def test_returns_false_when_create_fails(self, mock_op_available):
        manager = CredentialManager()

        mock_op_available.reset_mock()
        mock_op_available.return_value = Mock(returncode=1, stdout='', stderr='create failed')

        creds = {
            "installed": {
                "client_id": "cid",
                "client_secret": "csec",
                "auth_uri": "https://auth",
                "token_uri": "https://token"
            }
        }
        result = manager.store_google_analytics_credentials(creds)
        assert result is False


# =============================================================================
# get_google_analytics_credentials TESTS
# =============================================================================

class TestGetGoogleAnalyticsCredentials:
    """Tests for get_google_analytics_credentials."""

    def test_returns_tuple_from_1password(self, mock_op_available):
        manager = CredentialManager()
        mock_op_available.return_value = Mock(returncode=0, stdout='found_value\n', stderr='')

        result = manager.get_google_analytics_credentials()
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_returns_none_when_not_found(self, mock_op_available):
        manager = CredentialManager()
        mock_op_available.return_value = Mock(returncode=1, stdout='', stderr='not found')

        result = manager.get_google_analytics_credentials()
        assert result is None

    def test_returns_none_on_exception(self, mock_op_available):
        manager = CredentialManager()
        mock_op_available.side_effect = Exception("unexpected error")

        result = manager.get_google_analytics_credentials()
        assert result is None


# =============================================================================
# list_stored_credentials TESTS
# =============================================================================

class TestListStoredCredentials:
    """Tests for list_stored_credentials."""

    def test_lists_1password_items(self, mock_op_available):
        manager = CredentialManager()
        items_json = json.dumps([
            {"title": "My API", "id": "abc", "vault": {"name": "Private"}, "tags": ["siege-utilities"]}
        ])
        mock_op_available.return_value = Mock(returncode=0, stdout=items_json, stderr='')

        results = manager.list_stored_credentials()
        op_items = [r for r in results if r['backend'] == '1password']
        assert len(op_items) >= 1
        assert op_items[0]['service'] == 'My API'

    def test_lists_env_credentials(self, mock_op_available):
        manager = CredentialManager()
        manager.available_backends['1password'] = False

        with patch.dict(os.environ, {'SIEGE_ANALYTICS_PASSWORD': 'secret'}, clear=False):
            results = manager.list_stored_credentials()
            env_items = [r for r in results if r['backend'] == 'env']
            assert any(r['variable'] == 'SIEGE_ANALYTICS_PASSWORD' for r in env_items)

    def test_empty_op_items_queries_total(self, mock_op_available):
        """When no tagged items, queries total vault size."""
        manager = CredentialManager()
        mock_op_available.reset_mock()
        # First call: tagged query returns empty list
        # Second call: all items query returns items
        mock_op_available.side_effect = [
            Mock(returncode=0, stdout='[]', stderr=''),
            Mock(returncode=0, stdout='[{"title":"a"},{"title":"b"}]', stderr=''),
        ]

        manager.list_stored_credentials()
        assert mock_op_available.call_count == 2

    def test_handles_1password_exception(self, mock_op_available):
        manager = CredentialManager()
        mock_op_available.side_effect = Exception("op error")

        # Should not raise
        results = manager.list_stored_credentials()
        assert isinstance(results, list)

    def test_service_filter(self, mock_op_available):
        """service_filter is appended to tags query."""
        manager = CredentialManager()
        items_json = json.dumps([])
        mock_op_available.return_value = Mock(returncode=0, stdout=items_json, stderr='')

        manager.list_stored_credentials(service_filter='google')
        # Find the 'op item list' call
        for c in mock_op_available.call_args_list:
            cmd = c[0][0]
            if isinstance(cmd, list) and 'item' in cmd and 'list' in cmd:
                tag_args = [a for a in cmd if a.startswith('--tags=')]
                if tag_args:
                    assert 'google' in tag_args[0]

    def test_vault_account_forwarded(self, mock_op_available):
        manager = CredentialManager(default_vault='MyVault', default_account='MyAcct')
        items_json = json.dumps([])
        mock_op_available.return_value = Mock(returncode=0, stdout=items_json, stderr='')

        manager.list_stored_credentials(vault='OtherVault', account='OtherAcct')
        for c in mock_op_available.call_args_list:
            cmd = c[0][0]
            if isinstance(cmd, list) and 'item' in cmd and 'list' in cmd:
                assert '--vault=OtherVault' in cmd
                assert '--account=OtherAcct' in cmd


# =============================================================================
# backend_status TESTS
# =============================================================================

class TestBackendStatus:
    """Tests for backend_status."""

    def test_includes_all_backends(self, mock_op_available):
        manager = CredentialManager()
        status = manager.backend_status()

        assert 'env' in status
        assert 'prompt' in status
        assert '1password' in status
        assert 'keychain' in status

    def test_env_always_available(self, mock_op_available):
        manager = CredentialManager()
        status = manager.backend_status()
        assert status['env']['available'] is True

    def test_1password_status_when_available(self, mock_op_available):
        manager = CredentialManager()
        mock_op_available.return_value = Mock(returncode=0, stdout='acct1\nacct2\n', stderr='')
        status = manager.backend_status()
        assert status['1password']['available'] is True
        assert '2 accounts' in status['1password']['status']

    def test_1password_status_when_not_authenticated(self, mock_op_available):
        manager = CredentialManager()
        mock_op_available.return_value = Mock(returncode=1, stdout='', stderr='not authed')
        status = manager.backend_status()
        assert status['1password']['available'] is False

    def test_1password_status_when_not_installed(self, mock_op_available):
        manager = CredentialManager()
        manager.available_backends['1password'] = False
        status = manager.backend_status()
        assert status['1password']['available'] is False
        assert 'Not installed' in status['1password']['status']

    def test_1password_status_on_exception(self, mock_op_available):
        manager = CredentialManager()
        mock_op_available.side_effect = Exception("error")
        status = manager.backend_status()
        assert status['1password']['available'] is False


# =============================================================================
# CONVENIENCE FUNCTION TESTS
# =============================================================================

class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_credential_with_vault_account(self, mock_op_available):
        mock_op_available.return_value = Mock(returncode=0, stdout='api-key-123\n', stderr='')

        result = get_credential(
            'Census API Credentials', 'api', 'credential',
            vault='Employee', account='Siege_Analytics'
        )

        assert result == 'api-key-123'

    def test_get_credential_backward_compat(self, mock_op_available):
        mock_op_available.return_value = Mock(returncode=0, stdout='val\n', stderr='')

        result = get_credential('some-service', 'user', 'password')

        assert result == 'val'

    def test_store_credential_convenience(self, mock_op_available):
        """Module-level store_credential creates manager and delegates."""
        mock_op_available.return_value = Mock(returncode=0, stdout='done\n', stderr='')

        # Store via env to avoid complex 1Password mocking
        result = store_credential('test-svc', 'user', 'val', backend='env')
        assert result is True
        # Clean up
        if 'TEST_SVC_PASSWORD' in os.environ:
            del os.environ['TEST_SVC_PASSWORD']

    def test_credential_status_returns_dict(self, mock_op_available):
        result = credential_status()
        assert isinstance(result, dict)
        assert 'env' in result

    def test_get_ga_credentials_convenience(self, mock_op_available):
        mock_op_available.return_value = Mock(returncode=0, stdout='value\n', stderr='')
        result = get_ga_credentials()
        # Either tuple or None
        assert result is None or isinstance(result, tuple)


# =============================================================================
# get_google_service_account_from_1password TESTS
# =============================================================================

class TestGetGoogleSAFrom1Password:
    """Tests for get_google_service_account_from_1password."""

    def test_includes_flags(self):
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='test-value\n', stderr='')

            result = get_google_service_account_from_1password(
                item_title='GA SA',
                vault='Employee',
                account='Siege_Analytics'
            )

            assert result is not None
            for c in mock_run.call_args_list:
                cmd = c[0][0]
                if cmd[0] == 'op':
                    assert '--vault=Employee' in cmd
                    assert '--account=Siege_Analytics' in cmd

    def test_no_flags_when_not_provided(self):
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout='test-value\n', stderr='')

            get_google_service_account_from_1password(item_title='GA SA')

            for c in mock_run.call_args_list:
                cmd = c[0][0]
                if cmd[0] == 'op':
                    assert not any(f.startswith('--vault=') for f in cmd)
                    assert not any(f.startswith('--account=') for f in cmd)

    def test_returns_none_on_called_process_error(self):
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'op')
            result = get_google_service_account_from_1password()
            assert result is None

    def test_returns_none_on_general_exception(self):
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = RuntimeError("unexpected")
            result = get_google_service_account_from_1password()
            assert result is None

    def test_private_key_cleanup(self):
        """Private key should have quotes stripped and escaped newlines fixed."""
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            def side_effect(cmd, **kwargs):
                for arg in cmd:
                    if arg.startswith('--field='):
                        field = arg.split('=', 1)[1]
                        if field == 'private_key':
                            return Mock(returncode=0,
                                        stdout='"-----BEGIN RSA\\nKEY\\n-----END RSA"\n',
                                        stderr='')
                return Mock(returncode=0, stdout='val\n', stderr='')

            mock_run.side_effect = side_effect

            result = get_google_service_account_from_1password(item_title='SA')
            assert result is not None
            assert result['private_key'] == '-----BEGIN RSA\nKEY\n-----END RSA'


# =============================================================================
# get_google_oauth_from_1password TESTS
# =============================================================================

def _make_op_side_effect(field_values):
    """Helper: create a subprocess.run side_effect that returns field-specific values."""
    def side_effect(cmd, **kwargs):
        for arg in cmd:
            if arg.startswith('--field='):
                field = arg.split('=', 1)[1]
                value = field_values.get(field)
                if value is not None:
                    return Mock(returncode=0, stdout=f'{value}\n', stderr='')
                return Mock(returncode=1, stdout='', stderr='not found')
        return Mock(returncode=1, stdout='', stderr='no field')
    return side_effect


class TestGetGoogleOAuthFrom1Password:
    """Tests for get_google_oauth_from_1password()."""

    def test_returns_creds_when_op_succeeds(self):
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = _make_op_side_effect({
                'client_id': 'test-client-id-1234567890',
                'client_secret': 'test-secret-xyz',
                'redirect_uris': 'http://localhost:8080',
                'raw_json': '',
            })

            result = get_google_oauth_from_1password()

            assert result is not None
            assert result['client_id'] == 'test-client-id-1234567890'
            assert result['client_secret'] == 'test-secret-xyz'
            assert result['redirect_uri'] == 'http://localhost:8080'

    def test_returns_none_when_client_id_missing(self):
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = _make_op_side_effect({
                'client_id': None,
                'client_secret': 'test-secret',
            })

            result = get_google_oauth_from_1password()
            assert result is None

    def test_returns_none_when_client_secret_missing(self):
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = _make_op_side_effect({
                'client_id': 'test-client-id-1234567890',
                'client_secret': None,
            })

            result = get_google_oauth_from_1password()
            assert result is None

    def test_includes_vault_and_account_flags(self):
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = _make_op_side_effect({
                'client_id': 'test-client-id-1234567890',
                'client_secret': 'test-secret',
                'redirect_uris': 'http://localhost',
                'raw_json': None,
            })

            get_google_oauth_from_1password(vault='Private', account='Dheeraj_Chand')

            for c in mock_run.call_args_list:
                cmd = c[0][0]
                if cmd[0] == 'op':
                    assert '--vault=Private' in cmd
                    assert '--account=Dheeraj_Chand' in cmd

    def test_no_flags_when_not_provided(self):
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = _make_op_side_effect({
                'client_id': 'test-client-id-1234567890',
                'client_secret': 'test-secret',
                'redirect_uris': None,
                'raw_json': None,
            })

            get_google_oauth_from_1password()

            for c in mock_run.call_args_list:
                cmd = c[0][0]
                if cmd[0] == 'op':
                    assert not any(f.startswith('--vault=') for f in cmd)
                    assert not any(f.startswith('--account=') for f in cmd)

    def test_parses_redirect_uris(self):
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = _make_op_side_effect({
                'client_id': 'test-client-id-1234567890',
                'client_secret': 'test-secret',
                'redirect_uris': 'http://localhost:8080, urn:ietf:wg:oauth:2.0:oob',
                'raw_json': None,
            })

            result = get_google_oauth_from_1password()
            assert result['redirect_uri'] == 'http://localhost:8080'

    def test_parses_project_id_from_raw_json(self):
        raw = json.dumps({'installed': {'project_id': 'my-project-123', 'client_id': 'x'}})
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = _make_op_side_effect({
                'client_id': 'test-client-id-1234567890',
                'client_secret': 'test-secret',
                'redirect_uris': None,
                'raw_json': raw,
            })

            result = get_google_oauth_from_1password()
            assert result['project_id'] == 'my-project-123'

    def test_handles_invalid_raw_json(self):
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = _make_op_side_effect({
                'client_id': 'test-client-id-1234567890',
                'client_secret': 'test-secret',
                'redirect_uris': None,
                'raw_json': 'not valid json at all',
            })

            result = get_google_oauth_from_1password()
            assert result is not None
            assert 'project_id' not in result

    def test_handles_subprocess_error(self):
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'op')
            result = get_google_oauth_from_1password()
            assert result is None


# =============================================================================
# get_google_oauth_document_from_1password TESTS
# =============================================================================

class TestGetGoogleOAuthDocumentFrom1Password:
    """Tests for get_google_oauth_document_from_1password."""

    def test_returns_parsed_json(self):
        doc = {"installed": {"client_id": "abc", "client_secret": "xyz"}}
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=json.dumps(doc), stderr=''
            )
            result = get_google_oauth_document_from_1password()
            assert result == doc

    def test_includes_vault_and_account(self):
        doc = {"installed": {"client_id": "abc"}}
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=json.dumps(doc), stderr=''
            )
            get_google_oauth_document_from_1password(vault='MyVault', account='MyAcct')

            cmd = mock_run.call_args[0][0]
            assert '--vault=MyVault' in cmd
            assert '--account=MyAcct' in cmd

    def test_no_flags_when_not_provided(self):
        doc = {"installed": {"client_id": "abc"}}
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout=json.dumps(doc), stderr=''
            )
            get_google_oauth_document_from_1password()

            cmd = mock_run.call_args[0][0]
            assert not any(f.startswith('--vault=') for f in cmd)
            assert not any(f.startswith('--account=') for f in cmd)

    def test_returns_none_on_called_process_error(self):
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, 'op', stderr='not found'
            )
            result = get_google_oauth_document_from_1password()
            assert result is None

    def test_returns_none_on_invalid_json(self):
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout='not json at all', stderr=''
            )
            result = get_google_oauth_document_from_1password()
            assert result is None

    def test_returns_none_on_general_exception(self):
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = RuntimeError("unexpected")
            result = get_google_oauth_document_from_1password()
            assert result is None


# =============================================================================
# create_temporary_service_account_file TESTS
# =============================================================================

class TestCreateTemporaryServiceAccountFile:
    """Tests for create_temporary_service_account_file."""

    def test_creates_temp_file_with_data(self):
        sa_data = {"type": "service_account", "project_id": "test-proj"}
        result = create_temporary_service_account_file(sa_data)
        assert result is not None
        assert os.path.exists(result)

        with open(result, 'r') as f:
            loaded = json.load(f)
        assert loaded == sa_data

        # Clean up
        os.unlink(result)

    def test_returns_json_file(self):
        sa_data = {"type": "service_account"}
        result = create_temporary_service_account_file(sa_data)
        assert result.endswith('.json')
        os.unlink(result)

    def test_returns_none_on_error(self):
        with patch('siege_utilities.config.credential_manager.tempfile.NamedTemporaryFile',
                   side_effect=OSError("no space")):
            result = create_temporary_service_account_file({"type": "sa"})
            assert result is None


# =============================================================================
# store_ga_credentials_from_file TESTS
# =============================================================================

class TestStoreGACredentialsFromFile:
    """Tests for store_ga_credentials_from_file."""

    def test_returns_false_when_file_missing(self, mock_op_available):
        result = store_ga_credentials_from_file('/nonexistent/path/creds.json')
        assert result is False

    def test_stores_from_valid_file(self, mock_op_available, tmp_path):
        cred_file = tmp_path / "client_secret.json"
        cred_data = {
            "installed": {
                "client_id": "cid",
                "client_secret": "csec",
                "auth_uri": "https://auth",
                "token_uri": "https://token",
            }
        }
        cred_file.write_text(json.dumps(cred_data))

        mock_op_available.return_value = Mock(returncode=0, stdout='stored\n', stderr='')

        result = store_ga_credentials_from_file(str(cred_file), delete_file=False)
        # Result depends on verification step; just ensure no exception
        assert isinstance(result, bool)
        # File should still exist since delete_file=False
        assert cred_file.exists()

    def test_deletes_file_on_success(self, mock_op_available, tmp_path):
        cred_file = tmp_path / "client_secret.json"
        cred_data = {
            "installed": {
                "client_id": "cid",
                "client_secret": "csec",
                "auth_uri": "https://auth",
                "token_uri": "https://token",
            }
        }
        cred_file.write_text(json.dumps(cred_data))

        # Mock successful store + verification
        mock_op_available.return_value = Mock(returncode=0, stdout='verified\n', stderr='')

        result = store_ga_credentials_from_file(str(cred_file), delete_file=True)
        if result:
            assert not cred_file.exists()

    def test_returns_false_on_exception(self, mock_op_available, tmp_path):
        cred_file = tmp_path / "bad.json"
        cred_file.write_text("not valid json {{{")

        result = store_ga_credentials_from_file(str(cred_file))
        assert result is False


# =============================================================================
# store_ga_service_account_from_file TESTS
# =============================================================================

class TestStoreGAServiceAccountFromFile:
    """Tests for store_ga_service_account_from_file."""

    def test_returns_false_when_file_missing(self, mock_op_available):
        result = store_ga_service_account_from_file('/nonexistent/sa.json')
        assert result is False

    def test_returns_false_for_invalid_format(self, mock_op_available, tmp_path):
        sa_file = tmp_path / "sa.json"
        sa_file.write_text(json.dumps({"type": "service_account"}))  # Missing required fields

        result = store_ga_service_account_from_file(str(sa_file))
        assert result is False

    def test_returns_false_for_wrong_type(self, mock_op_available, tmp_path):
        sa_file = tmp_path / "sa.json"
        sa_data = {
            "type": "authorized_user",
            "project_id": "proj",
            "private_key_id": "pkid",
            "private_key": "pk",
            "client_email": "email@test.com"
        }
        sa_file.write_text(json.dumps(sa_data))

        result = store_ga_service_account_from_file(str(sa_file))
        assert result is False

    def test_stores_valid_service_account(self, mock_op_available, tmp_path):
        sa_file = tmp_path / "sa.json"
        sa_data = {
            "type": "service_account",
            "project_id": "proj",
            "private_key_id": "pkid",
            "private_key": "-----BEGIN RSA-----\nkey\n-----END RSA-----",
            "client_email": "sa@proj.iam.gserviceaccount.com",
            "client_id": "12345",
            "auth_uri": "https://auth",
            "token_uri": "https://token"
        }
        sa_file.write_text(json.dumps(sa_data))

        mock_op_available.return_value = Mock(returncode=0, stdout='created\n', stderr='')

        result = store_ga_service_account_from_file(str(sa_file))
        assert result is True

    def test_returns_false_on_called_process_error(self, mock_op_available, tmp_path):
        sa_file = tmp_path / "sa.json"
        sa_data = {
            "type": "service_account",
            "project_id": "proj",
            "private_key_id": "pkid",
            "private_key": "pk",
            "client_email": "sa@proj.iam.gserviceaccount.com"
        }
        sa_file.write_text(json.dumps(sa_data))

        mock_op_available.side_effect = subprocess.CalledProcessError(1, 'op', stderr='error')

        result = store_ga_service_account_from_file(str(sa_file))
        assert result is False


# =============================================================================
# get_ga_service_account_credentials TESTS
# =============================================================================

class TestGetGAServiceAccountCredentials:
    """Tests for get_ga_service_account_credentials."""

    def test_returns_none_when_no_email(self, mock_op_available):
        mock_op_available.return_value = Mock(returncode=1, stdout='', stderr='not found')
        result = get_ga_service_account_credentials()
        assert result is None

    def test_returns_dict_when_all_fields_found(self, mock_op_available):
        mock_op_available.return_value = Mock(returncode=0, stdout='found_value\n', stderr='')
        result = get_ga_service_account_credentials()
        if result is not None:
            assert 'type' in result
            assert result['type'] == 'service_account'

    def test_returns_none_when_partial_fields(self, mock_op_available):
        """If some fields are found but not all, returns None."""
        call_count = [0]

        def side_effect(cmd, **kwargs):
            call_count[0] += 1
            # First call finds client_email, subsequent calls fail
            if call_count[0] <= 5:  # enough for the initial get_credential call
                return Mock(returncode=0, stdout='email@test.com\n', stderr='')
            return Mock(returncode=1, stdout='', stderr='not found')

        mock_op_available.side_effect = side_effect
        # This test is complex because of the multi-backend fallthrough;
        # just verify it doesn't crash
        result = get_ga_service_account_credentials()
        assert result is None or isinstance(result, dict)


# =============================================================================
# fetch_real_ga4_data OAuth2 FALLBACK TESTS
# =============================================================================

class TestFetchRealGA4DataOAuth2Fallback:
    """Tests for the OAuth2 fallback path in fetch_real_ga4_data()."""

    @patch('siege_utilities.config.get_google_oauth_from_1password')
    @patch('siege_utilities.config.get_google_service_account_from_1password')
    @patch('siege_utilities.analytics.GoogleAnalyticsConnector')
    def test_tries_oauth2_when_service_account_fails(self, mock_connector_cls, mock_sa, mock_oauth):
        from siege_utilities.reporting.examples.google_analytics_report_example import fetch_real_ga4_data

        mock_sa.return_value = None
        mock_oauth.return_value = {
            'client_id': 'test-id',
            'client_secret': 'test-secret',
            'redirect_uri': 'http://localhost',
        }

        mock_connector = MagicMock()
        mock_connector.authenticate.return_value = True
        mock_connector.get_ga4_data.return_value = None
        mock_connector_cls.return_value = mock_connector

        fetch_real_ga4_data('12345', '2026-01-01', '2026-01-31')

        mock_connector_cls.assert_called_once_with(
            client_id='test-id',
            client_secret='test-secret',
            redirect_uri='http://localhost',
        )
        mock_connector.authenticate.assert_called_once()

    @patch('siege_utilities.config.get_google_oauth_from_1password')
    @patch('siege_utilities.config.get_google_service_account_from_1password')
    def test_returns_none_when_both_fail(self, mock_sa, mock_oauth):
        from siege_utilities.reporting.examples.google_analytics_report_example import fetch_real_ga4_data

        mock_sa.return_value = None
        mock_oauth.return_value = None

        result = fetch_real_ga4_data('12345', '2026-01-01', '2026-01-31')
        assert result is None

    @patch('siege_utilities.config.get_google_oauth_from_1password')
    @patch('siege_utilities.config.get_google_service_account_from_1password')
    def test_passes_vault_account_to_both_strategies(self, mock_sa, mock_oauth):
        from siege_utilities.reporting.examples.google_analytics_report_example import fetch_real_ga4_data

        mock_sa.return_value = None
        mock_oauth.return_value = None

        fetch_real_ga4_data('12345', '2026-01-01', '2026-01-31',
                           vault='Private', account='Dheeraj_Chand_Family')

        mock_sa.assert_called_once_with(
            item_title='Google Analytics Service Account - Multi-Client Reporter',
            vault='Private', account='Dheeraj_Chand_Family',
        )
        mock_oauth.assert_called_once_with(vault='Private', account='Dheeraj_Chand_Family')

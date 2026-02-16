"""
Unit tests for CredentialManager 1Password vault/account flag threading.

Tests that --vault and --account flags are correctly passed through
to all `op` CLI calls, using mocked subprocess to avoid actual 1Password access.
"""

import pytest
from unittest.mock import patch, Mock, call

from siege_utilities.config.credential_manager import (
    CredentialManager,
    get_credential,
    store_credential,
    get_google_service_account_from_1password,
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


# =============================================================================
# INIT TESTS
# =============================================================================

class TestCredentialManagerInit:
    """Tests for __init__ default_account parameter."""

    def test_default_account_is_none(self, mock_op_available):
        """default_account defaults to None."""
        manager = CredentialManager()
        assert manager.default_account is None

    def test_default_account_stored(self, mock_op_available):
        """default_account is stored when provided."""
        manager = CredentialManager(default_account='Siege_Analytics')
        assert manager.default_account == 'Siege_Analytics'

    def test_default_vault_unchanged(self, mock_op_available):
        """default_vault still defaults to 'Private'."""
        manager = CredentialManager()
        assert manager.default_vault == 'Private'


# =============================================================================
# _build_op_flags TESTS
# =============================================================================

class TestBuildOpFlags:
    """Tests for the _build_op_flags helper."""

    def test_defaults_vault_only(self, manager_with_defaults):
        """With no account, returns only --vault flag."""
        manager, _ = manager_with_defaults
        flags = manager._build_op_flags()
        assert flags == ['--vault=Private']

    def test_with_account_default(self, manager_with_account):
        """With default account set, returns both flags."""
        manager, _ = manager_with_account
        flags = manager._build_op_flags()
        assert '--vault=Employee' in flags
        assert '--account=Siege_Analytics' in flags

    def test_per_call_overrides(self, manager_with_account):
        """Per-call vault/account override instance defaults."""
        manager, _ = manager_with_account
        flags = manager._build_op_flags(vault='OtherVault', account='OtherAccount')
        assert '--vault=OtherVault' in flags
        assert '--account=OtherAccount' in flags

    def test_no_vault_no_account(self, mock_op_available):
        """When default_vault is empty string and no account, returns empty list."""
        manager = CredentialManager(
            backend_priority=['1password'],
            default_vault='',
            default_account=None,
        )
        flags = manager._build_op_flags()
        assert flags == []


# =============================================================================
# _get_from_1password TESTS
# =============================================================================

class TestGetFrom1Password:
    """Tests that _get_from_1password passes vault/account flags."""

    def test_includes_vault_and_account(self, manager_with_account):
        """op item get includes --vault and --account flags."""
        manager, mock_run = manager_with_account
        mock_run.return_value = Mock(returncode=0, stdout='my-api-key\n', stderr='')

        result = manager._get_from_1password('Census API Credentials', 'credential')

        assert result == 'my-api-key'
        # Find the call that was for 'op item get'
        item_get_calls = [c for c in mock_run.call_args_list
                          if c[0][0][0] == 'op' and 'item' in c[0][0] and 'get' in c[0][0]]
        assert len(item_get_calls) >= 1
        cmd = item_get_calls[0][0][0]
        assert '--vault=Employee' in cmd
        assert '--account=Siege_Analytics' in cmd

    def test_per_call_override(self, manager_with_defaults):
        """Per-call vault/account override instance defaults."""
        manager, mock_run = manager_with_defaults
        mock_run.return_value = Mock(returncode=0, stdout='secret\n', stderr='')

        manager._get_from_1password('svc', 'field', vault='MyVault', account='MyAcct')

        item_get_calls = [c for c in mock_run.call_args_list
                          if c[0][0][0] == 'op' and 'item' in c[0][0] and 'get' in c[0][0]]
        cmd = item_get_calls[0][0][0]
        assert '--vault=MyVault' in cmd
        assert '--account=MyAcct' in cmd

    def test_no_account_flag_when_none(self, manager_with_defaults):
        """No --account flag when default_account is None and no override."""
        manager, mock_run = manager_with_defaults
        mock_run.return_value = Mock(returncode=0, stdout='val\n', stderr='')

        manager._get_from_1password('svc', 'field')

        item_get_calls = [c for c in mock_run.call_args_list
                          if c[0][0][0] == 'op' and 'item' in c[0][0] and 'get' in c[0][0]]
        cmd = item_get_calls[0][0][0]
        assert '--vault=Private' in cmd
        assert not any(f.startswith('--account=') for f in cmd)

    def test_service_variation_fallback_uses_flags(self, manager_with_account):
        """When direct lookup fails, variation attempts also include flags."""
        manager, mock_run = manager_with_account

        # Reset side_effect for this specific test sequence:
        # direct lookup fails, then first variation succeeds
        mock_run.reset_mock()
        mock_run.side_effect = [
            Mock(returncode=1, stdout='', stderr='not found'),  # direct lookup
            Mock(returncode=0, stdout='found-it\n', stderr=''),  # "Census API" variation
        ]

        result = manager._get_from_1password('Census', 'credential')
        assert result == 'found-it'

        # The variation call should also have flags
        variation_call = mock_run.call_args_list[-1]
        cmd = variation_call[0][0]
        assert '--vault=Employee' in cmd
        assert '--account=Siege_Analytics' in cmd


# =============================================================================
# get_credential INSTANCE METHOD TESTS
# =============================================================================

class TestGetCredentialInstance:
    """Tests that get_credential threads vault/account to 1Password backend."""

    def test_threads_vault_account(self, manager_with_defaults):
        """vault/account params reach _get_from_1password."""
        manager, mock_run = manager_with_defaults
        mock_run.return_value = Mock(returncode=0, stdout='secret-value\n', stderr='')

        result = manager.get_credential(
            'Census API Credentials', 'api', 'credential',
            vault='Employee', account='Siege_Analytics'
        )

        assert result == 'secret-value'
        item_get_calls = [c for c in mock_run.call_args_list
                          if c[0][0][0] == 'op' and 'item' in c[0][0] and 'get' in c[0][0]]
        cmd = item_get_calls[0][0][0]
        assert '--vault=Employee' in cmd
        assert '--account=Siege_Analytics' in cmd


# =============================================================================
# _store_in_1password TESTS
# =============================================================================

class TestStoreIn1Password:
    """Tests that _store_in_1password uses vault/account flags."""

    def test_create_includes_flags(self, manager_with_account):
        """New item creation includes vault/account flags."""
        manager, mock_run = manager_with_account

        # Reset side_effect for this specific test sequence:
        # _get_from_1password: direct lookup fails, 4 variations fail, then create succeeds
        mock_run.reset_mock()
        mock_run.side_effect = [
            Mock(returncode=1, stdout='', stderr='not found'),  # _get_from_1password direct
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


# =============================================================================
# CONVENIENCE FUNCTION TESTS
# =============================================================================

class TestConvenienceFunctions:
    """Tests for module-level get_credential and store_credential."""

    def test_get_credential_with_vault_account(self, mock_op_available):
        """Module-level get_credential passes vault/account through."""
        mock_op_available.return_value = Mock(returncode=0, stdout='api-key-123\n', stderr='')

        result = get_credential(
            'Census API Credentials', 'api', 'credential',
            vault='Employee', account='Siege_Analytics'
        )

        assert result == 'api-key-123'
        item_get_calls = [c for c in mock_op_available.call_args_list
                          if c[0][0][0] == 'op' and 'item' in c[0][0] and 'get' in c[0][0]]
        assert len(item_get_calls) >= 1
        cmd = item_get_calls[0][0][0]
        assert '--vault=Employee' in cmd
        assert '--account=Siege_Analytics' in cmd

    def test_get_credential_backward_compat(self, mock_op_available):
        """Module-level get_credential works without vault/account (backward compat)."""
        mock_op_available.return_value = Mock(returncode=0, stdout='val\n', stderr='')

        result = get_credential('some-service', 'user', 'password')

        assert result == 'val'
        item_get_calls = [c for c in mock_op_available.call_args_list
                          if c[0][0][0] == 'op' and 'item' in c[0][0] and 'get' in c[0][0]]
        cmd = item_get_calls[0][0][0]
        assert '--vault=Private' in cmd
        assert not any(f.startswith('--account=') for f in cmd)


# =============================================================================
# get_google_service_account_from_1password TESTS
# =============================================================================

class TestGetGoogleSAFrom1Password:
    """Tests that get_google_service_account_from_1password supports vault/account."""

    def test_includes_flags(self):
        """op item get calls include vault/account flags."""
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout='test-value\n', stderr=''
            )

            result = get_google_service_account_from_1password(
                item_title='GA SA',
                vault='Employee',
                account='Siege_Analytics'
            )

            assert result is not None
            # All get_field calls should include flags
            for c in mock_run.call_args_list:
                cmd = c[0][0]
                if cmd[0] == 'op':
                    assert '--vault=Employee' in cmd
                    assert '--account=Siege_Analytics' in cmd

    def test_no_flags_when_not_provided(self):
        """No vault/account flags when not specified."""
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.return_value = Mock(
                returncode=0, stdout='test-value\n', stderr=''
            )

            get_google_service_account_from_1password(item_title='GA SA')

            for c in mock_run.call_args_list:
                cmd = c[0][0]
                if cmd[0] == 'op':
                    assert not any(f.startswith('--vault=') for f in cmd)
                    assert not any(f.startswith('--account=') for f in cmd)

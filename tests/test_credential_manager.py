"""
Unit tests for CredentialManager 1Password vault/account flag threading.

Tests that --vault and --account flags are correctly passed through
to all `op` CLI calls, using mocked subprocess to avoid actual 1Password access.

Also covers get_google_oauth_from_1password() and the OAuth2 fallback
path in fetch_real_ga4_data().
"""

import json
import subprocess

import pytest
from unittest.mock import patch, Mock, call, MagicMock

from siege_utilities.config.credential_manager import (
    CredentialManager,
    get_credential,
    store_credential,
    get_google_service_account_from_1password,
    get_google_oauth_from_1password,
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


# =============================================================================
# get_google_oauth_from_1password TESTS
# =============================================================================

def _make_op_side_effect(field_values):
    """Helper: create a subprocess.run side_effect that returns field-specific values.

    Args:
        field_values: dict mapping field_name -> stdout_value (or None for failure)
    """
    def side_effect(cmd, **kwargs):
        # Find the --field=xxx argument
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
        """Returns dict with client_id, client_secret, redirect_uri when op succeeds."""
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
        """Returns None when client_id field is not found."""
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = _make_op_side_effect({
                'client_id': None,
                'client_secret': 'test-secret',
            })

            result = get_google_oauth_from_1password()

            assert result is None

    def test_returns_none_when_client_secret_missing(self):
        """Returns None when client_secret field is not found."""
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = _make_op_side_effect({
                'client_id': 'test-client-id-1234567890',
                'client_secret': None,
            })

            result = get_google_oauth_from_1password()

            assert result is None

    def test_includes_vault_and_account_flags(self):
        """op item get calls include --vault and --account flags."""
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
        """No --vault/--account flags when args are None."""
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
        """Extracts the first URI from comma-separated redirect_uris."""
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = _make_op_side_effect({
                'client_id': 'test-client-id-1234567890',
                'client_secret': 'test-secret',
                'redirect_uris': 'http://localhost:8080, urn:ietf:wg:oauth:2.0:oob',
                'raw_json': None,
            })

            result = get_google_oauth_from_1password()

            assert result is not None
            assert result['redirect_uri'] == 'http://localhost:8080'

    def test_parses_project_id_from_raw_json(self):
        """Extracts project_id from raw_json installed section."""
        raw = json.dumps({'installed': {'project_id': 'my-project-123', 'client_id': 'x'}})
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = _make_op_side_effect({
                'client_id': 'test-client-id-1234567890',
                'client_secret': 'test-secret',
                'redirect_uris': None,
                'raw_json': raw,
            })

            result = get_google_oauth_from_1password()

            assert result is not None
            assert result['project_id'] == 'my-project-123'

    def test_handles_invalid_raw_json(self):
        """Gracefully handles unparseable raw_json (returns creds without project_id)."""
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = _make_op_side_effect({
                'client_id': 'test-client-id-1234567890',
                'client_secret': 'test-secret',
                'redirect_uris': None,
                'raw_json': 'not valid json at all',
            })

            result = get_google_oauth_from_1password()

            assert result is not None
            assert result['client_id'] == 'test-client-id-1234567890'
            assert 'project_id' not in result

    def test_handles_subprocess_error(self):
        """Returns None when subprocess raises CalledProcessError."""
        with patch('siege_utilities.config.credential_manager.subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'op')

            result = get_google_oauth_from_1password()

            assert result is None


# =============================================================================
# fetch_real_ga4_data OAuth2 FALLBACK TESTS
# =============================================================================

class TestFetchRealGA4DataOAuth2Fallback:
    """Tests for the OAuth2 fallback path in fetch_real_ga4_data().

    The functions are imported locally inside fetch_real_ga4_data() via
    ``from siege_utilities.config import ...``, so we patch at the source
    module (siege_utilities.config.credential_manager) and also patch
    the config package's namespace.
    """

    @patch('siege_utilities.config.get_google_oauth_from_1password')
    @patch('siege_utilities.config.get_google_service_account_from_1password')
    @patch('siege_utilities.analytics.GoogleAnalyticsConnector')
    def test_tries_oauth2_when_service_account_fails(self, mock_connector_cls, mock_sa, mock_oauth):
        """Falls back to OAuth2 when service account returns None."""
        from siege_utilities.reporting.examples.google_analytics_report_example import fetch_real_ga4_data

        mock_sa.return_value = None
        mock_oauth.return_value = {
            'client_id': 'test-id',
            'client_secret': 'test-secret',
            'redirect_uri': 'http://localhost',
        }

        mock_connector = MagicMock()
        mock_connector.authenticate.return_value = True
        mock_connector.get_ga4_data.return_value = None  # No data — but connector was created
        mock_connector_cls.return_value = mock_connector

        fetch_real_ga4_data('12345', '2026-01-01', '2026-01-31')

        # Verify OAuth2 connector was created (not service account)
        mock_connector_cls.assert_called_once_with(
            client_id='test-id',
            client_secret='test-secret',
            redirect_uri='http://localhost',
        )
        mock_connector.authenticate.assert_called_once()

    @patch('siege_utilities.config.get_google_oauth_from_1password')
    @patch('siege_utilities.config.get_google_service_account_from_1password')
    def test_returns_none_when_both_fail(self, mock_sa, mock_oauth):
        """Returns None when both service account and OAuth2 credentials fail."""
        from siege_utilities.reporting.examples.google_analytics_report_example import fetch_real_ga4_data

        mock_sa.return_value = None
        mock_oauth.return_value = None

        result = fetch_real_ga4_data('12345', '2026-01-01', '2026-01-31')

        assert result is None

    @patch('siege_utilities.config.get_google_oauth_from_1password')
    @patch('siege_utilities.config.get_google_service_account_from_1password')
    def test_passes_vault_account_to_both_strategies(self, mock_sa, mock_oauth):
        """vault and account kwargs are forwarded to both credential functions."""
        from siege_utilities.reporting.examples.google_analytics_report_example import fetch_real_ga4_data

        mock_sa.return_value = None
        mock_oauth.return_value = None

        fetch_real_ga4_data('12345', '2026-01-01', '2026-01-31',
                           vault='Private', account='Dheeraj_Chand_Family')

        mock_sa.assert_called_once_with(vault='Private', account='Dheeraj_Chand_Family')
        mock_oauth.assert_called_once_with(vault='Private', account='Dheeraj_Chand_Family')

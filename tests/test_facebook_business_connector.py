"""Tests for siege_utilities.analytics.facebook_business.

Mock tests pin init / auth-init / error translation. The
``requires_api_key`` smoke test hits the live Facebook Business API
when ``~/.siege-test-credentials.yaml`` has a ``facebook_business``
section.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def _patch_fb(monkeypatch):
    from siege_utilities.analytics import facebook_business as mod

    fake_api = MagicMock()
    fake_pkg = MagicMock()
    monkeypatch.setattr(mod, "FACEBOOK_BUSINESS_AVAILABLE", True)
    monkeypatch.setattr(mod, "FacebookAdsApi", fake_api, raising=False)
    monkeypatch.setattr(mod, "facebook_business", fake_pkg, raising=False)
    fake_pkg.adobjects.user.User = MagicMock()
    return {"api": fake_api, "pkg": fake_pkg}


def test_init_rejects_when_facebook_not_installed(monkeypatch):
    from siege_utilities.analytics import facebook_business as mod

    monkeypatch.setattr(mod, "FACEBOOK_BUSINESS_AVAILABLE", False)
    with pytest.raises(ImportError, match="facebook-business"):
        mod.FacebookBusinessConnector(access_token="x")


def test_init_uses_app_id_secret_when_provided(_patch_fb):
    from siege_utilities.analytics.facebook_business import FacebookBusinessConnector

    FacebookBusinessConnector(access_token="tok", app_id="app", app_secret="sec")
    _patch_fb["api"].init.assert_called_once_with("app", "sec", "tok")


def test_init_falls_back_to_token_only(_patch_fb):
    """When app_id/app_secret aren't supplied, the SDK is initialized
    with just the access token (the supported token-only auth path)."""
    from siege_utilities.analytics.facebook_business import FacebookBusinessConnector

    FacebookBusinessConnector(access_token="tok")
    _patch_fb["api"].init.assert_called_once_with(access_token="tok")


def test_get_ad_accounts_translates_errors_to_empty_list(_patch_fb):
    """Errors during ``me.get_ad_accounts()`` must translate to ``[]``
    not propagate raw facebook_business exceptions to callers — the
    rest of the codebase assumes List[Dict] from this method."""
    from siege_utilities.analytics.facebook_business import FacebookBusinessConnector

    user_inst = MagicMock()
    user_inst.get_ad_accounts.side_effect = RuntimeError("rate limited")
    _patch_fb["pkg"].adobjects.user.User.return_value = user_inst

    c = FacebookBusinessConnector(access_token="tok")
    assert c.get_ad_accounts() == []


def test_get_ad_accounts_maps_sdk_records_to_dicts(_patch_fb):
    from siege_utilities.analytics.facebook_business import FacebookBusinessConnector

    fake_account = {
        "id": "act_123", "name": "Test", "account_status": 1,
        "currency": "USD", "timezone_name": "America/Chicago",
    }
    user_inst = MagicMock()
    user_inst.get_ad_accounts.return_value = [fake_account]
    _patch_fb["pkg"].adobjects.user.User.return_value = user_inst

    c = FacebookBusinessConnector(access_token="tok")
    accounts = c.get_ad_accounts()
    assert accounts == [fake_account]


@pytest.mark.requires_api_key
def test_facebook_live_get_ad_accounts(api_credentials):
    pytest.importorskip("facebook_business")
    from siege_utilities.analytics.facebook_business import FacebookBusinessConnector

    creds = api_credentials.get("facebook_business")
    if not creds:
        pytest.skip("no 'facebook_business:' section in credentials file")

    c = FacebookBusinessConnector(
        access_token=creds["access_token"],
        app_id=creds.get("app_id"),
        app_secret=creds.get("app_secret"),
    )
    accounts = c.get_ad_accounts()
    assert isinstance(accounts, list)

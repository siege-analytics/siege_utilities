"""Tests for multi-linked Google account support on Person/User models."""

from datetime import datetime, timedelta

import pytest

from siege_utilities.config.models.oauth_integration import (
    GoogleAccountStatus,
    GoogleLinkedAccount,
    GoogleWorkspaceProduct,
)
from siege_utilities.config.models.person import Person

pytestmark = pytest.mark.config


def _person() -> Person:
    return Person(
        person_id="p1",
        name="Test Person",
        email="test@example.com",
    )


def _google_account(
    account_id: str,
    email: str,
    scopes=None,
    is_default: bool = False,
    status: GoogleAccountStatus = GoogleAccountStatus.ACTIVE,
) -> GoogleLinkedAccount:
    return GoogleLinkedAccount(
        account_id=account_id,
        email=email,
        granted_scopes=scopes or [],
        is_default=is_default,
        status=status,
        last_refreshed=datetime.now() - timedelta(minutes=5),
    )


class TestGoogleLinkedAccountModel:
    def test_scope_uniqueness_enforced(self):
        with pytest.raises(ValueError):
            _google_account(
                "acct1",
                "a@example.com",
                scopes=[
                    "https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/spreadsheets",
                ],
            )

    def test_write_scope_checks(self):
        acct = _google_account(
            "acct1",
            "a@example.com",
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        assert acct.can_write_product(GoogleWorkspaceProduct.SHEETS) is True
        assert acct.can_write_product(GoogleWorkspaceProduct.DOCS) is False

    def test_revoked_account_cannot_write(self):
        acct = _google_account(
            "acct1",
            "a@example.com",
            scopes=["https://www.googleapis.com/auth/documents"],
            status=GoogleAccountStatus.REVOKED,
        )
        assert acct.can_write_product(GoogleWorkspaceProduct.DOCS) is False


class TestPersonGoogleAccountLinking:
    def test_first_linked_account_becomes_default(self):
        person = _person()
        person.link_google_account(_google_account("acct1", "a@example.com"))
        default = person.get_default_google_account()
        assert default is not None
        assert default.account_id == "acct1"
        assert default.is_default is True

    def test_explicit_default_replaces_previous_default(self):
        person = _person()
        person.link_google_account(_google_account("acct1", "a@example.com"))
        person.link_google_account(
            _google_account("acct2", "b@example.com", is_default=True)
        )
        assert person.get_google_account("acct1").is_default is False
        assert person.get_google_account("acct2").is_default is True

    def test_duplicate_account_id_rejected(self):
        person = _person()
        person.link_google_account(_google_account("acct1", "a@example.com"))
        with pytest.raises(ValueError):
            person.link_google_account(_google_account("acct1", "b@example.com"))

    def test_duplicate_email_rejected(self):
        person = _person()
        person.link_google_account(_google_account("acct1", "a@example.com"))
        with pytest.raises(ValueError):
            person.link_google_account(_google_account("acct2", "a@example.com"))

    def test_unlink_default_promotes_next_account(self):
        person = _person()
        person.link_google_account(_google_account("acct1", "a@example.com"))
        person.link_google_account(_google_account("acct2", "b@example.com"))
        assert person.unlink_google_account("acct1") is True
        default = person.get_default_google_account()
        assert default is not None
        assert default.account_id == "acct2"
        assert default.is_default is True

    def test_can_write_uses_default_account(self):
        person = _person()
        person.link_google_account(
            _google_account(
                "acct1",
                "a@example.com",
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )
        )
        assert person.can_write_google_product(GoogleWorkspaceProduct.SHEETS) is True
        assert person.can_write_google_product(GoogleWorkspaceProduct.DOCS) is False

    def test_can_write_with_specific_account(self):
        person = _person()
        person.link_google_account(
            _google_account(
                "acct1",
                "a@example.com",
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
                is_default=True,
            )
        )
        person.link_google_account(
            _google_account(
                "acct2",
                "b@example.com",
                scopes=["https://www.googleapis.com/auth/documents"],
            )
        )
        assert (
            person.can_write_google_product(
                GoogleWorkspaceProduct.DOCS,
                account_id="acct2",
            )
            is True
        )
        assert (
            person.can_write_google_product(
                GoogleWorkspaceProduct.DOCS,
                account_id="acct1",
            )
            is False
        )

"""
Google Account registry for managing multiple Google accounts.

Provides a JSON-backed registry with default selection, filtering,
and persistence. Follows the DataSourceRegistry pattern.
"""

import json
import glob as _glob
from pathlib import Path
from typing import Dict, List, Optional

from .models.google_account import (
    GoogleAccount,
    GoogleAccountStatus,
    GoogleAccountType,
)


class GoogleAccountRegistry:
    """Manages multiple GoogleAccounts with default selection and persistence."""

    def __init__(self, config_path: Optional[Path] = None):
        self._accounts: Dict[str, GoogleAccount] = {}
        if config_path is not None:
            self.load(config_path)

    # ── CRUD ─────────────────────────────────────────────────────

    def register(self, account: GoogleAccount) -> None:
        """Register or update a Google account.

        Enforces at most one default: if *account.is_default* is True,
        all other accounts are demoted.
        """
        if account.is_default:
            for aid, existing in self._accounts.items():
                if aid != account.google_account_id:
                    existing.is_default = False
        self._accounts[account.google_account_id] = account

    def remove(self, google_account_id: str) -> bool:
        """Remove a Google account by ID. Returns True if found."""
        if google_account_id in self._accounts:
            removed_default = self._accounts[google_account_id].is_default
            del self._accounts[google_account_id]
            if removed_default and self._accounts:
                # Keep invariant: one default account when registry is non-empty.
                first_key = sorted(self._accounts.keys())[0]
                self.set_default(first_key)
            return True
        return False

    # ── Lookup ───────────────────────────────────────────────────

    def get(self, google_account_id: str) -> Optional[GoogleAccount]:
        """Get a Google account by ID."""
        return self._accounts.get(google_account_id)

    def get_by_email(self, email: str) -> Optional[GoogleAccount]:
        """Get the first Google account matching *email*."""
        for account in self._accounts.values():
            if account.email == email:
                return account
        return None

    def get_default(self) -> Optional[GoogleAccount]:
        """Get the default account, or None."""
        for account in self._accounts.values():
            if account.is_default:
                return account
        return None

    def set_default(self, google_account_id: str) -> None:
        """Set an account as the default. Raises ValueError if not found."""
        if google_account_id not in self._accounts:
            raise ValueError(f"Account '{google_account_id}' not found in registry")
        for aid, account in self._accounts.items():
            account.is_default = (aid == google_account_id)

    # ── Listing ──────────────────────────────────────────────────

    def list_accounts(
        self, status: Optional[GoogleAccountStatus] = None
    ) -> List[GoogleAccount]:
        """List all accounts, optionally filtered by status."""
        accounts = list(self._accounts.values())
        if status is not None:
            accounts = [a for a in accounts if a.status == status]
        return sorted(accounts, key=lambda a: a.google_account_id)

    def list_active(self) -> List[GoogleAccount]:
        """List only active accounts."""
        return self.list_accounts(status=GoogleAccountStatus.ACTIVE)

    def list_by_type(
        self, account_type: GoogleAccountType
    ) -> List[GoogleAccount]:
        """List accounts filtered by type."""
        return sorted(
            [a for a in self._accounts.values() if a.account_type == account_type],
            key=lambda a: a.google_account_id,
        )

    # ── Persistence (JSON) ───────────────────────────────────────

    def load(self, path: Path) -> None:
        """Load accounts from a JSON file."""
        path = Path(path)
        if not path.exists():
            return
        data = json.loads(path.read_text())
        for entry in data.get("accounts", []):
            account = GoogleAccount(**entry)
            self._accounts[account.google_account_id] = account

    def save(self, path: Path) -> None:
        """Save all accounts to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "accounts": [
                a.model_dump(mode="json")
                for a in sorted(
                    self._accounts.values(), key=lambda a: a.google_account_id
                )
            ]
        }
        path.write_text(json.dumps(data, indent=2, default=str))

    def __len__(self) -> int:
        return len(self._accounts)

    def __contains__(self, google_account_id: str) -> bool:
        return google_account_id in self._accounts


# ── Module-level convenience functions ───────────────────────────


def list_google_accounts_for_owner(
    owner_id: str, config_directory: str = "config"
) -> List[GoogleAccount]:
    """Discover Google account profiles for an owner via file glob."""
    pattern = str(Path(config_directory) / f"{owner_id}_google_account_*.json")
    accounts: List[GoogleAccount] = []
    for filepath in sorted(_glob.glob(pattern)):
        data = json.loads(Path(filepath).read_text())
        accounts.append(GoogleAccount(**data))
    return accounts


def save_google_account_profile(
    account: GoogleAccount, owner_id: str, config_directory: str = "config"
) -> str:
    """Save a single GoogleAccount to a per-owner JSON file. Returns the path."""
    directory = Path(config_directory)
    directory.mkdir(parents=True, exist_ok=True)
    filename = f"{owner_id}_google_account_{account.google_account_id}.json"
    path = directory / filename
    path.write_text(json.dumps(account.model_dump(mode="json"), indent=2, default=str))
    return str(path)


def load_google_account_profile(
    owner_id: str,
    google_account_id: str,
    config_directory: str = "config",
) -> Optional[GoogleAccount]:
    """Load a single GoogleAccount from a per-owner JSON file."""
    filename = f"{owner_id}_google_account_{google_account_id}.json"
    path = Path(config_directory) / filename
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return GoogleAccount(**data)


# ── Migration utility ────────────────────────────────────────────


def migrate_single_account(
    oauth_integration,
    google_account_id: str,
    email: str,
    display_name: str,
) -> GoogleAccount:
    """Convert an existing OAuthIntegration into a GoogleAccount.

    Copies scopes and the integration name as a reference.
    """
    scopes = [s.value if hasattr(s, "value") else str(s) for s in oauth_integration.scopes]
    return GoogleAccount(
        google_account_id=google_account_id,
        email=email,
        display_name=display_name,
        account_type=GoogleAccountType.OAUTH,
        status=GoogleAccountStatus.ACTIVE,
        oauth_integration_name=oauth_integration.name,
        scopes_granted=scopes,
        created_date=oauth_integration.created_date,
    )

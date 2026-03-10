#!/usr/bin/env python3
"""Authenticate for Google Workspace APIs via 1Password.

Auto-detects whether the 1Password item is an OAuth client secret
(opens browser) or a service account key (server-to-server, no browser).

Usage:
    # OAuth (default):
    python scripts/google_workspace_auth.py

    # Service account:
    python scripts/google_workspace_auth.py --mode service_account

    # Custom vault/account/item:
    python scripts/google_workspace_auth.py --mode service_account --vault Employee --account Siege_Analytics

    # Fully custom:
    python scripts/google_workspace_auth.py --item "My Custom Item" --vault MyVault --account MyAccount
"""

import argparse
import sys

from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient


# ── Per-mode defaults ────────────────────────────────────────────────
# Account identifier: use UUID for portability across machines.
# Siege_Analytics = TLTQ3ANAABGCNEK7KIAOTDNK2Q (team-siege.1password.com)
SIEGE_ANALYTICS_ACCOUNT = "TLTQ3ANAABGCNEK7KIAOTDNK2Q"

DEFAULTS = {
    "oauth": {
        "item": "Google OAuth Client - siege_utilities",
        "vault": "Personal",
        "account": SIEGE_ANALYTICS_ACCOUNT,
    },
    "service_account": {
        "item": "Google Service Account - siege_utilities",
        "vault": "Employee",
        "account": SIEGE_ANALYTICS_ACCOUNT,
    },
}
# ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Google Workspace authentication via 1Password",
    )
    parser.add_argument(
        "--mode", choices=["oauth", "service_account"], default="oauth",
        help="Auth mode: oauth (browser) or service_account (no browser). Default: oauth",
    )
    parser.add_argument(
        "--item", default=None,
        help="1Password item title (default depends on --mode)",
    )
    parser.add_argument(
        "--vault", default=None,
        help="1Password vault (default depends on --mode)",
    )
    parser.add_argument(
        "--account", default=None,
        help="1Password account shorthand (default: Siege_Analytics)",
    )
    args = parser.parse_args()

    # Resolve defaults based on mode
    mode_defaults = DEFAULTS[args.mode]
    item_title = args.item or mode_defaults["item"]
    vault = args.vault or mode_defaults["vault"]
    account = args.account or mode_defaults["account"]

    print("Google Workspace Authentication")
    print("=" * 40)
    print(f"  Mode:              {args.mode}")
    print(f"  1Password item:    {item_title}")
    print(f"  1Password vault:   {vault}")
    print(f"  1Password account: {account}")
    print()

    try:
        client = GoogleWorkspaceClient.from_1password(
            item_title=item_title,
            vault=vault,
            account=account,
        )
    except Exception as e:
        print(f"\nAuthentication failed: {e}")
        sys.exit(1)

    # Verify by listing Drive files
    print("Authentication successful! Verifying access...")
    try:
        result = client.drive_service().files().list(
            pageSize=5, fields="files(id, name, mimeType)"
        ).execute()
        files = result.get("files", [])
        if files:
            print(f"\nDrive access confirmed — found {len(files)} files:")
            for f in files:
                print(f"  {f['name']} ({f['mimeType']})")
        else:
            print("\nDrive access confirmed (no files found, normal for new accounts)")
    except Exception as e:
        print(f"\nDrive verification failed: {e}")
        print("Token was saved — Sheets/Docs/Slides may still work.")

    print("\nDone! NB18 and from_1password() will use cached credentials.")


if __name__ == "__main__":
    main()

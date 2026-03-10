#!/usr/bin/env python3
"""Authenticate for Google Workspace APIs via 1Password.

Auto-detects whether the 1Password item is an OAuth client secret
(opens browser) or a service account key (server-to-server, no browser).

Usage:
    # OAuth (browser flow, default):
    python scripts/google_workspace_auth.py

    # Service account (no browser):
    python scripts/google_workspace_auth.py --service-account
"""

import sys

from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient


# ── Defaults (edit these to match your 1Password setup) ──────────────
OAUTH_ITEM = "Google OAuth Client - siege_utilities"
OAUTH_VAULT = "Personal"

SA_ITEM = "Google Service Account - siege_utilities"
SA_VAULT = "Employee"

ACCOUNT = "Siege_Analytics"
# ─────────────────────────────────────────────────────────────────────


def main():
    service_account = "--service-account" in sys.argv

    if service_account:
        item_title = SA_ITEM
        vault = SA_VAULT
    else:
        item_title = OAUTH_ITEM
        vault = OAUTH_VAULT

    print("Google Workspace Authentication")
    print("=" * 40)
    print(f"  1Password item:    {item_title}")
    print(f"  1Password vault:   {vault}")
    print(f"  1Password account: {ACCOUNT}")
    print(f"  Mode: {'service account' if service_account else 'OAuth (browser)'}")
    print()

    try:
        client = GoogleWorkspaceClient.from_1password(
            item_title=item_title,
            vault=vault,
            account=ACCOUNT,
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

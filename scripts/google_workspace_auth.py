#!/usr/bin/env python3
"""One-time OAuth2 authentication for Google Workspace APIs.

Run this script interactively to authenticate via browser and cache
the token at ~/.siege/tokens/workspace_token.json. After this, the
notebook and GoogleWorkspaceClient.from_1password() will work without
browser interaction.

Usage:
    python scripts/google_workspace_auth.py
"""

import sys

from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient


def main():
    print("Google Workspace OAuth2 Authentication")
    print("=" * 45)
    print()
    print("This will:")
    print("  1. Pull client_secret from 1Password (Siege_Analytics)")
    print("  2. Open a browser for Google sign-in")
    print("  3. Cache the token at ~/.siege/tokens/workspace_token.json")
    print()

    try:
        client = GoogleWorkspaceClient.from_1password(
            item_title="Google OAuth Client - siege_utilities",
            account="Siege_Analytics",
        )
    except Exception as e:
        print(f"\nAuthentication failed: {e}")
        sys.exit(1)

    # Verify by listing Drive files
    print("\nAuthentication successful! Verifying access...")
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
            print("\nDrive access confirmed (no files found, which is normal for new accounts)")
    except Exception as e:
        print(f"\nDrive verification failed: {e}")
        print("The token was still saved — Sheets/Docs/Slides may work even if Drive listing doesn't.")

    print("\nDone! You can now run NB18 without browser interaction.")


if __name__ == "__main__":
    main()

"""Manual OAuth flow to obtain a token for Google API testing.

Prints a URL. You visit it, authorize, then paste the redirect URL back here.
No local server needed — works across SSH without tunnels.
"""

import json
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow

TOKEN_FILE = Path(__file__).parent / "google_test_token.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive.file",
]

def _get_client_config() -> dict:
    """Load OAuth client config from environment or 1Password.

    Required env vars:
        GOOGLE_OAUTH_CLIENT_ID
        GOOGLE_OAUTH_CLIENT_SECRET
        GOOGLE_OAUTH_PROJECT_ID  (optional, defaults to empty string)

    Or use 1Password CLI:
        export GOOGLE_OAUTH_CLIENT_ID=$(op item get "Google OAuth Desktop" --fields client_id --reveal)
        export GOOGLE_OAUTH_CLIENT_SECRET=$(op item get "Google OAuth Desktop" --fields client_secret --reveal)
    """
    import os
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("ERROR: Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET env vars.")
        print("  e.g. via 1Password CLI:")
        print('    export GOOGLE_OAUTH_CLIENT_ID=$(op item get "Google OAuth Desktop" --fields client_id --reveal)')
        print('    export GOOGLE_OAUTH_CLIENT_SECRET=$(op item get "Google OAuth Desktop" --fields client_secret --reveal)')
        sys.exit(1)
    return {
        "installed": {
            "client_id": client_id,
            "project_id": os.environ.get("GOOGLE_OAUTH_PROJECT_ID", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost"],
        }
    }


def main():
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        print("Refreshing expired token...")
        creds.refresh(Request())
    elif not creds or not creds.valid:
        # Use redirect_uri that won't actually need a server
        # Google will redirect to localhost which will fail to load,
        # but the auth code will be in the URL bar
        client_config = _get_client_config()
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri="http://localhost:1/",
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )

        print("\n1. Open this URL in your browser:\n")
        print(auth_url)
        print("\n2. Authorize with your @siegeanalytics.com account")
        print("3. The browser will redirect to localhost:1 and FAIL TO LOAD — that's OK")
        print("4. Copy the ENTIRE URL from your browser's address bar and paste it here:\n")

        redirect_url = input("Paste the full redirect URL: ").strip()

        flow.fetch_token(authorization_response=redirect_url)
        creds = flow.credentials

    TOKEN_FILE.write_text(creds.to_json())
    print(f"\nToken saved to {TOKEN_FILE}")
    print("Ready for integration tests.")


if __name__ == "__main__":
    main()

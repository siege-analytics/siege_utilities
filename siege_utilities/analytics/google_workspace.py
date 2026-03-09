"""
Google Workspace base client for Docs, Sheets, and Slides write APIs.

Provides shared authentication and service-building logic reused by
the Sheets, Slides, and Docs service modules.

Authentication follows the same patterns as GoogleAnalyticsConnector:
- OAuth2 (interactive flow with token file)
- Service Account (from 1Password or file)
- Explicit Credentials object

Usage:
    from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient

    # OAuth2 with token file
    client = GoogleWorkspaceClient.from_oauth(
        client_id="...", client_secret="...", token_file="token.json",
    )

    # Service Account from 1Password
    client = GoogleWorkspaceClient.from_service_account()

    # Get a specific API service
    sheets = client.sheets_service()
    docs = client.docs_service()
    slides = client.slides_service()
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

log = logging.getLogger(__name__)

try:
    from google.oauth2.credentials import Credentials
    from google.oauth2 import service_account
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    _GOOGLE_AVAILABLE = True
except ImportError:
    _GOOGLE_AVAILABLE = False

# Scopes needed for read/write on Docs, Sheets, Slides
WORKSPACE_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive.file",
]


def _require_google():
    if not _GOOGLE_AVAILABLE:
        raise ImportError(
            "Google API libraries not installed. "
            "Install with: pip install siege-utilities[analytics]"
        )


class GoogleWorkspaceClient:
    """Authenticated client that builds Google API service objects.

    Do not instantiate directly — use the ``from_oauth()`` or
    ``from_service_account()`` class methods.
    """

    def __init__(self, credentials):
        _require_google()
        self._credentials = credentials
        self._services: Dict[str, Any] = {}

    # ── Factory methods ──────────────────────────────────────────

    @classmethod
    def from_oauth(
        cls,
        client_id: str,
        client_secret: str,
        token_file: Optional[Union[str, Path]] = None,
        redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob",
        scopes: Optional[List[str]] = None,
    ) -> "GoogleWorkspaceClient":
        """Authenticate via OAuth2 interactive flow.

        If *token_file* exists and contains a valid/refreshable token,
        no browser interaction is needed.
        """
        _require_google()
        scopes = scopes or WORKSPACE_SCOPES
        creds = None

        if token_file:
            token_path = Path(token_file)
            if token_path.exists():
                creds = Credentials.from_authorized_user_file(str(token_path), scopes)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif not creds or not creds.valid:
            client_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uris": [redirect_uri],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, scopes)
            creds = flow.run_local_server(port=0)

        if token_file and creds:
            Path(token_file).write_text(creds.to_json())

        return cls(creds)

    @classmethod
    def from_service_account(
        cls,
        service_account_data: Optional[Dict[str, Any]] = None,
        service_account_file: Optional[Union[str, Path]] = None,
        scopes: Optional[List[str]] = None,
    ) -> "GoogleWorkspaceClient":
        """Authenticate via service account credentials.

        Provide *service_account_data* (dict) or *service_account_file* (path).
        If neither is given, attempts to fetch from 1Password via
        ``CredentialManager.get_google_service_account_from_1password()``.
        """
        _require_google()
        scopes = scopes or WORKSPACE_SCOPES

        if service_account_file:
            creds = service_account.Credentials.from_service_account_file(
                str(service_account_file), scopes=scopes,
            )
        elif service_account_data:
            creds = service_account.Credentials.from_service_account_info(
                service_account_data, scopes=scopes,
            )
        else:
            from siege_utilities.config.credential_manager import (
                get_google_service_account_from_1password,
            )
            data = get_google_service_account_from_1password()
            creds = service_account.Credentials.from_service_account_info(
                data, scopes=scopes,
            )

        return cls(creds)

    @classmethod
    def from_credentials(cls, credentials) -> "GoogleWorkspaceClient":
        """Wrap an already-authenticated ``google.auth.credentials.Credentials``."""
        _require_google()
        return cls(credentials)

    # ── Service builders ─────────────────────────────────────────

    def _get_service(self, api: str, version: str):
        key = f"{api}:{version}"
        if key not in self._services:
            self._services[key] = build(api, version, credentials=self._credentials)
        return self._services[key]

    def sheets_service(self):
        """Return the Google Sheets API v4 service object."""
        return self._get_service("sheets", "v4")

    def docs_service(self):
        """Return the Google Docs API v1 service object."""
        return self._get_service("docs", "v1")

    def slides_service(self):
        """Return the Google Slides API v1 service object."""
        return self._get_service("slides", "v1")

    def drive_service(self):
        """Return the Google Drive API v3 service object."""
        return self._get_service("drive", "v3")

    @property
    def credentials(self):
        return self._credentials

    # ── Batch update helpers ─────────────────────────────────────

    def batch_update_spreadsheet(
        self,
        spreadsheet_id: str,
        requests: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute a batch of Sheets API requests.

        Args:
            spreadsheet_id: Target spreadsheet ID.
            requests: List of request dicts per the Sheets API batchUpdate spec.

        Returns:
            The API response dict.
        """
        body = {"requests": requests}
        result = (
            self.sheets_service()
            .spreadsheets()
            .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
            .execute()
        )
        log.info("Executed %d batch requests on spreadsheet %s", len(requests), spreadsheet_id)
        return result

    def batch_update_document(
        self,
        document_id: str,
        requests: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute a batch of Docs API requests.

        Args:
            document_id: Target document ID.
            requests: List of request dicts per the Docs API batchUpdate spec.

        Returns:
            The API response dict.
        """
        body = {"requests": requests}
        return (
            self.docs_service()
            .documents()
            .batchUpdate(documentId=document_id, body=body)
            .execute()
        )

    def batch_update_presentation(
        self,
        presentation_id: str,
        requests: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute a batch of Slides API requests.

        Args:
            presentation_id: Target presentation ID.
            requests: List of request dicts per the Slides API batchUpdate spec.

        Returns:
            The API response dict.
        """
        body = {"requests": requests}
        return (
            self.slides_service()
            .presentations()
            .batchUpdate(presentationId=presentation_id, body=body)
            .execute()
        )

    # ── Drive utilities (copy, share, permissions) ───────────────

    def copy_file(self, file_id: str, title: Optional[str] = None) -> str:
        """Copy a Drive file (spreadsheet, doc, presentation) and return the new ID.

        Args:
            file_id: The ID of the file to copy.
            title: Optional title for the copy. ``None`` keeps the default
                "Copy of ..." naming.

        Returns:
            The new file's ID.
        """
        body: Dict[str, Any] = {}
        if title:
            body["name"] = title
        result = self.drive_service().files().copy(fileId=file_id, body=body).execute()
        new_id = result["id"]
        log.info("Copied %s → %s", file_id, new_id)
        return new_id

    def share_file(
        self,
        file_id: str,
        email: str,
        role: str = "writer",
        send_notification: bool = False,
    ) -> Dict[str, Any]:
        """Share a Drive file with a user.

        Args:
            file_id: The file to share.
            email: Email address of the recipient.
            role: ``"reader"``, ``"writer"``, or ``"commenter"``.
            send_notification: Whether to send an email notification.

        Returns:
            The permission resource dict.
        """
        permission = {"type": "user", "role": role, "emailAddress": email}
        result = (
            self.drive_service()
            .permissions()
            .create(
                fileId=file_id,
                body=permission,
                sendNotificationEmail=send_notification,
            )
            .execute()
        )
        log.info("Shared %s with %s (%s)", file_id, email, role)
        return result

    def move_to_folder(self, file_id: str, folder_id: str) -> Dict[str, Any]:
        """Move a file into a Drive folder.

        Args:
            file_id: The file to move.
            folder_id: Target folder ID.

        Returns:
            The updated file resource dict.
        """
        # Get current parents to remove
        f = self.drive_service().files().get(fileId=file_id, fields="parents").execute()
        previous_parents = ",".join(f.get("parents", []))

        result = (
            self.drive_service()
            .files()
            .update(
                fileId=file_id,
                addParents=folder_id,
                removeParents=previous_parents,
                fields="id, parents",
            )
            .execute()
        )
        log.info("Moved %s to folder %s", file_id, folder_id)
        return result

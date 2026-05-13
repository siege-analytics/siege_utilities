"""Tests for siege_utilities.analytics.google_workspace.GoogleWorkspaceClient.

Pins service-cache behavior, URL helpers, and the batch-update
wrappers' SDK call shape; live smoke test exercises a real
``sheets_service().spreadsheets().get()`` against a fixture
spreadsheet ID.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def _patch_google(monkeypatch):
    from siege_utilities.analytics import google_workspace as mod

    fake_build = MagicMock()
    monkeypatch.setattr(mod, "_GOOGLE_AVAILABLE", True)
    monkeypatch.setattr(mod, "build", fake_build, raising=False)
    return fake_build


def test_require_google_raises_when_unavailable(monkeypatch):
    from siege_utilities.analytics import google_workspace as mod

    monkeypatch.setattr(mod, "_GOOGLE_AVAILABLE", False)
    with pytest.raises(ImportError, match="Google API libraries"):
        mod._require_google()


def test_service_cache_reuses_builds(_patch_google):
    """build() is expensive; calling sheets_service() twice must
    not re-build. Verifies the ``self._services`` cache."""
    from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient

    client = GoogleWorkspaceClient(credentials=MagicMock())
    s1 = client.sheets_service()
    s2 = client.sheets_service()
    assert s1 is s2
    _patch_google.assert_called_once()


def test_different_services_built_independently(_patch_google):
    from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient

    _patch_google.side_effect = lambda *a, **kw: MagicMock(name=f"{a[0]}-{a[1]}")
    client = GoogleWorkspaceClient(credentials=MagicMock())
    client.sheets_service()
    client.docs_service()
    client.slides_service()
    # 3 distinct (api, version) pairs → 3 build() calls
    assert _patch_google.call_count == 3


def test_url_helpers_return_canonical_urls():
    from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient

    assert GoogleWorkspaceClient.spreadsheet_url("ABC123") == (
        "https://docs.google.com/spreadsheets/d/ABC123"
    )
    assert GoogleWorkspaceClient.document_url("DEF456") == (
        "https://docs.google.com/document/d/DEF456"
    )
    assert GoogleWorkspaceClient.presentation_url("GHI789") == (
        "https://docs.google.com/presentation/d/GHI789"
    )


def test_batch_update_spreadsheet_passes_requests_through(_patch_google):
    from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient

    fake_service = MagicMock()
    _patch_google.return_value = fake_service

    client = GoogleWorkspaceClient(credentials=MagicMock())
    req = [{"updateCells": {"range": {}, "fields": "*"}}]
    client.batch_update_spreadsheet("sheet-id", req)

    fake_service.spreadsheets.return_value.batchUpdate.assert_called_once_with(
        spreadsheetId="sheet-id", body={"requests": req},
    )


@pytest.mark.requires_api_key
def test_google_workspace_live_sheets_get(api_credentials):
    pytest.importorskip("googleapiclient.discovery")
    from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient

    creds = api_credentials.get("google_workspace")
    if not creds or not creds.get("service_account_json"):
        pytest.skip("no 'google_workspace.service_account_json' in credentials")
    if not creds.get("spreadsheet_id"):
        pytest.skip("no 'google_workspace.spreadsheet_id' fixture in credentials")

    client = GoogleWorkspaceClient.from_service_account(
        service_account_file=creds["service_account_json"],
    )
    result = (
        client.sheets_service()
        .spreadsheets()
        .get(spreadsheetId=creds["spreadsheet_id"])
        .execute()
    )
    assert "spreadsheetId" in result

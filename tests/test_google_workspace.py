"""Tests for Google Workspace services (Sheets, Docs, Slides).

All Google API calls are mocked — no real credentials needed.
"""

import pytest
from unittest.mock import MagicMock, patch


# ── GoogleWorkspaceClient ─────────────────────────────────────────


class TestGoogleWorkspaceClientImport:
    """Verify module imports succeed even without google-api-python-client."""

    def test_import_module(self):
        from siege_utilities.analytics import google_workspace
        assert hasattr(google_workspace, "GoogleWorkspaceClient")
        assert hasattr(google_workspace, "WORKSPACE_SCOPES")

    def test_workspace_scopes_has_all_apis(self):
        from siege_utilities.analytics.google_workspace import WORKSPACE_SCOPES
        scope_text = " ".join(WORKSPACE_SCOPES)
        assert "spreadsheets" in scope_text
        assert "documents" in scope_text
        assert "presentations" in scope_text
        assert "drive" in scope_text

    def test_lazy_import_from_analytics(self):
        from siege_utilities.analytics import GoogleWorkspaceClient
        assert GoogleWorkspaceClient is not None


@pytest.fixture
def mock_client():
    """Create a GoogleWorkspaceClient with mocked credentials and services."""
    with patch("siege_utilities.analytics.google_workspace._GOOGLE_AVAILABLE", True), \
         patch("siege_utilities.analytics.google_workspace.build") as mock_build:
        from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient

        mock_creds = MagicMock()
        client = GoogleWorkspaceClient.__new__(GoogleWorkspaceClient)
        client._credentials = mock_creds
        client._services = {}

        # Mock service builders
        mock_sheets = MagicMock()
        mock_docs = MagicMock()
        mock_slides = MagicMock()
        mock_drive = MagicMock()

        def side_effect(api, version, credentials=None):
            return {
                "sheets": mock_sheets,
                "docs": mock_docs,
                "slides": mock_slides,
                "drive": mock_drive,
            }[api]

        mock_build.side_effect = side_effect

        client._mock_sheets = mock_sheets
        client._mock_docs = mock_docs
        client._mock_slides = mock_slides
        client._mock_drive = mock_drive
        client._mock_build = mock_build

        yield client


class TestGoogleWorkspaceClient:
    def test_sheets_service(self, mock_client):
        svc = mock_client.sheets_service()
        assert svc is mock_client._mock_sheets

    def test_docs_service(self, mock_client):
        svc = mock_client.docs_service()
        assert svc is mock_client._mock_docs

    def test_slides_service(self, mock_client):
        svc = mock_client.slides_service()
        assert svc is mock_client._mock_slides

    def test_drive_service(self, mock_client):
        svc = mock_client.drive_service()
        assert svc is mock_client._mock_drive

    def test_service_caching(self, mock_client):
        s1 = mock_client.sheets_service()
        s2 = mock_client.sheets_service()
        assert s1 is s2
        # build() called only once for sheets
        assert mock_client._mock_build.call_count == 1

    def test_copy_file(self, mock_client):
        mock_client._mock_drive.files().copy().execute.return_value = {"id": "new_abc"}
        result = mock_client.copy_file("old_abc", "My Copy")
        assert result == "new_abc"

    def test_share_file(self, mock_client):
        mock_client._mock_drive.permissions().create().execute.return_value = {"id": "perm1"}
        result = mock_client.share_file("file1", "user@example.com", role="reader")
        assert result["id"] == "perm1"

    def test_batch_update_spreadsheet(self, mock_client):
        mock_resp = {"replies": []}
        (mock_client._mock_sheets.spreadsheets()
         .batchUpdate().execute.return_value) = mock_resp
        result = mock_client.batch_update_spreadsheet("ss_id", [{"addSheet": {}}])
        assert result == mock_resp

    def test_batch_update_document(self, mock_client):
        mock_resp = {"replies": []}
        (mock_client._mock_docs.documents()
         .batchUpdate().execute.return_value) = mock_resp
        result = mock_client.batch_update_document("doc_id", [{"insertText": {}}])
        assert result == mock_resp

    def test_batch_update_presentation(self, mock_client):
        mock_resp = {"replies": []}
        (mock_client._mock_slides.presentations()
         .batchUpdate().execute.return_value) = mock_resp
        result = mock_client.batch_update_presentation("pres_id", [{"createSlide": {}}])
        assert result == mock_resp


# ── Google Sheets ─────────────────────────────────────────────────


class TestGoogleSheetsImport:
    def test_import_module(self):
        from siege_utilities.analytics import google_sheets
        assert hasattr(google_sheets, "create_spreadsheet")
        assert hasattr(google_sheets, "write_values")
        assert hasattr(google_sheets, "read_values")
        assert hasattr(google_sheets, "copy_spreadsheet")

    def test_lazy_import_create_spreadsheet(self):
        from siege_utilities.analytics import create_spreadsheet
        assert callable(create_spreadsheet)


class TestGoogleSheets:
    def test_create_spreadsheet(self, mock_client):
        from siege_utilities.analytics.google_sheets import create_spreadsheet
        (mock_client._mock_sheets.spreadsheets()
         .create().execute.return_value) = {"spreadsheetId": "ss_123"}
        result = create_spreadsheet(mock_client, "Test Sheet")
        assert result == "ss_123"

    def test_create_spreadsheet_with_tabs(self, mock_client):
        from siege_utilities.analytics.google_sheets import create_spreadsheet
        (mock_client._mock_sheets.spreadsheets()
         .create().execute.return_value) = {"spreadsheetId": "ss_456"}
        result = create_spreadsheet(mock_client, "Multi Tab", sheet_names=["Data", "Summary"])
        assert result == "ss_456"

    def test_write_values(self, mock_client):
        from siege_utilities.analytics.google_sheets import write_values
        (mock_client._mock_sheets.spreadsheets().values()
         .update().execute.return_value) = {"updatedCells": 6}
        result = write_values(mock_client, "ss_123", "Sheet1!A1:B3", [["a", "b"], ["c", "d"]])
        assert result["updatedCells"] == 6

    def test_append_rows(self, mock_client):
        from siege_utilities.analytics.google_sheets import append_rows
        (mock_client._mock_sheets.spreadsheets().values()
         .append().execute.return_value) = {"updates": {"updatedRows": 2}}
        result = append_rows(mock_client, "ss_123", "Sheet1", [["x", "y"]])
        assert "updates" in result

    def test_read_values(self, mock_client):
        from siege_utilities.analytics.google_sheets import read_values
        (mock_client._mock_sheets.spreadsheets().values()
         .get().execute.return_value) = {"values": [["a", "b"], ["1", "2"]]}
        result = read_values(mock_client, "ss_123", "Sheet1!A1:B2")
        assert len(result) == 2
        assert result[0] == ["a", "b"]

    def test_read_values_empty(self, mock_client):
        from siege_utilities.analytics.google_sheets import read_values
        (mock_client._mock_sheets.spreadsheets().values()
         .get().execute.return_value) = {}
        result = read_values(mock_client, "ss_123", "Sheet1")
        assert result == []

    def test_copy_spreadsheet(self, mock_client):
        from siege_utilities.analytics.google_sheets import copy_spreadsheet
        mock_client._mock_drive.files().copy().execute.return_value = {"id": "ss_copy"}
        result = copy_spreadsheet(mock_client, "ss_123", "Copy of Test")
        assert result == "ss_copy"

    def test_get_spreadsheet_metadata(self, mock_client):
        from siege_utilities.analytics.google_sheets import get_spreadsheet_metadata
        meta = {"properties": {"title": "My Sheet"}, "sheets": []}
        (mock_client._mock_sheets.spreadsheets()
         .get().execute.return_value) = meta
        result = get_spreadsheet_metadata(mock_client, "ss_123")
        assert result["properties"]["title"] == "My Sheet"

    def test_add_sheet(self, mock_client):
        from siege_utilities.analytics.google_sheets import add_sheet
        (mock_client._mock_sheets.spreadsheets()
         .batchUpdate().execute.return_value) = {
            "replies": [{"addSheet": {"properties": {"sheetId": 42}}}]
        }
        result = add_sheet(mock_client, "ss_123", "NewTab")
        assert result == 42

    def test_batch_update_delegates(self, mock_client):
        from siege_utilities.analytics.google_sheets import batch_update
        mock_resp = {"replies": []}
        (mock_client._mock_sheets.spreadsheets()
         .batchUpdate().execute.return_value) = mock_resp
        result = batch_update(mock_client, "ss_123", [{"addSheet": {}}])
        assert result == mock_resp


class TestGoogleSheetsDataFrame:
    def test_write_dataframe(self, mock_client):
        pytest.importorskip("pandas")
        from siege_utilities.analytics.google_sheets import write_dataframe
        import pandas as _pd
        df = _pd.DataFrame({"name": ["Alice", "Bob"], "score": [95, 87]})
        (mock_client._mock_sheets.spreadsheets().values()
         .update().execute.return_value) = {"updatedCells": 6}
        result = write_dataframe(mock_client, "ss_123", df)
        assert result["updatedCells"] == 6

    def test_read_dataframe(self, mock_client):
        pytest.importorskip("pandas")
        from siege_utilities.analytics.google_sheets import read_dataframe
        (mock_client._mock_sheets.spreadsheets().values()
         .get().execute.return_value) = {
            "values": [["name", "score"], ["Alice", "95"], ["Bob", "87"]]
        }
        df = read_dataframe(mock_client, "ss_123")
        assert list(df.columns) == ["name", "score"]
        assert len(df) == 2

    def test_read_dataframe_empty(self, mock_client):
        pytest.importorskip("pandas")
        from siege_utilities.analytics.google_sheets import read_dataframe
        (mock_client._mock_sheets.spreadsheets().values()
         .get().execute.return_value) = {}
        df = read_dataframe(mock_client, "ss_123")
        assert len(df) == 0


# ── Google Docs ───────────────────────────────────────────────────


class TestGoogleDocsImport:
    def test_import_module(self):
        from siege_utilities.analytics import google_docs
        assert hasattr(google_docs, "create_document")
        assert hasattr(google_docs, "read_document_text")
        assert hasattr(google_docs, "copy_document")

    def test_lazy_import_create_document(self):
        from siege_utilities.analytics import create_document
        assert callable(create_document)


class TestGoogleDocs:
    def test_create_document(self, mock_client):
        from siege_utilities.analytics.google_docs import create_document
        (mock_client._mock_docs.documents()
         .create().execute.return_value) = {"documentId": "doc_123"}
        result = create_document(mock_client, "Test Doc")
        assert result == "doc_123"

    def test_get_document(self, mock_client):
        from siege_utilities.analytics.google_docs import get_document
        doc_data = {"documentId": "doc_123", "title": "Test"}
        (mock_client._mock_docs.documents()
         .get().execute.return_value) = doc_data
        result = get_document(mock_client, "doc_123")
        assert result["title"] == "Test"

    def test_copy_document(self, mock_client):
        from siege_utilities.analytics.google_docs import copy_document
        mock_client._mock_drive.files().copy().execute.return_value = {"id": "doc_copy"}
        result = copy_document(mock_client, "doc_123", "Copy of Doc")
        assert result == "doc_copy"

    def test_read_document_text(self, mock_client):
        from siege_utilities.analytics.google_docs import read_document_text
        doc = {
            "body": {
                "content": [
                    {
                        "paragraph": {
                            "elements": [
                                {"textRun": {"content": "Hello "}},
                                {"textRun": {"content": "World\n"}},
                            ]
                        }
                    }
                ]
            }
        }
        (mock_client._mock_docs.documents()
         .get().execute.return_value) = doc
        result = read_document_text(mock_client, "doc_123")
        assert result == "Hello World\n"

    def test_read_document_text_with_table(self, mock_client):
        from siege_utilities.analytics.google_docs import read_document_text
        doc = {
            "body": {
                "content": [
                    {
                        "table": {
                            "tableRows": [
                                {
                                    "tableCells": [
                                        {
                                            "content": [
                                                {
                                                    "paragraph": {
                                                        "elements": [
                                                            {"textRun": {"content": "Cell1"}}
                                                        ]
                                                    }
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ]
            }
        }
        (mock_client._mock_docs.documents()
         .get().execute.return_value) = doc
        result = read_document_text(mock_client, "doc_123")
        assert "Cell1" in result

    def test_insert_text(self, mock_client):
        from siege_utilities.analytics.google_docs import insert_text
        mock_resp = {"replies": []}
        (mock_client._mock_docs.documents()
         .batchUpdate().execute.return_value) = mock_resp
        result = insert_text(mock_client, "doc_123", "Hello", index=1)
        assert result == mock_resp

    def test_insert_text_with_formatting(self, mock_client):
        from siege_utilities.analytics.google_docs import insert_text
        mock_resp = {"replies": []}
        (mock_client._mock_docs.documents()
         .batchUpdate().execute.return_value) = mock_resp
        result = insert_text(mock_client, "doc_123", "Bold", bold=True, font_size=14)
        assert result == mock_resp

    def test_insert_paragraph(self, mock_client):
        from siege_utilities.analytics.google_docs import insert_paragraph
        mock_resp = {"replies": []}
        (mock_client._mock_docs.documents()
         .batchUpdate().execute.return_value) = mock_resp
        result = insert_paragraph(mock_client, "doc_123", "Title", heading="HEADING_1")
        assert result == mock_resp

    def test_insert_table(self, mock_client):
        from siege_utilities.analytics.google_docs import insert_table
        mock_resp = {"replies": []}
        (mock_client._mock_docs.documents()
         .batchUpdate().execute.return_value) = mock_resp
        result = insert_table(mock_client, "doc_123", rows=3, cols=2)
        assert result == mock_resp

    def test_replace_text(self, mock_client):
        from siege_utilities.analytics.google_docs import replace_text
        mock_resp = {"replies": []}
        (mock_client._mock_docs.documents()
         .batchUpdate().execute.return_value) = mock_resp
        result = replace_text(mock_client, "doc_123", "old", "new")
        assert result == mock_resp

    def test_batch_update_delegates(self, mock_client):
        from siege_utilities.analytics.google_docs import batch_update
        mock_resp = {"replies": []}
        (mock_client._mock_docs.documents()
         .batchUpdate().execute.return_value) = mock_resp
        result = batch_update(mock_client, "doc_123", [{"insertText": {}}])
        assert result == mock_resp


# ── Google Slides ─────────────────────────────────────────────────


class TestGoogleSlidesImport:
    def test_import_module(self):
        from siege_utilities.analytics import google_slides
        assert hasattr(google_slides, "create_presentation")
        assert hasattr(google_slides, "add_blank_slide")
        assert hasattr(google_slides, "copy_presentation")

    def test_lazy_import_create_presentation(self):
        from siege_utilities.analytics import create_presentation
        assert callable(create_presentation)


class TestGoogleSlides:
    def test_create_presentation(self, mock_client):
        from siege_utilities.analytics.google_slides import create_presentation
        (mock_client._mock_slides.presentations()
         .create().execute.return_value) = {"presentationId": "pres_123"}
        result = create_presentation(mock_client, "Test Pres")
        assert result == "pres_123"

    def test_get_presentation(self, mock_client):
        from siege_utilities.analytics.google_slides import get_presentation
        pres_data = {"presentationId": "pres_123", "title": "Test"}
        (mock_client._mock_slides.presentations()
         .get().execute.return_value) = pres_data
        result = get_presentation(mock_client, "pres_123")
        assert result["title"] == "Test"

    def test_copy_presentation(self, mock_client):
        from siege_utilities.analytics.google_slides import copy_presentation
        mock_client._mock_drive.files().copy().execute.return_value = {"id": "pres_copy"}
        result = copy_presentation(mock_client, "pres_123", "Copy of Pres")
        assert result == "pres_copy"

    def test_add_blank_slide(self, mock_client):
        from siege_utilities.analytics.google_slides import add_blank_slide
        mock_resp = {"replies": []}
        (mock_client._mock_slides.presentations()
         .batchUpdate().execute.return_value) = mock_resp
        result = add_blank_slide(mock_client, "pres_123")
        assert result.startswith("slide_")

    def test_add_blank_slide_with_index(self, mock_client):
        from siege_utilities.analytics.google_slides import add_blank_slide
        mock_resp = {"replies": []}
        (mock_client._mock_slides.presentations()
         .batchUpdate().execute.return_value) = mock_resp
        result = add_blank_slide(mock_client, "pres_123", layout="TITLE", insertion_index=0)
        assert result.startswith("slide_")

    def test_insert_text(self, mock_client):
        from siege_utilities.analytics.google_slides import insert_text
        mock_resp = {"replies": []}
        (mock_client._mock_slides.presentations()
         .batchUpdate().execute.return_value) = mock_resp
        result = insert_text(mock_client, "pres_123", "shape_1", "Hello")
        assert result == mock_resp

    def test_create_textbox(self, mock_client):
        from siege_utilities.analytics.google_slides import create_textbox
        mock_resp = {"replies": []}
        (mock_client._mock_slides.presentations()
         .batchUpdate().execute.return_value) = mock_resp
        result = create_textbox(mock_client, "pres_123", "slide_1", "Hello World")
        assert result.startswith("textbox_")

    def test_insert_image(self, mock_client):
        from siege_utilities.analytics.google_slides import insert_image
        mock_resp = {"replies": []}
        (mock_client._mock_slides.presentations()
         .batchUpdate().execute.return_value) = mock_resp
        result = insert_image(mock_client, "pres_123", "slide_1", "https://example.com/img.png")
        assert result.startswith("image_")

    def test_batch_update_delegates(self, mock_client):
        from siege_utilities.analytics.google_slides import batch_update
        mock_resp = {"replies": []}
        (mock_client._mock_slides.presentations()
         .batchUpdate().execute.return_value) = mock_resp
        result = batch_update(mock_client, "pres_123", [{"createSlide": {}}])
        assert result == mock_resp


# ── Cross-module consistency ──────────────────────────────────────


class TestAnalyticsExports:
    """Verify __init__.py exports the right names without collisions."""

    def test_all_sheets_exports(self):
        from siege_utilities.analytics import (
            create_spreadsheet, write_values, append_rows, read_values,
            write_dataframe, read_dataframe, add_sheet,
            get_spreadsheet_metadata, copy_spreadsheet,
        )
        assert all(callable(f) for f in [
            create_spreadsheet, write_values, append_rows, read_values,
            write_dataframe, read_dataframe, add_sheet,
            get_spreadsheet_metadata, copy_spreadsheet,
        ])

    def test_all_docs_exports(self):
        from siege_utilities.analytics import (
            create_document, get_document, copy_document, read_document_text,
            insert_paragraph, insert_table, replace_text,
        )
        assert all(callable(f) for f in [
            create_document, get_document, copy_document, read_document_text,
            insert_paragraph, insert_table, replace_text,
        ])

    def test_all_slides_exports(self):
        from siege_utilities.analytics import (
            create_presentation, get_presentation, copy_presentation,
            add_blank_slide, create_textbox,
        )
        assert all(callable(f) for f in [
            create_presentation, get_presentation, copy_presentation,
            add_blank_slide, create_textbox,
        ])

    def test_colliding_names_not_exported_at_top(self):
        """insert_text and batch_update exist in multiple modules.
        They should NOT be in the top-level analytics namespace."""
        from siege_utilities import analytics
        # These should not be directly importable without specifying the module
        assert "insert_text" not in analytics.__all__

    def test_colliding_names_accessible_via_module(self):
        """Colliding names are still accessible via their module."""
        from siege_utilities.analytics.google_docs import insert_text as docs_insert
        from siege_utilities.analytics.google_slides import insert_text as slides_insert
        assert docs_insert is not slides_insert

    def test_workspace_client_export(self):
        from siege_utilities.analytics import GoogleWorkspaceClient, WORKSPACE_SCOPES
        assert GoogleWorkspaceClient is not None
        assert isinstance(WORKSPACE_SCOPES, list)

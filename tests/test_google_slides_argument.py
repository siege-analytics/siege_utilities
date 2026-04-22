"""
Tests for upload_figure_to_drive, create_argument_slide,
and create_report_from_arguments in google_slides.py (SAL-66).

All tests use a mocked GoogleWorkspaceClient — no live API calls.
"""

import os
import tempfile
import uuid
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

from siege_utilities.analytics.google_slides import (
    create_argument_slide,
    create_report_from_arguments,
    upload_figure_to_drive,
)
from siege_utilities.reporting.pages.page_models import Argument, TableType

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client():
    client = MagicMock()
    # slides_service chain
    slides_svc = MagicMock()
    client.slides_service.return_value = slides_svc
    presentations = MagicMock()
    slides_svc.presentations.return_value = presentations
    presentations.create.return_value.execute.return_value = {
        "presentationId": "pres_abc123"
    }

    # batch_update_presentation returns a response dict
    client.batch_update_presentation.return_value = {"replies": []}

    # Drive helpers
    client.copy_file.return_value = "pres_copy_xyz"
    client.move_to_folder.return_value = None
    client.upload_file.return_value = "file_img_001"
    client.public_url.side_effect = lambda fid: f"https://drive.google.com/file/{fid}"
    client.presentation_url.side_effect = lambda pid: f"https://slides.google.com/{pid}"

    return client


@pytest.fixture
def simple_argument():
    df = pd.DataFrame({"category": ["D", "R"], "value": [60, 40]})
    return Argument(
        headline="Party ID",
        narrative="Democrats lead by 20 points.",
        table=df,
        table_type=TableType.SINGLE_RESPONSE,
    )


@pytest.fixture
def argument_with_map():
    df = pd.DataFrame({"category": ["D", "R"], "value": [60, 40]})
    mock_fig = MagicMock()
    mock_fig.savefig = MagicMock()
    return Argument(
        headline="Geographic Party Split",
        narrative="Strong metro concentration.",
        table=df,
        table_type=TableType.CROSS_TAB,
        map_figure=mock_fig,
    )


# ---------------------------------------------------------------------------
# upload_figure_to_drive
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not MATPLOTLIB_AVAILABLE, reason="matplotlib not installed")
class TestUploadFigureToDrive:
    def test_calls_savefig_and_upload(self, mock_client):
        fig, ax = plt.subplots()
        ax.bar(["A", "B"], [1, 2])
        url = upload_figure_to_drive(mock_client, fig, "test_fig")
        mock_client.upload_file.assert_called_once()
        assert "test_fig.png" in mock_client.upload_file.call_args[1].get(
            "name", mock_client.upload_file.call_args[0][1] if len(mock_client.upload_file.call_args[0]) > 1 else ""
        ) or "test_fig.png" in str(mock_client.upload_file.call_args)
        assert "drive.google.com" in url
        plt.close(fig)

    def test_returns_public_url(self, mock_client):
        fig, ax = plt.subplots()
        url = upload_figure_to_drive(mock_client, fig, "my_chart")
        assert url.startswith("https://")
        plt.close(fig)

    def test_temp_file_cleaned_up(self, mock_client):
        fig, ax = plt.subplots()
        original_upload = mock_client.upload_file

        captured_paths = []

        def capture_upload(**kwargs):
            path = kwargs.get("local_path") or (captured_paths.append(None) or "file")
            if path:
                captured_paths.append(path)
            return "file_id_123"

        mock_client.upload_file.side_effect = lambda **kw: (
            captured_paths.append(kw.get("local_path")) or "file_id_123"
        )

        upload_figure_to_drive(mock_client, fig, "cleanup_test")

        for path in captured_paths:
            if path:
                assert not os.path.exists(path), f"Temp file {path} not cleaned up"
        plt.close(fig)

    def test_with_folder_id(self, mock_client):
        fig, ax = plt.subplots()
        upload_figure_to_drive(mock_client, fig, "fig", folder_id="folder_xyz")
        call_kwargs = mock_client.upload_file.call_args
        assert "folder_xyz" in str(call_kwargs)
        plt.close(fig)


# ---------------------------------------------------------------------------
# create_argument_slide
# ---------------------------------------------------------------------------

class TestCreateArgumentSlide:
    def test_returns_slide_id_string(self, mock_client, simple_argument):
        slide_id = create_argument_slide(mock_client, "pres_123", simple_argument)
        assert isinstance(slide_id, str)
        assert len(slide_id) > 0

    def test_batch_update_called(self, mock_client, simple_argument):
        create_argument_slide(mock_client, "pres_123", simple_argument)
        assert mock_client.batch_update_presentation.called

    def test_headline_in_batch_requests(self, mock_client, simple_argument):
        create_argument_slide(mock_client, "pres_123", simple_argument)
        all_calls = mock_client.batch_update_presentation.call_args_list
        all_text = str(all_calls)
        assert simple_argument.headline in all_text

    def test_narrative_in_batch_requests(self, mock_client, simple_argument):
        create_argument_slide(mock_client, "pres_123", simple_argument)
        all_text = str(mock_client.batch_update_presentation.call_args_list)
        assert simple_argument.narrative in all_text

    def test_side_by_side_layout_used(self, mock_client, simple_argument):
        assert simple_argument.layout == "side_by_side"
        slide_id = create_argument_slide(mock_client, "pres_123", simple_argument)
        assert slide_id  # no exception means layout logic ran

    def test_full_width_layout_used(self, mock_client, argument_with_map):
        assert argument_with_map.layout == "full_width"
        slide_id = create_argument_slide(mock_client, "pres_123", argument_with_map)
        assert slide_id

    def test_base_note_included_if_present(self, mock_client):
        df = pd.DataFrame()
        arg = Argument(
            headline="MR Table", narrative="N",
            table=df, table_type=TableType.MULTIPLE_RESPONSE,
            base_note="n=342; multiple responses permitted",
        )
        create_argument_slide(mock_client, "pres_123", arg)
        all_text = str(mock_client.batch_update_presentation.call_args_list)
        assert "multiple responses" in all_text

    def test_insertion_index_passed_to_create_slide(self, mock_client, simple_argument):
        create_argument_slide(mock_client, "pres_123", simple_argument, slide_index=3)
        all_requests = str(mock_client.batch_update_presentation.call_args_list)
        assert "insertionIndex" in all_requests or "3" in all_requests


# ---------------------------------------------------------------------------
# create_report_from_arguments
# ---------------------------------------------------------------------------

class TestCreateReportFromArguments:
    def test_returns_presentation_id(self, mock_client, simple_argument):
        pres_id = create_report_from_arguments(
            mock_client, "Test Report", [simple_argument]
        )
        assert isinstance(pres_id, str)

    def test_creates_presentation(self, mock_client, simple_argument):
        create_report_from_arguments(mock_client, "My Report", [simple_argument])
        mock_client.slides_service().presentations().create.assert_called()

    def test_one_slide_per_argument(self, mock_client):
        args = [
            Argument(headline=f"Q{i}", narrative="N", table=pd.DataFrame(),
                     table_type=TableType.SINGLE_RESPONSE)
            for i in range(3)
        ]
        create_report_from_arguments(mock_client, "Multi-Arg", args)
        # Each argument generates at least one batch_update call (for createSlide)
        # 3 args × at least 1 call each = at least 3 calls
        assert mock_client.batch_update_presentation.call_count >= 3

    def test_uses_theme_copy_if_provided(self, mock_client, simple_argument):
        create_report_from_arguments(
            mock_client, "Themed Report", [simple_argument],
            theme_presentation_id="theme_pres_id",
        )
        mock_client.copy_file.assert_called_once_with("theme_pres_id", "Themed Report")

    def test_no_copy_without_theme(self, mock_client, simple_argument):
        create_report_from_arguments(mock_client, "Plain Report", [simple_argument])
        mock_client.copy_file.assert_not_called()

    def test_moves_to_folder_if_provided(self, mock_client, simple_argument):
        create_report_from_arguments(
            mock_client, "Folder Report", [simple_argument],
            folder_id="folder_abc",
        )
        mock_client.move_to_folder.assert_called()

    def test_empty_arguments_list(self, mock_client):
        pres_id = create_report_from_arguments(mock_client, "Empty", [])
        assert pres_id  # presentation still created, just no slides

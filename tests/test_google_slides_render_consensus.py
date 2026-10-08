"""The Slides renderer must call real client methods and report failures.

Consensus finding C8 (#1356): upload_figure_to_drive called
client.upload_file / client.public_url, which did not exist on
GoogleWorkspaceClient; the AttributeError was swallowed per-slide and
create_report_from_arguments returned a presentation id while logging the
requested slide count. argument.table was never rendered. The fix adds the
real Drive methods, renders the table, and raises when slides fail.
"""
import types

import pytest

pd = pytest.importorskip("pandas")

from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient
from siege_utilities.analytics import google_slides as gs


def test_client_exposes_the_drive_methods_the_renderer_calls():
    # The renderer calls client.upload_file and client.public_url; both must
    # exist on the real class (a spec mock below relies on this).
    assert hasattr(GoogleWorkspaceClient, "upload_file")
    assert hasattr(GoogleWorkspaceClient, "public_url")


def test_upload_figure_uses_only_real_client_methods():
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from unittest.mock import MagicMock

    # spec=GoogleWorkspaceClient makes calls to nonexistent methods raise
    # AttributeError, so this passes only because upload_file/public_url exist.
    client = MagicMock(spec=GoogleWorkspaceClient)
    client.upload_file.return_value = "file-123"
    client.public_url.return_value = "https://drive.google.com/uc?export=view&id=file-123"

    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    url = gs.upload_figure_to_drive(client, fig, "chart")
    plt.close(fig)

    assert url == "https://drive.google.com/uc?export=view&id=file-123"
    assert client.upload_file.called
    client.public_url.assert_called_once_with("file-123")


def test_table_is_rendered_not_dropped(monkeypatch):
    recorded = []
    monkeypatch.setattr(gs, "add_blank_slide", lambda *a, **k: "slide-1")
    monkeypatch.setattr(
        gs, "create_textbox",
        lambda client, pres, slide, text, **k: recorded.append(text),
    )
    monkeypatch.setattr(gs, "insert_image", lambda *a, **k: None)

    argument = types.SimpleNamespace(
        layout="side_by_side", headline="Turnout", narrative="Up 4 points.",
        base_note=None, source_note=None, map_figure=None, chart=None,
        table=pd.DataFrame({"metric": ["turnout"], "value": [0.54]}),
    )
    gs.create_argument_slide(object(), "pres-1", argument)
    joined = "\n".join(recorded)
    assert "metric" in joined and "turnout" in joined, "table content was dropped"


def test_report_raises_when_a_slide_fails(monkeypatch):
    from unittest.mock import MagicMock

    monkeypatch.setattr(gs, "create_presentation", lambda client, title, folder_id=None: "pres-x")

    def _boom(client, pres, argument, slide_index=None):
        raise RuntimeError("drive upload failed")

    monkeypatch.setattr(gs, "create_argument_slide", _boom)
    client = MagicMock()
    client.presentation_url.return_value = "https://docs.google.com/presentation/d/pres-x"

    arg = types.SimpleNamespace(headline="broken")
    with pytest.raises(RuntimeError, match="slides failed"):
        gs.create_report_from_arguments(client, "report", [arg])

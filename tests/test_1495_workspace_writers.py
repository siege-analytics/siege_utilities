"""Offline regressions for report slide counts and Docs text handling (#1495)."""

from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from siege_utilities.analytics import google_docs, google_slides, google_workspace
from siege_utilities.reporting.pages.page_models import Argument, TableType


@pytest.fixture
def workspace(monkeypatch):
    """Use the real client with a mocked googleapiclient service builder."""
    services = {api: MagicMock() for api in ("docs", "slides", "drive")}
    monkeypatch.setattr(google_workspace, "_GOOGLE_AVAILABLE", True)
    monkeypatch.setattr(
        google_workspace, "build",
        MagicMock(side_effect=lambda api, version, credentials: services[api]),
        raising=False,
    )
    return google_workspace.GoogleWorkspaceClient(MagicMock()), services


@pytest.mark.parametrize("argument_count", [5, 0])
@pytest.mark.parametrize(
    "theme_id, seed_ids",
    [
        ("template", ["sample_1", "sample_2", "sample_3"]),
        (None, ["default_title"]),
        (None, []),
    ],
    ids=["three-slide-template", "default-slide", "empty-presentation"],
)
def test_report_contains_only_argument_slides(workspace, argument_count, theme_id, seed_ids):
    client, services = workspace
    presentations = services["slides"].presentations.return_value
    files = services["drive"].files.return_value
    source = {
        "slides": [{"objectId": slide_id} for slide_id in seed_ids],
        "masters": [{"objectId": "brand_master"}],
        "layouts": [{"objectId": "brand_layout"}],
    }
    report = deepcopy(source)
    report["presentationId"] = "report"
    presentations.create.return_value.execute.return_value = deepcopy(report)
    files.copy.return_value.execute.return_value = {"id": "report"}
    presentations.get.return_value.execute.side_effect = lambda: deepcopy(report)
    requests = []

    def batch_update(presentationId, body):
        assert presentationId == "report"

        def execute():
            for request in body["requests"]:
                requests.append(request)
                if "deleteObject" in request:
                    object_id = request["deleteObject"]["objectId"]
                    slide = next(slide for slide in report["slides"] if slide["objectId"] == object_id)
                    report["slides"].remove(slide)
                elif "createSlide" in request:
                    slide = request["createSlide"]
                    report["slides"].insert(
                        slide.get("insertionIndex", len(report["slides"])),
                        {"objectId": slide["objectId"]},
                    )
            return {"replies": []}

        return MagicMock(execute=execute)

    presentations.batchUpdate.side_effect = batch_update
    arguments = [
        Argument(f"Argument {index}", "Report text", None, TableType.SINGLE_RESPONSE)
        for index in range(argument_count)
    ]

    result = google_slides.create_report_from_arguments(
        client, "Report", arguments, theme_presentation_id=theme_id,
    )

    assert result == "report"
    assert len(report["slides"]) == argument_count
    assert [slide["objectId"] for slide in report["slides"]] == [
        request["createSlide"]["objectId"] for request in requests if "createSlide" in request
    ]
    assert [request["deleteObject"]["objectId"] for request in requests if "deleteObject" in request] == seed_ids
    assert report["masters"] == source["masters"]
    assert report["layouts"] == source["layouts"]
    assert [slide["objectId"] for slide in source["slides"]] == seed_ids
    if theme_id:
        files.copy.assert_called_once_with(fileId="template", body={"name": "Report"})
        presentations.create.assert_not_called()
    else:
        presentations.create.assert_called_once_with(body={"title": "Report"})
        files.copy.assert_not_called()


@pytest.mark.parametrize("index", [1, 7])
@pytest.mark.parametrize("operation", ["text", "heading", "heading-with-newline"])
def test_docs_style_range_counts_utf16_units(workspace, index, operation):
    client, services = workspace
    text = "Turnout 📈 up"
    assert len(text) == 12
    if operation == "text":
        google_docs.insert_text(client, "doc", text, index=index, bold=True, italic=True, font_size=14)
        style_request = "updateTextStyle"
        expected_length = 13
    else:
        if operation == "heading-with-newline":
            text += "\n"
        google_docs.insert_paragraph(client, "doc", text, index=index, heading="HEADING_1")
        style_request = "updateParagraphStyle"
        expected_length = 14  # Includes the paragraph's trailing newline.

    update = services["docs"].documents.return_value.batchUpdate
    update.assert_called_once()
    assert update.call_args.kwargs["documentId"] == "doc"
    requests = update.call_args.kwargs["body"]["requests"]
    assert requests[1][style_request]["range"] == {
        "startIndex": index, "endIndex": index + expected_length,
    }


def _paragraph(text):
    return {"paragraph": {"elements": [{"textRun": {"content": text}}]}}


def _table(*content):
    return {"table": {"tableRows": [{"tableCells": [{"content": list(content)}]}]}}


@pytest.mark.parametrize("shape", ["legacy", "tabs", "tabs-with-legacy-body"])
def test_read_document_text_includes_nested_content_and_tabs(workspace, shape):
    client, services = workspace
    first_tab = {
        "body": {"content": [
            {"sectionBreak": {}},
            _paragraph("Body\n"),
            _table(_paragraph("Cell\n"), _table(_paragraph("Nested\n"))),
            {"tableOfContents": {"content": [_paragraph("Contents\n")]}},
            {"paragraph": {"elements": [{"footnoteReference": {"footnoteId": "note"}}]}},
        ]},
        "headers": {"header": {"content": [_paragraph("Header\n")]}},
        "footers": {"footer": {"content": [_table(_paragraph("Footer\n"))]}},
        "footnotes": {"note": {"content": [_paragraph("Footnote\n")]}},
    }
    expected = "Body\nCell\nNested\nContents\nHeader\nFooter\nFootnote\n"
    response = deepcopy(first_tab)
    if shape != "legacy":
        response = {"tabs": [
            {
                "documentTab": first_tab,
                "childTabs": [{
                    "documentTab": {"body": {"content": [_paragraph("Child tab\n")]}},
                    "childTabs": [{
                        "documentTab": {"body": {"content": [_paragraph("Grandchild tab\n")]}},
                    }],
                }],
            },
            {"documentTab": {
                "body": {"content": [_paragraph("Second tab\n")]},
                "footnotes": {"note": {"content": [_paragraph("Second footnote\n")]}},
            }},
        ]}
        expected += "Child tab\nGrandchild tab\nSecond tab\nSecond footnote\n"
        if shape == "tabs-with-legacy-body":
            response.update(deepcopy(first_tab))

    get = services["docs"].documents.return_value.get

    def get_document(documentId, includeTabsContent=False):
        assert documentId == "doc"
        return MagicMock(execute=lambda: deepcopy(response if includeTabsContent else first_tab))

    get.side_effect = get_document

    assert google_docs.read_document_text(client, "doc") == expected
    get.assert_called_once_with(documentId="doc", includeTabsContent=True)

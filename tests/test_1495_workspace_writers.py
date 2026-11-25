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
    presentations.get.assert_called_once_with(presentationId="report")
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


@pytest.mark.parametrize("failure_stage", ["get", "delete"])
def test_report_stops_when_initial_slides_cannot_be_removed(workspace, failure_stage):
    client, services = workspace
    presentations = services["slides"].presentations.return_value
    presentations.create.return_value.execute.return_value = {"presentationId": "report"}
    presentations.get.return_value.execute.return_value = {
        "slides": [{"objectId": "default_title"}],
    }
    if failure_stage == "get":
        presentations.get.return_value.execute.side_effect = RuntimeError("read failed")
    else:
        presentations.batchUpdate.return_value.execute.side_effect = RuntimeError("delete failed")

    argument = Argument("Headline", "Text", None, TableType.SINGLE_RESPONSE)
    with pytest.raises(RuntimeError, match="failed"):
        google_slides.create_report_from_arguments(client, "Report", [argument])

    if failure_stage == "get":
        presentations.batchUpdate.assert_not_called()
    else:
        presentations.batchUpdate.assert_called_once_with(
            presentationId="report",
            body={"requests": [{"deleteObject": {"objectId": "default_title"}}]},
        )


def _layout(object_id, master_id, name):
    return {"objectId": object_id, "layoutProperties": {"masterObjectId": master_id, "name": name}}


class LayoutNotInCurrentMasterError(Exception):
    """Stands in for the HttpError 400 the Slides API documents for a foreign layout."""

    status = 400


TWO_MASTER_LAYOUTS = [
    ("leftover_blank", "leftover", "BLANK"),
    ("brand_title", "brand", "TITLE"),
    ("brand_blank", "brand", "BLANK"),
]


def _strict_template(workspace, masters, layouts, slide_master, fail_creates=()):
    """Copy of a two-slide template whose createSlide follows the documented master rule.

    A new slide's layout is resolved against the master of the previous slide, the
    first slide's master at index 0, or the first master when there are no slides;
    a layout reference not found in that master raises a 400-style error. The
    createSlide requests numbered in ``fail_creates`` (from 1) raise RuntimeError
    before the slide exists, standing in for an argument slide that fails to build.
    """
    client, services = workspace
    presentations = services["slides"].presentations.return_value
    services["drive"].files.return_value.copy.return_value.execute.return_value = {"id": "report"}
    deck = [{"objectId": f"sample_{index}", "master": slide_master} for index in range(2)]
    requests = []
    creates = []

    def snapshot():
        return {
            "slides": [
                {"objectId": slide["objectId"],
                 "slideProperties": {"masterObjectId": slide["master"]} if slide["master"] else {}}
                for slide in deck
            ],
            "masters": [{"objectId": master} for master in masters],
            "layouts": [_layout(*layout) for layout in layouts],
        }

    def current_master(index):
        if not deck:
            return masters[0]
        slide = deck[0] if index == 0 else deck[min(index, len(deck)) - 1]
        return slide["master"] or masters[0]

    def batch_update(presentationId, body):
        def execute():
            for request in body["requests"]:
                requests.append(request)
                if "deleteObject" in request:
                    deck[:] = [s for s in deck if s["objectId"] != request["deleteObject"]["objectId"]]
                elif "createSlide" in request:
                    creates.append(request)
                    if len(creates) in fail_creates:
                        raise RuntimeError("slide creation failed")
                    create = request["createSlide"]
                    index = create.get("insertionIndex", len(deck))
                    master = current_master(index)
                    reference = create["slideLayoutReference"]
                    if "layoutId" in reference:
                        found = any(lid == reference["layoutId"] and lm == master for lid, lm, _ in layouts)
                    else:
                        found = any(lm == master and name == reference["predefinedLayout"]
                                    for _, lm, name in layouts)
                    if not found:
                        raise LayoutNotInCurrentMasterError(f"400: {reference} is not in master {master}")
                    deck.insert(index, {"objectId": create["objectId"], "master": master})
            return {"replies": []}

        return MagicMock(execute=execute)

    presentations.get.return_value.execute.side_effect = snapshot
    presentations.batchUpdate.side_effect = batch_update
    return client, deck, requests


def _arguments(count):
    return [Argument(f"Argument {index}", "Text", None, TableType.SINGLE_RESPONSE) for index in range(count)]


@pytest.mark.parametrize(
    "masters, layouts, slide_master, expected_master",
    [
        (["leftover", "brand"], TWO_MASTER_LAYOUTS, "brand", "brand"),
        (["leftover", "brand"], TWO_MASTER_LAYOUTS, "leftover", "leftover"),
        (["brand"], [("brand_blank", "brand", "BLANK")], "brand", "brand"),
        (["leftover", "brand"], [("leftover_blank", "leftover", "BLANK")], None, "leftover"),
    ],
    ids=["slides-on-second-master", "slides-on-first-master", "one-master", "slide-without-master"],
)
def test_report_slides_use_the_template_slide_master_under_the_documented_rule(
    workspace, masters, layouts, slide_master, expected_master,
):
    client, deck, _ = _strict_template(workspace, masters, layouts, slide_master)

    google_slides.create_report_from_arguments(client, "Report", _arguments(3), theme_presentation_id="template")

    assert len(deck) == 3
    assert not any(slide["objectId"].startswith("sample_") for slide in deck)
    assert [slide["master"] for slide in deck] == [expected_master] * 3


def test_anchor_slide_is_kept_until_the_report_slides_exist(workspace):
    client, _, requests = _strict_template(workspace, ["leftover", "brand"], TWO_MASTER_LAYOUTS, "brand")

    google_slides.create_report_from_arguments(client, "Report", _arguments(3), theme_presentation_id="template")

    created = [request["createSlide"] for request in requests if "createSlide" in request]
    deleted = [request["deleteObject"]["objectId"] for request in requests if "deleteObject" in request]
    assert deleted == ["sample_1", "sample_0"]
    assert requests[0] == {"deleteObject": {"objectId": "sample_1"}}
    assert requests[-1] == {"deleteObject": {"objectId": "sample_0"}}
    assert all("insertionIndex" not in slide for slide in created)
    assert [slide["slideLayoutReference"] for slide in created] == [{"predefinedLayout": "BLANK"}] * 3


def test_first_master_template_sends_the_requests_it_sent_before(workspace):
    client, deck, requests = _strict_template(workspace, ["leftover", "brand"], TWO_MASTER_LAYOUTS, "leftover")

    google_slides.create_report_from_arguments(client, "Report", _arguments(3), theme_presentation_id="template")

    created = [request["createSlide"] for request in requests if "createSlide" in request]
    assert requests[0] == {"deleteObject": {"objectId": "sample_0"}}
    assert requests[1] == {"deleteObject": {"objectId": "sample_1"}}
    assert "deleteObject" not in [next(iter(request)) for request in requests[2:]]
    assert [slide["insertionIndex"] for slide in created] == [0, 1, 2]
    assert [slide["slideLayoutReference"] for slide in created] == [{"layoutId": "leftover_blank"}] * 3


def test_failed_argument_slide_behind_an_anchor_keeps_later_slides_valid(workspace):
    client, deck, requests = _strict_template(
        workspace, ["leftover", "brand"], TWO_MASTER_LAYOUTS, "brand", fail_creates={2},
    )

    with pytest.raises(RuntimeError, match="1 of 3 slides failed"):
        google_slides.create_report_from_arguments(client, "Report", _arguments(3), theme_presentation_id="template")

    assert len(deck) == 2
    assert [slide["master"] for slide in deck] == ["brand", "brand"]
    assert not any(slide["objectId"].startswith("sample_") for slide in deck)
    assert requests[-1] == {"deleteObject": {"objectId": "sample_0"}}


def test_anchored_master_without_blank_layout_is_rejected_with_400(workspace):
    layouts = [("leftover_blank", "leftover", "BLANK"), ("brand_title", "brand", "TITLE")]
    client, deck, _ = _strict_template(workspace, ["leftover", "brand"], layouts, "brand")

    with pytest.raises(LayoutNotInCurrentMasterError):
        google_slides.create_report_from_arguments(client, "Report", _arguments(3), theme_presentation_id="template")

    assert [slide["objectId"] for slide in deck] == ["sample_0"]


def test_empty_report_on_a_second_master_template_keeps_no_anchor(workspace):
    client, deck, requests = _strict_template(workspace, ["leftover", "brand"], TWO_MASTER_LAYOUTS, "brand")

    google_slides.create_report_from_arguments(client, "Report", [], theme_presentation_id="template")

    assert deck == []
    assert requests == [{"deleteObject": {"objectId": "sample_0"}}, {"deleteObject": {"objectId": "sample_1"}}]


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


@pytest.mark.parametrize("operation", ["text", "heading"])
def test_docs_style_range_counts_a_lone_surrogate_as_one_unit(workspace, operation):
    client, services = workspace
    text = "bad \ud83d end"
    if operation == "text":
        google_docs.insert_text(client, "doc", text, index=1, bold=True)
        style_request, expected_length = "updateTextStyle", 9
    else:
        google_docs.insert_paragraph(client, "doc", text, index=1, heading="HEADING_1")
        style_request, expected_length = "updateParagraphStyle", 10

    requests = services["docs"].documents.return_value.batchUpdate.call_args.kwargs["body"]["requests"]
    assert requests[1][style_request]["range"] == {"startIndex": 1, "endIndex": 1 + expected_length}


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

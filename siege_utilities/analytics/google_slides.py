"""
Google Slides write service.

Provides functions for creating presentations, adding slides,
inserting text and images, and performing batch updates via the
Slides API v1.

Usage:
    from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient
    from siege_utilities.analytics.google_slides import (
        create_presentation, add_blank_slide, insert_text,
    )

    client = GoogleWorkspaceClient.from_service_account()
    pres_id = create_presentation(client, "Q1 Report")
    slide_id = add_blank_slide(client, pres_id)
    insert_text(client, pres_id, slide_id, "Hello World")
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


def create_presentation(
    client,
    title: str,
    folder_id: Optional[str] = None,
) -> str:
    """Create a new Google Slides presentation and return its ID.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        title: Title for the new presentation.
        folder_id: Optional Drive folder ID to create the presentation in.

    Returns:
        The presentation ID string.
    """
    body = {"title": title}
    result = client.slides_service().presentations().create(body=body).execute()
    pres_id = result["presentationId"]

    if folder_id:
        client.move_to_folder(pres_id, folder_id)

    url = client.presentation_url(pres_id)
    log.info("Created presentation %r → %s", title, url)
    return pres_id


def get_presentation(
    client,
    presentation_id: str,
) -> Dict[str, Any]:
    """Fetch full presentation metadata.

    Returns:
        The presentation resource dict.
    """
    return (
        client.slides_service()
        .presentations()
        .get(presentationId=presentation_id)
        .execute()
    )


def copy_presentation(
    client,
    presentation_id: str,
    title: Optional[str] = None,
) -> str:
    """Copy an entire presentation via the Drive API.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        presentation_id: Source presentation ID.
        title: Title for the copy (default: "Copy of ...").

    Returns:
        The new presentation ID.
    """
    return client.copy_file(presentation_id, title)


def add_blank_slide(
    client,
    presentation_id: str,
    layout: str = "BLANK",
    insertion_index: Optional[int] = None,
) -> str:
    """Add a blank slide to a presentation.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        presentation_id: Target presentation ID.
        layout: Predefined layout (``"BLANK"``, ``"TITLE"``,
            ``"TITLE_AND_BODY"``, etc.).
        insertion_index: Position (0-based). ``None`` appends at end.

    Returns:
        The new slide's object ID.
    """
    slide_id = f"slide_{uuid.uuid4().hex[:12]}"
    request: Dict[str, Any] = {
        "createSlide": {
            "objectId": slide_id,
            "slideLayoutReference": {"predefinedLayout": layout},
        }
    }
    if insertion_index is not None:
        request["createSlide"]["insertionIndex"] = insertion_index

    batch_update(client, presentation_id, [request])
    log.info("Added slide %s to %s", slide_id, presentation_id)
    return slide_id


def insert_text(
    client,
    presentation_id: str,
    object_id: str,
    text: str,
    insertion_index: int = 0,
) -> Dict[str, Any]:
    """Insert text into an existing shape or text box.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        presentation_id: Target presentation ID.
        object_id: The shape/text-box object ID to insert into.
        text: Text string to insert.
        insertion_index: Character index within the shape's text (default 0).

    Returns:
        The API response dict.
    """
    requests = [
        {
            "insertText": {
                "objectId": object_id,
                "text": text,
                "insertionIndex": insertion_index,
            }
        }
    ]
    return batch_update(client, presentation_id, requests)


def create_textbox(
    client,
    presentation_id: str,
    slide_id: str,
    text: str,
    left: float = 100,
    top: float = 100,
    width: float = 400,
    height: float = 50,
) -> str:
    """Create a text box on a slide and populate it with text.

    Dimensions are in EMU (English Metric Units). 1 inch = 914400 EMU.
    For convenience, this function accepts points (1 pt = 12700 EMU)
    but the values are treated as points internally.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        presentation_id: Target presentation ID.
        slide_id: Slide object ID.
        text: Text to put in the box.
        left, top: Position in points from top-left.
        width, height: Dimensions in points.

    Returns:
        The textbox object ID.
    """
    box_id = f"textbox_{uuid.uuid4().hex[:12]}"
    pt = 12700  # EMU per point

    requests = [
        {
            "createShape": {
                "objectId": box_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": width * pt, "unit": "EMU"},
                        "height": {"magnitude": height * pt, "unit": "EMU"},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": left * pt,
                        "translateY": top * pt,
                        "unit": "EMU",
                    },
                },
            }
        },
        {
            "insertText": {
                "objectId": box_id,
                "text": text,
                "insertionIndex": 0,
            }
        },
    ]
    batch_update(client, presentation_id, requests)
    log.info("Created textbox %s on slide %s", box_id, slide_id)
    return box_id


def insert_image(
    client,
    presentation_id: str,
    slide_id: str,
    image_url: str,
    left: float = 100,
    top: float = 100,
    width: float = 400,
    height: float = 300,
) -> str:
    """Insert an image onto a slide from a URL.

    The URL must be publicly accessible or a Google Drive file URL.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        presentation_id: Target presentation ID.
        slide_id: Slide object ID.
        image_url: Public URL of the image.
        left, top: Position in points.
        width, height: Size in points.

    Returns:
        The image object ID.
    """
    img_id = f"image_{uuid.uuid4().hex[:12]}"
    pt = 12700

    requests = [
        {
            "createImage": {
                "objectId": img_id,
                "url": image_url,
                "elementProperties": {
                    "pageObjectId": slide_id,
                    "size": {
                        "width": {"magnitude": width * pt, "unit": "EMU"},
                        "height": {"magnitude": height * pt, "unit": "EMU"},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": left * pt,
                        "translateY": top * pt,
                        "unit": "EMU",
                    },
                },
            }
        }
    ]
    batch_update(client, presentation_id, requests)
    log.info("Inserted image %s on slide %s", img_id, slide_id)
    return img_id


def batch_update(
    client,
    presentation_id: str,
    requests: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Execute a batch of Slides API requests.

    Delegates to :py:meth:`GoogleWorkspaceClient.batch_update_presentation`.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        presentation_id: Target presentation ID.
        requests: List of request dicts per the Slides API batchUpdate spec.

    Returns:
        The API response dict.
    """
    return client.batch_update_presentation(presentation_id, requests)


# ---------------------------------------------------------------------------
# Argument-level operations (SAL-66)
# ---------------------------------------------------------------------------

# Slide dimensions (points): Google Slides default 10in × 5.625in
_SLIDE_W = 720
_SLIDE_H = 405

# Layout configs: (title_box, narrative_box, figure_box)
# Each box is (left, top, width, height) in points
_LAYOUTS = {
    "full_width": {
        "title":     (36,  20,  648,  44),
        "narrative": (36,  72,  648,  80),
        "figure":    (36, 162,  648, 220),
    },
    "side_by_side": {
        "title":     (36,  20,  648,  44),
        "narrative": (36,  72,  304, 300),
        "figure":    (358, 72,  326, 300),
    },
}


def upload_figure_to_drive(
    client,
    figure,
    filename: str,
    folder_id: Optional[str] = None,
) -> str:
    """Save a matplotlib Figure to a temp PNG, upload to Google Drive, return URL.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        figure: matplotlib Figure object.
        filename: Name for the uploaded file (without extension).
        folder_id: Optional Drive folder ID.

    Returns:
        Public URL string for the uploaded image (suitable for insert_image).
    """
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        figure.savefig(tmp_path, format="png", dpi=150, bbox_inches="tight")
        file_id = client.upload_file(
            local_path=tmp_path,
            name=f"{filename}.png",
            mime_type="image/png",
            folder_id=folder_id,
        )
        url = client.public_url(file_id)
        log.info("Uploaded figure %r → Drive %s", filename, file_id)
        return url
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def create_argument_slide(
    client,
    presentation_id: str,
    argument,
    slide_index: Optional[int] = None,
) -> str:
    """Add one slide for an Argument.

    Layout is derived from argument.layout:
      "full_width"   → title / narrative / figure stacked vertically
      "side_by_side" → title top; narrative left, figure right

    Args:
        client: Authenticated GoogleWorkspaceClient.
        presentation_id: Target presentation ID.
        argument: Argument dataclass instance.
        slide_index: Insertion position. None → append at end.

    Returns:
        Slide object ID.
    """
    layout_key = argument.layout if argument.layout in _LAYOUTS else "side_by_side"
    layout = _LAYOUTS[layout_key]

    # Add blank slide
    slide_id = add_blank_slide(client, presentation_id, insertion_index=slide_index)

    # Headline text box
    tl, tt, tw, th = layout["title"]
    create_textbox(client, presentation_id, slide_id,
                   argument.headline, left=tl, top=tt, width=tw, height=th)

    # Narrative text box (includes base_note if present)
    body_text = argument.narrative
    if argument.base_note:
        body_text = f"{body_text}\n\n{argument.base_note}"
    if argument.source_note:
        body_text = f"{body_text}\n{argument.source_note}"
    nl, nt, nw, nh = layout["narrative"]
    create_textbox(client, presentation_id, slide_id,
                   body_text, left=nl, top=nt, width=nw, height=nh)

    # Figure (chart or map)
    fig = argument.map_figure if layout_key == "full_width" and argument.map_figure else argument.chart
    if fig is not None:
        fl, ft, fw, fh = layout["figure"]
        fig_name = f"fig_{slide_id}"
        try:
            img_url = upload_figure_to_drive(client, fig, fig_name)
            insert_image(client, presentation_id, slide_id, img_url,
                         left=fl, top=ft, width=fw, height=fh)
        except Exception as exc:
            log.warning("Could not upload figure for slide %s: %s", slide_id, exc)

    return slide_id


def create_report_from_arguments(
    client,
    title: str,
    arguments: List,
    folder_id: Optional[str] = None,
    theme_presentation_id: Optional[str] = None,
) -> str:
    """Create a complete presentation from a list of Arguments.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        title: Presentation title.
        arguments: List of Argument dataclass instances (one slide each).
        folder_id: Optional Drive folder to place the presentation in.
        theme_presentation_id: If given, copies this presentation first
            (preserves master slides / theme).

    Returns:
        Presentation ID of the newly created report.
    """
    if theme_presentation_id:
        pres_id = copy_presentation(client, theme_presentation_id, title=title)
        if folder_id:
            client.move_to_folder(pres_id, folder_id)
    else:
        pres_id = create_presentation(client, title, folder_id=folder_id)

    for i, argument in enumerate(arguments):
        try:
            create_argument_slide(client, pres_id, argument, slide_index=i)
        except Exception as exc:
            log.error("Failed to create slide %d for argument %r: %s",
                      i, argument.headline, exc)

    log.info("Created report %r with %d slides → %s",
             title, len(arguments), client.presentation_url(pres_id))
    return pres_id

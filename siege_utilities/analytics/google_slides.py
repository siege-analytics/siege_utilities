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

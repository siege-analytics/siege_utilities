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
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional, Tuple

log = logging.getLogger(__name__)

__all__ = [
    "add_blank_slide",
    "batch_update",
    "copy_presentation",
    "create_argument_slide",
    "create_presentation",
    "create_report_from_arguments",
    "create_textbox",
    "get_presentation",
    "insert_image",
    "insert_text",
    "temporary_public_figure",
    "upload_figure_to_drive",
]


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


def _http_error_types() -> Tuple[type, ...]:
    """Return ``(googleapiclient.errors.HttpError,)`` if it can have been raised.

    Evaluated in an ``except`` clause, after the Google call has run. An
    ``HttpError`` can only come from googleapiclient code, which imports
    ``googleapiclient.errors`` itself, so when that module is not loaded no
    ``HttpError`` exists to catch and the empty tuple is exact. This keeps
    googleapiclient an optional dependency of this module.
    """
    import sys

    errors = sys.modules.get("googleapiclient.errors")
    http_error = getattr(errors, "HttpError", None)
    return (http_error,) if isinstance(http_error, type) else ()


def _upload_figure_file(
    client,
    figure,
    filename: str,
    folder_id: Optional[str] = None,
) -> str:
    """Save a matplotlib Figure to a temp PNG, upload it to Drive, return its file ID.

    The uploaded file is private: no sharing permission is created here.
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
        log.debug("Uploaded figure %r -> Drive %s", filename, file_id)
        return file_id
    finally:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass


def upload_figure_to_drive(
    client,
    figure,
    filename: str,
    folder_id: Optional[str] = None,
) -> str:
    """Save a matplotlib Figure to a temp PNG, upload to Google Drive, return URL.

    Warning:
        The uploaded file is shared **anyone-with-the-link (reader)** via
        ``GoogleWorkspaceClient.public_url`` and is left in Drive. Nothing
        revokes that permission or deletes the file. For inserting a figure
        into a slide, use :func:`temporary_public_figure`, which deletes the
        Drive file once the insert has run.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        figure: matplotlib Figure object.
        filename: Name for the uploaded file (without extension).
        folder_id: Optional Drive folder ID. Without it the file lands in the
            root of the authenticated account's My Drive.

    Returns:
        Public URL string for the uploaded image (suitable for insert_image).
    """
    file_id = _upload_figure_file(client, figure, filename, folder_id=folder_id)
    return client.public_url(file_id)


def _delete_figure_file(client, file_id: str, raise_on_failure: bool) -> None:
    """Delete a temporary figure file from Drive (this also drops its permissions).

    A failure is always logged at ERROR with the file ID, because the file is
    still readable by anyone with its link. It is re-raised only when
    ``raise_on_failure`` is true, so that a cleanup failure never replaces an
    insert error that is already propagating.
    """
    try:
        client.drive_service().files().delete(fileId=file_id).execute()
        log.debug("Deleted temporary figure file %s from Drive", file_id)
    except Exception as exc:  # includes googleapiclient HttpError
        log.error(
            "Failed to delete temporary figure file %s from Drive; it remains "
            "readable by anyone with the link and must be removed manually: %s",
            file_id, exc,
        )
        if raise_on_failure:
            raise RuntimeError(
                f"Could not delete temporary public figure file {file_id} "
                f"from Drive: {exc}"
            ) from exc


@contextmanager
def temporary_public_figure(
    client,
    figure,
    filename: str,
    folder_id: Optional[str] = None,
) -> Iterator[str]:
    """Upload a figure, publish it for the duration of the block, then delete it.

    Slides ``createImage`` fetches the image once, at request time, from a
    URL that must be reachable without authentication, and stores its own
    copy. This context manager uploads the figure to ``folder_id``, grants an
    anyone-with-the-link reader permission, yields the public URL, and in a
    ``finally`` deletes the Drive file (which removes the permission too),
    whether or not the block raised.

    If the delete fails, the file ID is logged at ERROR. The delete error is
    raised only when the block itself succeeded; an error from the block is
    never masked by a cleanup failure.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        figure: matplotlib Figure object.
        filename: Name for the uploaded file (without extension).
        folder_id: Optional Drive folder for the temporary file.

    Yields:
        The public URL of the uploaded image.
    """
    file_id = _upload_figure_file(client, figure, filename, folder_id=folder_id)
    block_succeeded = False
    try:
        yield client.public_url(file_id)
        block_succeeded = True
    finally:
        _delete_figure_file(client, file_id, raise_on_failure=block_succeeded)


def _table_to_text(table) -> str:
    """Render an Argument.table (DataFrame or Chain) to plain text.

    A table-bearing Argument must not lose its table on a slide. This is a
    text rendering, not a native Slides table; it preserves the content.
    """
    import pandas as pd

    def _render(df: "pd.DataFrame") -> str:
        # Keep the index when it carries labels (e.g. metric names); drop only a
        # plain positional RangeIndex so meaningful row labels are not lost.
        keep_index = not isinstance(df.index, pd.RangeIndex)
        return df.to_string(index=keep_index)

    if isinstance(table, pd.DataFrame):
        return _render(table)
    to_df = getattr(table, "to_dataframe", None)
    if callable(to_df):
        df = to_df()
        if isinstance(df, pd.DataFrame):
            return _render(df)
    return str(table)


def create_argument_slide(
    client,
    presentation_id: str,
    argument,
    slide_index: Optional[int] = None,
    folder_id: Optional[str] = None,
    publish_figures: bool = True,
) -> str:
    """Add one slide for an Argument.

    Layout is derived from argument.layout:
      "full_width"   → title / narrative / figure stacked vertically
      "side_by_side" → title top; narrative left, figure right

    A figure is inserted through :func:`temporary_public_figure`: it is
    uploaded to ``folder_id``, shared anyone-with-the-link while Slides copies
    it, then deleted from Drive.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        presentation_id: Target presentation ID.
        argument: Argument dataclass instance.
        slide_index: Insertion position. None → append at end.
        folder_id: Drive folder for the temporary figure file. None → the
            root of the authenticated account's My Drive.
        publish_figures: If False, the figure is not uploaded, no
            anyone-with-the-link permission is created, and the slide is
            built without it (a WARNING is logged).

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
    # Render the table so a table-bearing Argument does not silently lose it.
    table = getattr(argument, "table", None)
    if table is not None:
        table_text = _table_to_text(table)
        if table_text:
            body_text = f"{body_text}\n\n{table_text}"
    nl, nt, nw, nh = layout["narrative"]
    create_textbox(client, presentation_id, slide_id,
                   body_text, left=nl, top=nt, width=nw, height=nh)

    # Figure (chart or map)
    fig = argument.map_figure if layout_key == "full_width" and argument.map_figure else argument.chart
    if fig is not None and not publish_figures:
        log.warning(
            "Slide %s: figure omitted because publish_figures=False "
            "(Slides can only insert images from a public URL)", slide_id,
        )
    elif fig is not None:
        fl, ft, fw, fh = layout["figure"]
        fig_name = f"fig_{slide_id}"
        try:
            with temporary_public_figure(
                client, fig, fig_name, folder_id=folder_id,
            ) as img_url:
                insert_image(client, presentation_id, slide_id, img_url,
                             left=fl, top=ft, width=fw, height=fh)
        except (OSError, ValueError, RuntimeError, KeyError,
                *_http_error_types()) as exc:
            # A map/chart is the core content of the slide; a failed figure is
            # a failed slide, not a text-only success. Propagate so
            # create_report_from_arguments aggregates it into its failure list
            # instead of returning a presentation id with missing figures.
            raise RuntimeError(
                f"Figure upload/insert failed for slide {slide_id} "
                f"(figure {fig_name}): {exc}"
            ) from exc

    return slide_id


def create_report_from_arguments(
    client,
    title: str,
    arguments: List,
    folder_id: Optional[str] = None,
    theme_presentation_id: Optional[str] = None,
    publish_figures: bool = True,
) -> str:
    """Create a complete presentation from a list of Arguments.

    Removes any existing content slides from the new presentation or theme
    copy before adding one slide per argument. Theme masters and layouts are
    preserved; the source template is unchanged. An empty argument list
    produces a presentation with no content slides. Failure to read or delete
    the initial slides propagates before report slides are added.

    Public exposure of figures:
        The Slides API can only insert an image from a URL that is reachable
        without authentication. With ``publish_figures=True`` (the default),
        each chart or map is therefore uploaded to Drive (into ``folder_id``
        when given), shared **anyone-with-the-link (reader)** for the
        duration of its ``createImage`` request, and then deleted from Drive,
        including when the insert fails. While it exists, anyone holding the
        URL can fetch the image without signing in. If the delete fails, the
        file ID is logged at ERROR and the file must be removed manually.
        Pass ``publish_figures=False`` to never create an anyone permission;
        figures are then left out of the slides.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        title: Presentation title.
        arguments: List of Argument dataclass instances (one slide each).
        folder_id: Optional Drive folder to place the presentation, and the
            temporary figure files, in.
        theme_presentation_id: If given, copies this presentation first
            (preserves masters, layouts, and theme; removes sample slides
            from the copy).
        publish_figures: If False, figures are not uploaded or published and
            are omitted from the slides.

    Returns:
        Presentation ID of the newly created report.
    """
    if theme_presentation_id:
        pres_id = copy_presentation(client, theme_presentation_id, title=title)
        if folder_id:
            client.move_to_folder(pres_id, folder_id)
    else:
        pres_id = create_presentation(client, title, folder_id=folder_id)

    presentation = get_presentation(client, pres_id)
    delete_requests = [
        {"deleteObject": {"objectId": slide["objectId"]}}
        for slide in presentation.get("slides", [])
    ]
    if delete_requests:
        batch_update(client, pres_id, delete_requests)
        log.debug("Deleted %d initial slides from report %s", len(delete_requests), pres_id)

    failures = []
    for i, argument in enumerate(arguments):
        try:
            create_argument_slide(
                client, pres_id, argument, slide_index=i,
                folder_id=folder_id, publish_figures=publish_figures,
            )
        except (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError) as exc:
            headline = getattr(argument, "headline", "?")
            log.error("Failed to create slide %d for argument %r: %s", i, headline, exc)
            failures.append((i, headline, repr(exc)))

    if failures:
        # SU-1: a report missing slides is not a success. Do not return the
        # presentation id as if everything rendered; surface what failed. The
        # presentation exists in Drive for inspection/cleanup.
        raise RuntimeError(
            f"create_report_from_arguments: {len(failures)} of {len(arguments)} "
            f"slides failed for presentation {pres_id} "
            f"({client.presentation_url(pres_id)}); failures={failures}. "
            f"The presentation was created but is incomplete."
        )

    log.info("Created report %r with %d slides → %s",
             title, len(arguments), client.presentation_url(pres_id))
    return pres_id

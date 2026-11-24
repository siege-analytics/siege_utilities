"""
Google Docs write service.

Provides functions for creating documents, inserting text, tables,
images, and performing batch updates via the Docs API v1.

Usage:
    from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient
    from siege_utilities.analytics.google_docs import (
        create_document, insert_text, insert_table,
    )

    client = GoogleWorkspaceClient.from_service_account()
    doc_id = create_document(client, "Meeting Notes")
    insert_text(client, doc_id, "Agenda\\n", bold=True)
    insert_table(client, doc_id, rows=3, cols=2)
"""

import logging
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

__all__ = [
    "batch_update",
    "copy_document",
    "create_document",
    "get_document",
    "insert_image",
    "insert_paragraph",
    "insert_table",
    "insert_text",
    "read_document_text",
    "replace_text",
]


def create_document(
    client,
    title: str,
    folder_id: Optional[str] = None,
) -> str:
    """Create a new Google Doc and return its document ID.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        title: Title for the new document.
        folder_id: Optional Drive folder ID to create the document in.

    Returns:
        The document ID string.
    """
    body = {"title": title}
    result = client.docs_service().documents().create(body=body).execute()
    doc_id = result["documentId"]

    if folder_id:
        client.move_to_folder(doc_id, folder_id)

    url = client.document_url(doc_id)
    log.info("Created document %r → %s", title, url)
    return doc_id


def get_document(
    client,
    document_id: str,
) -> Dict[str, Any]:
    """Fetch document metadata and the first tab's content structure.

    Returns:
        The document resource dict.
    """
    return (
        client.docs_service()
        .documents()
        .get(documentId=document_id)
        .execute()
    )


def copy_document(
    client,
    document_id: str,
    title: Optional[str] = None,
) -> str:
    """Copy a document via the Drive API.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        document_id: Source document ID.
        title: Title for the copy (default: "Copy of ...").

    Returns:
        The new document ID.
    """
    return client.copy_file(document_id, title)


def _read_structural_elements(content: List[Dict[str, Any]]) -> str:
    """Collect text runs in order, including nested tables and contents lists."""
    parts: List[str] = []
    pending = list(reversed(content))
    while pending:
        element = pending.pop()
        if "paragraph" in element:
            for paragraph_element in element["paragraph"].get("elements", []):
                parts.append(paragraph_element.get("textRun", {}).get("content", ""))
        elif "table" in element:
            children = [
                child
                for row in element["table"].get("tableRows", [])
                for cell in row.get("tableCells", [])
                for child in cell.get("content", [])
            ]
            pending.extend(reversed(children))
        elif "tableOfContents" in element:
            pending.extend(reversed(element["tableOfContents"].get("content", [])))
    return "".join(parts)


def read_document_text(
    client,
    document_id: str,
) -> str:
    """Read plain-text runs from all document tabs and text segments.

    Visits tabs depth-first, including child tabs. Within each tab, reads
    the body followed by headers, footers, and footnotes in API response
    order. Traverses paragraphs, nested tables, and tables of contents in
    every segment. Footnote text is included once in the footnotes section,
    not at each reference. Preserves text-run whitespace without adding
    separators, generated reference markers, or text from embedded objects.
    Legacy responses without tabs use the same traversal at document level.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        document_id: Target document ID.

    Returns:
        The document text as a single string.
    """
    doc = (
        client.docs_service()
        .documents()
        .get(documentId=document_id, includeTabsContent=True)
        .execute()
    )
    parts: List[str] = []
    pending = list(reversed(doc.get("tabs", [])))
    if not pending:
        pending = [{"documentTab": doc}]
    while pending:
        tab = pending.pop()
        document_tab = tab.get("documentTab", {})
        parts.append(_read_structural_elements(document_tab.get("body", {}).get("content", [])))
        for segment_type in ("headers", "footers", "footnotes"):
            for segment in document_tab.get(segment_type, {}).values():
                parts.append(_read_structural_elements(segment.get("content", [])))
        pending.extend(reversed(tab.get("childTabs", [])))

    return "".join(parts)


def insert_text(
    client,
    document_id: str,
    text: str,
    index: int = 1,
    bold: bool = False,
    italic: bool = False,
    font_size: Optional[int] = None,
) -> Dict[str, Any]:
    """Insert text at a given index in a document.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        document_id: Target document ID.
        text: Text to insert.
        index: UTF-16 code-unit index (1 = start of document body).
        bold: Apply bold formatting.
        italic: Apply italic formatting.
        font_size: Font size in points (``None`` = default).

    Returns:
        The API response dict.
    """
    requests: List[Dict[str, Any]] = [
        {
            "insertText": {
                "location": {"index": index},
                "text": text,
            }
        }
    ]

    # Apply formatting if any style is requested
    if bold or italic or font_size:
        style: Dict[str, Any] = {}
        fields = []
        if bold:
            style["bold"] = True
            fields.append("bold")
        if italic:
            style["italic"] = True
            fields.append("italic")
        if font_size:
            style["fontSize"] = {"magnitude": font_size, "unit": "PT"}
            fields.append("fontSize")

        requests.append({
            "updateTextStyle": {
                "range": {
                    "startIndex": index,
                    "endIndex": index + len(text.encode("utf-16-le")) // 2,
                },
                "textStyle": style,
                "fields": ",".join(fields),
            }
        })

    return batch_update(client, document_id, requests)


def insert_paragraph(
    client,
    document_id: str,
    text: str,
    index: int = 1,
    heading: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert a paragraph with optional heading style.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        document_id: Target document ID.
        text: Paragraph text (newline is appended automatically).
        index: UTF-16 code-unit index (1 = start of document body).
        heading: Named style (``"HEADING_1"`` through ``"HEADING_6"``,
            ``"TITLE"``, ``"SUBTITLE"``, or ``None`` for normal text).

    Returns:
        The API response dict.
    """
    full_text = text if text.endswith("\n") else text + "\n"

    requests: List[Dict[str, Any]] = [
        {
            "insertText": {
                "location": {"index": index},
                "text": full_text,
            }
        }
    ]

    if heading:
        requests.append({
            "updateParagraphStyle": {
                "range": {
                    "startIndex": index,
                    "endIndex": index + len(full_text.encode("utf-16-le")) // 2,
                },
                "paragraphStyle": {"namedStyleType": heading},
                "fields": "namedStyleType",
            }
        })

    return batch_update(client, document_id, requests)


def insert_table(
    client,
    document_id: str,
    rows: int,
    cols: int,
    index: int = 1,
) -> Dict[str, Any]:
    """Insert an empty table at the given index.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        document_id: Target document ID.
        rows: Number of rows.
        cols: Number of columns.
        index: Character index where the table is inserted.

    Returns:
        The API response dict.
    """
    requests = [
        {
            "insertTable": {
                "rows": rows,
                "columns": cols,
                "location": {"index": index},
            }
        }
    ]
    result = batch_update(client, document_id, requests)
    log.info("Inserted %dx%d table at index %d in %s", rows, cols, index, document_id)
    return result


def insert_image(
    client,
    document_id: str,
    image_uri: str,
    index: int = 1,
    width: Optional[float] = None,
    height: Optional[float] = None,
) -> Dict[str, Any]:
    """Insert an image from a URL.

    The URI must be publicly accessible or a Google Drive file.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        document_id: Target document ID.
        image_uri: Public URL of the image.
        index: Character index for insertion.
        width: Optional width in points.
        height: Optional height in points.

    Returns:
        The API response dict.
    """
    request: Dict[str, Any] = {
        "insertInlineImage": {
            "uri": image_uri,
            "location": {"index": index},
        }
    }
    if width:
        request["insertInlineImage"]["objectSize"] = {
            "width": {"magnitude": width, "unit": "PT"},
        }
        if height:
            request["insertInlineImage"]["objectSize"]["height"] = {
                "magnitude": height, "unit": "PT",
            }

    result = batch_update(client, document_id, [request])
    log.info("Inserted image at index %d in %s", index, document_id)
    return result


def replace_text(
    client,
    document_id: str,
    find: str,
    replace_with: str,
    match_case: bool = True,
) -> Dict[str, Any]:
    """Find and replace text throughout a document.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        document_id: Target document ID.
        find: Text to search for.
        replace_with: Replacement text.
        match_case: Whether the search is case-sensitive.

    Returns:
        The API response dict.
    """
    requests = [
        {
            "replaceAllText": {
                "containsText": {
                    "text": find,
                    "matchCase": match_case,
                },
                "replaceText": replace_with,
            }
        }
    ]
    result = batch_update(client, document_id, requests)
    log.info("Replaced %r → %r in %s", find, replace_with, document_id)
    return result


def batch_update(
    client,
    document_id: str,
    requests: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Execute a batch of Docs API requests.

    Delegates to :py:meth:`GoogleWorkspaceClient.batch_update_document`.

    Args:
        client: Authenticated GoogleWorkspaceClient.
        document_id: Target document ID.
        requests: List of request dicts per the Docs API batchUpdate spec.

    Returns:
        The API response dict.
    """
    return client.batch_update_document(document_id, requests)

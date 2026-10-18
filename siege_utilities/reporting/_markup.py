"""Escape plain data before embedding it in reporting markup."""

from html import escape


def _escape_paragraph(text: str) -> str:
    """Escape characters ReportLab Paragraph parses as mini-HTML markup.

    Paragraph treats ``<`` as a tag start and ``&`` as an entity start;
    a raw user string like ``"Q&A about <3 favorites"`` raises a parse
    error mid-render. We escape both before they reach the parser.
    Order matters — escape ``&`` first so the ``&`` introduced by
    ``&lt;`` / ``&gt;`` is not re-escaped.
    """
    if not isinstance(text, str):
        text = str(text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _build_popup_html(label=None, details=()) -> str:
    """Build a Folium popup with a bold label and plain-text detail lines."""
    parts = []
    if label is not None:
        parts.append(f"<b>{escape(str(label))}</b>")
    parts.extend(escape(str(detail)) for detail in details)
    return "<br>".join(parts)

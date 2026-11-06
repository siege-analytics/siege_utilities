"""Translate facade payloads into the PDF renderer's section format."""

import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from .report_generator import ReportGenerator

__all__ = []


def _chart_images(config: dict[str, Any], generator: ReportGenerator) -> list[Any]:
    """Render the bar, line and pie configurations collected by the facades."""
    data = config["data"]
    labels = data.get("labels", [])
    if not labels:
        return []
    charts = generator.chart_generator
    title = config.get("title", "")
    kind = config["type"]
    if kind == "pie":
        return [charts.create_pie_chart(
            {"Label": labels, "Value": data["data"]},
            labels_column="Label", values_column="Value", title=title,
        )]
    datasets = data.get("datasets", [])
    if kind == "line":
        # Numbering preserves series labels while keeping column names unique.
        columns = {
            f"{i + 1}. {item.get('label', 'Value')}": item["data"]
            for i, item in enumerate(datasets)
        }
        return [charts.create_line_chart(
            {"Label": labels, **columns}, x_column="Label",
            y_columns=list(columns), title=title,
        )] if datasets else []
    if kind == "bar":
        return [charts.create_bar_chart(
            {"Label": labels, "Value": item["data"]},
            x_column="Label", y_column="Value",
            title=f"{title} - {item['label']}" if item.get("label") else title,
            show_legend=False,
        ) for item in datasets]
    raise ValueError(f"Unsupported facade chart type: {kind}")


def _table_section(title: str, headers: list[Any], rows: list[list[Any]]) -> dict[str, Any]:
    """Wrap table text so long labels and posts fit the printable page."""
    # ReportLab remains optional until a facade actually renders a PDF.
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph

    from ._markup import _escape_paragraph

    style = getSampleStyleSheet()["BodyText"]
    style.fontSize = 8
    style.leading = 10
    data = [headers, *rows] if headers else rows
    return {
        "type": "table", "title": title,
        "content": {"data": [
            [Paragraph(_escape_paragraph(str(cell)), style) for cell in row]
            for row in data
        ]},
    }


def _render_facade_report(
    generator: ReportGenerator, payload: dict[str, Any], title: str,
) -> Path:
    """Write a uniquely named PDF and return its path after rendering succeeds."""
    sections = []
    if payload.get("executive_summary"):
        sections.append({
            "type": "text", "title": "Executive Summary",
            "content": payload["executive_summary"],
        })
    metrics = payload.get("metrics", {})
    if metrics:
        rows = []
        for name, metric in metrics.items():
            detail = metric if isinstance(metric, dict) else {"value": metric}
            rows.append([name, detail.get("value", ""), detail.get("change", ""),
                         detail.get("status", "")])
        sections.append(_table_section("Key Metrics", ["Metric", "Value", "Change", "Status"], rows))
    for table in payload.get("tables", []):
        sections.append(_table_section(table.get("title", ""), table.get("headers", []), table["data"]))
    if payload.get("insights"):
        sections.append({
            "type": "text", "title": "Key Insights",
            "content": "\n".join(f"- {insight}" for insight in payload["insights"]),
        })
    for chart in payload.get("charts", []):
        sections.append({
            "type": "charts", "title": chart.get("title", ""),
            "content": {"charts": _chart_images(chart, generator)},
        })

    # Custom data processors supply sections rather than the aggregate payload.
    for section in payload.get("sections", []):
        if section["type"] == "table":
            sections.append(_table_section(
                section.get("title", ""), section.get("headers", []), section["data"],
            ))
        elif section["type"] == "chart":
            config = section.get("chart_config")
            if config:
                sections.append({
                    "type": "charts", "title": section.get("title", ""),
                    "content": {"charts": _chart_images(config, generator),
                                "description": section.get("caption", "")},
                })
        else:
            sections.append(section)

    report_content = {
        "title": title,
        "metadata": {"title": title, "subtitle": payload.get("subtitle", "")},
        "sections": sections,
    }
    # Do not interpret client-controlled report titles as paths, or overwrite
    # earlier reports when the same title is used for another date window.
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", title).strip("_")[:80] or "report"
    output_path = generator.output_dir / f"{stem}_{uuid4().hex}.pdf"
    generator.generate_pdf_report(report_content, str(output_path))
    return Path(output_path)

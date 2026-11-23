"""Translate facade payloads into the PDF renderer's section format."""

import logging
import math
import numbers
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from .report_generator import ReportGenerator

__all__ = []

log = logging.getLogger(__name__)

_SUPPORTED_CHART_TYPES = ("bar", "line", "pie")


def _is_missing(value: Any) -> bool:
    """A chart value is missing when it is None, a NaN of any kind, or pandas.NA."""
    return value is None or (pd.api.types.is_scalar(value) and bool(pd.isna(value)))


def _checked_series(kind: str, title: str, labels: list[Any], values: list[Any]) -> list[Any]:
    """Return one series after checking it against the chart labels.

    Raises:
        ValueError: the series and the labels differ in length, or a known
            value is not a number.
    """
    if len(values) != len(labels):
        raise ValueError(
            f"Facade {kind} chart {title!r} has {len(labels)} labels "
            f"but {len(values)} values"
        )
    for value in values:
        if not _is_missing(value) and not isinstance(value, numbers.Number):
            raise ValueError(
                f"Facade {kind} chart {title!r} has a non-numeric value: {value!r}"
            )
    return list(values)


def _known_points(labels: list[Any], values: list[Any]) -> tuple[list[Any], list[Any]]:
    """Return the label/value pairs whose value is known, in order.

    The caller checks the lengths first (``_checked_series``).
    """
    pairs = [(label, value) for label, value in zip(labels, values) if not _is_missing(value)]
    return [label for label, _ in pairs], [value for _, value in pairs]


def _chart_images(config: dict[str, Any], generator: ReportGenerator) -> list[Any]:
    """Render the bar, line and pie configurations collected by the facades.

    A missing value (None, a NaN of any kind, or pandas.NA) is a gap, never a
    zero: bar and pie charts omit it, a line chart leaves a break. A chart
    with no labels, no datasets or no known values is left out with a warning.

    Raises:
        ValueError: the chart type is not bar, line or pie; a series and the
            labels differ in length; a known value is not a number; or the
            known values of a pie chart total zero.
    """
    # Validate the type before the empty-labels shortcut so an unsupported
    # configuration is reported even when it has nothing to draw.
    kind = config["type"]
    if kind not in _SUPPORTED_CHART_TYPES:
        raise ValueError(f"Unsupported facade chart type: {kind}")
    data = config["data"]
    labels = data.get("labels", [])
    title = config.get("title", "")
    if not labels:
        log.warning("Facade %s chart %r has no labels; it is left out", kind, title)
        return []
    charts = generator.chart_generator
    if kind == "pie":
        pie_labels, pie_values = _known_points(
            labels, _checked_series(kind, title, labels, data["data"]),
        )
        if not pie_values:
            log.warning("Facade pie chart %r has no known values; it is left out", title)
            return []
        if sum(pie_values) == 0:
            raise ValueError(f"Facade pie chart {title!r} has values that total zero")
        return [charts.create_pie_chart(
            {"Label": pie_labels, "Value": pie_values},
            labels_column="Label", values_column="Value", title=title,
        )]
    datasets = data.get("datasets", [])
    if not datasets:
        log.warning("Facade %s chart %r has no datasets; it is left out", kind, title)
        return []
    if kind == "line":
        # Numbering preserves series labels while keeping column names unique.
        # A missing value becomes NaN, which matplotlib draws as a break.
        columns = {
            f"{i + 1}. {item.get('label', 'Value')}": [
                math.nan if _is_missing(value) else value
                for value in _checked_series(kind, title, labels, item["data"])
            ]
            for i, item in enumerate(datasets)
        }
        if all(_is_missing(value) for series in columns.values() for value in series):
            log.warning("Facade line chart %r has no known values; it is left out", title)
            return []
        return [charts.create_line_chart(
            {"Label": labels, **columns}, x_column="Label",
            y_columns=list(columns), title=title,
        )]
    images = []
    for item in datasets:
        label = item.get("label")
        item_title = f"{title} - {label}" if title and label else (label or title)
        bar_labels, bar_values = _known_points(
            labels, _checked_series(kind, item_title, labels, item["data"]),
        )
        if not bar_values:
            log.warning("Facade bar chart %r has no known values; it is left out", item_title)
            continue
        images.append(charts.create_bar_chart(
            {"Label": bar_labels, "Value": bar_values},
            x_column="Label", y_column="Value",
            title=item_title, show_legend=False,
        ))
    return images


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
    # A chart that draws nothing is left out with its heading; _chart_images
    # has already logged why.
    for chart in payload.get("charts", []):
        images = _chart_images(chart, generator)
        if images:
            sections.append({
                "type": "charts", "title": chart.get("title", ""),
                "content": {"charts": images},
            })

    # Custom data processors supply sections rather than the aggregate payload.
    for section in payload.get("sections", []):
        if section["type"] == "table":
            sections.append(_table_section(
                section.get("title", ""), section.get("headers", []), section["data"],
            ))
        elif section["type"] == "chart":
            config = section.get("chart_config")
            images = _chart_images(config, generator) if config else []
            if images:
                sections.append({
                    "type": "charts", "title": section.get("title", ""),
                    "content": {"charts": images,
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

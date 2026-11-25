"""Translate facade payloads into the PDF renderer's section format."""

import logging
import math
import numbers
import re
from decimal import Decimal
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


_INT64_MIN = -(2 ** 63)
_INT64_MAX = 2 ** 63 - 1


def _plain_number(value: numbers.Number) -> int | float:
    """Return a known chart value as a built-in int or float.

    The chart engine hands values to matplotlib, which (from 3.11) rejects a
    ``Decimal`` in a pie chart. Integral values stay ints so value labels keep
    printing ``88`` rather than ``88.0``; that includes a finite ``Decimal``
    written without a fractional part (``Decimal("88")``, ``Decimal("1E+3")``,
    ``Decimal("0E+19")``) that fits a 64-bit integer, while ``Decimal("88.0")``
    stays a float. A larger whole-number ``Decimal`` becomes a float; its size
    is checked from the exponent before any int is built. Whether a whole
    series can stay ints is decided by ``_fits_int64``.
    """
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, Decimal) and value.is_finite() and value.as_tuple().exponent >= 0:
        if value.is_zero():
            return 0
        if value.adjusted() < 19:
            integral = int(value)
            if _INT64_MIN <= integral <= _INT64_MAX:
                return integral
    return float(value)


def _fits_int64(values: list[Any]) -> bool:
    """True when every int in a series, and their total, fits a signed 64-bit integer.

    A bar chart cannot draw an int outside that range, and a pie chart sums
    its values as 64-bit integers, so a larger total wraps and the wedges stop
    matching the legend. Such a series is drawn from floats instead.
    """
    ints = [value for value in values if type(value) is int]
    return (all(_INT64_MIN <= value <= _INT64_MAX for value in ints)
            and _INT64_MIN <= sum(ints) <= _INT64_MAX)


def _checked_series(kind: str, title: str, labels: list[Any], values: list[Any]) -> list[Any]:
    """Return one series after checking it against the chart labels.

    Known values come back as built-in ints or floats (``Decimal`` and NumPy
    scalars included); missing values are returned unchanged. When an int in
    the series, or the total of its ints, falls outside the signed 64-bit
    range, every int in the series is returned as a float.

    Raises:
        ValueError: the series and the labels differ in length, a known
            value is not a real number, or a value is too large to draw.
    """
    if len(values) != len(labels):
        raise ValueError(
            f"Facade {kind} chart {title!r} has {len(labels)} labels "
            f"but {len(values)} values"
        )
    checked = []
    for value in values:
        if _is_missing(value):
            checked.append(value)
            continue
        try:
            if not isinstance(value, numbers.Number):
                raise TypeError(type(value).__name__)
            # float() would drop the imaginary part of a NumPy complex.
            if isinstance(value, numbers.Complex) and not isinstance(value, numbers.Real):
                raise TypeError(f"{type(value).__name__} is not a real number")
            checked.append(_plain_number(value))
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(
                f"Facade {kind} chart {title!r} has a non-numeric value: {value!r}"
            ) from exc
    if not _fits_int64(checked):
        try:
            checked = [float(value) if type(value) is int else value for value in checked]
        except OverflowError as exc:
            raise ValueError(
                f"Facade {kind} chart {title!r} has a value too large to draw"
            ) from exc
    return checked


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
            labels differ in length; a known value is not a real number or
            is too large to draw; or the known values of a pie chart total
            zero.
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

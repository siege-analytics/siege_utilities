"""
Bar, line, pie, and proportional text bar chart mixins.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Any, Union

from .._markup import _escape_paragraph

# Core plotting libraries
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    sns = None

# Data processing
try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None
    np = None

try:
    from reportlab.platypus import Image
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    Image = None

log = logging.getLogger(__name__)

__all__ = [
    "BarChartMixin",
]


class BarChartMixin:
    """Bar chart, line chart, pie chart, and proportional text bar chart methods."""

    def create_bar_chart(self, data: Union[pd.DataFrame, Dict[str, Any]],
                        x_column: str = None, y_column: str = None,
                        title: str = "", width: float = 6.0, height: float = 4.0,
                        chart_type: str = "bar", group_by: str = None,
                        show_legend: bool = True, legend_position: str = "best") -> Image:
        """
        Create a bar chart from data.

        Args:
            data: DataFrame or dictionary with data
            x_column: Column name for X-axis (or 'index' for DataFrame index)
            y_column: Column name for Y-axis
            title: Chart title
            width: Chart width in inches
            height: Chart height in inches
            chart_type: Type of chart ('bar', 'horizontal')
            group_by: Column to group by for grouped bars

        Returns:
            ReportLab Image object
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Matplotlib not available")

        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data.copy()

            # Handle different data formats
            if x_column == 'index':
                x_values = df.index.tolist()
            elif x_column:
                x_values = df[x_column].tolist()
            else:
                x_values = range(len(df))

            if y_column:
                y_values = df[y_column].tolist()
            else:
                # Use first numeric column
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    y_column = numeric_cols[0]
                    y_values = df[y_column].tolist()
                else:
                    raise ValueError("No numeric columns found in data for bar chart")

            # Create figure with very conservative sizing to prevent ReportLab crashes
            fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)
            fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)

            # Create chart
            if chart_type == "horizontal":
                bars = ax.barh(x_values, y_values, color=self.default_colors['primary'])
                ax.set_xlabel(y_column)
                ax.set_ylabel(x_column if x_column != 'index' else 'Index')
            else:
                bars = ax.bar(x_values, y_values, color=self.default_colors['primary'])
                ax.set_xlabel(x_column if x_column != 'index' else 'Index')
                ax.set_ylabel(y_column)

            # Customize chart
            ax.set_title(title or f"{y_column} by {x_column if x_column != 'index' else 'Index'}")
            ax.grid(True, alpha=0.3)

            # Rotate x-axis labels if needed
            if len(x_values) > 5:
                plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

            # Add value labels on bars
            for bar in bars:
                bar_height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., bar_height,
                       f'{bar_height:,.0f}', ha='center', va='bottom')

            # Add legend with better positioning
            if show_legend and (group_by or len(y_values) > 1):
                if legend_position == "outside":
                    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                elif legend_position == "bottom":
                    ax.legend(bbox_to_anchor=(0.5, -0.15), loc='upper center', ncol=min(3, len(y_values) if len(y_values) > 1 else 1))
                else:  # "best" or default
                    ax.legend(loc='best')

            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)

        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as e:
            raise RuntimeError("Chart generation failed") from e

    def create_line_chart(self, data: Union[pd.DataFrame, Dict[str, Any]],
                         x_column: str = None, y_columns: List[str] = None,
                         title: str = "", width: float = 6.0, height: float = 4.0,
                         show_legend: bool = True, legend_position: str = "best") -> Image:
        """
        Create a line chart from data.

        Args:
            data: DataFrame or dictionary with data
            x_column: Column name for X-axis
            y_columns: List of column names for Y-axis (multiple lines)
            title: Chart title
            width: Chart width in inches
            height: Chart height in inches

        Returns:
            ReportLab Image object
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Matplotlib not available")

        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data.copy()

            # Handle different data formats
            if x_column == 'index':
                x_values = df.index.tolist()
            elif x_column:
                x_values = df[x_column].tolist()
            else:
                x_values = range(len(df))

            if not y_columns:
                # Use all numeric columns except x_column
                numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                if x_column in numeric_cols:
                    numeric_cols.remove(x_column)
                y_columns = numeric_cols[:5]  # Limit to 5 columns

            # Create figure with very conservative sizing to prevent ReportLab crashes
            fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)
            fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)

            # Plot each line
            for i, col in enumerate(y_columns):
                if col in df.columns:
                    color = self.color_palette[i % len(self.color_palette)]
                    ax.plot(x_values, df[col].tolist(),
                           label=col, color=color, linewidth=2, marker='o')

            # Customize chart
            ax.set_title(title or "Trends over time")
            ax.set_xlabel(x_column if x_column != 'index' else 'Index')
            ax.set_ylabel('Value')

            # Add legend with better positioning
            if show_legend and len(y_columns) > 1:
                if legend_position == "outside":
                    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                elif legend_position == "bottom":
                    ax.legend(bbox_to_anchor=(0.5, -0.15), loc='upper center', ncol=min(len(y_columns), 3))
                else:  # "best" or default
                    ax.legend(loc='best')
            elif show_legend and len(y_columns) == 1:
                # Single line - add legend if title suggests it's needed
                if "vs" in title.lower() or "comparison" in title.lower():
                    ax.legend([y_columns[0]], loc='best')

            ax.grid(True, alpha=0.3)

            # Rotate x-axis labels if needed
            if len(x_values) > 5:
                plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)

        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as e:
            raise RuntimeError("Chart generation failed") from e

    def create_pie_chart(self, data: Union[pd.DataFrame, Dict[str, Any]],
                        labels_column: str = None, values_column: str = None,
                        title: str = "", width: float = 6.0, height: float = 4.0,
                        show_legend: bool = True, legend_position: str = "right") -> Image:
        """
        Create a pie chart from data.

        Args:
            data: DataFrame or dictionary with data
            labels_column: Column name for labels
            values_column: Column name for values
            title: Chart title
            width: Chart width in inches
            height: Chart height in inches

        Returns:
            ReportLab Image object
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Matplotlib not available")

        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data.copy()

            # Handle different data formats
            if labels_column and values_column:
                labels = df[labels_column].tolist()
                values = df[values_column].tolist()
            else:
                # Use first two columns
                cols = df.columns.tolist()
                if len(cols) >= 2:
                    labels = df[cols[0]].tolist()
                    values = df[cols[1]].tolist()
                else:
                    raise ValueError("Need at least 2 columns for pie chart")

            # Create figure with larger size for dominant appearance
            fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)

            # Create clean pie chart with NO LABELS AT ALL
            ax.pie(values, labels=None, autopct=None,
                   colors=self.color_palette[:len(values)],
                   startangle=90)

            # Customize chart
            ax.set_title(title or "Data Distribution")

            # Add legend with configurable positioning to avoid collisions
            # Create legend table instead of matplotlib legend
            if show_legend:
                # Calculate percentages for the table
                total = sum(values)
                percentages = [(v/total)*100 for v in values]

                # Create legend table data
                legend_data = []
                for label, value, pct in zip(labels, values, percentages):
                    legend_data.append([
                        "■",  # Color indicator
                        "" if label is None else str(label),
                        f"{value:,}",
                        f"{pct:.1f}%"
                    ])

                self._draw_pie_legend_table(fig, ax, legend_data,
                                            self.color_palette[:len(values)],
                                            legend_position)
            elif legend_position == "bottom":
                fig.subplots_adjust(left=0.1, right=0.9, top=0.85, bottom=0.35)
            else:
                fig.subplots_adjust(left=0.1, right=0.6, top=0.9, bottom=0.1)

            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)

        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as e:
            raise RuntimeError("Chart generation failed") from e

    # Pie legend table layout. Margins and shares are figure fractions; font
    # sizes are points; padding is per side, in multiples of the font size.
    _PIE_LEGEND_HEADER = ('', 'Label', 'Value', 'Percent')
    _PIE_LEGEND_FONT_PT = 8.0
    _PIE_LEGEND_MIN_FONT_PT = 5.0
    _PIE_LEGEND_ROW_SPACING = 1.6
    _PIE_LEGEND_CELL_PAD = 0.3
    _PIE_LEGEND_MARGIN = 0.02
    _PIE_MIN_AXES_SHARE = 0.35
    _PIE_BOTTOM_LEGEND_MAX_SHARE = 0.45
    _PIE_TITLE_MIN_FONT_PT = 7.0
    _ELLIPSIS = "…"

    def _place_pie_title(self, fig, ax, margin: float) -> float:
        """Move the pie's title to the top of the figure and fit it there.

        The title is centred on the whole figure rather than on the (shrunk)
        pie axes, so a wide legend cannot push it off the canvas or under the
        table. A title wider than the figure is drawn smaller, down to
        ``_PIE_TITLE_MIN_FONT_PT``, and then wrapped onto more lines.

        Returns:
            The figure fraction below which the rest of the chart must stay.
        """
        import textwrap

        text = ax.get_title()
        if not text:
            return 1.0 - margin
        font = ax.title.get_fontsize()
        ax.set_title("")
        title = fig.suptitle(text, x=0.5, y=1.0 - margin, ha='center', va='top',
                             fontsize=font)
        fig_px_w = fig.get_figwidth() * fig.dpi
        max_px = (1.0 - 2 * margin) * fig_px_w

        width = title.get_window_extent().width
        if width > max_px:
            font = max(self._PIE_TITLE_MIN_FONT_PT, font * max_px / width)
            title.set_fontsize(font)
            width = title.get_window_extent().width
        chars = len(text)
        while width > max_px and chars > 1:
            chars = max(1, int(chars * max_px / width) - 1)
            title.set_text(textwrap.fill(text, width=chars, break_long_words=True))
            width = title.get_window_extent().width
        height = title.get_window_extent().height / (fig.get_figheight() * fig.dpi)
        return 1.0 - 2 * margin - height

    def _draw_pie_legend_table(self, fig, ax, rows: List[List[str]],
                               swatch_colors: List[str],
                               legend_position: str) -> None:
        """Draw the pie legend table so all of it lies inside the figure.

        The table gets its own axes sized in *figure* coordinates from the
        measured width of every column, and the pie axes are shrunk to leave
        room for it. If the table would still be too wide at the default font
        size the font is reduced (down to ``_PIE_LEGEND_MIN_FONT_PT``), and
        after that over-long labels are shortened with an ellipsis. Too many
        rows for the available height shrink the font further. The title is
        placed across the top of the figure, above both the pie and the
        table. The saved image is the figure canvas, so this keeps every
        column and the whole title visible (#1999).
        """
        margin = self._PIE_LEGEND_MARGIN
        base = self._PIE_LEGEND_FONT_PT
        pad = self._PIE_LEGEND_CELL_PAD
        header = list(self._PIE_LEGEND_HEADER)
        fig_w_pt = fig.get_figwidth() * 72.0
        fig_h_pt = fig.get_figheight() * 72.0
        n_rows = len(rows) + 1
        bottom = legend_position == "bottom"
        top = self._place_pie_title(fig, ax, margin)

        if bottom:
            avail_w = (1.0 - 2 * margin) * fig_w_pt
            avail_h = (min(self._PIE_BOTTOM_LEGEND_MAX_SHARE, top / 2)
                       - 2 * margin) * fig_h_pt
        else:
            avail_w = (1.0 - 3 * margin - self._PIE_MIN_AXES_SHARE) * fig_w_pt
            avail_h = (top - margin) * fig_h_pt

        def measure(text: str) -> float:
            """Width of ``text`` in points at the base font size (bold)."""
            probe = fig.text(0, 0, text, fontsize=base, weight='bold')
            try:
                extent = probe.get_window_extent()
            finally:
                probe.remove()
            return extent.width * 72.0 / fig.dpi

        # Natural (base-size) text width of each column.
        widths = [max(measure(row[col]) for row in [header] + rows)
                  for col in range(len(header))]

        def table_width(font: float, col_text_widths: List[float]) -> float:
            scale = font / base
            return sum(w * scale + 2 * pad * font for w in col_text_widths)

        font = min(base, avail_h / (n_rows * self._PIE_LEGEND_ROW_SPACING))
        width_fit = font * avail_w / table_width(font, widths)
        if width_fit < font:
            font = max(width_fit, min(self._PIE_LEGEND_MIN_FONT_PT, font))

        if table_width(font, widths) > avail_w:
            # Still too wide at the smallest font: shorten the labels.
            scale = font / base
            others = table_width(font, [w for i, w in enumerate(widths) if i != 1])
            label_budget = (avail_w - others - 2 * pad * font) / scale
            ellipsis_w = measure(self._ELLIPSIS)
            if label_budget < ellipsis_w:
                # Even the value/percent columns are too wide; size the
                # font to fit a one-character label column.
                fixed = [w if i != 1 else ellipsis_w for i, w in enumerate(widths)]
                font = font * avail_w / table_width(font, fixed)
                label_budget = ellipsis_w
            for row in rows:
                if measure(row[1]) > label_budget:
                    row[1] = self._truncate_to_width(row[1], label_budget, measure)
            widths[1] = max(measure(row[1]) for row in [header] + rows)

        scale = font / base
        col_pts = [w * scale + 2 * pad * font for w in widths]
        legend_w = sum(col_pts) / fig_w_pt
        legend_h = n_rows * font * self._PIE_LEGEND_ROW_SPACING / fig_h_pt

        if bottom:
            fig.subplots_adjust(left=0.1, right=0.9, top=top,
                                bottom=legend_h + 2 * margin)
            rect = [0.5 - legend_w / 2, margin, legend_w, legend_h]
        else:
            fig.subplots_adjust(left=0.05, right=1.0 - legend_w - 2 * margin,
                                top=top, bottom=0.05)
            rect = [1.0 - margin - legend_w, margin + (top - margin - legend_h) / 2,
                    legend_w, legend_h]

        legend_ax = fig.add_axes(rect)
        legend_ax.set_axis_off()
        total = sum(col_pts)
        table = legend_ax.table(cellText=rows,
                                colLabels=header,
                                colWidths=[w / total for w in col_pts],
                                cellLoc='center',
                                loc='center',
                                bbox=[0, 0, 1, 1])

        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(font)

        # Color the first column with the actual colors
        for i, color in enumerate(swatch_colors):
            table[(i+1, 0)].set_facecolor(color)
            table[(i+1, 0)].set_text_props(weight='bold')

        # Style header
        for i in range(len(header)):
            table[(0, i)].set_facecolor('#40466e')
            table[(0, i)].set_text_props(weight='bold', color='white')

        # Remove table borders
        for i in range(n_rows):
            for j in range(len(header)):
                table[(i, j)].set_edgecolor('none')

    @classmethod
    def _truncate_to_width(cls, text: str, budget: float, measure) -> str:
        """Longest prefix of ``text`` plus an ellipsis whose width fits ``budget``."""
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if measure(text[:mid].rstrip() + cls._ELLIPSIS) <= budget:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo].rstrip() + cls._ELLIPSIS

    def create_proportional_text_bar_chart(self,
                                         data: 'pd.DataFrame',
                                         labels_column: str,
                                         values_column: str,
                                         title: str = "Proportional Text Bar Chart",
                                         max_width: int = 50,
                                         bar_char: str = "\u2588",
                                         show_values: bool = True,
                                         sort_descending: bool = True) -> str:
        """
        Create a proportional text-based bar chart

        Args:
            data: DataFrame containing the data
            labels_column: Column name for labels
            values_column: Column name for values
            title: Chart title
            max_width: Maximum width of bars in characters
            bar_char: Character to use for bars
            show_values: Whether to show actual values
            sort_descending: Whether to sort by values descending

        Returns:
            Formatted text chart string
        """
        try:
            if data.empty:
                return f"<i>No data available for {_escape_paragraph(title)}</i>"

            # Sort data if requested
            if sort_descending:
                data = data.sort_values(values_column, ascending=False)

            # Get max value for proportional scaling
            max_value = data[values_column].max()

            # Create chart
            chart_lines = [f"<b>{_escape_paragraph(title)}</b>", "=" * len(title), ""]

            for _, row in data.iterrows():
                label = str(row[labels_column])
                value = row[values_column]

                # Calculate proportional bar length
                if max_value > 0:
                    bar_length = int((value / max_value) * max_width)
                else:
                    bar_length = 0

                # Create bar
                bar = bar_char * bar_length

                # Format the line
                if show_values:
                    chart_lines.append(_escape_paragraph(f"{label:<20} {bar} {value:,}"))
                else:
                    chart_lines.append(_escape_paragraph(f"{label:<20} {bar}"))

            return "<br/>".join(chart_lines)

        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as e:
            raise RuntimeError("Chart generation failed") from e

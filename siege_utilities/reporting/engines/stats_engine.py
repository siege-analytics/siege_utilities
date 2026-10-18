"""
Statistical chart mixins — heatmap, scatter plot, and text heatmap.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Union

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
    "StatsChartMixin",
]


class StatsChartMixin:
    """Statistical chart methods (heatmap, scatter plot, text heatmap)."""

    def create_heatmap(self, data: Union[pd.DataFrame, Dict[str, Any]],
                      x_column: str = None, y_column: str = None, value_column: str = None,
                      title: str = "", width: float = 8.0, height: float = 6.0) -> Image:
        """
        Create a heatmap from data.

        Args:
            data: DataFrame or dictionary with data
            x_column: Column name for X-axis
            y_column: Column name for Y-axis
            value_column: Column name for values
            title: Chart title
            width: Chart width in inches
            height: Chart height in inches

        Returns:
            ReportLab Image object
        """
        if not MATPLOTLIB_AVAILABLE or not sns:
            return self._create_placeholder_chart(width, height, "Matplotlib/Seaborn not available")

        try:
            # Convert data to DataFrame if needed
            if isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data.copy()

            # Handle different data formats
            if x_column and y_column and value_column:
                # Pivot data for heatmap
                pivot_data = df.pivot_table(values=value_column, index=y_column, columns=x_column, aggfunc='mean')
            else:
                # Use correlation matrix if no specific columns provided
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 1:
                    pivot_data = df[numeric_cols].corr()
                else:
                    raise ValueError("Need at least 2 numeric columns for heatmap")

            # Create figure
            fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)

            # Create heatmap
            sns.heatmap(pivot_data, annot=True, cmap='YlOrRd', center=0,
                       square=True, linewidths=0.5, cbar_kws={"shrink": 0.8})

            # Customize chart
            ax.set_title(title or "Data Heatmap")
            plt.tight_layout()

            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)

        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as e:


            raise RuntimeError(


                f"Heatmap Error: {e}"


            ) from e

    def create_scatter_plot(self, data: Union[pd.DataFrame, Dict[str, Any]],
                           x_column: str, y_column: str, color_column: str = None,
                           title: str = "", width: float = 6.0, height: float = 4.0) -> Image:
        """
        Create a scatter plot from data.

        Args:
            data: DataFrame or dictionary with data
            x_column: Column name for X-axis
            y_column: Column name for Y-axis
            color_column: Column name for color coding
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

            # Create figure with very conservative sizing to prevent ReportLab crashes
            fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)

            # Create scatter plot
            if color_column and color_column in df.columns:
                scatter = ax.scatter(df[x_column], df[y_column],
                                   c=df[color_column], cmap='viridis', alpha=0.6)
                plt.colorbar(scatter, ax=ax, label=color_column)
            else:
                ax.scatter(df[x_column], df[y_column], alpha=0.6, color=self.default_colors['primary'])

            # Customize chart
            ax.set_title(title or f"{y_column} vs {x_column}")
            ax.set_xlabel(x_column)
            ax.set_ylabel(y_column)
            ax.grid(True, alpha=0.3)

            plt.tight_layout()

            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)

        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as e:


            raise RuntimeError(


                f"Scatter Plot Error: {e}"


            ) from e

    def create_heatmap_text_chart(self,
                                data: 'pd.DataFrame',
                                x_column: str,
                                y_column: str,
                                value_column: str,
                                title: str = "Text Heatmap",
                                max_width: int = 20,
                                max_height: int = 10,
                                heat_chars: str = " \u2591\u2592\u2593\u2588") -> str:
        """
        Create a text-based heatmap with two-character cells and headers.

        Missing/non-finite cells use ``··`` and do not affect intensity scaling.
        Longer column labels are abbreviated to two characters and listed in
        full below the grid, in column order.

        Args:
            data: DataFrame containing the data
            x_column: Column name for x-axis labels
            y_column: Column name for y-axis labels
            value_column: Column name for values
            title: Chart title
            max_width: Maximum width in characters
            max_height: Maximum height in characters
            heat_chars: Characters for heat intensity (light to dark)

        Returns:
            Formatted text heatmap string
        """
        try:
            if data.empty:
                return f"<i>No data available for {_escape_paragraph(title)}</i>"

            # Create pivot table
            pivot_data = data.pivot_table(
                values=value_column,
                index=y_column,
                columns=x_column,
                dropna=False,
                observed=True,
            )

            # Normalize values to heat character indices
            finite_values = pivot_data.values[np.isfinite(pivot_data.values)]
            max_value = finite_values.max() if finite_values.size else 0
            min_value = finite_values.min() if finite_values.size else 0
            value_range = max_value - min_value if max_value > min_value else 1

            # Create heatmap
            chart_lines = [f"<b>{_escape_paragraph(title)}</b>", "=" * len(title), ""]

            # Add column headers
            cell_width = 2
            row_label_width = max(10, max((len(str(idx)) for idx in pivot_data.index), default=0))
            indent = " " * (row_label_width + 1)
            col_headers = [str(col)[:cell_width].ljust(cell_width) for col in pivot_data.columns]
            chart_lines.append(_escape_paragraph(indent + "".join(col_headers)))
            chart_lines.append(indent + "-" * (cell_width * len(col_headers)))

            # Add rows
            for idx, row in pivot_data.iterrows():
                row_label = str(idx).ljust(row_label_width)
                heat_row = ""

                for value in row:
                    if not np.isfinite(value):
                        heat_row += '··'
                        continue
                    # Normalize value to heat character index
                    normalized = (value - min_value) / value_range
                    char_index = int(normalized * (len(heat_chars) - 1))
                    char_index = max(0, min(char_index, len(heat_chars) - 1))
                    heat_row += heat_chars[char_index] * cell_width

                chart_lines.append(_escape_paragraph(f"{row_label} {heat_row}"))

            # Add legend
            chart_lines.append("")
            if any(len(str(col)) > cell_width for col in pivot_data.columns):
                chart_lines.append("Columns (left to right): " + _escape_paragraph(
                    ", ".join(str(col) for col in pivot_data.columns)))
            legend = " ".join(f"{char} {i/(len(heat_chars)-1)*100:.0f}%" for i, char in enumerate(heat_chars))
            chart_lines.append("Legend: " + _escape_paragraph(legend + " ·· missing"))

            return "<br/>".join(chart_lines)

        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as e:
            raise RuntimeError("Text heatmap generation failed") from e

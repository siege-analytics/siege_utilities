"""
Statistical chart mixins — heatmap, scatter plot, and text heatmap.
"""

import logging
from typing import Dict, Any, Optional, Union

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

from reportlab.platypus import Image

log = logging.getLogger(__name__)


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
                    return self._create_placeholder_chart(width, height, "Need numeric data for heatmap")

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

        except Exception as e:
            log.error(f"Error creating heatmap: {e}")
            return self._create_placeholder_chart(width, height, f"Heatmap Error: {str(e)}")

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

        except Exception as e:
            log.error(f"Error creating scatter plot: {e}")
            return self._create_placeholder_chart(width, height, f"Scatter Plot Error: {str(e)}")

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
        Create a text-based heatmap visualization

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
                return f"<i>No data available for {title}</i>"

            # Create pivot table
            pivot_data = data.pivot_table(
                values=value_column,
                index=y_column,
                columns=x_column,
                fill_value=0
            )

            # Normalize values to heat character indices
            max_value = pivot_data.values.max()
            min_value = pivot_data.values.min()
            value_range = max_value - min_value if max_value > min_value else 1

            # Create heatmap
            chart_lines = [f"<b>{title}</b>", "=" * len(title), ""]

            # Add column headers
            col_headers = [f"{col:<8}" for col in pivot_data.columns]
            chart_lines.append(" " * 12 + "".join(col_headers))
            chart_lines.append(" " * 12 + "-" * len("".join(col_headers)))

            # Add rows
            for idx, row in pivot_data.iterrows():
                row_label = f"{str(idx):<10}"
                heat_row = ""

                for value in row:
                    # Normalize value to heat character index
                    normalized = (value - min_value) / value_range
                    char_index = int(normalized * (len(heat_chars) - 1))
                    char_index = max(0, min(char_index, len(heat_chars) - 1))
                    heat_row += heat_chars[char_index] * 2

                chart_lines.append(f"{row_label} {heat_row}")

            # Add legend
            chart_lines.append("")
            chart_lines.append("Legend: " + " ".join([f"{heat_chars[i]} {i/(len(heat_chars)-1)*100:.0f}%" for i in range(len(heat_chars))]))

            return "<br/>".join(chart_lines)

        except Exception as e:
            log.error(f"Error creating text heatmap: {e}")
            return f"<i>Error creating text heatmap: {str(e)}</i>"

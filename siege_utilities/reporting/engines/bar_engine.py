"""
Bar, line, pie, and proportional text bar chart mixins.
"""

from __future__ import annotations

import logging
from math import isfinite
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
                        show_legend: bool = True, legend_position: str = "best",
                        value_format: str = None) -> Image:
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
            group_by: Column for side-by-side series. Repeated category/group
                pairs are summed; missing pairs are not plotted.
            value_format: Optional Python format specifier (e.g. ',.2f' or
                '.1%'). Defaults to integers for all-integer data, otherwise
                six significant digits, including small fractional values.

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

            # Keep categories in input order and give each group its own slot.
            bars = []
            if group_by:
                grouped = pd.DataFrame({
                    'category': x_values, 'group': df[group_by].tolist(),
                    'value': y_values,
                }).groupby(['category', 'group'], sort=False, dropna=False,
                           observed=True)['value'].sum(min_count=1).unstack('group')
                grouped = grouped.reindex(index=pd.Index(x_values).unique(),
                                          columns=pd.unique(df[group_by]))
                if grouped.empty:
                    raise ValueError("No grouped values found in data for bar chart")
                positions = np.arange(len(grouped))
                bar_width = 0.8 / len(grouped.columns)
                for i, group in enumerate(grouped.columns):
                    values = grouped[group]
                    present = values.notna().to_numpy()
                    offsets = positions + (i - (len(grouped.columns) - 1) / 2) * bar_width
                    options = {'label': str(group),
                               'color': self.color_palette[i % len(self.color_palette)]}
                    if chart_type == 'horizontal':
                        bars.extend(ax.barh(offsets[present], values[present],
                                            height=bar_width, **options))
                    else:
                        bars.extend(ax.bar(offsets[present], values[present],
                                           width=bar_width, **options))
                if chart_type == 'horizontal':
                    ax.set_yticks(positions, labels=grouped.index)
                else:
                    ax.set_xticks(positions, labels=grouped.index)
            elif chart_type == 'horizontal':
                bars = ax.barh(x_values, y_values, color=self.default_colors['primary'],
                               label=y_column)
            else:
                bars = ax.bar(x_values, y_values, color=self.default_colors['primary'],
                              label=y_column)

            if chart_type == "horizontal":
                ax.set_xlabel(y_column)
                ax.set_ylabel(x_column if x_column != 'index' else 'Index')
            else:
                ax.set_xlabel(x_column if x_column != 'index' else 'Index')
                ax.set_ylabel(y_column)

            # Customize chart
            ax.set_title(title or f"{y_column} by {x_column if x_column != 'index' else 'Index'}")
            ax.grid(True, alpha=0.3)

            # Rotate x-axis labels if needed
            if chart_type != 'horizontal' and len(x_values) > 5:
                plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

            # Add value labels on bars
            bar_values = [bar.get_width() if chart_type == 'horizontal'
                          else bar.get_height() for bar in bars]
            if value_format is None:
                value_format = ',.0f' if all(
                    isfinite(value) and float(value).is_integer() for value in bar_values
                ) else ',.6g'
            for bar, value in zip(bars, bar_values):
                if chart_type == 'horizontal':
                    ax.text(bar.get_x() + bar.get_width(),
                            bar.get_y() + bar.get_height() / 2,
                            format(value, value_format),
                            ha='left' if value >= 0 else 'right', va='center')
                else:
                    ax.text(bar.get_x() + bar.get_width() / 2,
                            bar.get_y() + bar.get_height(),
                            format(value, value_format), ha='center',
                            va='bottom' if value >= 0 else 'top')

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

            # Adjust subplot parameters to make room for legend table
            if legend_position == "bottom":
                fig.subplots_adjust(left=0.1, right=0.9, top=0.85, bottom=0.35)
            else:
                fig.subplots_adjust(left=0.1, right=0.6, top=0.9, bottom=0.1)

            # A zero or non-finite total cannot define wedges or percentages.
            total = sum(values)
            if any(value < 0 for value in values):
                raise ValueError("Pie values must be non-negative")
            if isfinite(total) and total > 0:
                ax.pie(values, labels=None, autopct=None,
                       colors=self.color_palette[:len(values)],
                       startangle=90)
            else:
                notice = "No positive values" if total == 0 else "Total unavailable"
                ax.text(0.5, 0.5, notice, ha='center', va='center', transform=ax.transAxes)

            # Customize chart
            ax.set_title(title or "Data Distribution")

            # Add legend with configurable positioning to avoid collisions
            # Create legend table instead of matplotlib legend
            if show_legend:
                # Calculate percentages for the table
                percentages = [
                    f"{value / total * 100:.1f}%" if isfinite(total) and total > 0
                    else "0.0%" if total == 0 else "n/a" for value in values
                ]

                # Create legend table data
                legend_data = []
                for i, (label, value, pct) in enumerate(zip(labels, values, percentages)):
                    legend_data.append([
                        "■",  # Color indicator
                        label,
                        f"{value:,}",
                        pct
                    ])

                # bbox is [left, bottom, width, height] in axes coordinates.
                if legend_position == "bottom":
                    table_bbox = [0.0, -0.6, 1.0, 0.5]
                else:
                    table_bbox = [1.05, 0.0, 0.6, 0.9]
                table = ax.table(cellText=legend_data,
                               colLabels=['', 'Label', 'Value', 'Percent'],
                               cellLoc='center',
                               loc='center',
                               bbox=table_bbox)

                # Style the table
                table.auto_set_font_size(False)
                table.set_fontsize(8)
                table.scale(1, 1.5)

                # Color the first column with the actual colors
                for i, color in enumerate(self.color_palette[:len(values)]):
                    table[(i+1, 0)].set_facecolor(color)
                    table[(i+1, 0)].set_text_props(weight='bold')

                # Style header
                for i in range(4):
                    table[(0, i)].set_facecolor('#40466e')
                    table[(0, i)].set_text_props(weight='bold', color='white')

                # Remove table borders
                for i in range(len(legend_data) + 1):
                    for j in range(4):
                        table[(i, j)].set_edgecolor('none')

            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)

        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as e:
            raise RuntimeError("Chart generation failed") from e

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

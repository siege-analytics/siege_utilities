"""
Composite chart mixins — convergence diagrams, dashboards, and subplot helpers.
"""

import logging
from typing import Dict, List, Any, Optional

# Core plotting libraries
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    mpatches = None
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
    "CompositeChartMixin",
]


class CompositeChartMixin:
    """Composite chart methods (convergence diagram, dashboard, summary charts, subplots)."""

    def create_convergence_diagram(self,
                                   sources: List[Dict[str, Any]],
                                   hub_label: str = "Unified Hub",
                                   outputs: Optional[List[Dict[str, Any]]] = None,
                                   title: str = "Convergence Diagram",
                                   width: float = 10.0,
                                   height: float = 6.0,
                                   arrow_style: str = "curved",
                                   arrow_count: Optional[int] = None,
                                   arrow_color: Optional[str] = None,
                                   show_magnitudes: bool = False,
                                   magnitude_key: str = "magnitude") -> Image:
        """
        Create a stylized convergence diagram with arrows into a labeled origin.

        Args:
            sources: Source node dictionaries; supports keys:
                ``label`` (required), ``color`` (optional), and optional magnitude key.
            hub_label: Center node label.
            outputs: Optional output node dictionaries (same schema as sources).
            title: Diagram title.
            width: Figure width in inches.
            height: Figure height in inches.
            arrow_style: One of ``curved``, ``radial``, ``orthogonal``.
            arrow_count: Optional max number of source arrows to render.
            arrow_color: Optional color override for arrows.
            show_magnitudes: If True, append magnitudes to source labels when present.
            magnitude_key: Dict key to read magnitude from.

        Returns:
            ReportLab Image object.
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Matplotlib not available")

        try:
            if not sources:
                raise ValueError("No sources provided for convergence diagram")

            out_nodes = outputs or []
            src_nodes = sources[:arrow_count] if arrow_count else sources

            primary = self.default_colors.get('primary', '#1f3a5f')
            secondary = self.default_colors.get('secondary', '#2f5b89')
            accent = self.default_colors.get('accent', '#ed8936')
            a_color = arrow_color or '#4a5568'

            fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)
            ax.set_xlim(0, 12)
            ax.set_ylim(0, 8)
            ax.axis('off')

            hub_x, hub_y, hub_r = 6.0, 4.0, 1.2
            hub = mpatches.Circle((hub_x, hub_y), hub_r, facecolor=primary, edgecolor='white', linewidth=2)
            ax.add_patch(hub)
            ax.text(hub_x, hub_y, hub_label, color='white', ha='center', va='center',
                    fontsize=10, fontweight='bold', wrap=True)

            # Left-side source nodes and inbound arrows
            src_y = np.linspace(7.0, 1.0, len(src_nodes))
            sx, sw, sh = 0.8, 2.9, 0.82

            for src, y in zip(src_nodes, src_y):
                label = str(src.get('label', 'Source'))
                mag = src.get(magnitude_key)
                if show_magnitudes and mag is not None:
                    label = f"{label}\n({mag})"

                fill = src.get('color', secondary)
                node = mpatches.FancyBboxPatch(
                    (sx, y - (sh / 2)),
                    sw,
                    sh,
                    boxstyle="round,pad=0.02,rounding_size=0.12",
                    linewidth=1.4,
                    facecolor=fill,
                    edgecolor='white',
                )
                ax.add_patch(node)
                ax.text(sx + (sw / 2), y, label, color='white', ha='center', va='center',
                        fontsize=8, fontweight='bold')

                if arrow_style == "radial":
                    conn = "arc3,rad=0.0"
                elif arrow_style == "orthogonal":
                    conn = "angle3,angleA=0,angleB=90"
                else:
                    conn = "arc3,rad=0.15"

                lw = 2.0
                if show_magnitudes and mag is not None:
                    try:
                        lw = max(1.4, min(4.2, 1.2 + float(mag)))
                    except (ValueError, TypeError):
                        lw = 2.0

                ax.annotate(
                    "",
                    xy=(hub_x - (hub_r * 0.94), hub_y),
                    xytext=(sx + sw, y),
                    arrowprops=dict(
                        arrowstyle="-|>",
                        lw=lw,
                        color=a_color,
                        connectionstyle=conn,
                    ),
                )

            # Optional right-side output nodes
            if out_nodes:
                out_y = np.linspace(6.3, 1.7, len(out_nodes))
                ox, ow, oh = 8.5, 2.7, 0.82
                for dst, y in zip(out_nodes, out_y):
                    label = str(dst.get('label', 'Output'))
                    fill = dst.get('color', accent)
                    node = mpatches.FancyBboxPatch(
                        (ox, y - (oh / 2)),
                        ow,
                        oh,
                        boxstyle="round,pad=0.02,rounding_size=0.12",
                        linewidth=1.4,
                        facecolor=fill,
                        edgecolor='white',
                    )
                    ax.add_patch(node)
                    ax.text(ox + (ow / 2), y, label, color='white', ha='center', va='center',
                            fontsize=8, fontweight='bold')

                    if arrow_style == "radial":
                        out_conn = "arc3,rad=0.0"
                    elif arrow_style == "orthogonal":
                        out_conn = "angle3,angleA=180,angleB=90"
                    else:
                        out_conn = "arc3,rad=-0.12"

                    ax.annotate(
                        "",
                        xy=(ox, y),
                        xytext=(hub_x + (hub_r * 0.94), hub_y),
                        arrowprops=dict(
                            arrowstyle="-|>",
                            lw=2.0,
                            color=a_color,
                            connectionstyle=out_conn,
                        ),
                    )

            ax.set_title(title, fontsize=13, fontweight='bold')
            return self._matplotlib_to_reportlab_image(fig, width, height)

        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as e:


            raise RuntimeError(


                f"Convergence Diagram Error: {e}"


            ) from e

    def create_dashboard(self, charts: List[Dict[str, Any]],
                        layout: str = "2x2", width: float = 12.0, height: float = 8.0) -> Image:
        """
        Create a dashboard with multiple charts.

        Every chart uses ``{'type': 'bar'|'line'|'pie'|'scatter', 'title': ...,
        'data': {'labels': [...], 'datasets': [{'label': 'Series',
        'data': [...]}]}}``. Each dataset has one numeric value per label;
        omitted series labels default to "Dataset N". Scatter labels supply
        x coordinates. Multiple pie datasets are concentric rings, ordered
        from outside to inside, with series/category entries in the legend.
        Invalid data, unsupported types, and grid overflow raise RuntimeError.

        Args:
            charts: List of chart configurations
            layout: Columns x rows (e.g., "2x2", "3x1")
            width: Total dashboard width in inches
            height: Total dashboard height in inches

        Returns:
            ReportLab Image object
        """
        fig = None
        try:
            # Parse layout
            cols, rows = map(int, layout.split('x'))
            if cols < 1 or rows < 1:
                raise ValueError("Dashboard layout dimensions must be positive")
            if len(charts) > cols * rows:
                overflow = [chart.get('title', f'Chart {i + 1}')
                            for i, chart in enumerate(charts) if i >= cols * rows]
                raise ValueError(f"Dashboard overflow for layout {layout}: {overflow}")
            for i, chart in enumerate(charts):
                chart_type = chart.get('type', 'bar')
                if chart_type not in ('bar', 'line', 'pie', 'scatter'):
                    name = chart.get('title', f'Chart {i + 1}')
                    raise ValueError(f"Unknown chart type {chart_type!r} for {name!r}")

            if not MATPLOTLIB_AVAILABLE:
                return self._create_placeholder_chart(width, height, "Matplotlib not available")

            # Create subplot grid with very conservative sizing to prevent ReportLab crashes
            fig, axes = plt.subplots(rows, cols, figsize=(width, height), dpi=self.default_dpi)

            # Handle single subplot case
            if rows == 1 and cols == 1:
                axes = [axes]
            elif rows == 1 or cols == 1:
                axes = axes.flatten()
            else:
                axes = axes.flatten()

            # Create each chart
            for i, chart_config in enumerate(charts):
                ax = axes[i]
                chart_type = chart_config.get('type', 'bar')
                chart_title = chart_config.get('title', f'Chart {i+1}')

                # Create chart based on type
                if chart_type == 'bar':
                    self._create_bar_subplot(ax, chart_config, chart_title)
                elif chart_type == 'line':
                    self._create_line_subplot(ax, chart_config, chart_title)
                elif chart_type == 'pie':
                    self._create_pie_subplot(ax, chart_config, chart_title)
                elif chart_type == 'scatter':
                    self._create_scatter_subplot(ax, chart_config, chart_title)

            # Hide empty subplots
            for i in range(len(charts), len(axes)):
                axes[i].set_visible(False)

            plt.tight_layout()

            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)

        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as e:
            if fig is not None:
                plt.close(fig)
            raise RuntimeError(f"Dashboard Error: {e}") from e

    def create_dataframe_summary_charts(self, df: 'pd.DataFrame',
                                     title: str = "", width: float = 8.0, height: float = 6.0) -> Image:
        """
        Create summary charts from a pandas DataFrame.

        Args:
            df: Pandas DataFrame
            title: Chart title
            width: Chart width in inches
            height: Chart height in inches

        Returns:
            ReportLab Image object
        """
        if not MATPLOTLIB_AVAILABLE or not PANDAS_AVAILABLE:
            return self._create_placeholder_chart(width, height, "Matplotlib/Pandas not available")

        try:
            # Get numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns

            if len(numeric_cols) == 0:
                raise ValueError("No numeric columns found for summary charts")

            # Create subplots
            fig, axes = plt.subplots(2, 2, figsize=(width, height), dpi=self.default_dpi)
            axes = axes.flatten()

            # Distribution plots
            for i, col in enumerate(numeric_cols[:4]):
                if i < len(axes):
                    ax = axes[i]
                    ax.hist(df[col].dropna(), bins=20, alpha=0.7, color=self.color_palette[i % len(self.color_palette)])
                    ax.set_title(f'{col} Distribution')
                    ax.set_xlabel(col)
                    ax.set_ylabel('Frequency')
                    ax.grid(True, alpha=0.3)

            # Hide empty subplots
            for i in range(len(numeric_cols[:4]), len(axes)):
                axes[i].set_visible(False)

            plt.suptitle(title or "DataFrame Summary Charts")
            plt.tight_layout()

            # Convert to ReportLab Image
            return self._matplotlib_to_reportlab_image(fig, width, height)

        except (ValueError, TypeError, KeyError, IndexError, AttributeError) as e:


            raise RuntimeError(


                f"Summary Charts Error: {e}"


            ) from e

    def _dashboard_data(self, chart_config: Dict[str, Any]):
        """Validate and normalize the shared labels/datasets schema without mutating it."""
        data = chart_config.get('data', {})
        labels = data.get('labels', [])
        datasets = data.get('datasets', [])
        title = chart_config.get('title', 'Chart')
        if not len(labels) or not len(datasets):
            raise ValueError(f"{title!r} requires non-empty labels and datasets")
        normalized = []
        for i, dataset in enumerate(datasets):
            label = dataset.get('label') or f'Dataset {i + 1}'
            values = np.asarray(dataset.get('data', []), dtype=float)
            if values.ndim != 1 or len(values) != len(labels):
                raise ValueError(f"{title!r}, dataset {label!r}: one value per label required")
            if not np.isfinite(values).all():
                raise ValueError(f"{title!r}, dataset {label!r}: values must be finite")
            normalized.append({'label': str(label), 'data': values})
        return labels, normalized

    def _create_bar_subplot(self, ax, chart_config: Dict[str, Any], title: str):
        """Plot every dataset as a labelled, side-by-side bar series."""
        labels, datasets = self._dashboard_data(chart_config)
        positions = np.arange(len(labels))
        bar_width = 0.8 / len(datasets)
        for i, dataset in enumerate(datasets):
            offsets = positions + (i - (len(datasets) - 1) / 2) * bar_width
            ax.bar(offsets, dataset['data'], width=bar_width, label=dataset['label'],
                   color=self.color_palette[i % len(self.color_palette)])
        ax.set_xticks(positions, labels=labels)
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _create_line_subplot(self, ax, chart_config: Dict[str, Any], title: str):
        """Create a line chart in a subplot."""
        labels, datasets = self._dashboard_data(chart_config)
        for i, dataset in enumerate(datasets):
            color = self.color_palette[i % len(self.color_palette)]
            ax.plot(labels, dataset['data'], label=dataset['label'], color=color, marker='o')
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _create_pie_subplot(self, ax, chart_config: Dict[str, Any], title: str):
        """Plot each dataset as a pie or concentric ring with a series/category legend."""
        labels, datasets = self._dashboard_data(chart_config)
        handles, legend_labels = [], []
        ring_width = 0.8 / len(datasets)
        for i, dataset in enumerate(datasets):
            values = dataset['data']
            if (values < 0).any() or values.sum() <= 0:
                raise ValueError(f"{title!r}, dataset {dataset['label']!r}: "
                                 "pie values must be non-negative with a positive total")
            wedges, _, _ = ax.pie(
                values, autopct='%1.1f%%', colors=self.color_palette,
                radius=1 - i * ring_width,
                wedgeprops={'width': ring_width} if len(datasets) > 1 else None,
            )
            handles.extend(wedges)
            legend_labels.extend(f"{dataset['label']}: {label}" for label in labels)
        ax.legend(handles, legend_labels)
        ax.set_title(title)

    def _create_scatter_subplot(self, ax, chart_config: Dict[str, Any], title: str):
        """Create a scatter plot in a subplot."""
        labels, datasets = self._dashboard_data(chart_config)
        for i, dataset in enumerate(datasets):
            ax.scatter(labels, dataset['data'], label=dataset['label'], alpha=0.6,
                       color=self.color_palette[i % len(self.color_palette)])
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)

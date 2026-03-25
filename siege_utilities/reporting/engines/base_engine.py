"""
Base engine mixin — ``__init__``, scaling, placeholder, and conversion helpers.
"""

import logging
import io
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

# Core plotting libraries
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    sns = None

# Geographic plotting
try:
    import folium
    from folium import plugins
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    folium = None

# Data processing
try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None
    np = None

from reportlab.platypus import Image, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet

log = logging.getLogger(__name__)


class BaseChartEngine:
    """Core infrastructure: init, colors, styling, scaling, save helpers."""

    def __init__(self, branding_config: Optional[Dict[str, Any]] = None,
                 output_dir: Optional[Path] = None,
                 max_chart_width: Optional[float] = None,
                 max_chart_height: Optional[float] = None):
        """
        Initialize the chart generator.

        Args:
            branding_config: Branding configuration for chart colors and styling
            output_dir: Directory for saving Folium HTML map files.
                        Defaults to ``~/.siege_utilities`` for backward compatibility.
            max_chart_width: Maximum chart width in inches for ReportLab output.
                             When set, charts wider than this are uniformly scaled
                             down to fit.  ``None`` disables width clamping.
            max_chart_height: Maximum chart height in inches for ReportLab output.
                              When set, charts taller than this are uniformly scaled
                              down to fit.  ``None`` disables height clamping.
        """
        self.branding_config = branding_config or {}
        self.output_dir = Path(output_dir) if output_dir is not None else Path.home() / ".siege_utilities"
        self.max_chart_width = max_chart_width
        self.max_chart_height = max_chart_height
        self.styles = getSampleStyleSheet()
        self._setup_default_colors()
        self._setup_plotting_style()

        # Set default figure size and DPI for professional quality
        self.default_figsize = (8, 5)
        self.default_dpi = 150

        # Set matplotlib global DPI for consistency
        if MATPLOTLIB_AVAILABLE:
            plt.rcParams['figure.dpi'] = 150
            plt.rcParams['savefig.dpi'] = 150

    def _setup_default_colors(self):
        """Setup default color scheme for charts."""
        self.default_colors = {
            'primary': self.branding_config.get('colors', {}).get('primary', '#0077CC'),
            'secondary': self.branding_config.get('colors', {}).get('secondary', '#EEEEEE'),
            'accent': self.branding_config.get('colors', {}).get('accent', '#FF6B35'),
            'success': '#28a745',
            'warning': '#ffc107',
            'danger': '#dc3545',
            'info': '#17a2b8',
            'light': '#f8f9fa',
            'dark': '#343a40'
        }

        # Color palette for multiple series
        self.color_palette = [
            self.default_colors['primary'],
            self.default_colors['accent'],
            self.default_colors['success'],
            self.default_colors['warning'],
            self.default_colors['info']
        ]

    def _setup_plotting_style(self):
        """Setup matplotlib and seaborn styling."""
        if MATPLOTLIB_AVAILABLE:
            # Set style
            plt.style.use('default')

            # Configure seaborn
            if sns:
                sns.set_palette(self.color_palette)
                sns.set_style("whitegrid")

            # Set default font sizes and DPI
            plt.rcParams['figure.dpi'] = 150
            plt.rcParams['font.size'] = 10
            plt.rcParams['axes.titlesize'] = 12
            plt.rcParams['axes.labelsize'] = 10
            plt.rcParams['xtick.labelsize'] = 9
            plt.rcParams['ytick.labelsize'] = 9
            plt.rcParams['legend.fontsize'] = 9
            plt.rcParams['figure.titlesize'] = 14

            # Enhanced legend settings to prevent label collisions
            plt.rcParams['legend.frameon'] = True
            plt.rcParams['legend.fancybox'] = True
            plt.rcParams['legend.shadow'] = True
            plt.rcParams['legend.framealpha'] = 0.9
            plt.rcParams['legend.edgecolor'] = 'black'
            plt.rcParams['legend.facecolor'] = 'white'

    def _scale_dimensions(self, width: float, height: float,
                          max_width: Optional[float] = None,
                          max_height: Optional[float] = None) -> tuple:
        """Return ``(width, height)`` uniformly scaled to fit within max bounds.

        Resolves effective maximums from instance-level defaults
        (``self.max_chart_width``/``self.max_chart_height``) and per-call
        overrides.  When both are set the *tighter* (smaller) limit wins.

        If no maximum is active, the original dimensions are returned
        unchanged.  Aspect ratio is always preserved.

        Args:
            width: Original width in inches.
            height: Original height in inches.
            max_width: Per-call maximum width override (``None`` → use instance default).
            max_height: Per-call maximum height override (``None`` → use instance default).

        Returns:
            ``(scaled_width, scaled_height)`` tuple.
        """
        # Resolve effective max — tighter of instance-level and per-call
        eff_max_w = self.max_chart_width
        if max_width is not None:
            eff_max_w = min(max_width, eff_max_w) if eff_max_w is not None else max_width

        eff_max_h = self.max_chart_height
        if max_height is not None:
            eff_max_h = min(max_height, eff_max_h) if eff_max_h is not None else max_height

        # No limits → nothing to do
        if eff_max_w is None and eff_max_h is None:
            return width, height

        scale = 1.0
        if eff_max_w is not None and width > eff_max_w:
            scale = min(scale, eff_max_w / width)
        if eff_max_h is not None and height > eff_max_h:
            scale = min(scale, eff_max_h / height)

        if scale < 1.0:
            new_w = width * scale
            new_h = height * scale
            log.info(
                "Auto-scaling chart from %.2f×%.2f to %.2f×%.2f in "
                "(max %.1s×%.1s, scale=%.3f)",
                width, height, new_w, new_h,
                eff_max_w, eff_max_h, scale,
            )
            return new_w, new_h

        return width, height

    def _save_folium_map(self, folium_map, filename: str, label: str,
                         width: float, height: float) -> Image:
        """Save a Folium map to *self.output_dir* and return a placeholder chart.

        Consolidates the identical mkdir → save → log → placeholder pattern
        used by every Folium-based method.

        Args:
            folium_map: A ``folium.Map`` instance.
            filename: File name (e.g. ``"temp_choropleth_map.html"``).
            label: Human-readable label shown in the placeholder image.
            width: Placeholder chart width (inches).
            height: Placeholder chart height (inches).

        Returns:
            ReportLab Image placeholder.
        """
        map_path = self.output_dir / filename
        map_path.parent.mkdir(parents=True, exist_ok=True)
        folium_map.save(str(map_path))
        log.info(f"{label} saved to {map_path}")
        return self._create_placeholder_chart(width, height, f"{label} — saved to {map_path}")

    def save_figure_as_vector(self, fig, output_path: Union[str, Path],
                              fmt: str = 'svg') -> Optional[Path]:
        """Save a matplotlib figure as a vector file (SVG, EPS, or PDF).

        Args:
            fig: Matplotlib figure.
            output_path: Destination file path (extension is overridden by *fmt*).
            fmt: Vector format — ``'svg'``, ``'eps'``, or ``'pdf'``.

        Returns:
            Path to the saved file, or ``None`` on error.
        """
        allowed = {'svg', 'eps', 'pdf'}
        if fmt not in allowed:
            log.error(f"Unsupported vector format '{fmt}'; expected one of {allowed}")
            return None

        try:
            out = Path(output_path).with_suffix(f'.{fmt}')
            out.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(str(out), format=fmt, bbox_inches='tight',
                        facecolor='white', edgecolor='none', pad_inches=0.1)
            log.info(f"Saved vector chart: {out}")
            return out
        except Exception as e:
            log.error(f"Error saving vector chart to {output_path}: {e}")
            return None

    def _matplotlib_to_reportlab_image(self, fig, width: float, height: float,
                                       max_width: Optional[float] = None,
                                       max_height: Optional[float] = None,
                                       vector_export_path: Optional[Union[str, Path]] = None,
                                       vector_format: str = 'svg') -> Image:
        """
        Convert matplotlib figure to ReportLab Image with size optimization.

        Optionally saves a vector copy (SVG/EPS/PDF) alongside the raster
        PDF embed.  The vector file is intended for designer handoff —
        InDesign and Illustrator can import SVG/EPS directly.

        Args:
            fig: Matplotlib figure
            width: Image width in inches
            height: Image height in inches
            max_width: Per-call max width override for ``_scale_dimensions``.
            max_height: Per-call max height override for ``_scale_dimensions``.
            vector_export_path: If provided, save a vector copy to this path.
            vector_format: Format for vector export (``'svg'``, ``'eps'``, ``'pdf'``).

        Returns:
            ReportLab Image object
        """
        try:
            # Save vector copy if requested (before closing the figure)
            if vector_export_path is not None:
                self.save_figure_as_vector(fig, vector_export_path, fmt=vector_format)

            # Use high DPI for crisp, professional quality
            optimal_dpi = self.default_dpi

            # Save figure to bytes buffer with optimized settings
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format='png', dpi=optimal_dpi,
                       facecolor='white', edgecolor='none', pad_inches=0.1)
            img_buffer.seek(0)

            # Check if image is still too large
            img_size = len(img_buffer.getvalue())
            if img_size > 5 * 1024 * 1024:  # 5MB limit
                log.warning(f"Image size {img_size/1024/1024:.1f}MB exceeds limit, reducing quality")
                img_buffer.seek(0)
                fig.savefig(img_buffer, format='png', dpi=100,
                           facecolor='white', edgecolor='none', pad_inches=0.1)
                img_buffer.seek(0)

            # Encode as base64
            img_data = base64.b64encode(img_buffer.getvalue()).decode()

            # Create data URL
            data_url = f"data:image/png;base64,{img_data}"

            # Close the figure to free memory
            plt.close(fig)

            # Auto-scale to fit within max bounds (if configured)
            scaled_w, scaled_h = self._scale_dimensions(
                width, height, max_width=max_width, max_height=max_height,
            )

            # Always specify both width and height explicitly.
            # ReportLab cannot reliably infer height from base64 data URLs
            # and may treat raw pixel height as points, producing oversized
            # images (e.g. 800px → 800pt = 11.1in instead of 4in at 200 DPI).
            rl_image = Image(data_url, width=scaled_w * inch,
                             height=scaled_h * inch)

            return rl_image

        except Exception as e:
            log.error(f"Error converting matplotlib figure to ReportLab Image: {e}")
            return self._create_placeholder_chart(width, height, "Image Conversion Error")

    def _create_placeholder_chart(self, width: float, height: float,
                                text: str = "Chart Placeholder") -> Image:
        """
        Create a placeholder chart when chart generation fails.

        Args:
            width: Chart width in inches
            height: Chart height in inches
            text: Text to display in placeholder

        Returns:
            ReportLab Image object
        """
        try:
            # Create a simple placeholder using matplotlib
            if MATPLOTLIB_AVAILABLE:
                fig, ax = plt.subplots(figsize=(width, height), dpi=self.default_dpi)
                ax.text(0.5, 0.5, text, ha='center', va='center', transform=ax.transAxes,
                       fontsize=12, bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                ax.axis('off')

                # Convert to ReportLab Image (inherits auto-scaling)
                return self._matplotlib_to_reportlab_image(fig, width, height)
            else:
                # Fallback to simple text — still honour auto-scaling
                sw, sh = self._scale_dimensions(width, height)
                return Image("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
                           width=sw*inch, height=sh*inch)
        except Exception as e:
            log.error(f"Error creating placeholder chart: {e}")
            # Return a minimal image — still honour auto-scaling
            sw, sh = self._scale_dimensions(width, height)
            return Image("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
                       width=sw*inch, height=sh*inch)

    def create_chart_with_caption(self, chart: Image, caption: str,
                                caption_style: Optional[str] = None) -> List:
        """
        Create a chart with a caption below it.

        Args:
            chart: The chart image
            caption: Caption text
            caption_style: Style name for the caption

        Returns:
            List containing chart and caption
        """
        if caption_style is None:
            caption_style = 'Caption' if 'Caption' in self.styles else 'Normal'

        return [chart, Paragraph(caption, self.styles[caption_style]), Spacer(1, 0.2 * inch)]

    def create_chart_section(self, title: str, charts: List[Image],
                           description: str = "", width: float = 6.0) -> List:
        """
        Create a complete chart section with title, description, and charts.

        Args:
            title: Section title
            charts: List of chart images
            description: Section description
            width: Section width in inches

        Returns:
            List of flowables for the section
        """
        section = []

        # Add title
        if title:
            section.append(Paragraph(title, self.styles['h2']))
            section.append(Spacer(1, 0.1 * inch))

        # Add description
        if description:
            section.append(Paragraph(description, self.styles['BodyText']))
            section.append(Spacer(1, 0.2 * inch))

        # Add charts
        for chart in charts:
            section.append(chart)
            section.append(Spacer(1, 0.2 * inch))

        return section

    def generate_chart_from_dataframe(self, df, chart_type: str = "bar",
                                    x_column: str = None, y_columns: List[str] = None,
                                    title: str = "", width: float = 6.0,
                                    height: float = 4.0) -> Image:
        """
        Generate a chart from a pandas DataFrame.

        Args:
            df: Pandas DataFrame
            chart_type: Type of chart to create
            x_column: Column to use for X-axis labels
            y_columns: Columns to use for Y-axis data
            title: Chart title
            width: Chart width in inches
            height: Chart height in inches

        Returns:
            ReportLab Image object
        """
        try:
            if chart_type == "bar":
                return self.create_bar_chart(df, x_column, y_columns[0] if y_columns else None, title, width, height)
            elif chart_type == "line":
                return self.create_line_chart(df, x_column, y_columns, title, width, height)
            elif chart_type == "pie":
                return self.create_pie_chart(df, x_column, y_columns[0] if y_columns else None, title, width, height)
            elif chart_type == "scatter":
                return self.create_scatter_plot(df, x_column, y_columns[0] if y_columns else None, title, width, height)
            elif chart_type == "heatmap":
                return self.create_heatmap(df, title=title, width=width, height=height)
            elif chart_type == "choropleth":
                return self.create_choropleth_map(df, x_column, y_columns[0] if y_columns else None, title, width, height)
            elif chart_type == "bivariate_choropleth":
                if y_columns and len(y_columns) >= 2:
                    return self.create_bivariate_choropleth(df, x_column, y_columns[0], y_columns[1], title, width, height)
                else:
                    return self._create_placeholder_chart(width, height, "Bivariate choropleth requires at least 2 value columns")
            else:
                return self.create_bar_chart(df, x_column, y_columns[0] if y_columns else None, title, width, height)

        except Exception as e:
            log.error(f"Error generating chart from DataFrame: {e}")
            return self._create_placeholder_chart(width, height, "DataFrame Chart Error")

    def create_custom_chart(self, chart_config: Dict[str, Any],
                           width: float = 6.0, height: float = 4.0) -> Image:
        """
        Create a custom chart based on configuration.

        Args:
            chart_config: Complete chart configuration
            width: Chart width in inches
            height: Chart height in inches

        Returns:
            ReportLab Image object
        """
        try:
            # Validate chart configuration
            required_keys = ['type', 'data']
            if not all(key in chart_config for key in required_keys):
                raise ValueError(f"Chart configuration missing required keys: {required_keys}")

            chart_type = chart_config['type']

            if chart_type == 'bar':
                return self.create_bar_chart(chart_config['data'], title=chart_config.get('title', ''), width=width, height=height)
            elif chart_type == 'line':
                return self.create_line_chart(chart_config['data'], title=chart_config.get('title', ''), width=width, height=height)
            elif chart_type == 'pie':
                return self.create_pie_chart(chart_config['data'], title=chart_config.get('title', ''), width=width, height=height)
            elif chart_type == 'scatter':
                return self.create_scatter_plot(chart_config['data'], title=chart_config.get('title', ''), width=width, height=height)
            elif chart_type == 'heatmap':
                return self.create_heatmap(chart_config['data'], title=chart_config.get('title', ''), width=width, height=height)
            elif chart_type == 'choropleth':
                return self.create_choropleth_map(chart_config['data'], title=chart_config.get('title', ''), width=width, height=height)
            elif chart_type == 'bivariate_choropleth':
                # For bivariate choropleth, we need additional configuration
                if 'location_column' in chart_config and 'value_columns' in chart_config and len(chart_config['value_columns']) >= 2:
                    return self.create_bivariate_choropleth(
                        chart_config['data'],
                        chart_config['location_column'],
                        chart_config['value_columns'][0],
                        chart_config['value_columns'][1],
                        title=chart_config.get('title', ''),
                        width=width,
                        height=height
                    )
                else:
                    return self._create_placeholder_chart(width, height, "Bivariate choropleth requires location_column and value_columns configuration")
            else:
                return self.create_bar_chart(chart_config['data'], title=chart_config.get('title', ''), width=width, height=height)

        except Exception as e:
            log.error(f"Error creating custom chart: {e}")
            return self._create_placeholder_chart(width, height, "Custom Chart Error")

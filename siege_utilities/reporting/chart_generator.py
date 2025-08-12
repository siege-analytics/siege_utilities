"""
Chart generation utilities for siege_utilities reporting system.
Supports multiple chart types and data sources.
"""

import logging
import json
import urllib.parse
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import requests
from reportlab.platypus import Image, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet

log = logging.getLogger(__name__)

class ChartGenerator:
    """
    Generates charts and visualizations for reports using various services.
    Supports QuickChart.io, Chart.js, and custom chart generation.
    """

    def __init__(self, branding_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the chart generator.
        
        Args:
            branding_config: Branding configuration for chart colors and styling
        """
        self.branding_config = branding_config or {}
        self.styles = getSampleStyleSheet()
        self._setup_default_colors()

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

    def create_bar_chart(self, labels: List[str], datasets: List[Dict[str, Any]], 
                        title: str = "", width: float = 6.0, height: float = 4.0,
                        chart_type: str = "bar") -> Image:
        """
        Create a bar chart using QuickChart.io.
        
        Args:
            labels: X-axis labels
            datasets: List of datasets with 'label' and 'data' keys
            title: Chart title
            width: Chart width in inches
            height: Chart height in inches
            chart_type: Type of chart ('bar', 'horizontalBar', 'line', 'pie')
            
        Returns:
            ReportLab Image object
        """
        chart_data = {
            'type': chart_type,
            'data': {
                'labels': labels,
                'datasets': []
            },
            'options': {
                'responsive': True,
                'scales': {'y': {'beginAtZero': True}},
                'plugins': {'title': {'display': True, 'text': title}}
            }
        }

        # Add datasets with colors
        for i, dataset in enumerate(datasets):
            color_key = list(self.default_colors.keys())[i % len(self.default_colors)]
            chart_data['data']['datasets'].append({
                'label': dataset.get('label', f'Dataset {i+1}'),
                'data': dataset.get('data', []),
                'backgroundColor': dataset.get('backgroundColor', self.default_colors[color_key]),
                'borderColor': dataset.get('borderColor', self.default_colors[color_key]),
                'borderWidth': dataset.get('borderWidth', 1)
            })

        return self._create_quickchart_image(chart_data, width, height)

    def create_line_chart(self, labels: List[str], datasets: List[Dict[str, Any]], 
                         title: str = "", width: float = 6.0, height: float = 4.0) -> Image:
        """
        Create a line chart.
        
        Args:
            labels: X-axis labels
            datasets: List of datasets with 'label' and 'data' keys
            title: Chart title
            width: Chart width in inches
            height: Chart height in inches
            
        Returns:
            ReportLab Image object
        """
        return self.create_bar_chart(labels, datasets, title, width, height, "line")

    def create_pie_chart(self, labels: List[str], data: List[float], 
                        title: str = "", width: float = 6.0, height: float = 4.0) -> Image:
        """
        Create a pie chart.
        
        Args:
            labels: Labels for each slice
            data: Values for each slice
            title: Chart title
            width: Chart width in inches
            height: Chart height in inches
            
        Returns:
            ReportLab Image object
        """
        chart_data = {
            'type': 'pie',
            'data': {
                'labels': labels,
                'datasets': [{
                    'data': data,
                    'backgroundColor': [self.default_colors[key] for key in list(self.default_colors.keys())[:len(data)]],
                    'borderColor': '#ffffff',
                    'borderWidth': 2
                }]
            },
            'options': {
                'responsive': True,
                'plugins': {'title': {'display': True, 'text': title}}
            }
        }

        return self._create_quickchart_image(chart_data, width, height)

    def create_heatmap(self, data: List[List[Any]], row_labels: List[str], 
                      col_labels: List[str], title: str = "", width: float = 6.0, 
                      height: float = 4.0) -> Image:
        """
        Create a heatmap visualization.
        
        Args:
            data: 2D array of values
            row_labels: Labels for rows
            col_labels: Labels for columns
            title: Chart title
            width: Chart width in inches
            height: Chart height in inches
            
        Returns:
            ReportLab Image object
        """
        # For heatmaps, we'll use a custom approach with tables
        # This is a placeholder - you might want to use matplotlib or seaborn for actual heatmaps
        chart_data = {
            'type': 'bar',
            'data': {
                'labels': col_labels,
                'datasets': []
            },
            'options': {
                'responsive': True,
                'scales': {'y': {'beginAtZero': True}},
                'plugins': {'title': {'display': True, 'text': title}}
            }
        }

        # Create a dataset for each row
        for i, row in enumerate(data):
            color_key = list(self.default_colors.keys())[i % len(self.default_colors)]
            chart_data['data']['datasets'].append({
                'label': row_labels[i] if i < len(row_labels) else f'Row {i+1}',
                'data': row,
                'backgroundColor': self.default_colors[color_key],
                'borderColor': self.default_colors[color_key],
                'borderWidth': 1
            })

        return self._create_quickchart_image(chart_data, width, height)

    def create_dashboard_chart(self, charts: List[Dict[str, Any]], 
                             layout: str = "2x2", width: float = 8.0, 
                             height: float = 6.0) -> List[Image]:
        """
        Create a dashboard with multiple charts.
        
        Args:
            charts: List of chart configurations
            layout: Layout string (e.g., "2x2", "3x1")
            width: Total dashboard width in inches
            height: Total dashboard height in inches
            
        Returns:
            List of ReportLab Image objects
        """
        # Parse layout
        if 'x' in layout:
            cols, rows = map(int, layout.split('x'))
        else:
            cols, rows = 2, 2

        # Calculate individual chart dimensions
        chart_width = width / cols
        chart_height = height / rows

        dashboard_charts = []
        for i, chart_config in enumerate(charts):
            if i >= cols * rows:
                break

            chart_type = chart_config.get('type', 'bar')
            if chart_type == 'bar':
                chart = self.create_bar_chart(
                    chart_config['labels'],
                    chart_config['datasets'],
                    chart_config.get('title', f'Chart {i+1}'),
                    chart_width,
                    chart_height
                )
            elif chart_type == 'line':
                chart = self.create_line_chart(
                    chart_config['labels'],
                    chart_config['datasets'],
                    chart_config.get('title', f'Chart {i+1}'),
                    chart_width,
                    chart_height
                )
            elif chart_type == 'pie':
                chart = self.create_pie_chart(
                    chart_config['labels'],
                    chart_config['data'],
                    chart_config.get('title', f'Chart {i+1}'),
                    chart_width,
                    chart_height
                )
            else:
                continue

            dashboard_charts.append(chart)

        return dashboard_charts

    def _create_quickchart_image(self, chart_data: Dict[str, Any], 
                                width: float, height: float) -> Image:
        """
        Create a chart image using QuickChart.io.
        
        Args:
            chart_data: Chart configuration data
            width: Chart width in inches
            height: Chart height in inches
            
        Returns:
            ReportLab Image object
        """
        try:
            # URL encode the chart data for QuickChart.io
            encoded_data = urllib.parse.quote(json.dumps(chart_data))
            chart_url = f"https://quickchart.io/chart?c={encoded_data}&width={int(width * 96)}&height={int(height * 96)}"
            
            # Create the image
            chart_image = Image(chart_url, width=width * inch, height=height * inch)
            log.info(f"Chart created successfully: {chart_data.get('type', 'unknown')} chart")
            return chart_image
            
        except Exception as e:
            log.error(f"Error creating chart: {e}")
            # Return a placeholder image
            return self._create_placeholder_chart(width, height, "Chart Error")

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
        # Create a simple placeholder using a data URL
        placeholder_data = {
            'type': 'bar',
            'data': {
                'labels': ['Placeholder'],
                'datasets': [{'label': 'Data', 'data': [1], 'backgroundColor': '#cccccc'}]
            },
            'options': {
                'responsive': True,
                'plugins': {'title': {'display': True, 'text': text}}
            }
        }
        
        encoded_data = urllib.parse.quote(json.dumps(placeholder_data))
        placeholder_url = f"https://quickchart.io/chart?c={encoded_data}&width={int(width * 96)}&height={int(height * 96)}"
        
        return Image(placeholder_url, width=width * inch, height=height * inch)

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
            if x_column is None:
                x_column = df.index.name or df.columns[0]
            
            if y_columns is None:
                y_columns = [col for col in df.columns if col != x_column]
            
            labels = df[x_column].astype(str).tolist()
            datasets = []
            
            for col in y_columns:
                if col in df.columns:
                    datasets.append({
                        'label': col,
                        'data': df[col].tolist()
                    })
            
            if chart_type == "pie":
                return self.create_pie_chart(labels, datasets[0]['data'], title, width, height)
            else:
                return self.create_bar_chart(labels, datasets, title, width, height, chart_type)
                
        except Exception as e:
            log.error(f"Error generating chart from DataFrame: {e}")
            return self._create_placeholder_chart(width, height, "DataFrame Chart Error")

    def create_custom_chart(self, chart_config: Dict[str, Any], 
                           width: float = 6.0, height: float = 4.0) -> Image:
        """
        Create a custom chart based on configuration.
        
        Args:
            chart_config: Complete chart configuration dictionary
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
            
            return self._create_quickchart_image(chart_config, width, height)
            
        except Exception as e:
            log.error(f"Error creating custom chart: {e}")
            return self._create_placeholder_chart(width, height, "Custom Chart Error")

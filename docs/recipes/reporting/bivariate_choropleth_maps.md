# Bivariate Choropleth Maps in Reports

## Problem Statement

You need to create professional reports that show the relationship between two variables across geographic regions. Traditional choropleth maps only show one variable at a time, but you want to visualize how two different metrics relate to each other spatially - for example, population density vs. median income by state, or market penetration vs. customer satisfaction by territory.

## Solution

Use the enhanced `ChartGenerator` class in siege_utilities to create bivariate choropleth maps that display two variables simultaneously using sophisticated color schemes and professional styling.

## Prerequisites

Install the required dependencies:
```bash
pip install -r siege_utilities/reporting/requirements_bivariate_choropleth.txt
```

## Step-by-Step Implementation

### 1. Basic Bivariate Choropleth for Reports

```python
from siege_utilities.reporting.chart_generator import ChartGenerator
import pandas as pd

# Initialize chart generator
chart_gen = ChartGenerator()

# Sample data - population density and median income by state
data = {
    'state': ['California', 'Texas', 'New York', 'Florida', 'Illinois'],
    'population_density': [251.3, 108.4, 421.0, 384.3, 231.1],
    'median_income': [75235, 64034, 72741, 59227, 69234]
}
df = pd.DataFrame(data)

# Create bivariate choropleth for reports
chart = chart_gen.create_bivariate_choropleth(
    data=df,
    location_column='state',
    value_column1='population_density',
    value_column2='median_income',
    title="Population Density vs Median Income by State",
    width=10.0,
    height=8.0
)
```

### 2. Advanced Bivariate Choropleth with GeoPandas

```python
import geopandas as gpd
from pathlib import Path

# Load geographic data (GeoJSON file)
geodata_path = Path("path/to/your/states.geojson")
gdf = gpd.read_file(geodata_path)

# Create advanced bivariate choropleth
chart = chart_gen.create_bivariate_choropleth_matplotlib(
    data=df,
    geodata=gdf,
    location_column='state',
    value_column1='population_density',
    value_column2='median_income',
    title="Advanced Bivariate Analysis: Population vs Income",
    width=12.0,
    height=10.0,
    color_scheme='custom'
)
```

### 3. Integration with Report Generator

```python
from siege_utilities.reporting.report_generator import ReportGenerator
from siege_utilities.reporting.client_branding import ClientBrandingManager

# Setup client branding
branding_manager = ClientBrandingManager()
branding_config = branding_manager.get_client_branding('your_client_name')

# Initialize report generator
report_gen = ReportGenerator(
    template_config='path/to/template.yaml',
    branding_config=branding_config
)

# Create report with bivariate choropleth
report_content = report_gen.create_analytics_report(
    title="Geographic Market Analysis",
    charts=[chart],  # Your bivariate choropleth chart
    data_summary="Analysis of population density and income patterns across states",
    insights=[
        "High population density correlates with higher median income in coastal states",
        "Midwestern states show moderate population density with stable income levels",
        "Southern states exhibit varied patterns requiring targeted analysis"
    ]
)

# Generate PDF report
report_gen.generate_pdf_report(report_content, "geographic_analysis_report.pdf")
```

### 4. Custom Chart Configuration

```python
# Define chart configuration for complex setups
chart_config = {
    'type': 'bivariate_choropleth',
    'title': 'Custom Bivariate Analysis',
    'data': df,
    'location_column': 'state',
    'value_columns': ['population_density', 'median_income'],
    'styling': {
        'color_scheme': 'diverging',
        'classification': 'quantiles',
        'bins': 5
    }
}

# Create chart using configuration
chart = chart_gen.create_custom_chart(
    chart_config=chart_config,
    width=10.0,
    height=8.0
)
```

### 5. Dashboard with Multiple Maps

```python
# Create multiple bivariate choropleth maps for different time periods
charts = []

# Current year data
chart_current = chart_gen.create_bivariate_choropleth(
    data=df_current,
    location_column='state',
    value_column1='population_density',
    value_column2='median_income',
    title="Current Year: Population vs Income"
)
charts.append(chart_current)

# Previous year data
chart_previous = chart_gen.create_bivariate_choropleth(
    data=df_previous,
    location_column='state',
    value_column1='population_density',
    value_column2='median_income',
    title="Previous Year: Population vs Income"
)
charts.append(chart_previous)

# Create dashboard
dashboard = chart_gen.create_dashboard(
    charts=charts,
    layout="2x1",
    width=16.0,
    height=8.0
)
```

## Expected Output

- **Professional PDF reports** with embedded bivariate choropleth maps
- **High-quality static images** suitable for publications and presentations
- **Interactive HTML maps** for web-based exploration
- **Consistent styling** that matches your client branding

## Notes

- **Data Quality**: Ensure your location identifiers match between data and geographic files
- **Color Schemes**: Choose appropriate schemes for your data characteristics
- **Performance**: Large datasets may require optimization or sampling
- **Accessibility**: Consider colorblind-friendly palettes for broader audience access

## Troubleshooting

### Common Issues

1. **"GeoPandas not available"**: Install required dependencies
2. **"Location column not found"**: Check column names in your data
3. **"No numeric data found"**: Ensure value columns contain numeric data
4. **Memory issues**: Use smaller datasets or optimize GeoJSON files

### Performance Tips

- Simplify complex geographic geometries
- Use appropriate map projections
- Consider data aggregation for large datasets
- Cache frequently used geographic data

## Advanced Usage

### Custom Color Schemes

```python
# Create custom color palette
custom_colors = ['#e8e8e8', '#e4acac', '#c85a5a', '#9c2929', '#67001f']
chart = chart_gen.create_bivariate_choropleth_matplotlib(
    # ... other parameters ...
    color_scheme='custom'
)
```

### Statistical Classification

```python
# Use advanced choropleth with custom classification
chart = chart_gen.create_advanced_choropleth(
    data=df,
    geodata=gdf,
    location_column='state',
    value_column='population_density',
    classification='natural_breaks',
    bins=7,
    color_scheme='YlOrRd'
)
```

This recipe provides a comprehensive approach to creating professional bivariate choropleth maps for your reports, with multiple rendering options and full integration with the siege_utilities reporting system.

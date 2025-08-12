# Bivariate Choropleth Maps in siege_utilities

This document describes the enhanced bivariate choropleth map functionality added to the `ChartGenerator` class in siege_utilities. Bivariate choropleth maps visualize the relationship between two variables across geographic regions using a sophisticated two-dimensional color scheme.

## Overview

Bivariate choropleth maps are powerful visualization tools that show how two different variables relate to each other across geographic areas. Unlike traditional choropleth maps that only show one variable, bivariate maps reveal patterns and relationships that might not be apparent when viewing variables separately.

## Features

- **Dual Variable Visualization**: Display two variables simultaneously on the same map
- **Multiple Rendering Engines**: Support for both Folium (interactive) and matplotlib (static) rendering
- **Custom Color Schemes**: Built-in and customizable color palettes optimized for bivariate data
- **Advanced Classification**: Multiple classification methods (quantiles, equal interval, natural breaks)
- **Integration Ready**: Seamlessly integrates with the existing reporting system
- **Flexible Data Sources**: Works with pandas DataFrames, dictionaries, and GeoJSON files

## Installation Requirements

To use the bivariate choropleth functionality, install the following dependencies:

```bash
pip install geopandas folium matplotlib pandas numpy
```

## Quick Start

### Basic Bivariate Choropleth

```python
from siege_utilities.reporting.chart_generator import ChartGenerator

# Initialize chart generator
chart_gen = ChartGenerator()

# Create bivariate choropleth
chart = chart_gen.create_bivariate_choropleth(
    data=your_dataframe,
    location_column='state',
    value_column1='population_density',
    value_column2='median_income',
    title="Population vs Income by State",
    width=10.0,
    height=8.0
)
```

### Advanced Bivariate Choropleth with GeoPandas

```python
# For more control and better styling
chart = chart_gen.create_bivariate_choropleth_matplotlib(
    data=your_dataframe,
    geodata=your_geojson_file,  # or GeoDataFrame
    location_column='state',
    value_column1='population_density',
    value_column2='median_income',
    title="Advanced Bivariate Analysis",
    width=12.0,
    height=10.0,
    color_scheme='custom'
)
```

## Method Reference

### `create_bivariate_choropleth()`

Creates a bivariate choropleth map using Folium for interactive web-based visualization.

**Parameters:**
- `data`: DataFrame or dictionary with data
- `location_column`: Column name for locations
- `value_column1`: First variable to visualize
- `value_column2`: Second variable to visualize
- `title`: Map title
- `width`: Map width in inches
- `height`: Map height in inches

**Returns:** ReportLab Image object

### `create_bivariate_choropleth_matplotlib()`

Creates a bivariate choropleth map using matplotlib and GeoPandas for high-quality static visualization.

**Parameters:**
- `data`: DataFrame or dictionary with data
- `geodata`: GeoDataFrame or path to GeoJSON file
- `location_column`: Column name for locations (must match geodata)
- `value_column1`: First variable (X-axis in bivariate scheme)
- `value_column2`: Second variable (Y-axis in bivariate scheme)
- `title`: Map title
- `width`: Map width in inches
- `height`: Map height in inches
- `color_scheme`: Color scheme ('default', 'custom', 'diverging')

**Returns:** ReportLab Image object

### `create_advanced_choropleth()`

Creates an advanced choropleth map with multiple classification options.

**Parameters:**
- `data`: DataFrame or dictionary with data
- `geodata`: GeoDataFrame or path to GeoJSON file
- `location_column`: Column name for locations
- `value_column`: Column name for values to color by
- `title`: Map title
- `width`: Map width in inches
- `height`: Map height in inches
- `classification`: Classification method ('quantiles', 'equal_interval', 'natural_breaks')
- `bins`: Number of bins for classification
- `color_scheme`: Color scheme for the map

**Returns:** ReportLab Image object

## Color Schemes

### Built-in Schemes

- **default**: Uses 'RdYlBu_r' colormap optimized for bivariate data
- **diverging**: Uses 'RdBu_r' for divergent data patterns
- **custom**: Creates a specialized 20-color palette for bivariate visualization

### Custom Color Schemes

You can create custom color schemes by modifying the `_create_bivariate_color_scheme()` method or by passing custom colormaps directly to the plotting functions.

## Data Format Requirements

### Input Data

Your data should have:
- A location column (e.g., state names, country codes)
- Two numeric value columns for the variables you want to visualize
- Consistent location identifiers between your data and geographic data

### Geographic Data

Geographic data can be:
- **GeoJSON files**: Loaded automatically by GeoPandas
- **GeoDataFrames**: Direct GeoPandas objects
- **Shapefiles**: Supported by GeoPandas

## Integration with Reporting System

### DataFrame Integration

```python
# Use with DataFrame-based chart generation
chart = chart_gen.generate_chart_from_dataframe(
    df=your_dataframe,
    chart_type='bivariate_choropleth',
    x_column='state',
    y_columns=['variable1', 'variable2'],
    title="Your Title"
)
```

### Custom Chart Configuration

```python
chart_config = {
    'type': 'bivariate_choropleth',
    'title': 'Your Title',
    'data': your_dataframe,
    'location_column': 'state',
    'value_columns': ['variable1', 'variable2']
}

chart = chart_gen.create_custom_chart(chart_config)
```

### Report Sections

```python
# Create complete report sections
report_section = chart_gen.create_chart_section(
    title="Geographic Analysis",
    charts=[chart1, chart2],
    description="Analysis of geographic patterns..."
)
```

## Examples

See `examples/bivariate_choropleth_example.py` for comprehensive examples including:

1. Basic bivariate choropleth creation
2. Advanced matplotlib-based visualization
3. Custom chart configuration
4. DataFrame integration
5. Advanced classification methods
6. Complete report integration

## Best Practices

### Data Preparation

1. **Clean your data**: Remove missing values and outliers that could skew the visualization
2. **Normalize variables**: Consider normalizing variables if they have very different scales
3. **Check location matching**: Ensure location identifiers match between your data and geographic data

### Visualization Design

1. **Choose appropriate color schemes**: Use diverging schemes for data that has a meaningful center point
2. **Consider accessibility**: Ensure sufficient contrast between colors
3. **Add legends**: Always include clear legends explaining the color coding

### Performance

1. **Limit data size**: Very large datasets can slow down rendering
2. **Use appropriate projections**: Choose map projections suitable for your geographic scope
3. **Optimize GeoJSON**: Simplify complex geometries for better performance

## Troubleshooting

### Common Issues

1. **Missing dependencies**: Ensure all required packages are installed
2. **Data type mismatches**: Check that location columns are strings and value columns are numeric
3. **Geographic data issues**: Verify that your GeoJSON files are valid and properly formatted
4. **Memory issues**: Large datasets may require chunking or sampling

### Error Messages

- **"Folium or GeoPandas not available"**: Install missing dependencies
- **"No numeric data found"**: Check that your value columns contain numeric data
- **"Location column not found"**: Verify column names in your data

## Advanced Usage

### Custom Legends

The system automatically creates bivariate legends, but you can customize them by modifying the `_add_bivariate_legend()` method.

### Multiple Maps

Create multiple bivariate choropleth maps for different regions or time periods and combine them in dashboards or reports.

### Interactive Features

When using Folium-based maps, you can add additional interactive features like:
- Popup information
- Layer controls
- Custom markers
- Zoom controls

## References

This implementation is based on the approach from the [bivariate-choropleth repository](https://github.com/mikhailsirenko/bivariate-choropleth) and adapted for integration with the siege_utilities reporting system.

## Contributing

To enhance the bivariate choropleth functionality:

1. Add new color schemes to `_create_bivariate_color_scheme()`
2. Implement additional classification methods
3. Add support for more geographic data formats
4. Enhance legend customization options
5. Add statistical analysis capabilities

## License

This functionality is part of the siege_utilities package and follows the same licensing terms.

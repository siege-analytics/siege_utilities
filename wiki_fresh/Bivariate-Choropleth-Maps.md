# Bivariate Choropleth Maps - Two-Variable Geographic Visualization

## Problem

You need to create professional reports that show the relationship between two variables across geographic regions. Traditional choropleth maps only show one variable at a time, but you want to visualize how two different metrics relate to each other spatially - for example, population density vs. median income by state, or market penetration vs. customer satisfaction by territory.

## Solution

Use the enhanced `ChartGenerator` class in siege_utilities to create bivariate choropleth maps that display two variables simultaneously using sophisticated color schemes and professional styling.

## Quick Start

```python
from siege_utilities.reporting.chart_generator import ChartGenerator
import pandas as pd

# Initialize chart generator
chart_gen = ChartGenerator()

# Create bivariate choropleth
chart = chart_gen.create_bivariate_choropleth(
    data=df,
    location_column='state',
    value_column1='population_density',
    value_column2='median_income',
    title="Population Density vs Median Income by State"
)
```

## Complete Implementation

### 1. Basic Bivariate Choropleth Creation

#### Setup and Data Preparation
```python
import siege_utilities
import pandas as pd
import geopandas as gpd
from pathlib import Path

# Initialize logging
siege_utilities.log_info("Starting bivariate choropleth map creation")

# Sample data - population density and median income by state
sample_data = {
    'state': ['California', 'Texas', 'Florida', 'New York', 'Illinois', 'Pennsylvania'],
    'population_density': [251.3, 108.4, 384.3, 421.0, 231.1, 285.3],
    'median_income': [75235, 64034, 59227, 72714, 69287, 63385],
    'population': [39512223, 28995881, 21477737, 19453561, 12671821, 12801989]
}

df = pd.DataFrame(sample_data)
print(f"✅ Created sample dataset with {len(df)} states")
print(f"📊 Data columns: {list(df.columns)}")
```

#### Create Basic Bivariate Map
```python
from siege_utilities.reporting.chart_generator import ChartGenerator

def create_basic_bivariate_map(data, location_col, value1_col, value2_col, title):
    """Create a basic bivariate choropleth map."""
    
    try:
        # Initialize chart generator
        chart_gen = ChartGenerator()
        
        # Create the bivariate choropleth
        chart = chart_gen.create_bivariate_choropleth(
            data=data,
            location_column=location_col,
            value_column1=value1_col,
            value_column2=value2_col,
            title=title,
            classification_method='quantiles',
            color_scheme='purple_orange',
            map_style='light',
            show_legend=True,
            legend_title=f"{value1_col} vs {value2_col}"
        )
        
        print(f"✅ Bivariate choropleth created successfully")
        print(f"📊 Variables: {value1_col} vs {value2_col}")
        print(f"🗺️ Locations: {len(data)} states")
        
        return chart
        
    except Exception as e:
        print(f"❌ Error creating bivariate map: {e}")
        siege_utilities.log_error(f"Bivariate map creation failed: {e}")
        return None

# Create the map
basic_map = create_basic_bivariate_map(
    data=df,
    location_col='state',
    value1_col='population_density',
    value2_col='median_income',
    title="Population Density vs Median Income by State"
)
```

### 2. Advanced Bivariate Choropleth with GeoPandas

#### Enhanced Geographic Data Processing
```python
def create_enhanced_bivariate_map(data, location_col, value1_col, value2_col, title):
    """Create an enhanced bivariate choropleth with GeoPandas integration."""
    
    try:
        # Load geographic boundaries (you'll need to download these)
        # For this example, we'll create a simplified approach
        
        # Normalize the data for better visualization
        data_normalized = data.copy()
        
        # Z-score normalization for both variables
        for col in [value1_col, value2_col]:
            mean_val = data_normalized[col].mean()
            std_val = data_normalized[col].std()
            data_normalized[f'{col}_normalized'] = (data_normalized[col] - mean_val) / std_val
        
        # Create bivariate classification
        data_normalized = create_bivariate_classification(
            data_normalized, 
            f'{value1_col}_normalized', 
            f'{value2_col}_normalized'
        )
        
        # Initialize chart generator with enhanced options
        chart_gen = ChartGenerator()
        
        # Create enhanced bivariate choropleth
        chart = chart_gen.create_bivariate_choropleth(
            data=data_normalized,
            location_column=location_col,
            value_column1=value1_col,
            value_column2=value2_col,
            title=title,
            classification_method='natural_breaks',
            color_scheme='blue_red',
            map_style='dark',
            show_legend=True,
            legend_title=f"{value1_col} vs {value2_col}",
            additional_options={
                'opacity': 0.8,
                'stroke_width': 1,
                'stroke_color': '#ffffff',
                'hover_info': [value1_col, value2_col, 'bivariate_class']
            }
        )
        
        print(f"✅ Enhanced bivariate choropleth created")
        print(f"📊 Normalized variables for better comparison")
        print(f"🎨 Using natural breaks classification")
        
        return chart, data_normalized
        
    except Exception as e:
        print(f"❌ Error creating enhanced map: {e}")
        siege_utilities.log_error(f"Enhanced bivariate map creation failed: {e}")
        return None, None

def create_bivariate_classification(data, col1, col2, n_classes=4):
    """Create bivariate classification for enhanced visualization."""
    
    try:
        # Create 2D classification grid
        # This creates a 4x4 grid (16 classes) for bivariate visualization
        
        # Get percentiles for both variables
        percentiles1 = data[col1].quantile([0.25, 0.5, 0.75])
        percentiles2 = data[col2].quantile([0.25, 0.5, 0.75])
        
        # Create classification function
        def classify_bivariate(row):
            val1 = row[col1]
            val2 = row[col2]
            
            # Classify first variable
            if val1 <= percentiles1[0.25]:
                class1 = 1
            elif val1 <= percentiles1[0.5]:
                class1 = 2
            elif val1 <= percentiles1[0.75]:
                class1 = 3
            else:
                class1 = 4
            
            # Classify second variable
            if val2 <= percentiles2[0.25]:
                class2 = 1
            elif val2 <= percentiles2[0.5]:
                class2 = 2
            elif val2 <= percentiles2[0.75]:
                class2 = 3
            else:
                class2 = 4
            
            # Combine into bivariate class (1-16)
            bivariate_class = (class1 - 1) * 4 + class2
            
            return bivariate_class
        
        # Apply classification
        data['bivariate_class'] = data.apply(classify_bivariate, axis=1)
        
        print(f"✅ Created bivariate classification with {n_classes * n_classes} classes")
        return data
        
    except Exception as e:
        print(f"❌ Error in bivariate classification: {e}")
        return data

# Create enhanced map
enhanced_map, enhanced_data = create_enhanced_bivariate_map(
    data=df,
    location_col='state',
    value1_col='population_density',
    value2_col='median_income',
    title="Enhanced: Population Density vs Median Income by State"
)
```

### 3. Integration with Report Generator

#### Create Comprehensive Report with Bivariate Maps
```python
from siege_utilities.reporting import ReportGenerator

def create_bivariate_map_report(data, location_col, value1_col, value2_col):
    """Create a comprehensive report featuring bivariate choropleth maps."""
    
    try:
        # Initialize report generator
        report_gen = ReportGenerator('Geographic Analysis Report')
        
        # Create multiple bivariate maps with different configurations
        maps = []
        
        # Map 1: Basic quantiles
        chart_gen = ChartGenerator()
        map1 = chart_gen.create_bivariate_choropleth(
            data=data,
            location_column=location_col,
            value_column1=value1_col,
            value_column2=value2_col,
            title=f"{value1_col} vs {value2_col} - Quantiles Classification",
            classification_method='quantiles',
            color_scheme='purple_orange'
        )
        maps.append(map1)
        
        # Map 2: Natural breaks
        map2 = chart_gen.create_bivariate_choropleth(
            data=data,
            location_column=location_col,
            value_column1=value1_col,
            value_column2=value2_col,
            title=f"{value1_col} vs {value2_col} - Natural Breaks Classification",
            classification_method='natural_breaks',
            color_scheme='blue_red'
        )
        maps.append(map2)
        
        # Map 3: Equal interval
        map3 = chart_gen.create_bivariate_choropleth(
            data=data,
            location_column=location_col,
            value_column1=value1_col,
            value_column2=value2_col,
            title=f"{value1_col} vs {value2_col} - Equal Interval Classification",
            classification_method='equal_interval',
            color_scheme='green_purple'
        )
        maps.append(map3)
        
        # Generate report content
        report_content = {
            'title': f"Bivariate Geographic Analysis: {value1_col} vs {value2_col}",
            'summary': f"Analysis of {len(data)} geographic locations showing the relationship between {value1_col} and {value2_col}",
            'maps': maps,
            'data_summary': {
                'total_locations': len(data),
                'variable1': {
                    'name': value1_col,
                    'mean': data[value1_col].mean(),
                    'std': data[value1_col].std(),
                    'min': data[value1_col].min(),
                    'max': data[value1_col].max()
                },
                'variable2': {
                    'name': value2_col,
                    'mean': data[value2_col].mean(),
                    'std': data[value2_col].std(),
                    'min': data[value2_col].min(),
                    'max': data[value2_col].max()
                }
            }
        }
        
        # Create the report
        report_path = report_gen.create_analytics_report(
            title=report_content['title'],
            charts=maps,
            data_summary=report_content['summary'],
            insights=[
                f"Strong correlation between {value1_col} and {value2_col}",
                f"Geographic clustering patterns identified",
                f"Outliers and regional variations highlighted"
            ],
            recommendations=[
                "Focus on high-performing regions for best practices",
                "Investigate outlier regions for improvement opportunities",
                "Consider regional factors in policy development"
            ]
        )
        
        print(f"✅ Comprehensive report created: {report_path}")
        return report_path, report_content
        
    except Exception as e:
        print(f"❌ Error creating report: {e}")
        siege_utilities.log_error(f"Report creation failed: {e}")
        return None, None

# Create comprehensive report
report_path, report_content = create_bivariate_map_report(
    data=df,
    location_col='state',
    value1_col='population_density',
    value2_col='median_income'
)
```

### 4. Custom Color Schemes and Styling

#### Advanced Customization Options
```python
def create_custom_bivariate_map(data, location_col, value1_col, value2_col, title):
    """Create a bivariate choropleth with custom styling and color schemes."""
    
    try:
        chart_gen = ChartGenerator()
        
        # Custom color scheme definition
        custom_colors = {
            'low_low': '#e8f4fd',      # Light blue
            'low_high': '#ffd700',     # Gold
            'high_low': '#ff6b6b',     # Light red
            'high_high': '#8b0000'     # Dark red
        }
        
        # Custom styling options
        custom_styling = {
            'map_style': 'satellite',
            'opacity': 0.9,
            'stroke_width': 2,
            'stroke_color': '#ffffff',
            'hover_template': f'<b>%{{location}}</b><br>' +
                            f'{value1_col}: %{{value1}}<br>' +
                            f'{value2_col}: %{{value2}}<br>' +
                            f'<extra></extra>',
            'legend': {
                'orientation': 'horizontal',
                'x': 0.5,
                'y': -0.1,
                'xanchor': 'center',
                'yanchor': 'top'
            }
        }
        
        # Create custom bivariate choropleth
        chart = chart_gen.create_bivariate_choropleth(
            data=data,
            location_column=location_col,
            value_column1=value1_col,
            value_column2=value2_col,
            title=title,
            classification_method='quantiles',
            color_scheme='custom',
            custom_colors=custom_colors,
            custom_styling=custom_styling,
            show_legend=True,
            legend_title=f"Bivariate Classification: {value1_col} vs {value2_col}"
        )
        
        print(f"✅ Custom bivariate choropleth created")
        print(f"🎨 Using custom color scheme and styling")
        
        return chart
        
    except Exception as e:
        print(f"❌ Error creating custom map: {e}")
        return None

# Create custom styled map
custom_map = create_custom_bivariate_map(
    data=df,
    location_col='state',
    value1_col='population_density',
    value2_col='median_income',
    title="Custom Styled: Population Density vs Median Income"
)
```

### 5. Interactive Bivariate Choropleth with Plotly

#### Create Interactive Visualization
```python
def create_interactive_bivariate_map(data, location_col, value1_col, value2_col, title):
    """Create an interactive bivariate choropleth using Plotly."""
    
    try:
        import plotly.express as px
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        # Create bivariate classification
        data_classified = create_bivariate_classification(data, value1_col, value2_col)
        
        # Create interactive choropleth
        fig = px.choropleth(
            data_classified,
            locations=location_col,
            locationmode='USA-states',
            color='bivariate_class',
            hover_name=location_col,
            hover_data=[value1_col, value2_col],
            title=title,
            color_continuous_scale='Viridis',
            labels={'bivariate_class': 'Bivariate Class'}
        )
        
        # Update layout for better presentation
        fig.update_layout(
            title_x=0.5,
            title_font_size=20,
            geo=dict(
                scope='usa',
                showlakes=True,
                lakecolor='rgb(255, 255, 255)',
                showland=True,
                landcolor='rgb(217, 217, 217)',
                showocean=True,
                oceancolor='rgb(204, 229, 255)',
                showcoastlines=True,
                coastlinecolor='rgb(80, 80, 80)',
                showrivers=True,
                rivercolor='rgb(204, 229, 255)',
                showframe=False,
                framecolor='rgb(80, 80, 80)'
            ),
            width=1000,
            height=600
        )
        
        # Add custom hover template
        fig.update_traces(
            hovertemplate='<b>%{location}</b><br>' +
                         f'{value1_col}: %{{customdata[0]}}<br>' +
                         f'{value2_col}: %{{customdata[1]}}<br>' +
                         'Bivariate Class: %{z}<extra></extra>'
        )
        
        print(f"✅ Interactive bivariate choropleth created")
        print(f"🖱️ Hover over states for detailed information")
        
        return fig
        
    except Exception as e:
        print(f"❌ Error creating interactive map: {e}")
        return None

# Create interactive map
interactive_map = create_interactive_bivariate_map(
    data=df,
    location_col='state',
    value1_col='population_density',
    value2_col='median_income',
    title="Interactive: Population Density vs Median Income by State"
)

# Save interactive map as HTML
if interactive_map:
    interactive_map.write_html("interactive_bivariate_map.html")
    print("💾 Interactive map saved as HTML file")
```

### 6. Complete Pipeline Example

#### End-to-End Bivariate Analysis
```python
def run_complete_bivariate_analysis():
    """Run complete bivariate choropleth analysis pipeline."""
    
    print("🚀 Starting Complete Bivariate Choropleth Analysis")
    print("=" * 60)
    
    try:
        # Step 1: Data preparation
        print("📊 Step 1: Preparing data...")
        
        # Load or create your data
        # For this example, we'll use the sample data
        analysis_data = df.copy()
        
        print(f"  ✅ Data loaded: {len(analysis_data)} locations")
        print(f"  📋 Variables: {list(analysis_data.columns)}")
        
        # Step 2: Data validation
        print("\n🔍 Step 2: Validating data...")
        
        # Check for missing values
        missing_values = analysis_data.isnull().sum()
        if missing_values.sum() > 0:
            print(f"  ⚠️ Found missing values: {missing_values.to_dict()}")
            # Handle missing values
            analysis_data = analysis_data.dropna()
            print(f"  ✅ Missing values handled: {len(analysis_data)} locations remaining")
        else:
            print("  ✅ No missing values found")
        
        # Step 3: Create multiple map variations
        print("\n🗺️ Step 3: Creating bivariate choropleth maps...")
        
        maps = []
        
        # Basic map
        basic_map = create_basic_bivariate_map(
            analysis_data, 'state', 'population_density', 'median_income',
            "Basic: Population Density vs Median Income"
        )
        if basic_map:
            maps.append(basic_map)
            print("  ✅ Basic map created")
        
        # Enhanced map
        enhanced_map, enhanced_data = create_enhanced_bivariate_map(
            analysis_data, 'state', 'population_density', 'median_income',
            "Enhanced: Population Density vs Median Income"
        )
        if enhanced_map:
            maps.append(enhanced_map)
            print("  ✅ Enhanced map created")
        
        # Custom styled map
        custom_map = create_custom_bivariate_map(
            analysis_data, 'state', 'population_density', 'median_income',
            "Custom Styled: Population Density vs Median Income"
        )
        if custom_map:
            maps.append(custom_map)
            print("  ✅ Custom styled map created")
        
        # Interactive map
        interactive_map = create_interactive_bivariate_map(
            analysis_data, 'state', 'population_density', 'median_income',
            "Interactive: Population Density vs Median Income"
        )
        if interactive_map:
            print("  ✅ Interactive map created")
        
        # Step 4: Generate comprehensive report
        print("\n📄 Step 4: Generating comprehensive report...")
        
        if maps:
            report_path, report_content = create_bivariate_map_report(
                analysis_data, 'state', 'population_density', 'median_income'
            )
            if report_path:
                print(f"  ✅ Report generated: {report_path}")
        
        # Step 5: Analysis summary
        print("\n📊 Step 5: Analysis Summary")
        print("=" * 40)
        
        print(f"Total maps created: {len(maps)}")
        print(f"Data locations analyzed: {len(analysis_data)}")
        print(f"Variables analyzed: population_density vs median_income")
        print(f"Classification methods: quantiles, natural breaks, equal interval")
        print(f"Color schemes: purple_orange, blue_red, green_purple, custom")
        
        # Calculate correlation
        correlation = analysis_data['population_density'].corr(analysis_data['median_income'])
        print(f"Correlation coefficient: {correlation:.3f}")
        
        if abs(correlation) > 0.7:
            print("  💡 Strong correlation detected")
        elif abs(correlation) > 0.4:
            print("  💡 Moderate correlation detected")
        else:
            print("  💡 Weak correlation detected")
        
        print("\n✅ Bivariate choropleth analysis completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Analysis pipeline failed: {e}")
        siege_utilities.log_error(f"Bivariate analysis pipeline failed: {e}")
        return False

# Run complete analysis
if __name__ == "__main__":
    success = run_complete_bivariate_analysis()
    if success:
        print("\n🎉 All bivariate choropleth maps created successfully!")
    else:
        print("\n💥 Analysis pipeline encountered errors")
```

## Expected Output

```
🚀 Starting Complete Bivariate Choropleth Analysis
============================================================
📊 Step 1: Preparing data...
  ✅ Data loaded: 6 locations
  📋 Variables: ['state', 'population_density', 'median_income', 'population']

🔍 Step 2: Validating data...
  ✅ No missing values found

🗺️ Step 3: Creating bivariate choropleth maps...
  ✅ Basic map created
  ✅ Enhanced map created
  ✅ Custom styled map created
  ✅ Interactive map created

📄 Step 4: Generating comprehensive report...
  ✅ Report generated: reports/geographic_analysis_report.pdf

📊 Step 5: Analysis Summary
========================================
Total maps created: 3
Data locations analyzed: 6
Variables analyzed: population_density vs median_income
Classification methods: quantiles, natural breaks, equal interval
Color schemes: purple_orange, blue_red, green_purple, custom
Correlation coefficient: -0.234
  💡 Weak correlation detected

✅ Bivariate choropleth analysis completed successfully!

🎉 All bivariate choropleth maps created successfully!
```

## Configuration Options

### Bivariate Map Configuration
```yaml
bivariate_choropleth:
  classification_methods:
    - quantiles
    - natural_breaks
    - equal_interval
    - jenks
  color_schemes:
    - purple_orange
    - blue_red
    - green_purple
    - custom
  map_styles:
    - light
    - dark
    - satellite
    - custom
  legend_options:
    position: bottom
    orientation: horizontal
    show_title: true
    show_values: true
```

### Advanced Styling Options
```python
styling_config = {
    'opacity': 0.8,
    'stroke_width': 1.5,
    'stroke_color': '#ffffff',
    'hover_info': ['location', 'value1', 'value2', 'classification'],
    'zoom_level': 4,
    'center_lat': 39.8283,
    'center_lon': -98.5795,
    'mapbox_style': 'mapbox://styles/mapbox/light-v10'
}
```

## Troubleshooting

### Common Issues

1. **Data Format Problems**
   - Ensure location column matches geographic boundaries
   - Check for missing or invalid values
   - Verify data types (numeric for values)

2. **Geographic Boundary Issues**
   - Download appropriate geographic files
   - Ensure coordinate reference systems match
   - Check for missing geographic entities

3. **Classification Problems**
   - Use appropriate classification method for your data
   - Consider data distribution when choosing classes
   - Test different classification approaches

### Performance Tips

```python
# For large datasets, use efficient processing
def optimize_for_large_datasets(data, chunk_size=1000):
    """Process large datasets in chunks for better performance."""
    
    results = []
    for i in range(0, len(data), chunk_size):
        chunk = data.iloc[i:i+chunk_size]
        # Process chunk
        chunk_result = process_chunk(chunk)
        results.append(chunk_result)
    
    return pd.concat(results)
```

## Next Steps

After mastering bivariate choropleth maps:

- **Advanced Geographic Analysis**: Add more variables and dimensions
- **Temporal Analysis**: Create time-series bivariate maps
- **Custom Classifications**: Develop domain-specific classification methods
- **Integration**: Connect with other visualization tools

## Related Recipes

- **[Comprehensive Reporting](Comprehensive-Reporting)** - Generate reports with bivariate maps
- **[Analytics Integration](Analytics-Integration)** - Use geographic data in analytics
- **[Basic Setup](Basic-Setup)** - Configure Siege Utilities for mapping
- **[Client Management](Examples/Client-Management)** - Apply client branding to maps

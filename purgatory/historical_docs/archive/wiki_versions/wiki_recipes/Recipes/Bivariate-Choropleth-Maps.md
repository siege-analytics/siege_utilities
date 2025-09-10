# 🗺️ Bivariate Choropleth Maps - Two-Variable Geographic Visualization

<div align="center">

![Choropleth](https://img.shields.io/badge/Choropleth-Two_Variable-blue)
![Maps](https://img.shields.io/badge/Maps-Geographic_Visualization-green)
![Analysis](https://img.shields.io/badge/Analysis-Spatial_Relationships-orange)

**Visualize relationships between two variables across geographic regions** 🌍

</div>

---

## 🎯 **Problem Statement**

You need to create professional reports that show the relationship between two variables across geographic regions. Traditional choropleth maps only show one variable at a time, but you want to visualize how two different metrics relate to each other spatially - for example, population density vs. median income by state, or market penetration vs. customer satisfaction by territory.

## 💡 **Solution**

Use the enhanced `ChartGenerator` class in siege_utilities to create bivariate choropleth maps that display two variables simultaneously using sophisticated color schemes and professional styling.

## 🚀 **Quick Start**

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

## 📋 **Complete Implementation**

### **1. Basic Bivariate Choropleth for Reports**

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

print(f"✅ Bivariate choropleth created: {chart}")
```

### **2. Advanced Bivariate Choropleth with GeoPandas**

```python
import geopandas as gpd
from pathlib import Path
from siege_utilities.reporting.chart_generator import ChartGenerator

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

print(f"✅ Advanced bivariate choropleth created: {chart}")
```

### **3. Integration with Report Generator**

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

print(f"✅ Report created with bivariate choropleth")
```

### **4. Custom Color Schemes and Styling**

```python
from siege_utilities.reporting.chart_generator import ChartGenerator
import matplotlib.colors as mcolors

# Initialize chart generator
chart_gen = ChartGenerator()

# Custom color scheme for bivariate analysis
custom_colors = {
    'low_low': '#e8e8e8',      # Light gray for low-low values
    'low_high': '#5ac8c8',     # Teal for low-high values
    'high_low': '#ff9500',     # Orange for high-low values
    'high_high': '#007aff'     # Blue for high-high values
}

# Create bivariate choropleth with custom styling
chart = chart_gen.create_bivariate_choropleth(
    data=df,
    location_column='state',
    value_column1='population_density',
    value_column2='median_income',
    title="Custom Styled Bivariate Analysis",
    color_scheme='custom',
    custom_colors=custom_colors,
    classification_method='quantiles',
    bins=4,
    width=12.0,
    height=10.0,
    dpi=300
)

print(f"✅ Custom styled bivariate choropleth created")
```

### **5. Interactive Bivariate Choropleth with Plotly**

```python
from siege_utilities.reporting.chart_generator import ChartGenerator
import plotly.express as px
import plotly.graph_objects as go

# Initialize chart generator
chart_gen = ChartGenerator()

# Create interactive bivariate choropleth
interactive_chart = chart_gen.create_bivariate_choropleth_plotly(
    data=df,
    location_column='state',
    value_column1='population_density',
    value_column2='median_income',
    title="Interactive Bivariate Analysis",
    hover_data=['state', 'population_density', 'median_income'],
    color_continuous_scale='Viridis',
    width=1000,
    height=600
)

# Save interactive chart
interactive_chart.write_html("bivariate_choropleth_interactive.html")
print(f"✅ Interactive bivariate choropleth saved")
```

### **6. Complete Bivariate Analysis Pipeline**

```python
from siege_utilities.reporting.chart_generator import ChartGenerator
from siege_utilities.reporting.report_generator import ReportGenerator
import pandas as pd
import geopandas as gpd
from pathlib import Path

class BivariateChoroplethAnalysis:
    """Complete pipeline for bivariate choropleth analysis"""
    
    def __init__(self, client_name="Siege Analytics"):
        self.chart_gen = ChartGenerator()
        self.report_gen = ReportGenerator(client_name)
        self.analysis_results = {}
    
    def load_data(self, data_path, geodata_path=None):
        """Load data and geographic data"""
        try:
            # Load main data
            if data_path.endswith('.csv'):
                self.data = pd.read_csv(data_path)
            elif data_path.endswith('.xlsx'):
                self.data = pd.read_excel(data_path)
            else:
                raise ValueError("Unsupported data format")
            
            # Load geographic data if provided
            if geodata_path:
                self.geodata = gpd.read_file(geodata_path)
            else:
                self.geodata = None
            
            print(f"✅ Data loaded: {len(self.data)} records")
            return True
            
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return False
    
    def create_bivariate_analysis(self, location_col, value_col1, value_col2, 
                                 title="Bivariate Analysis", **kwargs):
        """Create comprehensive bivariate analysis"""
        
        try:
            # Basic bivariate choropleth
            basic_chart = self.chart_gen.create_bivariate_choropleth(
                data=self.data,
                location_column=location_col,
                value_column1=value_col1,
                value_column2=value_col2,
                title=title,
                **kwargs
            )
            
            # Advanced matplotlib version if geodata available
            if self.geodata is not None:
                advanced_chart = self.chart_gen.create_bivariate_choropleth_matplotlib(
                    data=self.data,
                    geodata=self.geodata,
                    location_column=location_col,
                    value_column1=value_col1,
                    value_column2=value_col2,
                    title=f"Advanced {title}",
                    **kwargs
                )
            else:
                advanced_chart = None
            
            # Interactive plotly version
            interactive_chart = self.chart_gen.create_bivariate_choropleth_plotly(
                data=self.data,
                location_column=location_col,
                value_column1=value_col1,
                value_column2=value_col2,
                title=f"Interactive {title}",
                **kwargs
            )
            
            # Store results
            self.analysis_results = {
                'basic_chart': basic_chart,
                'advanced_chart': advanced_chart,
                'interactive_chart': interactive_chart,
                'data_summary': self._generate_data_summary(value_col1, value_col2),
                'insights': self._generate_insights(value_col1, value_col2)
            }
            
            print(f"✅ Bivariate analysis completed")
            return True
            
        except Exception as e:
            print(f"❌ Error in bivariate analysis: {e}")
            return False
    
    def _generate_data_summary(self, col1, col2):
        """Generate data summary for the analysis"""
        
        summary = {
            'total_regions': len(self.data),
            'variable1': {
                'name': col1,
                'mean': self.data[col1].mean(),
                'median': self.data[col1].median(),
                'min': self.data[col1].min(),
                'max': self.data[col1].max()
            },
            'variable2': {
                'name': col2,
                'mean': self.data[col2].mean(),
                'median': self.data[col2].median(),
                'min': self.data[col2].min(),
                'max': self.data[col2].max()
            },
            'correlation': self.data[col1].corr(self.data[col2])
        }
        
        return summary
    
    def _generate_insights(self, col1, col2):
        """Generate insights from the bivariate analysis"""
        
        insights = []
        
        # Correlation insights
        correlation = self.data[col1].corr(self.data[col2])
        if abs(correlation) > 0.7:
            insights.append(f"Strong correlation ({correlation:.2f}) between {col1} and {col2}")
        elif abs(correlation) > 0.4:
            insights.append(f"Moderate correlation ({correlation:.2f}) between {col1} and {col2}")
        else:
            insights.append(f"Weak correlation ({correlation:.2f}) between {col1} and {col2}")
        
        # Regional insights
        high_col1 = self.data[self.data[col1] > self.data[col1].quantile(0.8)]
        high_col2 = self.data[self.data[col2] > self.data[col2].quantile(0.8)]
        
        insights.append(f"Top 20% {col1} regions: {len(high_col1)}")
        insights.append(f"Top 20% {col2} regions: {len(high_col2)}")
        
        # Overlap analysis
        overlap = set(high_col1.index) & set(high_col2.index)
        insights.append(f"Regions in top 20% of both variables: {len(overlap)}")
        
        return insights
    
    def generate_report(self, title="Bivariate Choropleth Analysis Report"):
        """Generate comprehensive report with all charts"""
        
        try:
            # Prepare charts for report
            charts = []
            if self.analysis_results.get('basic_chart'):
                charts.append(self.analysis_results['basic_chart'])
            if self.analysis_results.get('advanced_chart'):
                charts.append(self.analysis_results['advanced_chart'])
            
            # Generate report
            report_path = self.report_gen.create_analytics_report(
                title=title,
                charts=charts,
                data_summary=str(self.analysis_results['data_summary']),
                insights=self.analysis_results['insights'],
                recommendations=[
                    "Consider regional clustering for targeted interventions",
                    "Analyze outliers for special case studies",
                    "Develop region-specific strategies based on variable patterns"
                ]
            )
            
            print(f"✅ Report generated: {report_path}")
            return report_path
            
        except Exception as e:
            print(f"❌ Error generating report: {e}")
            return None

# Usage example
if __name__ == "__main__":
    # Initialize analysis pipeline
    analysis = BivariateChoroplethAnalysis("Acme Corporation")
    
    # Load data
    data_loaded = analysis.load_data(
        data_path="data/state_metrics.csv",
        geodata_path="data/states.geojson"
    )
    
    if data_loaded:
        # Create bivariate analysis
        analysis_success = analysis.create_bivariate_analysis(
            location_col='state',
            value_col1='population_density',
            value_col2='median_income',
            title="Population Density vs Median Income Analysis"
        )
        
        if analysis_success:
            # Generate report
            report_path = analysis.generate_report()
            print(f"🎯 Analysis complete! Report saved to: {report_path}")
```

## 📊 **Expected Output**

### **Basic Bivariate Choropleth**
```
✅ Bivariate choropleth created: <matplotlib.figure.Figure object>
```

### **Advanced Analysis**
```
✅ Data loaded: 50 records
✅ Bivariate analysis completed
✅ Report generated: reports/bivariate_analysis_20240115.pdf
🎯 Analysis complete! Report saved to: reports/bivariate_analysis_20240115.pdf
```

### **Report Structure**
```
📄 Bivariate Choropleth Analysis Report
├── 🏢 Title Page
├── 📋 Executive Summary
├── 🗺️ Bivariate Choropleth Maps
│   ├── Basic Choropleth
│   ├── Advanced Matplotlib Version
│   └── Interactive Plotly Version
├── 📊 Data Summary
│   ├── Population Density Statistics
│   ├── Median Income Statistics
│   └── Correlation Analysis
├── 💡 Key Insights
├── 🎯 Recommendations
└── 📚 Appendices
```

## 🔧 **Configuration Options**

### **Color Schemes**
```python
# Predefined color schemes
color_schemes = [
    'viridis',      # Default scientific colormap
    'plasma',       # High contrast
    'inferno',      # Dark theme
    'magma',        # Light theme
    'custom'        # User-defined colors
]

# Custom color configuration
custom_colors = {
    'low_low': '#e8e8e8',      # Light gray
    'low_high': '#5ac8c8',     # Teal
    'high_low': '#ff9500',     # Orange
    'high_high': '#007aff'     # Blue
}
```

### **Classification Methods**
```python
# Data classification methods
classification_methods = [
    'quantiles',        # Equal number of regions per class
    'equal_interval',   # Equal range per class
    'natural_breaks',   # Natural clustering
    'jenks',           # Jenks natural breaks
    'custom'           # User-defined breaks
]

# Custom classification
custom_breaks = {
    'variable1': [0, 100, 200, 300, 500],
    'variable2': [0, 50000, 70000, 90000, 120000]
}
```

### **Styling Options**
```python
# Chart styling configuration
styling_config = {
    'width': 12.0,           # Inches
    'height': 10.0,          # Inches
    'dpi': 300,              # Resolution
    'title_fontsize': 16,    # Title font size
    'label_fontsize': 12,    # Label font size
    'legend_fontsize': 10,   # Legend font size
    'grid': True,            # Show grid
    'frame': True            # Show frame
}
```

## 🚨 **Troubleshooting**

### **Common Issues**

1. **🗺️ Geographic Data Missing**: Ensure geodata file is properly formatted (GeoJSON, Shapefile)
2. **🎨 Color Scheme Errors**: Check color scheme names and custom color definitions
3. **📊 Data Format Issues**: Verify data columns match expected names and types
4. **💾 Memory Issues**: Reduce DPI or chart size for large datasets

### **Performance Tips**

- **⚡ Data Optimization**: Pre-process large datasets before visualization
- **💾 Memory Management**: Use appropriate DPI settings for your use case
- **🔄 Caching**: Cache generated charts for repeated use
- **📊 Batch Processing**: Generate multiple charts in batch operations

### **Best Practices**

- **🎨 Color Selection**: Use colorblind-friendly color schemes
- **📊 Data Validation**: Validate data before visualization
- **🗺️ Geographic Accuracy**: Ensure geographic data matches your analysis regions
- **📋 Documentation**: Document color schemes and classification methods
- **🔄 Consistency**: Use consistent styling across related visualizations

## 🚀 **Next Steps**

After mastering bivariate choropleth maps:

- **[Comprehensive Reporting](Recipes/Comprehensive-Reporting.md)** - Integrate maps into reports
- **[Advanced Mapping](Recipes/Advanced-Mapping.md)** - Explore other map types
- **[Data Visualization](Recipes/Data-Visualization.md)** - Create comprehensive visualizations
- **[Geographic Analysis](Recipes/Geographic-Analysis.md)** - Perform spatial analysis

## 🔗 **Related Recipes**

- **[Basic Setup](Recipes/Basic-Setup.md)** - Install and configure Siege Utilities
- **[Comprehensive Reporting](Recipes/Comprehensive-Reporting.md)** - Create reports with maps
- **[Analytics Integration](Recipes/Analytics-Integration.md)** - Connect data sources
- **[Client Management](Examples/Client-Management.md)** - Apply client branding

---

<div align="center">

**Ready to create bivariate choropleth maps?** 🗺️

**[Next: Comprehensive Reporting](Recipes/Comprehensive-Reporting.md)** → **[Advanced Mapping](Recipes/Advanced-Mapping.md)**

</div>

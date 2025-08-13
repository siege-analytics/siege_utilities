# 📖 Recipes & Examples

<div align="center">

**Step-by-Step Implementation Guides and Working Examples**

![Recipes](https://img.shields.io/badge/Recipes-Step%20by%20Step-blue?style=for-the-badge&logo=book)

</div>

---

## 🎯 **Overview**

This section provides comprehensive examples, recipes, and implementation guides to help you get the most out of Siege Utilities. Each recipe includes working code, explanations, and best practices.

---

## 🚀 **Quick Examples**

### **Basic Bivariate Choropleth**
```python
from siege_utilities.reporting.chart_generator import ChartGenerator
import pandas as pd

# Initialize
chart_gen = ChartGenerator()

# Sample data
data = {
    'state': ['CA', 'TX', 'NY', 'FL'],
    'population': [39512223, 28995881, 19453561, 21477737],
    'income': [75235, 64034, 72741, 59227]
}
df = pd.DataFrame(data)

# Create map
chart = chart_gen.create_bivariate_choropleth_matplotlib(
    data=df,
    location_column='state',
    value_column1='population',
    value_column2='income',
    title="Population vs Income by State"
)
```

### **Professional Report Generation**
```python
from siege_utilities.reporting.report_generator import ReportGenerator

# Initialize
report_gen = ReportGenerator()

# Create report
report_content = report_gen.create_comprehensive_report(
    title="Geographic Analysis Report",
    author="Analytics Team",
    client="Research Institute",
    table_of_contents=True
)

# Add content
report_content = report_gen.add_map_section(
    report_content,
    "Regional Analysis",
    [chart],
    map_type="bivariate_choropleth"
)

# Generate PDF
report_gen.generate_pdf_report(report_content, "report.pdf")
```

---

## 📚 **Available Recipes**

### **Mapping & Visualization**
- **Bivariate Choropleth Maps**: Two-variable geographic analysis
- **Marker Maps**: Point location visualization
- **3D Maps**: Elevation and height analysis
- **Heatmap Maps**: Density and intensity mapping
- **Cluster Maps**: Grouped data visualization
- **Flow Maps**: Movement and connection patterns

### **Report Generation**
- **PDF Reports**: Professional document creation
- **PowerPoint Presentations**: Automated slide generation
- **Client Branding**: Custom styling and logos
- **Automation**: Scheduled report generation

### **Integration & APIs**
- **Google Analytics**: Website performance data
- **Facebook Business**: Advertising insights
- **Database Systems**: Customer and business data
- **Custom APIs**: Third-party integrations

---

## 🎨 **Advanced Recipes**

### **Multi-Source Data Integration**
```python
# Collect from multiple sources
ga_data = collect_google_analytics_data()
fb_data = collect_facebook_data()
db_data = collect_database_data()

# Combine and analyze
combined_data = combine_data_sources([ga_data, fb_data, db_data])

# Create comprehensive visualization
chart = chart_gen.create_bivariate_choropleth_matplotlib(
    data=combined_data,
    location_column='region',
    value_column1='web_traffic',
    value_column2='ad_performance'
)
```

### **Automated Report Generation**
```python
import schedule
import time

def generate_daily_report():
    """Generate daily performance report."""
    # Collect data
    data = collect_daily_data()
    
    # Create report
    report_content = create_daily_report(data)
    
    # Generate and save
    report_gen.generate_pdf_report(
        report_content, 
        "daily_report_" + time.strftime('%Y%m%d') + ".pdf"
    )

# Schedule daily generation
schedule.every().day.at("09:00").do(generate_daily_report)

# Run scheduler
while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 🔧 **Best Practices**

### **Data Preparation**
1. **Clean Data**: Remove duplicates and handle missing values
2. **Validate Formats**: Ensure consistent data types
3. **Check Coordinates**: Verify geographic data accuracy
4. **Optimize Performance**: Use appropriate data structures

### **Map Design**
1. **Choose Colors**: Select appropriate color schemes
2. **Clear Labels**: Use descriptive titles and legends
3. **Appropriate Scale**: Match detail level to audience
4. **Professional Appearance**: Maintain consistent styling

### **Report Organization**
1. **Logical Flow**: Organize content sequentially
2. **Clear Sections**: Well-defined boundaries
3. **Consistent Formatting**: Professional appearance
4. **Actionable Insights**: Clear recommendations

---

## 🚨 **Troubleshooting**

### **Common Issues**
- **Installation Problems**: Check dependencies and Python version
- **Data Errors**: Validate data formats and column names
- **Performance Issues**: Optimize data size and structure
- **Output Problems**: Check file paths and permissions

### **Getting Help**
1. **Check Documentation**: This wiki and GitHub Pages
2. **Review Examples**: Working code samples
3. **Search Issues**: GitHub issue tracker
4. **Community Support**: Discussions and Q&A

---

<div align="center">

**Ready to implement your solutions?**

[🗺️ Explore Maps](Mapping-and-Visualization) • [📄 Create Reports](Report-Generation) • [🔌 Integrate APIs](Integration-and-APIs)

---

*Build, create, and innovate with Siege Utilities* 📖✨

</div>

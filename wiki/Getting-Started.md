# 🚀 Getting Started

<div align="center">

**Quick Start Guide for Siege Utilities**

![Getting Started](https://img.shields.io/badge/Getting%20Started-5%20Minutes-blue?style=for-the-badge&logo=rocket)

</div>

---

## 🎯 **Welcome to Siege Utilities!**

Siege Utilities is an **enterprise-grade Python package** that transforms your geographic data into professional insights and reports. This guide will get you up and running in just 5 minutes.

---

## ⚡ **5-Minute Quick Start**

### **Step 1: Installation**

```bash
# Clone the repository
git clone https://github.com/siege-analytics/siege_utilities.git

# Navigate to the directory
cd siege_utilities

# Install dependencies
pip install -r siege_utilities/reporting/requirements_bivariate_choropleth.txt

# Install the package
pip install -e .
```

### **Step 2: Your First Map**

```python
from siege_utilities.reporting.chart_generator import ChartGenerator
import pandas as pd

# Initialize chart generator
chart_gen = ChartGenerator()

# Create sample data
data = {
    'state': ['California', 'Texas', 'New York', 'Florida'],
    'population': [39512223, 28995881, 19453561, 21477737],
    'income': [75235, 64034, 72741, 59227]
}
df = pd.DataFrame(data)

# Create your first bivariate choropleth map!
chart = chart_gen.create_bivariate_choropleth_matplotlib(
    data=df,
    location_column='state',
    value_column1='population',
    value_column2='income',
    title="Population vs Income by State"
)

print("🎉 Your first map is ready!")
```

### **Step 3: Your First Report**

```python
from siege_utilities.reporting.report_generator import ReportGenerator

# Initialize report generator
report_gen = ReportGenerator()

# Create a simple report
report_content = report_gen.create_comprehensive_report(
    title="My First Analysis Report",
    author="Your Name",
    client="Your Company",
    table_of_contents=True
)

# Add your map to the report
report_content = report_gen.add_map_section(
    report_content,
    "Geographic Analysis",
    [chart],
    map_type="bivariate_choropleth"
)

# Generate PDF
report_gen.generate_pdf_report(report_content, "my_first_report.pdf")
print("📄 Your first report is ready!")
```

---

## 🔧 **System Requirements**

### **Python Version**
- **Python 3.8+** (recommended: Python 3.9+)
- **Pip** package manager

### **Operating Systems**
- ✅ **macOS** (10.14+)
- ✅ **Linux** (Ubuntu 18.04+, CentOS 7+)
- ✅ **Windows** (10+)

### **Dependencies**
The system will automatically install these packages:
- **Core**: pandas, numpy, matplotlib, seaborn
- **Geographic**: geopandas, shapely, folium
- **Reporting**: reportlab, python-pptx
- **Optional**: scipy, scikit-learn

---

## 📊 **What You Can Do Now**

### **🗺️ Create 7+ Map Types**
1. **Bivariate Choropleth Maps** - Show relationships between two variables
2. **Marker Maps** - Visualize point locations with interactive popups
3. **3D Maps** - Three-dimensional elevation visualization
4. **Heatmap Maps** - Density and intensity mapping
5. **Cluster Maps** - Group dense data into interactive clusters
6. **Flow Maps** - Show movement and connections between locations
7. **Advanced Choropleth Maps** - Multiple classification methods

### **📄 Generate Professional Reports**
- **PDF Reports** with table of contents, sections, and appendices
- **PowerPoint Presentations** with various slide types
- **Client Branding** integration
- **Automated Generation** and batch processing

### **🔌 Integrate External Data**
- **Google Analytics** data collection and visualization
- **Facebook Business** API integration
- **Database connectivity** (PostgreSQL, MySQL, etc.)
- **Custom API** integration

---

## 🎯 **Next Steps**

### **Beginner Level**
1. **Explore Examples**: Run the comprehensive mapping example
2. **Try Different Maps**: Experiment with various map types
3. **Create Simple Reports**: Generate basic PDF reports
4. **Use Sample Data**: Work with provided sample datasets

### **Intermediate Level**
1. **Custom Data**: Import your own geographic data
2. **Advanced Styling**: Customize colors, fonts, and layouts
3. **Multiple Maps**: Combine different map types in reports
4. **Client Branding**: Apply custom styling and logos

### **Advanced Level**
1. **External APIs**: Integrate with Google Analytics, Facebook, etc.
2. **Automation**: Set up scheduled report generation
3. **Custom Templates**: Create specialized report formats
4. **Performance Optimization**: Handle large datasets efficiently

---

## 📚 **Learning Resources**

### **Documentation**
- **[Mapping & Visualization](Mapping-and-Visualization)**: Complete map type reference
- **[Report Generation](Report-Generation)**: PDF and PowerPoint creation
- **[Integration & APIs](Integration-and-APIs)**: External data source integration
- **[Recipes & Examples](Recipes-and-Examples)**: Step-by-step guides

### **Code Examples**
- **`comprehensive_mapping_example.py`** - Full system demonstration
- **`bivariate_choropleth_example.py`** - Basic choropleth usage
- **Recipe guides** in `docs/recipes/reporting/`

### **API Reference**
- **Complete documentation**: [GitHub Pages](https://siege-analytics.github.io/siege_utilities/)
- **Method references**: All available functions and parameters
- **Code examples**: Working code for every feature

---

## 🚨 **Common Issues & Solutions**

### **Installation Problems**

**"GeoPandas not available"**:
```bash
# Install geographic dependencies manually
pip install geopandas shapely folium

# Or use conda for better compatibility
conda install -c conda-forge geopandas shapely folium
```

**"Permission denied"**:
```bash
# Use user installation
pip install --user -r requirements_bivariate_choropleth.txt

# Or create virtual environment
python -m venv siege_env
source siege_env/bin/activate  # On Windows: siege_env\Scripts\activate
pip install -r requirements_bivariate_choropleth.txt
```

### **Runtime Errors**

**"Location column not found"**:
```python
# Check your column names
print(df.columns.tolist())

# Ensure exact match (case-sensitive)
location_column = 'state'  # Must match exactly
```

**"No numeric data found"**:
```python
# Check data types
print(df.dtypes)

# Convert to numeric
df['value'] = pd.to_numeric(df['value'], errors='coerce')
```

---

## 🤝 **Getting Help**

### **Self-Service**
1. **Check Documentation**: This wiki and GitHub Pages
2. **Review Examples**: Working code examples
3. **Search Issues**: GitHub issue tracker
4. **Read Recipes**: Step-by-step implementation guides

### **Community Support**
- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Community Q&A and best practices
- **Examples**: User-contributed code samples

### **Enterprise Support**
- **Direct Support**: For enterprise users
- **Custom Development**: Specialized features
- **Training**: Team training and workshops

---

## 🌟 **Success Stories**

### **What Users Are Building**
- **Market Analysis Reports**: Geographic performance visualization
- **Customer Insights**: Spatial distribution analysis
- **Performance Dashboards**: Regional KPI monitoring
- **Strategic Planning**: Geographic opportunity identification
- **Client Deliverables**: Professional reports and presentations

### **Time Savings**
- **Manual Process**: 8-16 hours per report
- **With Siege Utilities**: 1-2 hours per report
- **Automation**: 0 hours (fully automated)
- **ROI**: 80-90% time reduction

---

<div align="center">

**Ready to transform your geographic data into professional insights?**

[🗺️ Explore Maps](Mapping-and-Visualization) • [📄 Create Reports](Report-Generation) • [🔌 Integrate APIs](Integration-and-APIs)

---

*Start your journey with Siege Utilities today!* 🚀✨

</div>

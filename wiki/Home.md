# 🚀 Siege Utilities Wiki

<div align="center">

![Siege Analytics Logo](https://img.shields.io/badge/Siege%20Analytics-Professional%20Analytics-blue?style=for-the-badge&logo=analytics)

**Enterprise-Grade Python Utilities for Geographic Analysis & Professional Reporting**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Documentation](https://img.shields.io/badge/Docs-GitHub%20Pages-blue.svg)](https://siege-analytics.github.io/siege_utilities/)
[![Issues](https://img.shields.io/badge/Issues-GitHub-orange.svg)](https://github.com/siege-analytics/siege_utilities/issues)

</div>

---

## 🎯 **What is Siege Utilities?**

Siege Utilities is a comprehensive Python package that provides **enterprise-grade capabilities** for geographic data analysis, professional report generation, and business intelligence. Built with modern Python practices and designed for production use, it transforms raw data into actionable insights through sophisticated mapping and reporting systems.

---

## 🌟 **Key Capabilities**

### 🗺️ **Advanced Geographic Visualization**
- **7+ Map Types**: Choropleth, marker, 3D, heatmap, cluster, and flow maps
- **Bivariate Analysis**: Sophisticated two-variable geographic correlation mapping
- **Interactive Maps**: Folium-based interactive visualizations with popups and controls
- **Professional Output**: Publication-quality static maps for reports and presentations

### 📄 **Comprehensive Reporting System**
- **PDF Generation**: Professional reports with TOC, sections, and appendices
- **PowerPoint Integration**: Automated presentation creation with various slide types
- **Client Branding**: Custom styling and professional appearance
- **Multiple Formats**: Support for various output types and layouts

### 🔌 **Enterprise Integration**
- **External APIs**: Google Analytics, Facebook Business, custom APIs
- **Database Connectivity**: PostgreSQL, MySQL, and other database systems
- **Data Processing**: Pandas, Spark, and custom data pipeline support
- **Automation**: Scheduled reporting and batch processing capabilities

---

## 🚀 **Quick Start**

### **Installation**
```bash
# Clone the repository
git clone https://github.com/siege-analytics/siege_utilities.git

# Install dependencies
pip install -r siege_utilities/reporting/requirements_bivariate_choropleth.txt

# Install the package
pip install -e .
```

### **Basic Usage**
```python
from siege_utilities.reporting.chart_generator import ChartGenerator
import pandas as pd

# Initialize chart generator
chart_gen = ChartGenerator()

# Create a bivariate choropleth map
data = {
    'state': ['California', 'Texas', 'New York'],
    'population': [39512223, 28995881, 19453561],
    'income': [75235, 64034, 72741]
}
df = pd.DataFrame(data)

chart = chart_gen.create_bivariate_choropleth_matplotlib(
    data=df,
    location_column='state',
    value_column1='population',
    value_column2='income',
    title="Population vs Income by State"
)
```

---

## 📚 **Documentation Sections**

### **🗺️ [Mapping & Visualization](Mapping-and-Visualization)**
- Bivariate choropleth maps
- Marker maps and clustering
- 3D elevation visualization
- Heatmaps and flow maps
- Advanced classification methods

### **📄 [Report Generation](Report-Generation)**
- PDF report creation
- PowerPoint presentation generation
- Document structure and organization
- Client branding and customization

### **🔌 [Integration & APIs](Integration-and-APIs)**
- Google Analytics integration
- Facebook Business API
- Database connectivity
- Custom API integration

### **📖 [Recipes & Examples](Recipes-and-Examples)**
- Step-by-step implementation guides
- Working code examples
- Best practices and patterns
- Troubleshooting guides

### **🏗️ [Architecture & Development](Architecture-and-Development)**
- System architecture overview
- Development setup and testing
- Contributing guidelines
- Performance optimization

---

## 🎨 **Professional Features**

<div align="center">

| Feature | Description | Benefit |
|---------|-------------|---------|
| 🗺️ **Multiple Map Types** | 7+ visualization methods | Comprehensive geographic analysis |
| 📊 **Professional Reports** | PDF with TOC and sections | Publication-ready outputs |
| 🎯 **Client Branding** | Custom styling and logos | Professional appearance |
| 🔄 **Automation** | Scheduled and batch processing | Time-saving workflows |
| 📈 **Scalability** | Large dataset handling | Enterprise-grade performance |

</div>

---

## 🚀 **Use Cases**

### **Business Intelligence**
- **Market Analysis**: Geographic performance visualization
- **Customer Insights**: Spatial distribution analysis
- **Performance Tracking**: Regional KPI monitoring
- **Strategic Planning**: Geographic opportunity identification

### **Client Services**
- **Professional Reports**: Publication-quality deliverables
- **Presentations**: Automated PowerPoint generation
- **Data Visualization**: Interactive and static maps
- **Custom Analysis**: Tailored geographic insights

### **Research & Analytics**
- **Academic Research**: Publication-quality visualizations
- **Data Science**: Advanced spatial analysis
- **Government**: Policy and planning support
- **Non-profit**: Impact assessment and reporting

---

## 🔧 **Technical Excellence**

- **Modern Python**: Type hints, async support, and best practices
- **Modular Design**: Easy maintenance and extension
- **Comprehensive Testing**: Full test suite with coverage reporting
- **Performance Optimized**: Efficient data processing and visualization
- **Production Ready**: Enterprise-grade reliability and error handling

---

## 🤝 **Community & Support**

### **Getting Help**
- 📖 **Documentation**: Comprehensive guides and references
- 🐛 **Issues**: GitHub issue tracking and bug reports
- 💬 **Discussions**: Community forums and Q&A
- 📧 **Support**: Direct support for enterprise users

### **Contributing**
- 🚀 **Feature Requests**: Suggest new capabilities
- 🐛 **Bug Reports**: Help improve reliability
- 📚 **Documentation**: Enhance guides and examples
- 💻 **Code Contributions**: Submit pull requests

---

## 📊 **Project Status**

<div align="center">

| Component | Status | Version |
|-----------|--------|---------|
| **Core Utilities** | ✅ Production Ready | v1.0 |
| **Mapping System** | ✅ Production Ready | v1.0 |
| **Reporting System** | ✅ Production Ready | v1.0 |
| **API Integration** | ✅ Production Ready | v1.0 |
| **Documentation** | ✅ Comprehensive | v1.0 |

</div>

---

## 🌟 **Why Choose Siege Utilities?**

- **🎯 Professional Quality**: Enterprise-grade capabilities
- **🚀 Time Savings**: Automated workflows and batch processing
- **🔧 Flexibility**: Customizable for specific business needs
- **📈 Scalability**: Handles large datasets efficiently
- **💼 Business Ready**: Professional outputs for stakeholders
- **🆓 Open Source**: Free to use and modify

---

<div align="center">

**Ready to transform your geographic data into professional insights?**

[🚀 Get Started](Getting-Started) • [📚 View Documentation](https://siege-analytics.github.io/siege_utilities/) • [💻 View Source](https://github.com/siege-analytics/siege_utilities)

---

*Built with ❤️ by the Siege Analytics Team*

</div>

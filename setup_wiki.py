#!/usr/bin/env python3
"""
GitHub Wiki Setup Script for Siege Utilities

This script sets up a professional GitHub wiki with Siege branding,
comprehensive documentation, and proper structure.

Usage:
    python setup_wiki.py
"""

import os
import subprocess
import shutil
from pathlib import Path

def run_command(command, cwd=None):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=cwd, 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {command}")
        print(f"Error: {e.stderr}")
        return None

def setup_wiki_repository():
    """Set up the GitHub wiki repository."""
    
    print("🚀 Setting up GitHub Wiki for Siege Utilities...")
    
    # Check if we're in the right directory
    if not Path("siege_utilities").exists():
        print("❌ Please run this script from the siege_utilities root directory")
        return False
    
    # Create wiki directory if it doesn't exist
    wiki_dir = Path("wiki")
    if wiki_dir.exists():
        print("📁 Wiki directory already exists, cleaning...")
        shutil.rmtree(wiki_dir)
    
    wiki_dir.mkdir(exist_ok=True)
    
    # Copy wiki files
    print("📋 Copying wiki files...")
    
    # Copy all wiki markdown files
    wiki_files = [
        "Home.md",
        "Getting-Started.md", 
        "Mapping-and-Visualization.md",
        "Report-Generation.md"
    ]
    
    for file_name in wiki_files:
        source_path = Path(f"siege_utilities/reporting/wiki/{file_name}")
        if source_path.exists():
            shutil.copy2(source_path, wiki_dir / file_name)
            print(f"✅ Copied {file_name}")
        else:
            print(f"⚠️  Warning: {file_name} not found")
    
    # Create additional wiki pages
    create_additional_wiki_pages(wiki_dir)
    
    # Initialize git repository
    print("🔧 Initializing git repository...")
    run_command("git init", cwd=wiki_dir)
    
    # Add all files
    run_command("git add .", cwd=wiki_dir)
    
    # Initial commit
    commit_message = "Initial wiki setup with Siege branding and comprehensive documentation"
    run_command(f'git commit -m "{commit_message}"', cwd=wiki_dir)
    
    print("✅ Wiki repository initialized successfully!")
    print("\n📋 Next steps:")
    print("1. Create a new repository on GitHub named 'siege_utilities.wiki'")
    print("2. Add the remote origin:")
    print("   cd wiki")
    print("   git remote add origin https://github.com/siege-analytics/siege_utilities.wiki.git")
    print("3. Push to GitHub:")
    print("   git push -u origin main")
    
    return True

def create_additional_wiki_pages(wiki_dir):
    """Create additional wiki pages for completeness."""
    
    # Create Integration & APIs page
    integration_content = """# 🔌 Integration & APIs

<div align="center">

**Connect with External Data Sources and APIs**

![Integration](https://img.shields.io/badge/Integration-External%20APIs-green?style=for-the-badge&logo=api)

</div>

---

## 🎯 **Overview**

Siege Utilities provides seamless integration with external data sources, APIs, and databases, enabling you to create comprehensive geographic analysis from multiple data streams.

---

## 🚀 **Quick Start**

### **Google Analytics Integration**
```python
from siege_utilities.analytics.google_analytics import GoogleAnalyticsConnector

# Initialize connector
ga_connector = GoogleAnalyticsConnector(
    credentials_path='credentials.json',
    property_id='your_property_id'
)

# Retrieve geographic data
ga_data = ga_connector.batch_retrieve_ga_data(
    metrics=['sessions', 'bounce_rate'],
    dimensions=['country', 'region'],
    date_range=['2023-01-01', '2023-12-31']
)
```

### **Facebook Business Integration**
```python
from siege_utilities.analytics.facebook_business import FacebookBusinessConnector

# Initialize connector
fb_connector = FacebookBusinessConnector(
    access_token='your_access_token',
    app_id='your_app_id',
    app_secret='your_app_secret'
)

# Retrieve advertising data
fb_data = fb_connector.batch_retrieve_facebook_data(
    metrics=['impressions', 'clicks', 'spend'],
    breakdowns=['country', 'region']
)
```

---

## 📚 **Available Integrations**

- **Google Analytics**: Website performance and geographic traffic
- **Facebook Business**: Advertising performance and audience insights
- **Database Systems**: PostgreSQL, MySQL, and other databases
- **Custom APIs**: RESTful API integration
- **File Systems**: CSV, Excel, and other data formats

---

## 🔧 **Advanced Features**

- **Batch Processing**: Handle large datasets efficiently
- **Real-time Updates**: Live data integration
- **Error Handling**: Robust failure recovery
- **Performance Optimization**: Caching and optimization
- **Custom Connectors**: Extend for your specific needs

---

<div align="center">

**Ready to integrate your data sources?**

[🗺️ Create Maps](Mapping-and-Visualization) • [📄 Generate Reports](Report-Generation) • [📖 View Examples](Recipes-and-Examples)

---

*Connect, analyze, and visualize with Siege Utilities* 🔌✨

</div>
"""
    
    with open(wiki_dir / "Integration-and-APIs.md", "w") as f:
        f.write(integration_content)
    
    # Create Recipes & Examples page
    recipes_content = """# 📖 Recipes & Examples

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
        f"daily_report_{time.strftime('%Y%m%d')}.pdf"
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
"""
    
    with open(wiki_dir / "Recipes-and-Examples.md", "w") as f:
        f.write(recipes_content)
    
    # Create Architecture & Development page
    architecture_content = """# 🏗️ Architecture & Development

<div align="center">

**System Architecture, Development Setup, and Contributing Guidelines**

![Architecture](https://img.shields.io/badge/Architecture-System%20Design-blue?style=for-the-badge&logo=architecture)

</div>

---

## 🎯 **Overview**

Siege Utilities is built with modern Python practices, modular architecture, and enterprise-grade reliability. This section covers the system design, development setup, and how to contribute to the project.

---

## 🏗️ **System Architecture**

### **Core Components**

```
siege_utilities/
├── reporting/           # Reporting and visualization system
│   ├── chart_generator.py      # Map and chart creation
│   ├── report_generator.py     # PDF report generation
│   ├── powerpoint_generator.py # PowerPoint creation
│   └── client_branding.py     # Branding and styling
├── analytics/           # External API integrations
│   ├── google_analytics.py    # Google Analytics connector
│   └── facebook_business.py   # Facebook Business API
├── config/              # Configuration management
│   ├── clients.py             # Client profile management
│   ├── connections.py         # Database and API connections
│   └── databases.py           # Database connectivity
└── core/                # Core utility functions
    ├── logging.py             # Logging and monitoring
    ├── string_utils.py        # String manipulation
    └── file_operations.py     # File handling utilities
```

### **Design Principles**

1. **Modularity**: Independent, reusable components
2. **Extensibility**: Easy to add new features
3. **Reliability**: Robust error handling and validation
4. **Performance**: Efficient data processing and visualization
5. **Maintainability**: Clean code and comprehensive testing

---

## 🔧 **Development Setup**

### **Prerequisites**
- **Python 3.8+** (recommended: 3.9+)
- **Git** for version control
- **Virtual environment** for dependency isolation

### **Setup Steps**

```bash
# Clone repository
git clone https://github.com/siege-analytics/siege_utilities.git
cd siege_utilities

# Create virtual environment
python -m venv siege_env
source siege_env/bin/activate  # On Windows: siege_env\Scripts\activate

# Install development dependencies
pip install -r requirements_bivariate_choropleth.txt
pip install -r test_requirements.txt

# Install package in development mode
pip install -e .

# Run tests
python -m pytest tests/
```

### **Development Tools**
- **Pytest**: Testing framework
- **Black**: Code formatting
- **Flake8**: Linting and style checking
- **MyPy**: Type checking
- **Pre-commit**: Git hooks for quality

---

## 🧪 **Testing & Quality**

### **Test Structure**
```
tests/
├── conftest.py                 # Test configuration
├── test_chart_generator.py     # Chart generation tests
├── test_report_generator.py    # Report generation tests
├── test_integration.py         # Integration tests
└── test_performance.py         # Performance tests
```

### **Running Tests**
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_chart_generator.py

# Run with coverage
python -m pytest --cov=siege_utilities

# Run performance tests
python -m pytest tests/test_performance.py -m "performance"
```

### **Code Quality**
```bash
# Format code
black siege_utilities/

# Check style
flake8 siege_utilities/

# Type checking
mypy siege_utilities/

# Run pre-commit hooks
pre-commit run --all-files
```

---

## 🚀 **Contributing Guidelines**

### **How to Contribute**

1. **Fork the Repository**: Create your own fork
2. **Create Feature Branch**: `git checkout -b feature/amazing-feature`
3. **Make Changes**: Implement your feature or fix
4. **Add Tests**: Include tests for new functionality
5. **Run Tests**: Ensure all tests pass
6. **Submit Pull Request**: Create PR with clear description

### **Code Standards**

**Python Style**:
- Follow PEP 8 guidelines
- Use type hints for all functions
- Include comprehensive docstrings
- Write clear, readable code

**Documentation**:
- Update relevant documentation
- Include code examples
- Add to appropriate recipe guides
- Update API reference

**Testing**:
- Maintain high test coverage
- Include edge case testing
- Add performance tests for critical functions
- Ensure backward compatibility

### **Pull Request Process**

1. **Clear Description**: Explain what and why
2. **Related Issues**: Link to relevant issues
3. **Testing**: Show test results and coverage
4. **Documentation**: Update docs and examples
5. **Review**: Address reviewer feedback

---

## 🔍 **Performance & Optimization**

### **Performance Monitoring**
```python
import time
import cProfile
import pstats

def profile_function(func, *args, **kwargs):
    """Profile function performance."""
    profiler = cProfile.Profile()
    profiler.enable()
    
    start_time = time.time()
    result = func(*args, **kwargs)
    end_time = time.time()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)
    
    print(f"Execution time: {end_time - start_time:.4f} seconds")
    return result
```

### **Optimization Strategies**

1. **Data Processing**:
   - Use efficient data structures
   - Implement chunked processing
   - Cache frequently used data
   - Optimize memory usage

2. **Visualization**:
   - Sample large datasets
   - Use appropriate chart types
   - Optimize rendering settings
   - Implement lazy loading

3. **Report Generation**:
   - Stream large documents
   - Use efficient templates
   - Optimize image compression
   - Implement parallel processing

---

## 🔒 **Security & Best Practices**

### **Security Guidelines**
1. **API Keys**: Never commit credentials
2. **Data Validation**: Validate all inputs
3. **Error Handling**: Don't expose sensitive information
4. **Dependencies**: Keep dependencies updated

### **Best Practices**
1. **Logging**: Use appropriate log levels
2. **Error Handling**: Graceful failure recovery
3. **Configuration**: Use environment variables
4. **Documentation**: Keep docs updated

---

## 📚 **Additional Resources**

- **[GitHub Repository](https://github.com/siege-analytics/siege_utilities)**: Source code and issues
- **[Documentation](https://siege-analytics.github.io/siege_utilities/)**: Complete API reference
- **[Issues](https://github.com/siege-analytics/siege_utilities/issues)**: Bug reports and feature requests
- **[Discussions](https://github.com/siege-analytics/siege_utilities/discussions)**: Community Q&A

---

<div align="center">

**Ready to contribute to Siege Utilities?**

[🚀 Get Started](Getting-Started) • [📖 View Examples](Recipes-and-Examples) • [🗺️ Explore Features](Mapping-and-Visualization)

---

*Build the future of geographic analytics with us* 🏗️✨

</div>
"""
    
    with open(wiki_dir / "Architecture-and-Development.md", "w") as f:
        f.write(architecture_content)
    
    print("✅ Created additional wiki pages:")
    print("   - Integration-and-APIs.md")
    print("   - Recipes-and-Examples.md") 
    print("   - Architecture-and-Development.md")

if __name__ == "__main__":
    setup_wiki_repository()

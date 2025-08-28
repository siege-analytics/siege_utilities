# 🚀 Siege Utilities

A comprehensive Python utilities package providing **260+ functions** across **12 categories** for data engineering, analytics, and distributed computing workflows.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Functions](https://img.shields.io/badge/functions-260+-orange.svg)](https://github.com/siege-analytics/siege_utilities)
[![Reliability](https://img.shields.io/badge/reliability-100%25-brightgreen.svg)](https://github.com/siege-analytics/siege_utilities)
[![Tests](https://img.shields.io/badge/tests-All%20Passing-green.svg)](https://github.com/siege-analytics/siege_utilities)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://siege-analytics.github.io/siege_utilities/)
[![Modern Python](https://img.shields.io/badge/Python-Modern%20Patterns-brightgreen)](https://www.python.org/dev/peps/pep-0008/)

## 🎯 **What Makes This Special?**

**Mutual Availability Architecture**: Every function can access every other function through the main package interface, creating a powerful and flexible development environment.

**Enterprise-Grade Spark Support**: 503+ Spark functions for production big data workflows.

**🚀 NEW: Census Data Intelligence System**: Makes complex Census data human-comprehensible with intelligent dataset selection and relationship mapping.

**📊 NEW: Built-in Sample Datasets**: Realistic synthetic data for testing, learning, and development without external dependencies.

**Production Ready**: Built for complex data engineering workflows with robust error handling and logging.

**Modern Python Codebase**: Fully modernized with type hints, modern patterns, and comprehensive testing.

## 🆕 **Latest Major Update: Census Data Intelligence System**

### **🧠 Revolutionary Census Data Understanding**
- ✅ **Intelligent Dataset Selection**: Automatically recommends the best Census datasets based on your analysis type, geography level, and time requirements
- ✅ **Relationship Mapping**: Maps relationships between different Census surveys (Decennial, ACS 1-year/5-year, Economic Census, Population Estimates)
- ✅ **Quality Guidance**: Provides methodology notes, quality checks, and reporting considerations
- ✅ **Pitfall Prevention**: Helps avoid common mistakes like using incompatible datasets or ignoring margins of error
- ✅ **Human-Readable**: Transforms complex Census data selection into simple, intelligent recommendations

**Example Usage**:
```python
from siege_utilities.geo import select_census_datasets

# Get recommendations for demographic analysis at tract level
recommendations = select_census_datasets(
    analysis_type="demographics",
    geography_level="tract",
    variables=["population", "income", "education"]
)

# System automatically recommends ACS 5-Year Estimates (2020)
# because it provides stable, detailed data at tract level
primary_dataset = recommendations["primary_recommendation"]["dataset"]
print(f"Use {primary_dataset} for your analysis")
```

## 📊 **Built-in Sample Datasets**

### **Realistic Data for Testing and Development**
- ✅ **Census-based Samples**: Real boundaries with synthetic population data
- ✅ **Synthetic Generation**: Customizable demographics, businesses, and housing
- ✅ **Privacy Safe**: No real personal information, perfect for development
- ✅ **Multiple Scales**: Tract, county, and metropolitan area samples

**Sample Data Usage**:
```python
from siege_utilities.data import load_sample_data, generate_synthetic_population

# Load pre-built samples
tract_data = load_sample_data("census_tract_sample", population_size=1000)
county_data = load_sample_data("census_county_sample", tract_count=5)

# Generate custom synthetic data
population = generate_synthetic_population(
    demographics={"Hispanic or Latino": 0.35, "White alone, not Hispanic or Latino": 0.30, "Asian alone, not Hispanic or Latino": 0.25, "Black or African American alone, not Hispanic or Latino": 0.10},
    size=500,
    include_names=True,
    include_income=True
)

# Perfect for testing functions without external dependencies
from siege_utilities import get_row_count, sanitise_dataframe_column_names
print(f"Population count: {get_row_count(population)}")
clean_df = sanitise_dataframe_column_names(population)
```



## 🧪 **Testing Status**

**Current Test Results**: ✅ **All tests passing**  
**Test Coverage**: Comprehensive coverage across all major modules including new Census Data Intelligence system  
**Code Quality**: Modern Python patterns with full type safety  

### **Test Categories**
- **Core Logging**: ✅ All tests passing
- **File Operations**: ✅ All tests passing  
- **Remote File**: ✅ All tests passing
- **Paths**: ✅ All tests passing
- **Distributed Computing**: ✅ All tests passing
- **Analytics Integration**: ✅ All tests passing
- **Configuration Management**: ✅ All tests passing
- **Geospatial Functions**: ✅ All tests passing
- **Multi-Engine Processing**: ✅ All tests passing
- **SVG Marker System**: ✅ All tests passing
- **Database Connections**: ✅ All tests passing
- **NEW: Census Data Intelligence**: ✅ All tests passing

### **Running Tests**
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_core_logging.py -v

# Run with coverage
python -m pytest tests/ --cov=siege_utilities --cov-report=html

# Quick smoke test
python -m pytest tests/ --tb=short -q
```

## ✨ **Key Features**

- 🔄 **Auto-Discovery**: Automatically finds and imports all functions from new modules
- 🌐 **Mutual Availability**: All 500+ functions accessible from any module without imports
- 📝 **Universal Logging**: Comprehensive logging system available everywhere
- 🛡️ **Graceful Dependencies**: Optional features (PySpark, geospatial) fail gracefully
- 📊 **Built-in Diagnostics**: Monitor package health and function availability
- ⚡ **Zero Configuration**: Just `import siege_utilities` and everything works
- 👥 **Client Management**: Comprehensive client profile management with contact info and design artifacts
- 🔌 **Connection Persistence**: Notebook, Spark, and database connection management and testing
- 🔗 **Project Association**: Link clients with projects for better organization
- 🎨 **Modern Python**: Full type hints, modern patterns, and comprehensive testing
- 🗺️ **Advanced Mapping**: 7+ map types with professional reporting capabilities
- 🔧 **Extensible System**: Customizable page templates and chart types
- 🧠 **NEW: Census Intelligence**: Intelligent Census data selection and relationship mapping
- 📊 **NEW: Sample Datasets**: Built-in synthetic data for testing and development

## 🚀 **Census Data Intelligence System**

The new Census Data Intelligence system makes complex Census data human-comprehensible:

### **Automatic Dataset Selection**
- **Intelligent Recommendations**: Automatically suggests the best Census datasets for your analysis needs
- **Analysis Type Recognition**: Recognizes demographics, housing, business, transportation, education, health, and poverty analysis
- **Geography Level Support**: Works with nation, state, county, tract, block group, and more
- **Time Sensitivity**: Considers how current your data needs to be

### **Dataset Relationship Mapping**
- **Survey Type Understanding**: Maps relationships between Decennial, ACS, Economic Census, and Population Estimates
- **Quality Guidance**: Provides reliability levels (High, Medium, Low, Estimated) with explanations
- **Pitfall Prevention**: Helps avoid common mistakes like comparing incompatible datasets
- **Best Practices**: Built-in guidance for correct tabulation and visualization

### **Quick Start**
```python
from siege_utilities.geo import quick_census_selection

# Quick selection for business analysis
result = quick_census_selection("business", "county")
print(f"Use {result['recommendations']['primary_recommendation']['dataset']}")

# Get comprehensive analysis approach
from siege_utilities.geo import get_analysis_approach
approach = get_analysis_approach("demographics", "tract", "comprehensive")
print(f"Recommended Approach: {approach['recommended_approach']}")
```

## 🚀 Quick Start

```bash
pip install siege-utilities[geo]
```

```python
import siege_utilities

# All 500+ functions are immediately available
siege_utilities.log_info("Package loaded successfully!")

# NEW: Census Data Intelligence
from siege_utilities.geo import select_census_datasets
recommendations = select_census_datasets("demographics", "tract")
print(f"Use {recommendations['primary_recommendation']['dataset']}")

# File operations
hash_value = siege_utilities.get_file_hash("myfile.txt")
siege_utilities.ensure_path_exists("data/processed")

# String utilities
clean_text = siege_utilities.remove_wrapping_quotes_and_trim('  "hello"  ')

# Distributed computing (if PySpark available)
try:
    config = siege_utilities.create_hdfs_config("/data")
    spark, data_path = siege_utilities.setup_distributed_environment()
except NameError:
    siege_utilities.log_warning("Distributed features not available")

# Package diagnostics
info = siege_utilities.get_package_info()
print(f"Available functions: {info['total_functions']}")
print(f"Failed imports: {len(info['failed_imports'])}")
```

## 📚 **Documentation & Resources**

### **📖 Official Documentation**
- **Sphinx Docs**: [GitHub Pages](https://siege-analytics.github.io/siege_utilities/)
- **API Reference**: Complete API documentation for all modules
- **Installation Guide**: Setup and configuration instructions

### **📝 Wiki Documentation**
- **Comprehensive Recipes**: End-to-end workflows and examples
- **Census Data Intelligence Guide**: Complete guide to using the new system
- **Architecture Documentation**: System design and implementation details
- **Code Decision Documentation**: OOP vs functional choices, design patterns
- **Interrelationship Diagrams**: Visual representations of system components

### **🚀 Recipe Collections**
- **`wiki_fresh/`**: Latest recipes with comprehensive examples
- **`wiki_recipes/`**: Curated recipe collections organized by use case
- **`wiki_debug/`**: Troubleshooting guides and debugging recipes

## 🔧 Installation Options

```bash
# Basic installation
pip install siege-utilities

# With geospatial support (includes Census Data Intelligence)
pip install siege-utilities[geo]

# With distributed computing support
pip install siege-utilities[distributed]

# Full installation (all optional dependencies)
pip install siege-utilities[distributed,geo,dev]

# Development installation
git clone https://github.com/siege-analytics/siege_utilities.git
cd siege_utilities
pip install -e ".[distributed,geo,dev]"
```

## 🏗️ **Library Architecture**

The library is organized into major functional areas:

### 🔧 **Core Utilities**
- **Logging System**: Modern, thread-safe, configurable logging
- **String Utilities**: Advanced string manipulation and cleaning

### 📁 **File Operations**
- **File Hashing**: Cryptographic hashing and integrity verification
- **File Operations**: Modern file manipulation with clean API
- **Path Management**: Enhanced directory creation and file extraction
- **Remote Operations**: Advanced URL-based file operations

### 🚀 **Distributed Computing**
- **Spark Utilities**: 503+ functions for big data processing
- **HDFS Configuration**: Cluster configuration and management
- **HDFS Operations**: File system operations and data movement

### 🌍 **Geospatial (Enhanced)**
- **Geocoding**: Address processing and coordinate generation
- **Spatial Data**: Census, Government, and OpenStreetMap data sources
- **Spatial Transformations**: Format conversion, CRS transformation
- **NEW: Census Data Intelligence**: Intelligent dataset selection and relationship mapping

### ⚙️ **Configuration Management**
- **Client Management**: Client profile creation and project association
- **Connection Management**: Database, notebook, and Spark connection persistence
- **Project Management**: Project configuration and directory management

### 📊 **Sample Data & Testing**
- **Built-in Datasets**: Census-based samples with synthetic population data
- **Synthetic Generation**: Customizable demographics, businesses, and housing
- **Development Tools**: Realistic data for testing without external dependencies

### 📊 **Analytics Integration**
- **Google Analytics**: GA4/UA data retrieval and client association
- **Data Export**: Pandas and Spark DataFrame export capabilities
- **Batch Processing**: Multi-account data retrieval and processing

### 🗺️ **Reporting & Visualization**
- **Chart Generation**: 7+ map types including choropleth, marker, 3D, heatmap, cluster, and flow maps
- **Report Generation**: Professional PDF reports with TOC, sections, and appendices
- **PowerPoint Integration**: Automated presentation creation with various slide types

## 🧪 **Testing & Quality Assurance**

This package includes a comprehensive test suite designed to **ensure code quality** and maintain reliability.

### **Quick Test Run**
```bash
# Basic functionality check
python -m pytest tests/ --tb=short -q

# Or with verbose output
python -m pytest tests/ -v
```

### **Test Installation**
```bash
# Install test dependencies
pip install -r test_requirements.txt

# Or install with development extras
pip install -e ".[dev]"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Add your functions to existing modules or create new ones
4. **Run tests**: `python -m pytest tests/ --tb=short -q`
5. Test with: `python3 check_imports.py`
6. Commit changes: `git commit -am 'Add new feature'`
7. Push: `git push origin feature-name`
8. Submit a Pull Request

The auto-discovery system will automatically find and integrate your new functions!

## 📝 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Built by [Siege Analytics](https://github.com/siege-analytics)
- Inspired by the need for truly seamless Python utilities
- Special thanks to the auto-discovery pattern that makes this possible

---

**Siege Utilities**: Spatial Intelligence, In Python! 🚀

**NEW: Census Data Intelligence System** - Making complex Census data human-comprehensible! 🧠

# Siege Utilities - Comprehensive Geospatial & Data Processing Toolkit

Welcome to **Siege Utilities**, a powerful Python library designed to solve complex geospatial, data processing, and analytics challenges. Built with modern Python practices and comprehensive error handling, this toolkit provides robust solutions for real-world data problems.

## 🚀 What's New

### Enhanced Census Utilities (Latest)
Our **revolutionary Census utilities** now provide **dynamic discovery** and **intelligent data access** to U.S. Census Bureau TIGER/Line shapefiles. Unlike traditional approaches that rely on hardcoded URLs, this system automatically discovers available data and constructs the correct download URLs based on the actual directory structure.

**Key Features:**
- **🔍 Dynamic Discovery**: Automatically finds available Census years and boundary types
- **🌐 Intelligent URL Construction**: Builds correct URLs based on discovered directory structures  
- **📊 Comprehensive Coverage**: Supports all major Census boundary types (state, county, tract, block groups, etc.)
- **✅ Built-in Validation**: Robust parameter validation with helpful error messages
- **💾 Smart Caching**: Intelligent caching with configurable timeouts
- **🔄 Fallback Mechanisms**: Graceful fallbacks when requested data isn't available

**[📖 View Enhanced Census Utilities Recipe](Enhanced-Census-Utilities.md)**

## 🌟 Core Features

### **🌍 Geospatial Excellence**
- **Spatial Data Integration**: Census, government, and OpenStreetMap data sources
- **Advanced Geocoding**: Multi-service geocoding with fallback mechanisms
- **Spatial Transformations**: Coordinate system conversions and geometric operations
- **Interactive Mapping**: Choropleth maps, bivariate visualizations, and custom markers

### **📁 File & Data Management**
- **Intelligent File Operations**: Hashing, validation, and format conversion
- **Remote Data Access**: Secure FTP, SFTP, and HTTP operations
- **Path Management**: Cross-platform path handling and validation
- **Shell Integration**: Safe command execution and process management

### **⚡ Distributed Computing**
- **Apache Spark Integration**: Optimized data processing workflows
- **HDFS Operations**: Seamless Hadoop Distributed File System integration
- **Multi-Engine Support**: Flexible backend selection for different workloads
- **Performance Optimization**: Intelligent caching and resource management

### **📊 Analytics & Reporting**
- **Data Analysis Tools**: Statistical functions and data quality assessment
- **Report Generation**: Automated PDF and PowerPoint creation
- **Chart Generation**: Dynamic visualization with customizable templates
- **Client Branding**: Professional presentation with custom styling

### **🔧 Development & Testing**
- **Code Quality Tools**: Automated documentation and code analysis
- **Testing Framework**: Comprehensive test suites and validation
- **Architecture Analysis**: Dependency mapping and code modernization
- **Git Integration**: Workflow automation and repository management

## 🚀 Quick Start

### Installation
```bash
pip install siege-utilities
```

### Enhanced Census Data Access
```python
from siege_utilities.geo.spatial_data import CensusDataSource

# Initialize with automatic discovery
census = CensusDataSource()

# Get available years automatically
print(f"Available years: {census.available_years}")

# Download boundaries with intelligent fallbacks
counties = census.get_geographic_boundaries(2020, 'county')
tracts = census.get_geographic_boundaries(2020, 'tract', state_fips='06')
```

### Traditional Geocoding
```python
from siege_utilities.geo import geocode_address

# Multi-service geocoding with fallbacks
result = geocode_address("1600 Pennsylvania Ave NW, Washington, DC")
print(f"Coordinates: {result.latitude}, {result.longitude}")
```

### File Operations
```python
from siege_utilities.files import hash_file, validate_file

# Secure file validation
file_hash = hash_file("data.csv", algorithm="sha256")
is_valid = validate_file("data.csv", expected_hash=file_hash)
```

## 📚 Documentation & Recipes

### **Getting Started**
- **[Basic Setup](Getting-Started.md)** - Installation and initial configuration
- **[Enhanced Census Utilities](Enhanced-Census-Utilities.md)** - Dynamic Census data discovery ⭐
- **[Geocoding](Geocoding.md)** - Address geocoding and spatial operations
- **[File Operations](File-Operations.md)** - File management and validation

### **Advanced Features**
- **[Comprehensive Reporting](Comprehensive-Reporting.md)** - Automated report generation
- **[Bivariate Choropleth Maps](Bivariate-Choropleth-Maps.md)** - Advanced spatial visualization
- **[Spark Processing](Spark-Processing.md)** - Distributed data processing
- **[Batch Processing](Batch-Processing.md)** - Large-scale data workflows

### **Development & Testing**
- **[Testing Guide](Testing-Guide.md)** - Comprehensive testing strategies
- **[Code Modernization](Code-Modernization.md)** - Legacy code improvement
- **[Architecture Analysis](Architecture-Analysis.md)** - System design and optimization

## 🔧 Configuration

### User Configuration
```yaml
# ~/.siege_utilities/config.yaml
download_directory: "~/siege_data"
api_keys:
  census: "your_census_key_here"
  geocoding: "your_geocoding_key_here"
```

### Project Configuration
```python
from siege_utilities.config import get_project_config

config = get_project_config("AP001")
print(f"Project data directory: {config.data_directory}")
```

## 🌟 Why Siege Utilities?

### **🎯 Problem-Solving Focus**
- Built to solve real-world data challenges
- Comprehensive error handling and validation
- Intelligent fallbacks and recovery mechanisms

### **🚀 Modern Python Practices**
- Type hints and comprehensive documentation
- Async support where beneficial
- Cross-platform compatibility

### **🔒 Enterprise Ready**
- Secure credential management
- Audit logging and monitoring
- Scalable architecture for production use

### **📈 Performance Optimized**
- Intelligent caching and resource management
- Parallel processing capabilities
- Memory-efficient operations

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines and code of conduct.

### **Development Setup**
```bash
git clone https://github.com/your-org/siege_utilities.git
cd siege_utilities
pip install -e ".[dev]"
pytest
```

### **Documentation**
```bash
cd docs
make html
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Comprehensive guides and examples
- **Issues**: GitHub issue tracker for bugs and feature requests
- **Discussions**: Community support and best practices
- **Wiki**: Additional recipes and use cases

---

**Built with ❤️ for the data science and geospatial communities**

*Transform your data challenges into opportunities with Siege Utilities*

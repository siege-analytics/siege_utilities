# 🚀 Getting Started with Siege Utilities

<div align="center">

![Quick Start](https://img.shields.io/badge/Quick_Start-5_Minutes-blue)
![Modern Python](https://img.shields.io/badge/Python-Modern_Patterns-brightgreen)
![Zero Config](https://img.shields.io/badge/Setup-Zero_Configuration-green)

**Get up and running in minutes!** ⚡

</div>

---

## 🎯 **What You'll Learn**

By the end of this guide, you'll be able to:
- ✅ Install and configure Siege Utilities
- ✅ Import and use any of the 1147+ functions
- ✅ Understand the auto-discovery system
- ✅ Run your first spatial analysis
- ✅ Generate professional reports and maps

## 📦 **Installation**

### **Basic Installation**

```bash
# Install the core package
pip install siege-utilities

# Verify installation
python -c "import siege_utilities; print('✅ Installed successfully!')"
```

### **Installation with Extras**

```bash
# With distributed computing support (Spark, HDFS)
pip install siege-utilities[distributed]

# With geospatial support (GeoPandas, Shapely)
pip install siege-utilities[geo]

# With development tools (testing, linting)
pip install siege-utilities[dev]

# Full installation with all optional dependencies
pip install siege-utilities[distributed,geo,dev]
```

### **Development Installation**

```bash
# Clone the repository
git clone https://github.com/siege-analytics/siege_utilities.git
cd siege_utilities

# Install in development mode
pip install -e ".[distributed,geo,dev]"
```

## 🚀 **Your First Steps**

### **1. Basic Import and Usage**

```python
import siege_utilities

# All 500+ functions are immediately available!
siege_utilities.log_info("🚀 Siege Utilities loaded successfully!")

# Check what's available
info = siege_utilities.get_package_info()
print(f"Available functions: {info['total_functions']}")
print(f"Loaded modules: {info['total_modules']}")
```

### **2. Your First File Operation**

```python
import siege_utilities

# Create a directory (no import needed!)
siege_utilities.ensure_path_exists("my_project/data")

# Write some data
siege_utilities.touch_file("my_project/data/sample.txt")

# Check if it exists
if siege_utilities.file_exists("my_project/data/sample.txt"):
    print("✅ File created successfully!")
```

### **3. Your First Map**

```python
import siege_utilities
import pandas as pd

# Create sample data
data = pd.DataFrame({
    'state': ['CA', 'NY', 'TX', 'FL'],
    'value': [100, 200, 150, 300],
    'category': ['A', 'B', 'A', 'C']
})

# Generate a choropleth map (no import needed!)
map_image = siege_utilities.create_choropleth_map(
    data=data,
    location_column='state',
    value_column='value',
    map_type='choropleth',
    title='Sample US States Map'
)

print("🗺️ Map generated successfully!")
```

## 🔍 **Understanding Auto-Discovery**

### **How It Works**

Siege Utilities uses a **revolutionary auto-discovery system** that makes all functions available everywhere:

```python
# Traditional approach - lots of imports needed
from package.module1 import function_a
from package.module2 import function_b
from package.core.logging import log_info

def my_function():
    log_info("Starting process")
    result_a = function_a()
    result_b = function_b()

# Siege Utilities approach - everything just works!
import siege_utilities

def my_function():
    siege_utilities.log_info("Starting process")      # Available everywhere
    result_a = siege_utilities.function_a()           # Available everywhere
    result_b = siege_utilities.function_b()           # Available everywhere
```

### **The Magic Behind the Scenes**

1. **Phase 1**: Bootstrap core logging system
2. **Phase 2**: Import modules in dependency order
3. **Phase 3**: Auto-discover all `.py` files and subpackages
4. **Phase 4**: Inject all functions into all modules (mutual availability)
5. **Phase 5**: Provide comprehensive diagnostics

**Result**: 500+ functions accessible from anywhere with zero imports!

## 🗺️ **Your First Spatial Analysis**

### **1. Download Census Data**

```python
import siege_utilities

# Download US state boundaries from Census Bureau
states_gdf = siege_utilities.get_census_boundaries(
    geography='state',
    year=2020
)

print(f"✅ Downloaded {len(states_gdf)} states")
print(f"Columns: {list(states_gdf.columns)}")
```

### **2. Create a Professional Map**

```python
# Generate a professional choropleth map
map_image = siege_utilities.create_choropleth_map(
    data=states_gdf,
    location_column='NAME',
    value_column='ALAND',  # Land area
    map_type='choropleth',
    title='US States by Land Area',
    color_scheme='Blues',
    classification_method='quantiles'
)

print("🗺️ Professional map created!")
```

### **3. Generate a Report**

```python
# Create a professional PDF report
report = siege_utilities.create_analytics_report(
    title="US States Analysis",
    charts=[map_image],
    data_summary="Analysis of US states by land area",
    insights=[
        "Alaska has the largest land area",
        "Rhode Island has the smallest land area",
        "Land area varies significantly across states"
    ],
    recommendations=[
        "Consider population density for better context",
        "Include economic indicators for comprehensive analysis"
    ]
)

print("📊 Professional report generated!")
```

## 🔧 **Configuration Setup**

### **1. User Configuration**

Create a configuration file to customize your experience:

```python
import siege_utilities

# Set up user configuration
config = siege_utilities.create_user_config(
    username="your_name",
    email="your_email@example.com",
    github_login="your_github",
    default_download_directory="~/Downloads/siege_data",
    api_keys={
        'census': 'your_census_api_key',
        'google_analytics': 'your_ga_key'
    }
)

# Save configuration
siege_utilities.save_user_config(config)
print("✅ Configuration saved!")
```

### **2. Client Branding**

Set up professional client branding:

```python
# Create client profile with branding
client = siege_utilities.create_client_profile(
    name="Acme Corporation",
    client_id="ACME001",
    contact_info={
        "primary_contact": "John Doe",
        "email": "john@acme.com",
        "phone": "+1-555-0123"
    },
    branding={
        "primary_color": "#1f77b4",
        "secondary_color": "#ff7f0e",
        "logo_path": "path/to/logo.png",
        "font_family": "Arial"
    }
)

# Save client profile
siege_utilities.save_client_profile(client)
print("✅ Client profile created!")
```

## 🧪 **Testing Your Setup**

### **1. Run Quick Tests**

```bash
# Quick validation of all tests
python -m pytest tests/ --tb=short -q

# Expected output: 158 tests passing
```

### **2. Check Package Health**

```python
import siege_utilities

# Comprehensive package diagnostics
info = siege_utilities.get_package_info()
print(f"Total functions: {info['total_functions']}")
print(f"Loaded modules: {info['total_modules']}")
print(f"Failed imports: {len(info['failed_imports'])}")

# Check dependencies
deps = siege_utilities.check_dependencies()
print(f"PySpark available: {deps['pyspark']}")
print(f"GeoPandas available: {deps['geopandas']}")
```

### **3. Test Core Functionality**

```python
# Test logging
siege_utilities.log_info("Test message")
siege_utilities.log_warning("Test warning")
siege_utilities.log_error("Test error")

# Test file operations
siege_utilities.ensure_path_exists("test_dir")
siege_utilities.touch_file("test_dir/test.txt")
assert siege_utilities.file_exists("test_dir/test.txt")

# Clean up
siege_utilities.remove_tree("test_dir")
print("✅ Core functionality tests passed!")
```

## 🚨 **Troubleshooting**

### **Common Issues**

#### **Import Errors**
```bash
# If you get import errors, check your Python environment
python --version
pip list | grep siege

# Reinstall if needed
pip uninstall siege-utilities
pip install siege-utilities
```

#### **Missing Dependencies**
```bash
# Install missing optional dependencies
pip install geopandas shapely folium plotly

# Or install with extras
pip install siege-utilities[geo]
```

#### **Permission Issues**
```bash
# If you get permission errors on file operations
# Check your current working directory and permissions
pwd
ls -la

# Create directories in user space
mkdir -p ~/siege_workspace
cd ~/siege_workspace
```

### **Getting Help**

- **GitHub Issues**: [Report bugs](https://github.com/siege-analytics/siege_utilities/issues)
- **Documentation**: [Full API docs](https://siege-analytics.github.io/siege_utilities/)
- **Discussions**: [Community help](https://github.com/siege-analytics/siege_utilities/discussions)

## 🎯 **Next Steps**

Now that you're up and running, explore these areas:

1. **[File Operations](File-Operations)** - Master file handling and management
2. **[Mapping & Visualization](Mapping-Visualization)** - Create stunning maps and charts
3. **[Report Generation](Report-Generation)** - Generate professional reports and presentations
4. **[Spatial Data](Spatial-Data)** - Work with Census, Government, and OSM data
5. **[Testing Guide](Testing-Guide)** - Learn our comprehensive testing approach

## 🎉 **Congratulations!**

You've successfully set up Siege Utilities and are ready to unlock the power of **1147+ functions** for data engineering, analytics, and spatial intelligence!

---

<div align="center">

**Ready to explore?** 🚀

**[Next: Core Functions](Core-Functions)** → **[File Operations](File-Operations)** → **[Mapping & Visualization](Mapping-Visualization)**

</div>

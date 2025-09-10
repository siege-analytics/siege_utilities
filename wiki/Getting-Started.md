# Getting Started with Siege Utilities

## Welcome to Siege Utilities! 🚀

Siege Utilities is a comprehensive Python utilities package providing **1147+ functions** across **25 modules** for data engineering, analytics, and distributed computing workflows. This guide will help you get up and running quickly.

## What You'll Learn

- ✅ Install and configure Siege Utilities
- 🔧 Set up your development environment
- 📊 Run your first data operations
- 🗺️ Create your first visualizations
- 📈 Generate your first reports
- 🚀 Scale to advanced workflows

## Quick Installation

### Prerequisites

- **Python 3.8+** (3.9+ recommended)
- **pip** package manager
- **Git** (for development)

### Install from PyPI

```bash
# Install the latest stable version
pip install siege-utilities

# Verify installation
python -c "import siege_utilities; print('✅ Installation successful!')"
```

### Install from Source (Development)

```bash
# Clone the repository
git clone https://github.com/siege-analytics/siege_utilities.git
cd siege_utilities

# Install in development mode
pip install -e .

# Run tests to verify
pytest tests/ -v
```

### Install with UV (Recommended for Modern Development)

UV is a fast, modern Python package manager that provides better dependency resolution and faster installs:

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a new project
uv init my-siege-project
cd my-siege-project

# Add siege_utilities with all dependencies
uv add --editable ../siege_utilities

# Or install with specific extras
uv add --extra geo ../siege_utilities
uv add --extra distributed ../siege_utilities
uv add --extra all ../siege_utilities

# Verify installation
uv run python -c "import siege_utilities; print('✅ UV installation successful!')"
```

### Package Format Generation

The library includes powerful functions for modern package management:

```python
from siege_utilities.development.architecture import (
    generate_requirements_txt,
    generate_pyproject_toml,
    generate_poetry_toml,
    generate_uv_toml
)

# Generate modern package configuration files
generate_requirements_txt("setup.py", "requirements.txt")
generate_pyproject_toml("setup.py", "pyproject.toml")
generate_poetry_toml("setup.py", "pyproject_poetry.toml")
```

## Your First Steps

### 1. Basic Import and Verification

```python
import siege_utilities

# Check what's available
print(f"🚀 Siege Utilities loaded successfully!")
print(f"📊 Available functions: {len([f for f in dir(siege_utilities) if not f.startswith('_')])}")

# Test basic functionality
siege_utilities.log_info("Hello from Siege Utilities!")
```

### 2. Your First File Operation

```python
from pathlib import Path

# Create a test directory
test_dir = Path("test_siege_utilities")
test_dir.mkdir(exist_ok=True)

# Create a test file
test_file = test_dir / "hello.txt"
test_file.write_text("Hello from Siege Utilities!")

# Use Siege Utilities to check the file
file_exists = siege_utilities.file_exists(str(test_file))
file_size = siege_utilities.get_file_size(str(test_file))
line_count = siege_utilities.count_lines(str(test_file))

print(f"📁 File exists: {file_exists}")
print(f"📏 File size: {file_size} bytes")
print(f"📊 Line count: {line_count}")

# Clean up
siege_utilities.remove_tree(str(test_dir))
print("🧹 Test directory cleaned up")
```

### 3. Your First Data Analysis

```python
import pandas as pd

# Create sample data
data = {
    'name': ['Alice', 'Bob', 'Charlie', 'Diana'],
    'age': [25, 30, 35, 28],
    'city': ['New York', 'Los Angeles', 'Chicago', 'Boston'],
    'salary': [75000, 85000, 90000, 80000]
}

df = pd.DataFrame(data)
print("📊 Sample data created:")
print(df)

# Use Siege Utilities for data operations
# Save data
output_file = "sample_data.csv"
df.to_csv(output_file, index=False)

# Check file
file_info = siege_utilities.get_file_info(output_file)
print(f"\n📁 File saved: {output_file}")
print(f"📏 Size: {file_info['size']} bytes")
print(f"📅 Created: {file_info['created']}")

# Clean up
siege_utilities.delete_existing_file_and_replace_it_with_an_empty_file(output_file)
print("🧹 Sample file cleaned up")
```

## Core Concepts

### 1. Auto-Discovery System

Siege Utilities automatically discovers and makes available all functions from all modules:

```python
# All functions are available from the main package
import siege_utilities

# File operations
file_exists = siege_utilities.file_exists("example.txt")
file_size = siege_utilities.get_file_size("example.txt")

# String utilities
cleaned_text = siege_utilities.clean_string("  Hello World  ")
text_length = siege_utilities.get_string_length("Hello World")

# Logging
siege_utilities.log_info("This is an info message")
siege_utilities.log_error("This is an error message")

print("✨ All functions work without individual imports!")
```

### 2. Universal Logging

Every function has access to comprehensive logging:

```python
# Initialize logging
siege_utilities.init_logger(
    log_level="INFO",
    log_to_file=True,
    log_file="my_app.log"
)

# Use logging throughout your application
siege_utilities.log_info("Application started")
siege_utilities.log_debug("Processing data...")
siege_utilities.log_warning("Resource usage high")
siege_utilities.log_error("Connection failed")

print("📝 Check my_app.log for detailed logs")
```

### 3. Graceful Dependencies

Optional features fail gracefully when dependencies aren't available:

```python
# Try to use advanced features
try:
    # This will work if PySpark is installed
    spark_data = siege_utilities.process_spark_data(data)
    print("⚡ Spark processing successful")
except Exception as e:
    print(f"⚠️ Spark not available: {e}")
    print("💡 Install PySpark for distributed processing")

try:
    # This will work if geospatial libraries are installed
    geo_data = siege_utilities.process_geospatial_data(data)
    print("🗺️ Geospatial processing successful")
except Exception as e:
    print(f"⚠️ Geospatial libraries not available: {e}")
    print("💡 Install GeoPandas for spatial analysis")
```

## Configuration Setup

### 1. User Configuration

Create a configuration file for your preferences:

```python
# Create user configuration
config = {
    'user_info': {
        'name': 'Your Name',
        'email': 'your.email@example.com',
        'github': 'your_github_username'
    },
    'preferences': {
        'default_download_dir': '~/Downloads',
        'log_level': 'INFO',
        'theme': 'dark'
    },
    'api_keys': {
        'google_analytics': 'your_ga_key',
        'facebook_business': 'your_fb_key'
    }
}

# Save configuration
siege_utilities.save_user_config(config)
print("⚙️ User configuration saved")
```

### 2. Client Branding Setup

Set up client profiles for professional reports:

```python
from siege_utilities.config.clients import create_client_profile

# Create a client profile
client_profile = create_client_profile(
    name="Acme Corporation",
    client_id="ACME001",
    contact_info={
        "primary_contact": "John Smith",
        "email": "john@acme.com",
        "phone": "+1-555-0123"
    },
    brand_colors=["#0066CC", "#FF6600"],
    logo_path="assets/logos/acme_logo.png"
)

print(f"🏢 Client profile created: {client_profile['name']}")
```

## First Project: Data Analysis Pipeline

### Complete Example

```python
import siege_utilities
import pandas as pd
from pathlib import Path

def run_first_project():
    """Run your first complete project with Siege Utilities."""
    
    print("🚀 Starting Your First Siege Utilities Project")
    print("=" * 50)
    
    try:
        # Step 1: Setup
        print("📁 Step 1: Setting up project...")
        
        # Create project directory
        project_dir = Path("my_first_project")
        project_dir.mkdir(exist_ok=True)
        
        # Initialize logging
        siege_utilities.init_logger(
            log_level="INFO",
            log_to_file=True,
            log_file=project_dir / "project.log"
        )
        
        siege_utilities.log_info("Project started")
        print("  ✅ Project directory created")
        print("  ✅ Logging initialized")
        
        # Step 2: Create sample data
        print("\n📊 Step 2: Creating sample data...")
        
        # Generate sample sales data
        sales_data = {
            'date': pd.date_range('2024-01-01', periods=30, freq='D'),
            'product': ['Product A', 'Product B', 'Product C'] * 10,
            'quantity': [10, 15, 8, 12, 20, 5, 18, 14, 9, 16] * 3,
            'price': [25.99, 19.99, 34.99, 22.50, 15.99, 45.00, 28.75, 32.50, 18.99, 24.99] * 3,
            'region': ['North', 'South', 'East', 'West'] * 7 + ['North', 'South']
        }
        
        df = pd.DataFrame(sales_data)
        df['total_revenue'] = df['quantity'] * df['price']
        
        print(f"  ✅ Sample data created: {len(df)} rows")
        print(f"  📊 Columns: {', '.join(df.columns)}")
        
        # Step 3: Data processing
        print("\n🔧 Step 3: Processing data...")
        
        # Calculate summary statistics
        summary_stats = {
            'total_sales': df['total_revenue'].sum(),
            'avg_order_value': df['total_revenue'].mean(),
            'total_products': df['quantity'].sum(),
            'unique_products': df['product'].nunique(),
            'date_range': f"{df['date'].min().date()} to {df['date'].max().date()}"
        }
        
        print("  ✅ Summary statistics calculated")
        
        # Step 4: Save results
        print("\n💾 Step 4: Saving results...")
        
        # Save data
        data_file = project_dir / "sales_data.csv"
        df.to_csv(data_file, index=False)
        
        # Save summary
        summary_file = project_dir / "summary_report.txt"
        with open(summary_file, 'w') as f:
            f.write("SALES SUMMARY REPORT\n")
            f.write("=" * 20 + "\n\n")
            for key, value in summary_stats.items():
                f.write(f"{key.replace('_', ' ').title()}: {value}\n")
        
        print("  ✅ Data saved to CSV")
        print("  ✅ Summary report generated")
        
        # Step 5: File operations with Siege Utilities
        print("\n📁 Step 5: File operations...")
        
        # Check files
        data_exists = siege_utilities.file_exists(str(data_file))
        summary_exists = siege_utilities.file_exists(str(summary_file))
        
        data_size = siege_utilities.get_file_size(str(data_file))
        summary_size = siege_utilities.get_file_size(str(summary_file))
        
        print(f"  📊 Data file: {data_exists} ({data_size} bytes)")
        print(f"  📋 Summary file: {summary_exists} ({summary_size} bytes)")
        
        # Step 6: Generate insights
        print("\n💡 Step 6: Generating insights...")
        
        insights = []
        
        # Top performing product
        top_product = df.groupby('product')['total_revenue'].sum().idxmax()
        top_revenue = df.groupby('product')['total_revenue'].sum().max()
        insights.append(f"Top product: {top_product} (${top_revenue:,.2f})")
        
        # Best performing region
        best_region = df.groupby('region')['total_revenue'].sum().idxmax()
        region_revenue = df.groupby('region')['total_revenue'].sum().max()
        insights.append(f"Best region: {best_region} (${region_revenue:,.2f})")
        
        # Revenue trend
        daily_revenue = df.groupby('date')['total_revenue'].sum()
        trend = "increasing" if daily_revenue.iloc[-1] > daily_revenue.iloc[0] else "decreasing"
        insights.append(f"Revenue trend: {trend}")
        
        print("  ✅ Insights generated:")
        for insight in insights:
            print(f"    💡 {insight}")
        
        # Step 7: Project summary
        print("\n📊 Project Summary")
        print("=" * 20)
        print(f"Project directory: {project_dir}")
        print(f"Files created: {len(list(project_dir.glob('*')))}")
        print(f"Data processed: {len(df)} records")
        print(f"Total revenue: ${summary_stats['total_sales']:,.2f}")
        
        siege_utilities.log_info("Project completed successfully")
        print("\n🎉 Your first project completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Project failed: {e}")
        siege_utilities.log_error(f"Project failed: {e}")
        return False

# Run your first project
if __name__ == "__main__":
    success = run_first_project()
    if success:
        print("\n🚀 Ready for more advanced projects!")
    else:
        print("\n💥 Project encountered errors - check the logs")
```

## Next Steps

### 1. Explore Core Modules

- **File Operations**: Master file and directory management
- **String Utilities**: Learn text processing capabilities
- **Logging System**: Understand comprehensive logging
- **Path Operations**: Work with file paths efficiently

### 2. Advanced Features

- **Analytics Integration**: Connect with Google Analytics and Facebook Business
- **Geographic Analysis**: Create maps and spatial visualizations
- **Report Generation**: Build professional PDF and PowerPoint reports
- **Spark Processing**: Scale to distributed computing

### 3. Real-World Projects

- **Data Pipeline**: Build automated data processing workflows
- **Dashboard Creation**: Generate interactive visualizations
- **Client Reporting**: Create branded reports for clients
- **Performance Monitoring**: Track and optimize system performance

## Troubleshooting

### Common Issues

1. **Installation Problems**
   ```bash
   # Upgrade pip first
   pip install --upgrade pip
   
   # Install with verbose output
   pip install siege-utilities -v
   
   # Check Python version
   python --version
   ```

2. **Import Errors**
   ```python
   # Check if package is installed
   pip list | grep siege-utilities
   
   # Try reinstalling
   pip uninstall siege-utilities
   pip install siege-utilities
   ```

3. **Function Not Found**
   ```python
   # Check available functions
   import siege_utilities
   print(dir(siege_utilities))
   
   # Check specific module
   print(dir(siege_utilities.files))
   ```

### Getting Help

- **Documentation**: Check the comprehensive documentation
- **GitHub Issues**: Report bugs and request features
- **Community**: Join discussions and share solutions
- **Examples**: Study the provided examples and recipes

## Configuration Files

### User Config Example

```yaml
# ~/.siege_utilities/config.yaml
user_info:
  name: "Your Name"
  email: "your.email@example.com"
  github: "your_github_username"
  company: "Your Company"

preferences:
  default_download_dir: "~/Downloads"
  log_level: "INFO"
  theme: "dark"
  language: "en"

api_keys:
  google_analytics: "your_ga_key_here"
  facebook_business: "your_fb_key_here"
  census_api: "your_census_key_here"

paths:
  projects: "~/Projects"
  data: "~/Data"
  reports: "~/Reports"
  templates: "~/Templates"
```

### Client Config Example

```yaml
# ~/.siege_utilities/clients.yaml
clients:
  acme_corporation:
    name: "Acme Corporation"
    client_id: "ACME001"
    contact_info:
      primary_contact: "John Smith"
      email: "john@acme.com"
      phone: "+1-555-0123"
      address: "123 Business St, City, State"
    
    branding:
      primary_color: "#0066CC"
      secondary_color: "#FF6600"
      accent_color: "#00CC66"
      logo_path: "assets/logos/acme_logo.png"
      font_family: "Arial"
    
    preferences:
      report_format: "PDF"
      include_charts: true
      include_tables: true
      branding_level: "full"
```

## Performance Tips

### 1. Efficient Imports

```python
# Good: Import only what you need for specific operations
from siege_utilities.files.operations import file_exists, get_file_size
from siege_utilities.core.logging import log_info, log_error

# Better: Use the main package for most operations
import siege_utilities

# Best: Use auto-discovery for maximum convenience
import siege_utilities
# All functions automatically available!
```

### 2. Batch Operations

```python
# Process multiple files efficiently
files = ["file1.txt", "file2.txt", "file3.txt"]

# Use list comprehension for batch operations
file_sizes = [siege_utilities.get_file_size(f) for f in files]
file_exists_list = [siege_utilities.file_exists(f) for f in files]

print(f"Total size: {sum(file_sizes)} bytes")
print(f"Files found: {sum(file_exists_list)}")
```

### 3. Error Handling

```python
# Graceful error handling
def safe_file_operation(file_path):
    try:
        if siege_utilities.file_exists(file_path):
            size = siege_utilities.get_file_size(file_path)
            return f"File size: {size} bytes"
        else:
            return "File not found"
    except Exception as e:
        siege_utilities.log_error(f"Error processing {file_path}: {e}")
        return f"Error: {e}"

# Use the function
result = safe_file_operation("example.txt")
print(result)
```

## Ready to Continue?

You've completed the Getting Started guide! Here's what you can do next:

1. **Explore Recipes**: Check out the comprehensive recipes for specific use cases
2. **Build Projects**: Apply what you've learned to real-world scenarios
3. **Advanced Features**: Dive into analytics, reporting, and distributed computing
4. **Contribute**: Share your experiences and help improve the library

## Related Resources

- **[Basic Setup](Basic-Setup)** - Detailed installation and configuration
- **[Testing Guide](Testing-Guide)** - Verify your installation and learn testing
- **[Analytics Integration](Analytics-Integration)** - Connect with data sources
- **[Comprehensive Reporting](Comprehensive-Reporting)** - Generate professional reports
- **[Client Management](Examples/Client-Management)** - Set up client profiles and branding

---

**Welcome to the Siege Utilities community! 🎉**

Start building amazing data solutions today. If you have questions or need help, check the documentation, join the community, or create an issue on GitHub.

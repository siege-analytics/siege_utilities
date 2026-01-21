# 🚀 Basic Setup - Getting Started with Siege Utilities

<div align="center">

![Setup](https://img.shields.io/badge/Setup-Installation_%26_Configuration-blue)
![Python](https://img.shields.io/badge/Python-3.8%2B-green)
![Installation](https://img.shields.io/badge/Installation-Pip_%26_Source-orange)

**Install and configure Siege Utilities for powerful data engineering and analytics** ⚡

</div>

---

## 🎯 **Problem**

You need to install and configure Siege Utilities on your system to start using its powerful utilities for data engineering, analytics, and file operations.

## 💡 **Solution**

Install Siege Utilities using pip and verify the installation with a simple test script. Configure logging and test basic functionality to ensure everything is working correctly.

## 🚀 **Quick Start**

```bash
# Install from PyPI
pip install siege-utilities

# Verify installation
python -c "import siege_utilities; print('✅ Installation successful!')"
```

## 📋 **Complete Implementation**

### **1. Installation Methods**

#### **Option A: Install from PyPI (Recommended)**
```bash
# Install the latest stable version
pip install siege-utilities

# Install with specific version
pip install siege-utilities==2.0.0

# Install with extra dependencies
pip install siege-utilities[full]
```

#### **Option B: Install from Source**
```bash
# Clone the repository
git clone https://github.com/siege-analytics/siege_utilities.git
cd siege_utilities

# Install in development mode
pip install -e .

# Or install with specific requirements
pip install -r requirements.txt
```

#### **Option C: Install in Virtual Environment (Recommended)**
```bash
# Create virtual environment
python -m venv siege_env

# Activate virtual environment
# On Windows:
siege_env\Scripts\activate
# On macOS/Linux:
source siege_env/bin/activate

# Install Siege Utilities
pip install siege-utilities
```

### **2. Verify Installation**

```python
import siege_utilities

# Check available functions
print(f"Available functions: {len(dir(siege_utilities))}")
print(f"First 10 functions: {dir(siege_utilities)[:10]}")

# Test basic functionality
print(f"Package version: {siege_utilities.__version__}")

# Check specific modules
print(f"Core modules: {[m for m in dir(siege_utilities) if not m.startswith('_')]}")
```

### **3. Basic Configuration**

```python
import siege_utilities
from pathlib import Path

# Initialize logging
siege_utilities.log_info("Starting Siege Utilities configuration")

# Initialize logging with custom configuration
siege_utilities.init_logger(
    name='my_app',
    log_to_file=True,
    log_dir='logs',
    level='INFO'
)

# Test logging functionality
siege_utilities.log_info("Siege Utilities initialized successfully!")
siege_utilities.log_debug("Debug information available")
siege_utilities.log_warning("Warning messages work")
siege_utilities.log_error("Error logging functional")

# Check logging configuration
print("✅ Logging system initialized")
```

### **4. Test File Operations**

```python
import siege_utilities
from pathlib import Path

# Create a test directory
test_dir = Path('test_siege_utilities')
siege_utilities.ensure_path_exists(test_dir)

# Create a test file
test_file = test_dir / 'test.txt'
with open(test_file, 'w') as f:
    f.write('Hello Siege Utilities!')

# Test file operations
files = siege_utilities.list_directory(test_dir)
print(f"Files in {test_dir}: {files}")

# Test file existence
file_exists = siege_utilities.file_exists(test_file)
print(f"Test file exists: {file_exists}")

# Test file size
file_size = siege_utilities.get_file_size(test_file)
print(f"Test file size: {file_size} bytes")

# Clean up
siege_utilities.remove_tree(test_dir)
print("✅ Cleanup completed")
```

### **5. Test Core Utilities**

```python
import siege_utilities
import pandas as pd

# Test string utilities
text = "Hello World"
uppercase = siege_utilities.to_uppercase(text)
print(f"String utility test: {text} -> {uppercase}")

# Test path utilities
test_path = "path/to/file.txt"
normalized = siege_utilities.normalize_path(test_path)
print(f"Path utility test: {test_path} -> {normalized}")

# Test data utilities
data = pd.DataFrame({'A': [1, 2, 3], 'B': ['a', 'b', 'c']})
print(f"DataFrame created: {data.shape}")

print("✅ Core utilities test completed")
```

### **6. Complete Setup Script**

```python
#!/usr/bin/env python3
"""
Complete Siege Utilities Setup and Verification Script
"""

import siege_utilities
from pathlib import Path
import sys

def run_complete_setup():
    """Run complete setup and verification"""
    
    print("🚀 SIEGE UTILITIES COMPLETE SETUP")
    print("=" * 50)
    
    try:
        # Step 1: Verify installation
        print("\n1️⃣ Verifying installation...")
        version = siege_utilities.__version__
        function_count = len(dir(siege_utilities))
        print(f"   ✅ Version: {version}")
        print(f"   ✅ Functions available: {function_count}")
        
        # Step 2: Initialize logging
        print("\n2️⃣ Initializing logging system...")
        siege_utilities.init_logger(
            name='setup_verification',
            log_to_file=True,
            log_dir='logs',
            level='INFO'
        )
        siege_utilities.log_info("Logging system initialized")
        print("   ✅ Logging system ready")
        
        # Step 3: Test file operations
        print("\n3️⃣ Testing file operations...")
        test_dir = Path('test_siege_utilities')
        siege_utilities.ensure_path_exists(test_dir)
        
        test_file = test_dir / 'test.txt'
        with open(test_file, 'w') as f:
            f.write('Siege Utilities Test File')
        
        files = siege_utilities.list_directory(test_dir)
        file_exists = siege_utilities.file_exists(test_file)
        
        print(f"   ✅ Directory created: {test_dir}")
        print(f"   ✅ File created: {test_file}")
        print(f"   ✅ Files listed: {files}")
        print(f"   ✅ File exists: {file_exists}")
        
        # Step 4: Test core utilities
        print("\n4️⃣ Testing core utilities...")
        text = "test string"
        uppercase = siege_utilities.to_uppercase(text)
        print(f"   ✅ String utility: {text} -> {uppercase}")
        
        # Step 5: Cleanup
        print("\n5️⃣ Cleaning up test files...")
        siege_utilities.remove_tree(test_dir)
        print("   ✅ Test files removed")
        
        # Step 6: Summary
        print("\n" + "=" * 50)
        print("SETUP VERIFICATION COMPLETE")
        print("=" * 50)
        print(f"✅ Version: {version}")
        print(f"✅ Functions: {function_count}")
        print(f"✅ Logging: Ready")
        print(f"✅ File Operations: Working")
        print(f"✅ Core Utilities: Functional")
        print(f"✅ Ready to use Siege Utilities!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Setup verification failed: {e}")
        siege_utilities.log_error(f"Setup verification failed: {e}")
        return False

if __name__ == "__main__":
    success = run_complete_setup()
    sys.exit(0 if success else 1)
```

## 📊 **Expected Output**

```
🚀 SIEGE UTILITIES COMPLETE SETUP
==================================================

1️⃣ Verifying installation...
   ✅ Version: 2.0.0
   ✅ Functions available: 1147

2️⃣ Initializing logging system...
   ✅ Logging system ready

3️⃣ Testing file operations...
   ✅ Directory created: test_siege_utilities
   ✅ File created: test_siege_utilities/test.txt
   ✅ Files listed: ['test.txt']
   ✅ File exists: True

4️⃣ Testing core utilities...
   ✅ String utility: test string -> TEST STRING

5️⃣ Cleaning up test files...
   ✅ Test files removed

==================================================
SETUP VERIFICATION COMPLETE
==================================================
✅ Version: 2.0.0
✅ Functions: 1147
✅ Logging: Ready
✅ File Operations: Working
✅ Core Utilities: Functional
✅ Ready to use Siege Utilities!
```

## 🔧 **Configuration Options**

### **Logging Configuration**
```python
# Custom logging configuration
siege_utilities.init_logger(
    name='my_app',
    log_to_file=True,
    log_dir='logs',
    level='DEBUG',  # DEBUG, INFO, WARNING, ERROR
    max_bytes=10485760,  # 10MB
    backup_count=5
)
```

### **Environment Variables**
```bash
# Set environment variables for configuration
export SIEGE_LOG_LEVEL=DEBUG
export SIEGE_LOG_DIR=/var/log/siege
export SIEGE_CONFIG_PATH=/etc/siege/config.yaml
```

### **Configuration File**
```yaml
# config.yaml
logging:
  level: INFO
  file: true
  directory: logs
  max_size: 10MB
  backup_count: 5

paths:
  default_download: ~/Downloads
  temp_directory: /tmp/siege
  config_directory: ~/.config/siege
```

## 🚨 **Troubleshooting**

### **Common Issues**

1. **🔐 Import Error**: Make sure you're using the correct Python environment
2. **📁 Permission Denied**: Check file permissions for logging and file operations
3. **📦 Missing Dependencies**: Run `pip install -r requirements.txt` if installing from source
4. **🐍 Python Version**: Ensure Python 3.8+ is installed
5. **🌐 Network Issues**: Check internet connection for PyPI installation

### **Installation Problems**

```bash
# Force reinstall
pip install --force-reinstall siege-utilities

# Install with specific Python version
python3.9 -m pip install siege-utilities

# Check installed packages
pip list | grep siege

# Uninstall and reinstall
pip uninstall siege-utilities
pip install siege-utilities
```

### **Virtual Environment Issues**

```bash
# Create new virtual environment
python -m venv new_env

# Activate environment
source new_env/bin/activate  # Linux/Mac
new_env\Scripts\activate     # Windows

# Install in clean environment
pip install siege-utilities
```

## 📋 **System Requirements**

### **Minimum Requirements**
- **Python**: 3.8 or higher
- **RAM**: 512MB available
- **Disk Space**: 100MB for installation
- **OS**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)

### **Recommended Requirements**
- **Python**: 3.9 or higher
- **RAM**: 2GB available
- **Disk Space**: 500MB for installation and data
- **OS**: Latest stable versions

### **Optional Dependencies**
```bash
# Install with full feature set
pip install siege-utilities[full]

# Install specific extras
pip install siege-utilities[spark]      # Spark support
pip install siege-utilities[geo]        # Geographic features
pip install siege-utilities[analytics]  # Analytics integration
```

## 🚀 **Next Steps**

After successful setup:

- **[Getting Started](Getting-Started.md)** - Learn basic usage patterns
- **[Client Management](Examples/Client-Management.md)** - Set up client profiles
- **[File Operations](Recipes/File-Operations.md)** - Master file handling
- **[Testing Guide](Testing-Guide.md)** - Run comprehensive tests

## 🔗 **Related Recipes**

- **[Getting Started](Getting-Started.md)** - First steps with Siege Utilities
- **[Testing Guide](Testing-Guide.md)** - Verify your installation
- **[Configuration Management](Configuration-Management.md)** - Advanced configuration
- **[Troubleshooting](Troubleshooting.md)** - Solve common issues

---

<div align="center">

**Ready to get started?** 🚀

**[Next: Getting Started](Getting-Started.md)** → **[Client Management](Examples/Client-Management.md)**

</div>

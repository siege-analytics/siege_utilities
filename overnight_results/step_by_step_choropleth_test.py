#!/usr/bin/env python
# coding: utf-8

# # Bivariate Choropleth Test
# 
# This notebook will create a bivariate choropleth map.

# In[1]:


# Cell 1: Setup and Import (Fixed for Environment Issue)
# ======================================================

import sys
import warnings
import os
warnings.filterwarnings('ignore')

print("🔧 Setting up environment...")

# Add the current development directory to Python path
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
    print(f"✅ Added {current_dir} to Python path")

print(f"📍 Current working directory: {current_dir}")
print(f"🐍 Python path includes: {current_dir in sys.path}")

# Import siege_utilities
try:
    import siege_utilities
    print("✅ siege_utilities imported successfully")
    print(f" Library version: {getattr(siege_utilities, '__version__', 'Unknown')}")
    
    # Test the new functions
    print("\n Testing new Census functions:")
    
    # Check for get_census_boundaries
    if hasattr(siege_utilities, 'get_census_boundaries'):
        print("✅ get_census_boundaries: AVAILABLE")
    else:
        print("❌ get_census_boundaries: MISSING")
    
    # Check for get_census_data  
    if hasattr(siege_utilities, 'get_census_data'):
        print("✅ get_census_data: AVAILABLE")
    else:
        print("❌ get_census_data: MISSING")
    
    # Check for join_boundaries_and_data
    if hasattr(siege_utilities, 'join_boundaries_and_data'):
        print("✅ join_boundaries_and_data: AVAILABLE")
    else:
        print("❌ join_boundaries_and_data: MISSING")
    
    # Check for create_sample_dataset
    if hasattr(siege_utilities, 'create_sample_dataset'):
        print("✅ create_sample_dataset: AVAILABLE")
    else:
        print("❌ create_sample_dataset: MISSING")
    
    # If still missing, show what's actually available
    if not any(hasattr(siege_utilities, f) for f in ['get_census_boundaries', 'get_census_data', 'join_boundaries_and_data', 'create_sample_dataset']):
        print("\n🔍 Available functions (searching for 'census', 'boundary', 'join', 'sample'):")
        available = [f for f in dir(siege_utilities) if any(x in f.lower() for x in ['census', 'boundary', 'join', 'sample'])]
        for func in available:
            print(f"  • {func}")
    
    print("\n🎯 Ready to test Census data pipeline!")
    
except ImportError as e:
    print(f"❌ Failed to import siege_utilities: {e}")
    print("💡 Make sure you're in the correct environment and the library is installed")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)


# In[2]:


# Cell 2: Configure Download Directory
# ====================================

print("📁 Configuring download directory...")

try:
    # Get current user config
    current_config = siege_utilities.user_config.get_user_profile()
    print(f"📍 Current download directory: {current_config.get('preferred_download_directory', 'Not set')}")
    
    # Set download directory to ~/Downloads for easier access
    new_download_dir = os.path.expanduser("~/Downloads")
    print(f"🔄 Setting download directory to: {new_download_dir}")
    
    # Update the config
    siege_utilities.user_config.update_user_profile({
        'preferred_download_directory': new_download_dir
    })
    
    # Verify the change
    updated_config = siege_utilities.user_config.get_user_profile()
    print(f"✅ Download directory successfully configured!")
    print(f"📍 New download directory: {updated_config.get('preferred_download_directory', 'Not set')}")
    
    # Test if the directory exists and is writable
    if os.path.exists(new_download_dir):
        print(f"✅ Directory exists: {new_download_dir}")
        
        # Check if we can write to it
        test_file = os.path.join(new_download_dir, "test_write.tmp")
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            print("✅ Directory is writable")
        except Exception as e:
            print(f"⚠️ Directory write test failed: {e}")
    else:
        print(f"❌ Directory does not exist: {new_download_dir}")
        
except Exception as e:
    print(f"❌ Error configuring download directory: {e}")
    print("💡 Continuing with default settings...")

print("\n🎯 Ready to test Census data downloads!")


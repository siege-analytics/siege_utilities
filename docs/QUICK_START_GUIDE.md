# Quick Start Guide - Siege Utilities

Get up and running with Siege Utilities in minutes! This guide covers the most common use cases.

## 🚀 Installation

```bash
# Basic installation
pip install siege-utilities

# With geospatial support (recommended)
pip install siege-utilities[geo]

# Full installation with all features
pip install siege-utilities[distributed,geo,dev]
```

## ⚡ 5-Minute Quick Start

### 1. Basic Usage

```python
import siege_utilities as su

# Logging (works immediately)
su.log_info("Hello from Siege Utilities!")

# File operations
hash_value = su.get_file_hash("myfile.txt")
su.ensure_path_exists("data/processed")

# String utilities
clean_text = su.remove_wrapping_quotes_and_trim('  "hello world"  ')
print(clean_text)  # "hello world"
```

### 2. Configuration Setup (NEW!)

```python
from siege_utilities.config import HydraConfigManager

# Load user profile with validation
with HydraConfigManager() as manager:
    user_profile = manager.load_user_profile()
    print(f"Welcome, {user_profile.full_name}!")

# Load client-specific branding
branding = manager.load_branding_config("client_a")
print(f"Brand color: {branding.primary_color}")
```

### 3. Census Data (with geospatial support)

```python
# Get Census boundaries
boundaries = su.get_census_boundaries(
    year=2020,
    geographic_level='county',
    state_fips='06'  # California
)

print(f"Found {len(boundaries)} counties")
```

### 4. Distributed Computing (if PySpark available)

```python
try:
    # Setup Spark session
    spark, data_path = su.setup_distributed_environment()
    print("Spark ready!")
except ImportError:
    print("PySpark not available - install with: pip install pyspark")
```

## 🎯 Common Use Cases

### Data Processing Pipeline

```python
import siege_utilities as su

# 1. Setup logging
su.log_info("Starting data pipeline")

# 2. Create directory structure
su.ensure_path_exists("data/raw")
su.ensure_path_exists("data/processed")

# 3. Download data
su.download_file("https://example.com/data.csv", "data/raw/data.csv")

# 4. Verify integrity
hash_value = su.get_file_hash("data/raw/data.csv")
su.log_info(f"File hash: {hash_value}")

# 5. Process data (if pandas available)
try:
    import pandas as pd
    df = pd.read_csv("data/raw/data.csv")
    su.log_info(f"Loaded {len(df)} rows")
except ImportError:
    su.log_warning("Pandas not available - install with: pip install pandas")
```

### Client Report Generation

```python
from siege_utilities.config import HydraConfigManager, BrandingConfig

# Load client-specific configuration
with HydraConfigManager() as manager:
    # Get branding for specific client
    branding = manager.load_branding_config("client_a")
    
    # Use branding in reports
    print(f"Generating report with:")
    print(f"  Primary color: {branding.primary_color}")
    print(f"  Font: {branding.primary_font}")
    
    # Load user preferences
    user_profile = manager.load_user_profile()
    output_dir = user_profile.preferred_download_directory
    print(f"  Output directory: {output_dir}")
```

### Geospatial Analysis

```python
# Get Census data
counties = su.get_census_boundaries(
    year=2020,
    geographic_level='county',
    state_fips='06'  # California
)

# Geocode addresses
addresses = ["San Francisco, CA", "Los Angeles, CA"]
for address in addresses:
    result = su.use_nominatim_geocoder(address)
    if result:
        coords = json.loads(result)
        print(f"{address}: {coords['nominatim_lat']}, {coords['nominatim_lng']}")
```

## 🔧 Configuration Management

### Create User Profile

```python
from siege_utilities.config import UserProfile

# Create a new user profile
user = UserProfile(
    username="john_doe",
    email="john@example.com",
    full_name="John Doe",
    default_output_format="pptx",
    preferred_download_directory="/Users/john/Downloads/siege_utilities"
)

print(f"Created profile for: {user.full_name}")
```

### Create Client Profile

```python
from siege_utilities.config import ClientProfile, ContactInfo, BrandingConfig

# Create client profile with branding
client = ClientProfile(
    client_id="acme_corp",
    client_name="Acme Corporation",
    client_code="ACME",
    contact_info=ContactInfo(
        email="contact@acme.com",
        website="https://acme.com"
    ),
    industry="Technology",
    branding_config=BrandingConfig(
        primary_color="#1f77b4",
        secondary_color="#ff7f0e",
        primary_font="Arial"
    )
)

print(f"Created profile for: {client.client_name}")
```

## 📊 Package Information

```python
# Get comprehensive package info
info = su.get_package_info()

print(f"Total functions: {info['total_functions']}")
print(f"Available categories: {list(info['categories'].keys())}")

# Check specific category
core_functions = info['categories']['core']
print(f"Core functions: {len(core_functions)}")
```

## 🛠️ Troubleshooting

### Missing Dependencies

```python
# Check what's available
info = su.get_package_info()
print(f"Available functions: {info['total_functions']}")

# Try a function that might need dependencies
try:
    result = su.create_bivariate_choropleth({}, 'location', 'var1', 'var2')
except ImportError as e:
    print(f"Install dependencies: {e}")
```

### Configuration Issues

```python
# Check configuration status
from siege_utilities.config import get_default_profile_location

profile_dir = get_default_profile_location()
print(f"Profile directory: {profile_dir}")

# Create default profiles if needed
from siege_utilities.config import create_default_profiles
create_default_profiles()
```

## 🎯 Next Steps

1. **Explore Examples**: Check `examples/` directory for comprehensive examples
2. **Read Documentation**: Full documentation in `docs/` directory
3. **Run Tests**: `python -m pytest tests/` to verify everything works
4. **Battle Test**: Run `python scripts/battle_test_hydra_pydantic.py` for comprehensive testing

## 💡 Pro Tips

- **Always use the context manager** for HydraConfigManager: `with HydraConfigManager() as manager:`
- **Check function availability** before using: `info = su.get_package_info()`
- **Use validation**: The new Pydantic models catch errors early
- **Client-specific configs**: Override defaults with client-specific YAML files
- **Migration**: Use `python scripts/migrate_to_hydra.py --dry-run` to migrate existing configs

---

**Ready to dive deeper?** Check out the [User Guide](USER_GUIDE.md) for comprehensive documentation!

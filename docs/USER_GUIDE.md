# Siege Utilities User Guide

Welcome to Siege Utilities! This guide will help you get started with the library and its powerful new Hydra + Pydantic configuration system.

## 🚀 Quick Start

### Installation

```bash
# Basic installation
pip install siege-utilities

# With geospatial support (includes Census Data Intelligence)
pip install siege-utilities[geo]

# With distributed computing support
pip install siege-utilities[distributed]

# Full installation (all optional dependencies)
pip install siege-utilities[distributed,geo,dev]
```

### Modern Package Management with UV

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a new UV project
uv init my-siege-project
cd my-siege-project

# Add siege_utilities with all dependencies
uv add siege-utilities[geo]
```

### Basic Usage

```python
import siege_utilities as su

# All 260+ functions are immediately available
su.log_info("Package loaded successfully!")

# Get package information
info = su.get_package_info()
print(f"Available: {info['total_functions']} functions")

# Core utilities work immediately
hash_value = su.get_file_hash("myfile.txt")
clean_text = su.remove_wrapping_quotes_and_trim('  "hello"  ')
```

## 🔧 NEW: Hydra + Pydantic Configuration System

### Overview

The new configuration system provides:
- **Type-safe configuration management** with full IDE support
- **Client-specific customization** with hierarchical overrides
- **Comprehensive validation** with detailed error messages
- **Seamless migration** from legacy configuration systems

### Quick Configuration Setup

```python
from siege_utilities.config import HydraConfigManager

# Load configurations with validation
with HydraConfigManager() as manager:
    # Load user profile
    user_profile = manager.load_user_profile()
    print(f"User: {user_profile.full_name}")
    
    # Load client-specific branding
    branding = manager.load_branding_config("client_a")
    print(f"Brand color: {branding.primary_color}")
```

### Creating User Profiles

```python
from siege_utilities.config import UserProfile

# Create a user profile with validation
user_profile = UserProfile(
    username="john_doe",
    email="john@example.com",
    full_name="John Doe",
    organization="Acme Corp",
    default_output_format="pptx",
    default_dpi=300,
    preferred_download_directory="/Users/john/Downloads/siege_utilities"
)

# The system automatically validates all fields
print(f"User: {user_profile.full_name}")
print(f"Download directory: {user_profile.preferred_download_directory}")
```

### Creating Client Profiles

```python
from siege_utilities.config import ClientProfile, ContactInfo, BrandingConfig

# Create contact information
contact = ContactInfo(
    email="client@example.com",
    phone="+1-555-123-4567",
    website="https://example.com"
)

# Create branding configuration
branding = BrandingConfig(
    primary_color="#1f77b4",
    secondary_color="#ff7f0e",
    accent_color="#2ca02c",
    text_color="#000000",
    background_color="#ffffff",
    primary_font="Arial",
    secondary_font="Arial"
)

# Create client profile
client = ClientProfile(
    client_id="example_corp",
    client_name="Example Corporation",
    client_code="EXAMPLE",
    contact_info=contact,
    industry="Technology",
    project_count=5,
    status="active",
    branding_config=branding
)

print(f"Client: {client.client_name}")
print(f"Brand color: {client.branding_config.primary_color}")
```

### Database Connections

```python
from siege_utilities.config import DatabaseConnection

# Create a database connection with validation
db_conn = DatabaseConnection(
    name="production_db",
    connection_type="postgresql",
    host="db.example.com",
    port=5432,
    database="production",
    username="admin",
    password="SecurePassword123",  # Must meet strength requirements
    ssl_enabled=True,
    connection_timeout=30,
    max_connections=20
)

# Get connection string
conn_string = db_conn.get_connection_string()
print(f"Connection: {conn_string}")
```

### Social Media Accounts

```python
from siege_utilities.config import SocialMediaAccount

# Create a social media account
social_account = SocialMediaAccount(
    platform="facebook",
    account_id="123456789",
    account_name="Example Corp",
    access_token="valid_facebook_access_token_123456789",
    is_active=True,
    api_version="v2.0"
)

# Get authentication headers
auth_headers = social_account.get_auth_headers()
print(f"Auth headers: {auth_headers}")
```

## 📁 Configuration File Structure

The system uses a hierarchical configuration structure:

```
siege_utilities/configs/
├── default/
│   ├── user_profile.yaml          # Default user settings
│   ├── client_profile.yaml        # Default client settings
│   ├── branding_config.yaml       # Default branding
│   ├── database_connections.yaml  # Default database configs
│   └── social_media_accounts.yaml # Default social media configs
├── client/
│   ├── client_a/
│   │   ├── branding.yaml          # Client A specific branding
│   │   └── database_connections.yaml
│   └── client_b/
│       └── branding.yaml          # Client B specific branding
└── experiments/
    ├── report_variants/
    └── chart_testing/
```

### Client-Specific Configuration

To create client-specific configurations:

1. **Create client directory**:
   ```bash
   mkdir -p siege_utilities/configs/client/your_client
   ```

2. **Create branding override**:
   ```yaml
   # siege_utilities/configs/client/your_client/branding.yaml
   defaults:
     - /default/branding_config
     - _self_
   
   colors:
     primary_color: "#2E86AB"    # Your brand color
     secondary_color: "#A23B72"  # Your accent color
     accent_color: "#F18F01"     # Your highlight color
   
   typography:
     primary_font: "Helvetica"
     secondary_font: "Georgia"
   ```

3. **Load client-specific configuration**:
   ```python
   with HydraConfigManager() as manager:
       branding = manager.load_branding_config("your_client")
       # Will use your client-specific colors and fonts
   ```

## 🔄 Migration from Legacy System

### Automated Migration

Use the programmatic migration helpers from `siege_utilities.config` for migration workflows.

### Programmatic Migration

```python
from siege_utilities.config import migrate_configurations

# Perform migration
results = migrate_configurations(dry_run=False)

print(f"Migrated {results['total_migrated']} profiles")
print(f"User profile: {'✅' if results['user_profile']['migrated'] else '❌'}")
```

## 🧪 Testing Your Configuration

### Validation Examples

```python
# Test email validation
try:
    user = UserProfile(email="invalid-email")
except ValueError as e:
    print(f"Validation error: {e}")

# Test password strength validation
try:
    db_conn = DatabaseConnection(
        name="test",
        connection_type="postgresql",
        host="localhost",
        port=5432,
        database="test",
        username="user",
        password="weak"  # Too weak
    )
except ValueError as e:
    print(f"Password validation: {e}")

# Test color format validation
try:
    branding = BrandingConfig(
        primary_color="red",  # Invalid hex format
        secondary_color="#ff7f0e",
        # ... other required fields
    )
except ValueError as e:
    print(f"Color validation: {e}")
```

### Running the Example Script

```bash
# Run the comprehensive example
python -m siege_utilities.examples.enhanced_features_demo

# Optional: run import diagnostics
python scripts/check_imports.py
```

## 📊 Advanced Features

### Configuration Overrides

```python
with HydraConfigManager() as manager:
    # Load configuration with overrides
    config_data = manager.load_config(
        "default/user_profile",
        overrides=["default.default_output_format=pdf", "default.default_dpi=600"]
    )
```

### Dynamic Configuration Updates

```python
# Test updating configurations at runtime
with HydraConfigManager() as manager:
    # Load initial configuration
    initial_branding = manager.load_branding_config()
    
    # Simulate configuration update (in real scenario, this would update files)
    # For testing, we'll just verify the system can handle multiple loads
    updated_branding = manager.load_branding_config()
    
    print("Configuration reload successful!")
```

### Multi-Client Workflows

```python
def generate_multi_client_reports():
    with HydraConfigManager() as manager:
        clients = ["client_a", "client_b"]
        reports_generated = 0
        
        for client in clients:
            try:
                branding = manager.load_branding_config(client)
                print(f"Generating report for {client} with {branding.primary_color}")
                reports_generated += 1
            except Exception:
                # Fall back to default
                branding = manager.load_branding_config()
                print(f"Using default branding for {client}")
                reports_generated += 1
        
        return reports_generated

# Generate reports for multiple clients
count = generate_multi_client_reports()
print(f"Generated {count} reports")
```

## 🛠️ Troubleshooting

### Common Issues

1. **Validation Errors**: Check field formats and constraints
2. **Missing Configurations**: Ensure all required fields are provided
3. **Override Conflicts**: Check for conflicting configuration values
4. **Migration Issues**: Use dry-run to identify migration problems

### Debugging

```python
# Enable verbose logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Load with debugging
with HydraConfigManager() as manager:
    # Will show detailed loading information
    profile = manager.load_user_profile()
```

### Error Messages

The system provides detailed error messages for validation failures:

```
ValidationError: 3 validation errors for UserProfile
email
  String should match pattern '^[^@]+@[^@]+\.[^@]+$' [type=string_pattern_mismatch, input_value='invalid-email', input_type=str]
password
  String should have at least 8 characters [type=string_too_short, input_value='123', input_type=str]
```

## 📚 Additional Resources

- [Complete Configuration Documentation](HYDRA_PYDANTIC_CONFIGURATION.md)
- [API Reference](api/)
- [Migration Guide](migration/)
- [`siege_utilities/examples/`](../siege_utilities/examples/)
- [Troubleshooting Guide](troubleshooting/)

## 🤝 Getting Help

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check the comprehensive guides
- **Examples**: Run the example scripts to see usage patterns
- **Battle Testing**: Use the battle testing script to validate your setup

---

**Happy configuring with Siege Utilities!** 🚀

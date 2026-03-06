# Hydra + Pydantic Configuration System

This document describes the new Hydra + Pydantic configuration system for siege_utilities, which provides powerful configuration management with comprehensive validation.

## Overview

The new configuration system combines:
- **Hydra**: Flexible configuration composition and management
- **Pydantic**: Type-safe data validation and serialization
- **Hierarchical Configuration**: Client-specific overrides with defaults
- **Migration Support**: Seamless transition from legacy systems

## Key Features

- ✅ **Type Safety**: Full IDE support and runtime validation
- ✅ **Configuration Composition**: Hierarchical configuration with overrides
- ✅ **Client-Specific Customization**: Easy client branding and preferences
- ✅ **Validation**: Comprehensive data validation with detailed error messages
- ✅ **Migration Tools**: Automated migration from legacy systems
- ✅ **Backward Compatibility**: Gradual transition without breaking changes

## Quick Start

### Basic Usage

```python
from siege_utilities.config import HydraConfigManager

# Initialize the configuration manager
with HydraConfigManager() as manager:
    # Load user profile
    user_profile = manager.load_user_profile()
    print(f"User: {user_profile.full_name}")
    
    # Load client-specific branding
    branding = manager.load_branding_config("client_a")
    print(f"Primary color: {branding.primary_color}")
```

### Configuration Structure

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

## Configuration Models

### UserProfile

```python
from siege_utilities.config.models import UserProfile

# Create a user profile with validation
profile = UserProfile(
    username="john_doe",
    email="john@example.com",
    full_name="John Doe",
    github_login="johndoe",
    organization="Acme Corp",
    default_output_format="pptx",
    default_dpi=300
)

# Access validated data
print(f"Username: {profile.username}")
print(f"Email: {profile.email}")
print(f"Download directory: {profile.preferred_download_directory}")
```

### ClientProfile

```python
from siege_utilities.config.models import ClientProfile, ContactInfo, BrandingConfig

# Create a client profile
contact = ContactInfo(
    email="client@example.com",
    phone="+1-555-123-4567",
    website="https://example.com"
)

branding = BrandingConfig(
    primary_color="#1f77b4",
    secondary_color="#ff7f0e",
    accent_color="#2ca02c",
    text_color="#000000",
    background_color="#ffffff",
    primary_font="Arial",
    secondary_font="Arial"
)

client = ClientProfile(
    client_id="acme_corp",
    client_name="Acme Corporation",
    client_code="ACME",
    contact_info=contact,
    industry="Technology",
    branding_config=branding,
    project_count=5,
    status="active"
)
```

### DatabaseConnection

```python
from siege_utilities.config.models import DatabaseConnection

# Create a database connection with validation
db_conn = DatabaseConnection(
    name="production_db",
    connection_type="postgresql",
    host="prod-db.company.com",
    port=5432,
    database="client_data",
    username="admin",
    password="SecurePassword123",  # Must be 8+ chars with uppercase, lowercase, number
    ssl_enabled=True
)

# Get connection string
conn_string = db_conn.get_connection_string()
print(f"Connection: {conn_string}")
```

## Hydra Configuration Manager

### Loading Configurations

```python
from siege_utilities.config import HydraConfigManager

with HydraConfigManager() as manager:
    # Load user profile
    user_profile = manager.load_user_profile()
    
    # Load client profile
    client_profile = manager.load_client_profile("client_a")
    
    # Load branding with client-specific overrides
    branding = manager.load_branding_config("client_a")
    
    # Load database connections
    db_connections = manager.load_database_connections("client_a")
    
    # Load social media accounts
    social_accounts = manager.load_social_media_accounts("client_a")
```

### Configuration Overrides

```python
# Load configuration with overrides
config_data = manager.load_config(
    "default/user_profile",
    overrides=["default.default_output_format=pdf", "default.default_dpi=600"]
)
```

## Client-Specific Configuration

### Creating Client Configurations

1. **Create client directory**:
   ```bash
   mkdir -p siege_utilities/configs/client/client_a
   ```

2. **Create branding override**:
   ```yaml
   # siege_utilities/configs/client/client_a/branding.yaml
   defaults:
     - /default/branding_config
     - _self_
   
   colors:
     primary_color: "#2E86AB"    # Blue theme
     secondary_color: "#A23B72"  # Pink accent
     accent_color: "#F18F01"     # Orange highlight
   
   typography:
     primary_font: "Helvetica"
     secondary_font: "Georgia"
   ```

3. **Load client-specific configuration**:
   ```python
   with HydraConfigManager() as manager:
       branding = manager.load_branding_config("client_a")
       # Will use client-specific colors and fonts
   ```

### Configuration Inheritance

The system supports hierarchical configuration inheritance:

1. **Default Configuration**: Base settings for all clients
2. **Client Overrides**: Client-specific customizations
3. **Runtime Overrides**: Programmatic overrides during execution

```python
# Load with inheritance: client_a overrides default
branding = manager.load_branding_config("client_a")

# Load default only
branding = manager.load_branding_config()
```

## Migration from Legacy System

### Automated Migration

Use the programmatic migration utilities to transition from the legacy system.

### Programmatic Migration

```python
from siege_utilities.config.migration import migrate_configurations

# Perform migration
results = migrate_configurations(dry_run=False)

print(f"Migrated {results['total_migrated']} profiles")
print(f"User profile: {'✅' if results['user_profile']['migrated'] else '❌'}")
```

## Validation Examples

### Field Validation

```python
# Email validation
try:
    profile = UserProfile(email="invalid-email")
except ValueError as e:
    print(f"Validation error: {e}")

# Password strength validation
try:
    db_conn = DatabaseConnection(
        name="test",
        connection_type="postgresql",
        host="localhost",
        port=5432,
        database="test",
        username="user",
        password="weak"  # Too short
    )
except ValueError as e:
    print(f"Password validation: {e}")

# Color format validation
try:
    branding = BrandingConfig(
        primary_color="red",  # Invalid hex format
        secondary_color="#ff7f0e",
        # ... other required fields
    )
except ValueError as e:
    print(f"Color validation: {e}")
```

### Custom Validators

The system includes comprehensive custom validators:

- **Email Format**: Validates email structure
- **Password Strength**: Requires uppercase, lowercase, numbers
- **Phone Numbers**: Validates phone number format
- **URLs**: Validates website and LinkedIn URLs
- **Color Codes**: Validates hex color format
- **Database Names**: Validates database naming conventions

## Best Practices

### Configuration Organization

1. **Use Hierarchical Structure**: Organize configs by client and type
2. **Minimize Duplication**: Use defaults and overrides effectively
3. **Validate Early**: Validate configurations at load time
4. **Document Customizations**: Document client-specific overrides

### Security Considerations

1. **Sensitive Data**: Store API keys and passwords securely
2. **Access Control**: Restrict access to configuration directories
3. **Validation**: Always validate input data
4. **Backup**: Regular backup of configuration files

### Performance Tips

1. **Lazy Loading**: Load configurations only when needed
2. **Caching**: Cache frequently accessed configurations
3. **Minimal Overrides**: Use minimal overrides for better performance
4. **Validation Caching**: Cache validation results when possible

## Troubleshooting

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

## API Reference

### HydraConfigManager

```python
class HydraConfigManager:
    def __init__(self, config_dir: Optional[Path] = None)
    def load_user_profile(self, client_code: Optional[str] = None) -> UserProfile
    def load_client_profile(self, client_code: str) -> ClientProfile
    def load_branding_config(self, client_code: Optional[str] = None) -> BrandingConfig
    def load_database_connections(self, client_code: Optional[str] = None) -> List[DatabaseConnection]
    def load_social_media_accounts(self, client_code: Optional[str] = None) -> List[SocialMediaAccount]
```

### Configuration Models

```python
# Core models
UserProfile
ClientProfile
ContactInfo
BrandingConfig
ReportPreferences

# Connection models
DatabaseConnection
SocialMediaAccount

# Migration utilities
ConfigurationMigrator
migrate_configurations
backup_and_migrate
```

## Examples

### Complete Workflow Example

```python
from siege_utilities.config import HydraConfigManager
from siege_utilities.config.models import *

def generate_client_report(client_code: str):
    """Generate a report for a specific client using their configuration."""
    
    with HydraConfigManager() as manager:
        # Load client-specific configuration
        client_profile = manager.load_client_profile(client_code)
        branding = manager.load_branding_config(client_code)
        db_connections = manager.load_database_connections(client_code)
        
        # Use configuration for report generation
        print(f"Generating report for {client_profile.client_name}")
        print(f"Using brand color: {branding.primary_color}")
        print(f"Available databases: {[conn.name for conn in db_connections]}")
        
        # Generate report with client branding
        # ... report generation logic ...
```

### Configuration Validation Example

```python
def validate_client_configuration(client_code: str) -> bool:
    """Validate a client's complete configuration."""
    
    try:
        with HydraConfigManager() as manager:
            # Load all configurations
            client_profile = manager.load_client_profile(client_code)
            branding = manager.load_branding_config(client_code)
            db_connections = manager.load_database_connections(client_code)
            
            # Validate business rules
            if not client_profile.contact_info.email:
                raise ValueError("Client must have contact email")
            
            if not db_connections:
                raise ValueError("Client must have at least one database connection")
            
            # Validate branding consistency
            if branding.primary_color == branding.secondary_color:
                raise ValueError("Primary and secondary colors must be different")
            
            return True
            
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        return False
```

## Migration Guide

### From Legacy System

1. **Backup Existing Configurations** using your normal backup workflow.

2. **Test Migration** in a temporary directory with a dry-run style execution path.

3. **Perform Migration** using the programmatic migration utilities.

4. **Verify Migration**:
   ```python
   from siege_utilities.config import HydraConfigManager
   
   with HydraConfigManager() as manager:
       # Test loading migrated configurations
       profile = manager.load_user_profile()
       print("Migration successful!")
   ```

### Configuration Mapping

| Legacy Field | New Field | Notes |
|-------------|-----------|-------|
| `username` | `username` | Direct mapping |
| `email` | `email` | Enhanced validation |
| `download_dir` | `preferred_download_directory` | Path validation |
| `output_format` | `default_output_format` | Enum validation |
| `branding.primary_color` | `branding_config.primary_color` | Hex validation |
| `database.connections` | `database_connections` | List of validated connections |

## Conclusion

The Hydra + Pydantic configuration system provides a robust, type-safe, and flexible foundation for managing siege_utilities configurations. With comprehensive validation, client-specific customization, and seamless migration support, it enables powerful configuration management while maintaining data integrity and system reliability.

For more information, see:
- [Configuration Example Module](../siege_utilities/examples/enhanced_features_demo.py)
- [Migration Guide](migration/)
- [API Reference](api/)
- [Troubleshooting Guide](troubleshooting/)

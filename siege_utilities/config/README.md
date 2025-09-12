# Configuration Management

This module provides comprehensive configuration management for the siege_utilities library, featuring both legacy support and a new enhanced system with Pydantic validation.

## Enhanced Configuration System

The enhanced configuration system provides type-safe configuration management with the following benefits:

- **Type Safety**: Pydantic validation catches configuration errors at runtime
- **Hierarchical Resolution**: Smart fallback system for download directories
- **Backward Compatibility**: Existing functional API continues to work
- **Export/Import**: Easy configuration backup and migration
- **No Forced OOP**: Hybrid functional + data models approach

## Quick Start

```python
import siege_utilities as su

# Create and save user profile
user_profile = su.EnhancedUserProfile(
    username='your_username',
    email='your@email.com',
    preferred_download_directory='/Users/username/Downloads/siege_utilities'
)
su.save_user_profile(user_profile)

# Create and save client profile
client = su.ClientProfile(
    client_name='Client Name',
    client_code='CLIENT_CODE',
    download_directory='/Users/username/Downloads/siege_utilities/client_code'
)
su.save_client_profile(client)

# Get download directory with hierarchical resolution
download_dir = su.get_download_directory(client_code='CLIENT_CODE')

# Profile management
default_location = su.get_default_profile_location()
su.create_default_profiles()
summary = su.get_profile_summary()
```

## Available Classes

### Enhanced Classes (Recommended)

- `EnhancedUserProfile`: Type-safe user configuration with validation
- `ClientProfile`: Client-specific settings and preferences
- `SiegeConfig`: Unified configuration container

### Legacy Classes (Backward Compatibility)

- `UserProfile`: Original dataclass-based user configuration
- `UserConfigManager`: Legacy configuration manager

## Available Functions

### Core Functions

- `load_user_profile()`: Load user profile with validation and defaults
- `save_user_profile()`: Save user profile with validation
- `load_client_profile()`: Load client profile by code
- `save_client_profile()`: Save client profile with validation
- `get_download_directory()`: Get download directory with hierarchical resolution
- `list_client_profiles()`: List available client profile codes
- `export_config_yaml()`: Export configuration to YAML file
- `import_config_yaml()`: Import configuration from YAML file

## File Structure

```
~/.siege_utilities/
└── config/
    ├── user_config.yaml          # User profile
    └── clients/
        ├── CLIENT1.yaml         # Client profiles
        └── CLIENT2.yaml
```

## Validation

The enhanced system provides comprehensive validation:

```python
# Valid configuration
user = su.EnhancedUserProfile(
    default_output_format='pptx',  # ✅ Valid
    default_dpi=150,  # ✅ Valid range
    log_level='DEBUG'  # ✅ Valid level
)

# Invalid configuration (will raise ValueError)
try:
    user = su.EnhancedUserProfile(
        default_output_format='invalid',  # ❌ Invalid format
        default_dpi=50,  # ❌ Too low
        log_level='INVALID'  # ❌ Invalid level
    )
except ValueError as e:
    print(f"Validation error: {e}")
```

## Migration Guide

### From Legacy to Enhanced

```python
# Legacy approach
from siege_utilities.config.user_config import UserProfile as LegacyUserProfile

# Enhanced approach (recommended)
from siege_utilities.config.enhanced_config import UserProfile as EnhancedUserProfile

# Both work side by side
legacy_profile = LegacyUserProfile()
enhanced_profile = EnhancedUserProfile()
```

## Examples

See the [Enhanced Configuration System documentation](../../wiki/Enhanced-Configuration-System.md) for comprehensive examples and best practices.

## Testing

Run the configuration tests:

```bash
# Run all config tests
python -m pytest tests/test_enhanced_config.py -v

# Run with config marker
python -m pytest -m config -v
```

## Support

For issues or questions about the configuration system, please refer to the main documentation or create an issue in the project repository.

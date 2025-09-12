# Enhanced Configuration System

## Overview

The Enhanced Configuration System provides a robust, type-safe configuration management solution using Pydantic validation while maintaining a functional API approach. This hybrid system combines the power of data validation with the simplicity of functional programming.

## Key Features

- **🔒 Type Safety**: Pydantic validation catches configuration errors at runtime
- **📁 Hierarchical Directory Resolution**: Smart fallback system for download directories
- **🔄 Backward Compatibility**: Existing functional API continues to work
- **📤 Export/Import**: Easy configuration backup and migration
- **🛡️ Validation**: Invalid config values are caught and handled gracefully
- **⚡ No Forced OOP**: Data models + functional API = best of both worlds

## Architecture

### Hybrid Approach

The system uses a hybrid approach that combines:

1. **Pydantic Data Models**: For type safety and validation
2. **Functional API**: For easy-to-use configuration management
3. **YAML Storage**: Human-readable configuration files
4. **Hierarchical Resolution**: Smart fallback for directory management

### Components

```
Enhanced Configuration System
├── Data Models (Pydantic)
│   ├── UserProfile
│   ├── ClientProfile
│   └── SiegeConfig
├── Functional API
│   ├── load_user_profile()
│   ├── save_user_profile()
│   ├── load_client_profile()
│   ├── save_client_profile()
│   ├── get_download_directory()
│   ├── list_client_profiles()
│   ├── export_config_yaml()
│   └── import_config_yaml()
└── Storage
    ├── ~/.siege_utilities/config/user_config.yaml
    └── ~/.siege_utilities/config/clients/
```

## Usage Examples

### Basic User Profile Management

```python
import siege_utilities as su

# Create user profile with validation
user_profile = su.EnhancedUserProfile(
    username='john_doe',
    email='john@example.com',
    full_name='John Doe',
    preferred_download_directory='/Users/john/Downloads/siege_utilities',
    default_output_format='pptx',
    default_dpi=300
)

# Save profile
su.save_user_profile(user_profile)

# Load profile
loaded_user = su.load_user_profile()
print(f"Welcome, {loaded_user.full_name}!")
```

### Client Profile Management

```python
# Create client profile
client = su.ClientProfile(
    client_name='Acme Corporation',
    client_code='ACME',
    download_directory='/tmp/acme_downloads',
    industry='Technology',
    project_count=10,
    status='active',
    contact_info={
        'email': 'contact@acme.com',
        'phone': '555-0123'
    }
)

# Save client profile
su.save_client_profile(client)

# Load client profile
acme_client = su.load_client_profile('ACME')
print(f"Client: {acme_client.client_name} ({acme_client.industry})")
```

### Hierarchical Directory Resolution

The system provides intelligent directory resolution with the following priority:

1. **Specific Path** (highest priority)
2. **Client Directory** (if client code provided)
3. **User Directory** (fallback)
4. **System Default** (lowest priority)

```python
# Test different directory resolutions
user_dir = su.get_download_directory()
client_dir = su.get_download_directory(client_code='ACME')
specific_dir = su.get_download_directory(specific_path='/tmp/override')

print(f"User directory: {user_dir}")
print(f"ACME directory: {client_dir}")
print(f"Override directory: {specific_dir}")
```

### Configuration Export/Import

```python
# Export configuration
su.export_config_yaml('/tmp/config_backup.yaml', include_api_keys=False)

# Import configuration
su.import_config_yaml('/tmp/config_backup.yaml')
```

## Data Models

### UserProfile

Enhanced user profile with validation:

```python
class UserProfile(BaseModel):
    # Personal Information
    username: str = ""
    email: str = ""
    full_name: str = ""
    github_login: str = ""
    organization: str = ""
    
    # Preferences
    preferred_download_directory: Path = Field(
        default_factory=lambda: Path.home() / "Downloads" / "siege_utilities"
    )
    default_output_format: str = Field(default="pdf", pattern="^(pdf|pptx|html)$")
    preferred_map_style: str = Field(default="open-street-map")
    default_color_scheme: str = Field(default="YlOrRd")
    
    # Technical Preferences
    default_dpi: int = Field(default=300, ge=72, le=600)
    default_figure_size: tuple = Field(default=(10, 8))
    enable_logging: bool = True
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    
    # API Keys (will be handled securely)
    google_analytics_key: str = ""
    facebook_business_key: str = ""
    census_api_key: str = ""
    
    # Database Preferences
    default_database: str = Field(default="postgresql", pattern="^(postgresql|mysql|sqlite|duckdb)$")
    postgresql_connection: str = ""
    duckdb_path: str = ""
```

### ClientProfile

Client-specific configuration:

```python
class ClientProfile(BaseModel):
    client_id: str = ""
    client_name: str
    client_code: str
    
    # Contact Information
    contact_info: Dict[str, str] = Field(default_factory=dict)
    
    # Client-specific preferences
    download_directory: Optional[Path] = None
    data_format: str = Field(default="parquet", pattern="^(parquet|csv|json|xlsx)$")
    report_style: str = Field(default="standard")
    
    # Design artifacts
    logo_path: str = ""
    brand_colors: List[str] = Field(default_factory=list)
    style_guide: str = ""
    templates: List[str] = Field(default_factory=list)
    
    # Metadata
    industry: str = ""
    project_count: int = Field(default=0, ge=0)
    status: str = Field(default="active", pattern="^(active|inactive|archived)$")
    notes: str = ""
```

## Validation Examples

The system provides comprehensive validation:

```python
# Valid configurations work fine
valid_user = su.EnhancedUserProfile(
    username='testuser',
    default_output_format='pptx',  # Valid format
    default_dpi=150,  # Valid DPI range
    log_level='DEBUG'  # Valid log level
)

# Invalid configurations are rejected
try:
    invalid_user = su.EnhancedUserProfile(
        default_output_format='invalid',  # ❌ Invalid format
        default_dpi=50,  # ❌ Too low
        log_level='INVALID'  # ❌ Invalid level
    )
except ValueError as e:
    print(f"Validation error: {e}")
```

## File Structure

The configuration system stores files in a structured hierarchy:

```
~/.siege_utilities/
└── config/
    ├── user_config.yaml          # User profile
    └── clients/
        ├── ACME.yaml            # Acme Corp client profile
        ├── BETA.yaml            # Beta Industries client profile
        └── ...                  # Additional client profiles
```

### Example YAML Files

**user_config.yaml:**
```yaml
username: john_doe
email: john@example.com
full_name: John Doe
preferred_download_directory: /Users/john/Downloads/siege_utilities
default_output_format: pptx
default_dpi: 300
default_figure_size: [10, 8]
enable_logging: true
log_level: INFO
```

**clients/ACME.yaml:**
```yaml
client_name: Acme Corporation
client_code: ACME
download_directory: /tmp/acme_downloads
industry: Technology
project_count: 10
status: active
contact_info:
  email: contact@acme.com
  phone: "555-0123"
data_format: parquet
report_style: standard
```

## API Reference

### Core Functions

#### `load_user_profile(config_dir: Optional[Path] = None) -> UserProfile`
Load user profile with validation and defaults.

#### `save_user_profile(profile: UserProfile, config_dir: Optional[Path] = None) -> None`
Save user profile with validation.

#### `load_client_profile(client_code: str, config_dir: Optional[Path] = None) -> Optional[ClientProfile]`
Load client profile by code.

#### `save_client_profile(profile: ClientProfile, config_dir: Optional[Path] = None) -> None`
Save client profile with validation.

#### `get_download_directory(client_code: Optional[str] = None, specific_path: Optional[str] = None, config_dir: Optional[Path] = None) -> Path`
Get download directory with hierarchical resolution.

#### `list_client_profiles(config_dir: Optional[Path] = None) -> List[str]`
List available client profile codes.

#### `export_config_yaml(output_path: str, include_api_keys: bool = False, config_dir: Optional[Path] = None) -> None`
Export configuration to YAML file.

#### `import_config_yaml(input_path: str, config_dir: Optional[Path] = None) -> None`
Import configuration from YAML file.

## Testing

The enhanced configuration system includes comprehensive unit tests:

```bash
# Run all config tests
python -m pytest tests/test_enhanced_config.py -v

# Run with config marker
python -m pytest -m config -v

# Run specific test class
python -m pytest tests/test_enhanced_config.py::TestUserProfile -v
```

### Test Coverage

The test suite covers:
- ✅ UserProfile validation and defaults
- ✅ ClientProfile validation and defaults
- ✅ Save/load operations
- ✅ Hierarchical directory resolution
- ✅ Export/import functionality
- ✅ Error handling and edge cases
- ✅ Integration workflows

## Migration from Legacy System

The enhanced system maintains backward compatibility:

```python
# Legacy code still works
from siege_utilities.config.user_config import UserProfile as LegacyUserProfile

# New enhanced system
from siege_utilities.config.enhanced_config import UserProfile as EnhancedUserProfile

# Both can coexist
legacy_profile = LegacyUserProfile()
enhanced_profile = EnhancedUserProfile()
```

## Best Practices

### 1. Use Enhanced Classes for New Code

```python
# ✅ Recommended for new code
user = su.EnhancedUserProfile(username='newuser')
client = su.ClientProfile(client_name='New Client', client_code='NEW')
```

### 2. Validate Early

```python
# ✅ Validate at creation time
try:
    profile = su.EnhancedUserProfile(default_dpi=800)  # Will fail
except ValueError as e:
    print(f"Invalid configuration: {e}")
```

### 3. Use Hierarchical Resolution

```python
# ✅ Let the system handle directory resolution
download_dir = su.get_download_directory(client_code='ACME')
```

### 4. Export Before Major Changes

```python
# ✅ Backup before changes
su.export_config_yaml('/tmp/backup.yaml')
```

## Troubleshooting

### Common Issues

**Q: "UserProfile object has no attribute 'model_dump'"**
A: Use `EnhancedUserProfile` instead of the legacy `UserProfile`.

**Q: "Expecting value: line 1 column 1 (char 0)"**
A: This indicates a YAML parsing issue. Check file permissions and content.

**Q: Validation errors with tuples**
A: The system automatically converts tuples to lists for YAML compatibility.

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger('siege_utilities.config.enhanced_config').setLevel(logging.DEBUG)
```

## Future Enhancements

Planned improvements include:
- 🔐 Encrypted API key storage
- 🌐 Remote configuration sync
- 📊 Configuration analytics
- 🔄 Auto-backup and versioning
- 🎨 Configuration UI

## Related Documentation

- [Basic Setup](Basic-Setup.md)
- [Testing Guide](Testing-Guide.md)
- [Architecture Overview](Architecture/System-Architecture-Overview.md)
- [Client Management](Examples/Client-Management.md)

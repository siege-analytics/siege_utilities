# Admin Module

The `siege_utilities.admin` module provides library administration utilities for managing configuration, profiles, and system settings.

## Profile Location Management

### Default Profile Location

By default, profiles are stored in a gitignored `profiles/` directory within the project root:

```
siege_utilities_verify/
├── profiles/
│   ├── users/
│   │   └── user_config.yaml
│   └── clients/
│       ├── GOV001.yaml
│       └── BIZ001.yaml
└── .gitignore  # Contains "profiles/" to exclude from version control
```

### Custom Profile Locations

You can set custom profile locations for different use cases:

```python
import siege_utilities as su

# Set a custom location for a specific project
custom_location = Path("/path/to/custom/profiles")
su.set_profile_location(custom_location, "project_a")

# Use the custom location
user_profile = su.load_user_profile(config_dir=custom_location / "users")
```

### Profile Location Functions

- `get_default_profile_location()` - Get the default project profiles directory
- `set_profile_location(location, profile_type)` - Set custom profile location
- `get_profile_location(profile_type)` - Get current profile location
- `list_profile_locations()` - List all configured profile locations
- `validate_profile_location(location)` - Validate a profile location is usable

## Default Profile Creation

### Creating Default Profiles

Create example user and client profiles in a specified location:

```python
import siege_utilities as su

# Create default profiles in current directory
user_profile, client_profiles = su.create_default_profiles()

# Create in custom location
custom_location = Path("/path/to/profiles")
user_profile, client_profiles = su.create_default_profiles(custom_location)
```

### Example Client Profiles

The system creates two example client profiles:

1. **Government Agency (GOV001)**
   - Industry: Government
   - Data format: Parquet
   - Brand colors: Blue, White, Red

2. **Private Business (BIZ001)**
   - Industry: Private Sector
   - Data format: CSV
   - Brand colors: Green, White, Gold

## Profile Migration

### Migrating Profiles

Move profiles from one location to another:

```python
import siege_utilities as su

# Basic migration
source_dir = Path("/old/profiles")
target_dir = Path("/new/profiles")
stats = su.migrate_profiles(source_dir, target_dir)

print(f"Migrated {stats['users_migrated']} user profiles")
print(f"Migrated {stats['clients_migrated']} client profiles")
```

### Migration with Backup

Create a backup of the target location before migration:

```python
# Migration with backup
stats = su.migrate_profiles(source_dir, target_dir, backup=True)
# Creates /new/profiles.backup if target exists
```

### Migration Statistics

The migration function returns detailed statistics:

```python
{
    "users_migrated": 1,
    "clients_migrated": 2,
    "files_copied": 3,
    "errors": 0
}
```

## Profile Summary

### Getting Profile Summary

Get detailed information about profiles in a location:

```python
summary = su.get_profile_summary()

print(f"Location: {summary['location']}")
print(f"User profiles: {summary['user_profiles']}")
print(f"Client profiles: {summary['client_profiles']}")
print(f"Client codes: {summary['client_codes']}")
print(f"Total size: {summary['total_size_mb']} MB")
```

### Summary Fields

- `location` - Profile directory path
- `exists` - Whether the directory exists
- `user_profiles` - Number of user profile files
- `client_profiles` - Number of client profile files
- `client_codes` - List of client codes
- `total_size_mb` - Total size in megabytes

## Complete Workflow Example

```python
import siege_utilities as su
from pathlib import Path

# 1. Set up custom profile location
custom_location = Path("/path/to/project/profiles")
su.set_profile_location(custom_location, "project")

# 2. Create default profiles
user_profile, client_profiles = su.create_default_profiles(custom_location)

# 3. Get summary
summary = su.get_profile_summary(custom_location)
print(f"Created {summary['client_profiles']} client profiles")

# 4. Migrate to backup location
backup_location = Path("/backup/profiles")
stats = su.migrate_profiles(custom_location, backup_location, backup=True)

# 5. Load profiles from custom location
user = su.load_user_profile(custom_location / "users")
clients = su.list_client_profiles(custom_location / "clients")

print(f"Loaded user: {user.username}")
print(f"Available clients: {clients}")
```

## Benefits

1. **Gitignored Storage** - Profiles are stored in `profiles/` directory excluded from version control
2. **Flexible Locations** - Support for custom profile locations per project/client
3. **Migration Support** - Easy migration between profile locations with backup
4. **Default Templates** - Pre-configured example profiles for quick setup
5. **Comprehensive Management** - Full CRUD operations for profile locations
6. **Validation** - Built-in validation for profile locations and permissions

## Security Considerations

- Profile directories are gitignored to prevent sensitive data from being committed
- API keys and credentials should be stored in profiles, not in code
- Use `export_config_yaml(include_api_keys=False)` when sharing configurations
- Validate profile locations before use to ensure proper permissions

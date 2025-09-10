# Client and Connection Configuration

This document describes the client and connection configuration functionality in `siege_utilities`, which provides comprehensive management of client profiles, connection profiles, and their associations with projects.

## Overview

The client and connection configuration system allows you to:

- **Manage Client Profiles**: Store client information, contact details, design artifacts, and preferences
- **Manage Connection Profiles**: Configure and persist notebook, Spark, database, and other connections
- **Associate Clients with Projects**: Link clients to specific projects for better organization
- **Search and Filter**: Find clients and connections based on various criteria
- **Validate and Test**: Ensure data integrity and test connection functionality

## Client Profile Management

### Creating Client Profiles

```python
import siege_utilities

# Basic client profile
contact_info = {
    "primary_contact": "John Doe",
    "email": "john.doe@company.com",
    "phone": "+1-555-0123",
    "address": "123 Business St, City, State"
}

client = siege_utilities.create_client_profile(
    "Acme Corporation",
    "ACME001",
    contact_info,
    industry="Technology",
    project_count=5
)
```

### Advanced Client Profiles

```python
# Client with design artifacts and preferences
client = siege_utilities.create_client_profile(
    "Premium Client",
    "PREMIUM001",
    contact_info,
    industry="Finance",
    logo_path="/assets/logos/premium_logo.png",
    brand_colors=["#0066CC", "#FF6600"],
    style_guide="/assets/style_guides/premium_guide.pdf",
    data_format="parquet",
    report_style="executive",
    notification_preferences={
        "email": True,
        "slack": False,
        "frequency": "weekly"
    }
)
```

### Client Profile Structure

```json
{
  "client_id": "uuid-string",
  "client_name": "Company Name",
  "client_code": "COMP001",
  "contact_info": {
    "primary_contact": "Contact Name",
    "email": "email@company.com",
    "phone": "+1-555-0123",
    "address": "Full Address"
  },
  "metadata": {
    "created_date": "2024-01-01T00:00:00",
    "last_updated": "2024-01-01T00:00:00",
    "status": "active",
    "industry": "Technology",
    "project_count": 0,
    "notes": "Additional notes"
  },
  "design_artifacts": {
    "logo_path": "/path/to/logo.png",
    "brand_colors": ["#0066CC", "#FF6600"],
    "style_guide": "/path/to/style_guide.pdf",
    "templates": ["template1.html", "template2.html"]
  },
  "preferences": {
    "data_format": "parquet",
    "report_style": "standard",
    "notification_preferences": {}
  },
  "project_associations": []
}
```

### Managing Client Profiles

```python
# Save client profile
file_path = siege_utilities.save_client_profile(client, "config")

# Load client profile
loaded_client = siege_utilities.load_client_profile("ACME001", "config")

# Update client profile
updates = {
    "contact_info": {"phone": "+1-555-9999"},
    "metadata": {"project_count": 10}
}
success = siege_utilities.update_client_profile("ACME001", updates, "config")

# List all clients
clients = siege_utilities.list_client_profiles("config")

# Search clients
tech_clients = siege_utilities.search_client_profiles(
    "Technology", 
    ["metadata.industry"]
)

# Validate client profile
validation = siege_utilities.validate_client_profile(client)
if validation['is_valid']:
    print("Profile is valid")
else:
    print(f"Issues: {validation['issues']}")
```

## Connection Profile Management

### Creating Connection Profiles

#### Notebook Connections

```python
# Jupyter Lab connection
notebook_conn = siege_utilities.create_connection_profile(
    "Jupyter Lab",
    "notebook",
    {
        "url": "http://localhost:8888",
        "token": "abc123def456",
        "workspace": "/home/user/notebooks"
    },
    auto_connect=True,
    kernel_type="python3",
    preferred_browser="chrome"
)
```

#### Spark Connections

```python
# Spark cluster connection
spark_conn = siege_utilities.create_connection_profile(
    "Spark Cluster",
    "spark",
    {
        "master_url": "spark://spark-master:7077",
        "app_name": "DataAnalytics"
    },
    driver_memory="4g",
    executor_memory="2g",
    spark_home="/opt/spark",
    hadoop_conf_dir="/opt/hadoop/etc/hadoop"
)
```

#### Database Connections

```python
# Database connection
db_conn = siege_utilities.create_connection_profile(
    "PostgreSQL DB",
    "database",
    {
        "connection_string": "postgresql://user:pass@localhost:5432/db"
    },
    connection_pool_size=10,
    ssl_mode="require",
    read_timeout=30
)
```

### Connection Profile Structure

```json
{
  "connection_id": "uuid-string",
  "name": "Connection Name",
  "connection_type": "notebook|spark|database|api",
  "connection_params": {
    "url": "connection_url",
    "token": "auth_token"
  },
  "metadata": {
    "created_date": "2024-01-01T00:00:00",
    "last_used": "2024-01-01T00:00:00",
    "last_connected": "2024-01-01T00:00:00",
    "connection_count": 0,
    "status": "active",
    "auto_connect": false,
    "timeout": 30,
    "retry_attempts": 3
  },
  "security": {
    "encrypted": false,
    "encryption_method": "",
    "credentials_stored": false
  },
  "tags": [],
  "notes": "",
  "notebook_specific": {
    "kernel_type": "python3",
    "auto_start": true,
    "workspace_path": "",
    "preferred_browser": "default"
  }
}
```

### Managing Connection Profiles

```python
# Save connection profile
file_path = siege_utilities.save_connection_profile(conn, "config")

# Load connection profile
loaded_conn = siege_utilities.load_connection_profile(conn_id, "config")

# Find connection by name
conn = siege_utilities.find_connection_by_name("Jupyter Lab", "config")

# List connections (all or by type)
all_connections = siege_utilities.list_connection_profiles("config")
notebook_connections = siege_utilities.list_connection_profiles("notebook", "config")

# Update connection profile
updates = {"metadata": {"status": "inactive"}}
success = siege_utilities.update_connection_profile(conn_id, updates, "config")

# Test connection
result = siege_utilities.test_connection(conn_id, "config")
if result['success']:
    print(f"Connection successful! Response time: {result['response_time_ms']}ms")

# Get connection status
status = siege_utilities.get_connection_status(conn_id, "config")
print(f"Health: {status['health']}, Last connected: {status['last_connected']}")

# Cleanup old connections
removed = siege_utilities.cleanup_old_connections(90, "config")
print(f"Removed {removed} old connections")
```

## Project Association

### Associating Clients with Projects

```python
# Associate client with project
success = siege_utilities.associate_client_with_project(
    "ACME001",  # client_code
    "PROJ001",  # project_code
    "config"
)

# Get all projects for a client
projects = siege_utilities.get_client_project_associations("ACME001", "config")
print(f"Client has {len(projects)} projects: {projects}")
```

## Search and Filtering

### Client Search

```python
# Search by industry
tech_clients = siege_utilities.search_client_profiles(
    "Technology",
    ["metadata.industry"]
)

# Search by name
name_results = siege_utilities.search_client_profiles(
    "Acme",
    ["client_name"]
)

# Search by contact
contact_results = siege_utilities.search_client_profiles(
    "john@example.com",
    ["contact_info.email"]
)
```

### Connection Filtering

```python
# List only notebook connections
notebook_conns = siege_utilities.list_connection_profiles("notebook", "config")

# List only active connections
all_conns = siege_utilities.list_connection_profiles("config")
active_conns = [conn for conn in all_conns if conn['status'] == 'active']
```

## Validation and Testing

### Client Profile Validation

```python
# Validate client profile
validation = siege_utilities.validate_client_profile(client)

if validation['is_valid']:
    print("✅ Profile is valid")
else:
    print("❌ Profile has issues:")
    for issue in validation['issues']:
        print(f"   - {issue}")

if validation['warnings']:
    print("⚠️  Warnings:")
    for warning in validation['warnings']:
        print(f"   - {warning}")
```

### Connection Testing

```python
# Test notebook connection
result = siege_utilities.test_connection(notebook_conn_id, "config")
if result['success']:
    print("✅ Notebook connection successful")
    print(f"   Response time: {result['response_time_ms']}ms")
else:
    print(f"❌ Connection failed: {result['error']}")

# Test Spark connection
result = siege_utilities.test_connection(spark_conn_id, "config")
if result['success']:
    print(f"✅ Spark connection successful (version: {result['spark_version']})")
```

## Configuration Directory Structure

The system creates the following directory structure:

```
config/
├── client_ACME001.json          # Client profiles
├── client_PREMIUM001.json
├── project_ACME001.json         # Project configurations
├── database_analytics.json      # Database configurations
└── connections/                 # Connection profiles
    ├── connection_uuid1.json
    ├── connection_uuid2.json
    └── connection_uuid3.json
```

## Best Practices

### Client Profile Management

1. **Use Consistent Naming**: Establish a naming convention for client codes (e.g., `COMP001`, `COMP002`)
2. **Validate Contact Information**: Always include primary contact and email
3. **Store Design Assets**: Keep logos, style guides, and templates organized
4. **Regular Updates**: Update client information when projects or preferences change

### Connection Management

1. **Secure Credentials**: Use environment variables or encrypted storage for sensitive information
2. **Test Connections**: Regularly test connections to ensure they're working
3. **Monitor Health**: Use connection status to identify problematic connections
4. **Cleanup Old Connections**: Remove unused connections to maintain organization

### Project Association

1. **Clear Relationships**: Associate clients with projects when work begins
2. **Track Associations**: Monitor which clients are working on which projects
3. **Update Counts**: Keep project counts accurate for reporting

## Error Handling

The system provides comprehensive error handling:

```python
try:
    client = siege_utilities.create_client_profile("Name", "CODE", contact_info)
except ValueError as e:
    print(f"Validation error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")

# Check for missing profiles
client = siege_utilities.load_client_profile("NONEXISTENT", "config")
if client is None:
    print("Client profile not found")

# Handle connection test failures
result = siege_utilities.test_connection(conn_id, "config")
if not result['success']:
    print(f"Connection test failed: {result['error']}")
```

## Examples

See the `examples/client_and_connection_demo.py` file for a complete demonstration of all functionality.

## Testing

Run the test suite to ensure everything works correctly:

```bash
pytest tests/test_client_and_connection_config.py -v
```

## Dependencies

The system has minimal external dependencies:

- **Core**: `pathlib`, `json`, `datetime`, `uuid` (all built-in)
- **Optional**: `requests` (for notebook connection testing), `pyspark` (for Spark testing), `sqlalchemy` (for database testing)

## Future Enhancements

Planned improvements include:

- **Encryption**: Secure storage of sensitive connection information
- **Connection Pooling**: Manage multiple active connections
- **Audit Logging**: Track changes to profiles and connections
- **API Integration**: REST API for remote management
- **Web Interface**: Browser-based management interface

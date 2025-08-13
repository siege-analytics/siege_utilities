# Remote Operations Recipe

## Overview
This recipe demonstrates how to use the remote operations utilities in `siege_utilities` for secure remote file transfers, system administration, and distributed computing operations.

## Prerequisites
- Python 3.7+
- `siege_utilities` library installed
- Access to remote systems (SSH, SFTP, etc.)
- Basic understanding of network protocols and security
- Required dependencies: `paramiko`, `fabric`, `boto3` (for AWS)

## Installation
```bash
pip install siege_utilities
pip install paramiko fabric boto3
```

## Basic Remote Operations

### 1. SSH Connection Management

```python
from siege_utilities.files.remote import RemoteOperations
from siege_utilities.config.connections import ConnectionManager

# Initialize remote operations
remote_ops = RemoteOperations()

# Create SSH connection
ssh_config = {
    "hostname": "remote-server.com",
    "username": "admin",
    "password": "password123",  # Use key-based auth in production
    "port": 22,
    "timeout": 30
}

connection = remote_ops.create_ssh_connection(ssh_config)

# Test connection
if connection.is_connected():
    print("SSH connection established successfully")
else:
    print("Failed to establish SSH connection")
```

### 2. Basic Remote Commands

```python
# Execute remote command
result = remote_ops.execute_command(
    connection,
    "ls -la /home/admin"
)

print(f"Command output: {result['output']}")
print(f"Exit code: {result['exit_code']}")
print(f"Error: {result['error']}")

# Execute multiple commands
commands = [
    "cd /tmp",
    "pwd",
    "ls -la"
]

for cmd in commands:
    result = remote_ops.execute_command(connection, cmd)
    print(f"Command '{cmd}': {result['output']}")
```

### 3. File Transfer Operations

```python
# Upload file to remote server
upload_success = remote_ops.upload_file(
    connection,
    local_path="data/local_file.txt",
    remote_path="/home/admin/remote_file.txt"
)

print(f"Upload successful: {upload_success}")

# Download file from remote server
download_success = remote_ops.download_file(
    connection,
    remote_path="/home/admin/remote_file.txt",
    local_path="data/downloaded_file.txt"
)

print(f"Download successful: {download_success}")

# Upload directory recursively
upload_dir_success = remote_ops.upload_directory(
    connection,
    local_dir="data/local_folder/",
    remote_dir="/home/admin/remote_folder/"
)
```

## Advanced Remote Operations

### 1. Batch Operations

```python
# Batch execute commands
command_batch = [
    "mkdir -p /tmp/batch_test",
    "cd /tmp/batch_test",
    "echo 'Hello World' > test.txt",
    "cat test.txt",
    "rm -rf /tmp/batch_test"
]

batch_results = remote_ops.execute_batch_commands(
    connection,
    command_batch,
    stop_on_error=True
)

for i, result in enumerate(batch_results):
    print(f"Command {i+1}: {result['success']}")
    if not result['success']:
        print(f"Error: {result['error']}")

# Batch file operations
file_operations = [
    {
        "operation": "upload",
        "local": "file1.txt",
        "remote": "/remote/file1.txt"
    },
    {
        "operation": "download",
        "remote": "/remote/file2.txt",
        "local": "file2.txt"
    }
]

for op in file_operations:
    if op["operation"] == "upload":
        success = remote_ops.upload_file(
            connection,
            op["local"],
            op["remote"]
        )
    elif op["operation"] == "download":
        success = remote_ops.download_file(
            connection,
            op["remote"],
            op["local"]
        )
    
    print(f"{op['operation']} {'successful' if success else 'failed'}")
```

### 2. Remote File Management

```python
# List remote directory contents
remote_files = remote_ops.list_remote_directory(
    connection,
    "/home/admin/"
)

print("Remote files:")
for file_info in remote_files:
    print(f"  {file_info['name']}: {file_info['size']} bytes")

# Check remote file existence
file_exists = remote_ops.remote_file_exists(
    connection,
    "/home/admin/important_file.txt"
)

print(f"File exists: {file_exists}")

# Get remote file information
file_info = remote_ops.get_remote_file_info(
    connection,
    "/home/admin/important_file.txt"
)

if file_info:
    print(f"File size: {file_info['size']} bytes")
    print(f"Modified: {file_info['modified']}")
    print(f"Permissions: {file_info['permissions']}")

# Create remote directory
mkdir_success = remote_ops.create_remote_directory(
    connection,
    "/home/admin/new_folder"
)

# Remove remote file
rm_success = remote_ops.remove_remote_file(
    connection,
    "/home/admin/old_file.txt"
)
```

### 3. Remote System Monitoring

```python
# Get system information
system_info = remote_ops.get_system_info(connection)
print(f"OS: {system_info['os']}")
print(f"Kernel: {system_info['kernel']}")
print(f"Architecture: {system_info['architecture']}")

# Get disk usage
disk_usage = remote_ops.get_disk_usage(connection, "/")
print(f"Total: {disk_usage['total']} GB")
print(f"Used: {disk_usage['used']} GB")
print(f"Available: {disk_usage['available']} GB")

# Get memory usage
memory_usage = remote_ops.get_memory_usage(connection)
print(f"Total RAM: {memory_usage['total']} MB")
print(f"Used RAM: {memory_usage['used']} MB")
print(f"Free RAM: {memory_usage['free']} MB")

# Get process information
processes = remote_ops.get_process_list(connection, limit=10)
print("Top processes:")
for proc in processes:
    print(f"  {proc['pid']}: {proc['name']} - {proc['cpu']}% CPU")
```

## Security and Authentication

### 1. Key-Based Authentication

```python
# Use SSH key for authentication
key_config = {
    "hostname": "secure-server.com",
    "username": "admin",
    "key_filename": "~/.ssh/id_rsa",
    "port": 22,
    "timeout": 30
}

key_connection = remote_ops.create_ssh_connection(key_config)

# Use passphrase-protected key
passphrase_config = {
    "hostname": "secure-server.com",
    "username": "admin",
    "key_filename": "~/.ssh/id_rsa",
    "passphrase": "your_passphrase",
    "port": 22
}

passphrase_connection = remote_ops.create_ssh_connection(passphrase_config)
```

### 2. Connection Security

```python
# Configure connection security
secure_config = {
    "hostname": "secure-server.com",
    "username": "admin",
    "key_filename": "~/.ssh/id_rsa",
    "port": 22,
    "timeout": 30,
    "allow_agent": False,
    "look_for_keys": False,
    "banner_timeout": 60,
    "auth_timeout": 60
}

# Verify host key
secure_config["host_key_verification"] = True
secure_config["known_hosts_file"] = "~/.ssh/known_hosts"

secure_connection = remote_ops.create_ssh_connection(secure_config)
```

### 3. Multi-Factor Authentication

```python
# Configure MFA for SSH
mfa_config = {
    "hostname": "mfa-server.com",
    "username": "admin",
    "key_filename": "~/.ssh/id_rsa",
    "mfa_enabled": True,
    "mfa_method": "totp",  # or "sms", "email"
    "mfa_secret": "your_mfa_secret"
}

mfa_connection = remote_ops.create_ssh_connection(mfa_config)
```

## Performance Optimization

### 1. Connection Pooling

```python
from siege_utilities.files.remote import ConnectionPool

# Create connection pool
pool = ConnectionPool(
    max_connections=5,
    connection_timeout=30,
    idle_timeout=300
)

# Get connection from pool
connection = pool.get_connection(ssh_config)

# Use connection
result = remote_ops.execute_command(connection, "hostname")

# Return connection to pool
pool.return_connection(connection)

# Close pool when done
pool.close()
```

### 2. Parallel Operations

```python
from concurrent.futures import ThreadPoolExecutor
import threading

def execute_remote_task(server_config, command):
    """Execute command on remote server"""
    connection = remote_ops.create_ssh_connection(server_config)
    try:
        result = remote_ops.execute_command(connection, command)
        return {"server": server_config["hostname"], "result": result}
    finally:
        connection.close()

# Execute commands on multiple servers in parallel
servers = [
    {"hostname": "server1.com", "username": "admin", "key_filename": "~/.ssh/id_rsa"},
    {"hostname": "server2.com", "username": "admin", "key_filename": "~/.ssh/id_rsa"},
    {"hostname": "server3.com", "username": "admin", "key_filename": "~/.ssh/id_rsa"}
]

command = "uptime"

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(execute_remote_task, server, command)
        for server in servers
    ]
    
    results = [future.result() for future in futures]

for result in results:
    print(f"{result['server']}: {result['result']['output']}")
```

### 3. Compression and Optimization

```python
# Upload with compression
compressed_upload = remote_ops.upload_file(
    connection,
    "data/large_file.txt",
    "/remote/large_file.txt.gz",
    compress=True,
    compression_type="gzip"
)

# Download with compression
compressed_download = remote_ops.download_file(
    connection,
    "/remote/large_file.txt.gz",
    "data/downloaded_file.txt",
    decompress=True
)

# Use rsync for efficient file transfers
rsync_success = remote_ops.rsync_directory(
    connection,
    "data/local_folder/",
    "/remote/folder/",
    delete_remote=True,
    preserve_permissions=True
)
```

## Error Handling and Recovery

### 1. Connection Retry Logic

```python
from siege_utilities.core.logging import Logger

logger = Logger("remote_operations")

def execute_with_retry(connection_func, max_retries=3, delay=5):
    """Execute remote operation with retry logic"""
    
    for attempt in range(max_retries):
        try:
            return connection_func()
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                logger.error("All retry attempts failed")
                raise

# Use retry logic
def upload_file_with_retry():
    return remote_ops.upload_file(
        connection,
        "data/file.txt",
        "/remote/file.txt"
    )

success = execute_with_retry(upload_file_with_retry)
```

### 2. Connection Health Monitoring

```python
class ConnectionMonitor:
    def __init__(self, connection, check_interval=60):
        self.connection = connection
        self.check_interval = check_interval
        self.last_check = time.time()
        self.logger = Logger("connection_monitor")
    
    def is_healthy(self):
        """Check if connection is still healthy"""
        current_time = time.time()
        
        if current_time - self.last_check > self.check_interval:
            try:
                # Simple health check
                result = remote_ops.execute_command(self.connection, "echo 'health_check'")
                self.last_check = current_time
                return result['exit_code'] == 0
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                return False
        
        return True
    
    def ensure_healthy(self):
        """Ensure connection is healthy, reconnect if needed"""
        if not self.is_healthy():
            self.logger.warning("Connection unhealthy, attempting reconnect...")
            try:
                self.connection.close()
                self.connection = remote_ops.create_ssh_connection(ssh_config)
                self.logger.info("Connection reestablished")
            except Exception as e:
                self.logger.error(f"Reconnection failed: {e}")
                raise

# Use connection monitor
monitor = ConnectionMonitor(connection)

# Before each operation
monitor.ensure_healthy()
result = remote_ops.execute_command(connection, "hostname")
```

## Integration Examples

### 1. With Configuration Management

```python
from siege_utilities.config.connections import ConnectionManager

# Load connections from configuration
conn_manager = ConnectionManager()
connections = conn_manager.load_connections("config/connections.yaml")

# Execute commands on all configured servers
for conn_name, conn_config in connections.items():
    print(f"Processing {conn_name}...")
    
    connection = remote_ops.create_ssh_connection(conn_config)
    try:
        # Update system packages
        result = remote_ops.execute_command(connection, "sudo apt update")
        print(f"Update result: {result['output']}")
        
        # Check disk space
        disk_usage = remote_ops.get_disk_usage(connection, "/")
        print(f"Disk usage: {disk_usage['used']}/{disk_usage['total']} GB")
        
    finally:
        connection.close()
```

### 2. With CI/CD Pipelines

```python
def deploy_to_servers(servers, deployment_config):
    """Deploy application to multiple servers"""
    
    logger = Logger("deployment")
    logger.info(f"Starting deployment to {len(servers)} servers")
    
    deployment_results = []
    
    for server in servers:
        logger.info(f"Deploying to {server['hostname']}")
        
        connection = remote_ops.create_ssh_connection(server)
        try:
            # Create deployment directory
            remote_ops.create_remote_directory(connection, "/opt/app")
            
            # Upload application files
            remote_ops.upload_directory(
                connection,
                "build/",
                "/opt/app/"
            )
            
            # Set permissions
            remote_ops.execute_command(connection, "chmod +x /opt/app/*.sh")
            
            # Restart services
            remote_ops.execute_command(connection, "sudo systemctl restart app")
            
            deployment_results.append({
                "server": server['hostname'],
                "status": "success"
            })
            
            logger.info(f"Deployment to {server['hostname']} successful")
            
        except Exception as e:
            logger.error(f"Deployment to {server['hostname']} failed: {e}")
            deployment_results.append({
                "server": server['hostname'],
                "status": "failed",
                "error": str(e)
            })
        
        finally:
            connection.close()
    
    return deployment_results

# Execute deployment
servers = [
    {"hostname": "prod1.example.com", "username": "deploy", "key_filename": "~/.ssh/deploy_key"},
    {"hostname": "prod2.example.com", "username": "deploy", "key_filename": "~/.ssh/deploy_key"}
]

deployment_config = {
    "app_name": "myapp",
    "version": "1.0.0",
    "environment": "production"
}

results = deploy_to_servers(servers, deployment_config)
```

### 3. With Monitoring Systems

```python
def collect_system_metrics(servers):
    """Collect system metrics from multiple servers"""
    
    metrics = {}
    
    for server in servers:
        connection = remote_ops.create_ssh_connection(server)
        try:
            server_metrics = {}
            
            # System info
            system_info = remote_ops.get_system_info(connection)
            server_metrics['system'] = system_info
            
            # Disk usage
            disk_usage = remote_ops.get_disk_usage(connection, "/")
            server_metrics['disk'] = disk_usage
            
            # Memory usage
            memory_usage = remote_ops.get_memory_usage(connection)
            server_metrics['memory'] = memory_usage
            
            # Process count
            result = remote_ops.execute_command(connection, "ps aux | wc -l")
            server_metrics['process_count'] = int(result['output'].strip())
            
            metrics[server['hostname']] = server_metrics
            
        finally:
            connection.close()
    
    return metrics

# Collect metrics
servers = [
    {"hostname": "monitor1.example.com", "username": "monitor", "key_filename": "~/.ssh/monitor_key"},
    {"hostname": "monitor2.example.com", "username": "monitor", "key_filename": "~/.ssh/monitor_key"}
]

metrics = collect_system_metrics(servers)

# Process metrics
for server, server_metrics in metrics.items():
    print(f"\n{server}:")
    print(f"  OS: {server_metrics['system']['os']}")
    print(f"  Disk: {server_metrics['disk']['used']}/{server_metrics['disk']['total']} GB")
    print(f"  Memory: {server_metrics['memory']['used']}/{server_metrics['memory']['total']} MB")
    print(f"  Processes: {server_metrics['process_count']}")
```

## Best Practices

### 1. Security
- Always use key-based authentication in production
- Implement proper access controls and user management
- Regularly rotate SSH keys and credentials
- Use connection timeouts and rate limiting

### 2. Performance
- Implement connection pooling for multiple operations
- Use compression for large file transfers
- Implement parallel processing for multiple servers
- Monitor connection health and implement reconnection logic

### 3. Error Handling
- Always implement proper error handling and logging
- Use retry logic for transient failures
- Implement circuit breakers for failing connections
- Provide meaningful error messages and context

### 4. Monitoring
- Monitor connection health and performance
- Implement logging for all remote operations
- Track operation success rates and response times
- Set up alerts for connection failures

## Troubleshooting

### Common Issues

1. **Connection Timeouts**
   ```python
   # Increase timeout values
   ssh_config["timeout"] = 60
   ssh_config["auth_timeout"] = 60
   ```

2. **Authentication Failures**
   ```python
   # Verify key permissions and ownership
   import os
   os.chmod("~/.ssh/id_rsa", 0o600)
   os.chown("~/.ssh/id_rsa", os.getuid(), os.getgid())
   ```

3. **File Transfer Issues**
   ```python
   # Check disk space and permissions
   disk_usage = remote_ops.get_disk_usage(connection, "/")
   if disk_usage['available'] < required_space:
       print("Insufficient disk space")
   ```

## Conclusion

The remote operations utilities in `siege_utilities` provide comprehensive tools for secure remote system administration and file management. By following this recipe, you can:

- Establish secure SSH connections with proper authentication
- Execute remote commands and manage files efficiently
- Implement robust error handling and recovery mechanisms
- Optimize performance with connection pooling and parallel processing
- Integrate remote operations into larger automation workflows

Remember to always prioritize security, implement proper error handling, and monitor connection health for reliable remote operations.

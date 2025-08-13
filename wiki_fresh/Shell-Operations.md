# Shell Operations Recipe

## Overview
This recipe demonstrates how to use the shell operations utilities in `siege_utilities` for executing shell commands, managing processes, and automating system administration tasks.

## Prerequisites
- Python 3.7+
- `siege_utilities` library installed
- Basic understanding of shell commands and process management
- Required dependencies: `psutil`, `subprocess`

## Installation
```bash
pip install siege_utilities
pip install psutil
```

## Basic Shell Operations

### 1. Simple Command Execution

```python
from siege_utilities.files.shell import ShellOperations

# Initialize shell operations
shell_ops = ShellOperations()

# Execute a simple command
result = shell_ops.execute_command("ls -la")
print(f"Command output: {result['output']}")
print(f"Exit code: {result['exit_code']}")
print(f"Error: {result['error']}")

# Execute command with working directory
result = shell_ops.execute_command(
    "pwd",
    working_directory="/tmp"
)
print(f"Working directory: {result['output']}")

# Execute command with environment variables
env_vars = {"CUSTOM_VAR": "value", "DEBUG": "1"}
result = shell_ops.execute_command(
    "echo $CUSTOM_VAR",
    environment=env_vars
)
print(f"Environment variable: {result['output']}")
```

### 2. Command Execution with Options

```python
# Execute command with timeout
result = shell_ops.execute_command(
    "sleep 10",
    timeout=5
)
print(f"Command timed out: {result['timeout']}")

# Execute command with shell expansion
result = shell_ops.execute_command(
    "echo $HOME",
    shell=True
)
print(f"Home directory: {result['output']}")

# Execute command and capture stderr separately
result = shell_ops.execute_command(
    "ls /nonexistent",
    capture_stderr=True
)
print(f"Stdout: {result['output']}")
print(f"Stderr: {result['error']}")
```

### 3. Batch Command Execution

```python
# Execute multiple commands
commands = [
    "mkdir -p /tmp/test_dir",
    "cd /tmp/test_dir",
    "echo 'Hello World' > test.txt",
    "cat test.txt",
    "rm -rf /tmp/test_dir"
]

for cmd in commands:
    result = shell_ops.execute_command(cmd)
    print(f"Command '{cmd}': {result['exit_code']}")

# Execute commands as a single shell script
script = """
mkdir -p /tmp/batch_test
cd /tmp/batch_test
echo "Hello World" > test.txt
cat test.txt
rm -rf /tmp/batch_test
"""

result = shell_ops.execute_script(script)
print(f"Script execution: {result['exit_code']}")
```

## Advanced Shell Operations

### 1. Process Management

```python
# Start a background process
process = shell_ops.start_process(
    "tail -f /var/log/syslog",
    background=True
)

print(f"Process started with PID: {process['pid']}")

# Check if process is running
is_running = shell_ops.is_process_running(process['pid'])
print(f"Process running: {is_running}")

# Get process information
process_info = shell_ops.get_process_info(process['pid'])
print(f"Process name: {process_info['name']}")
print(f"CPU usage: {process_info['cpu_percent']}%")
print(f"Memory usage: {process_info['memory_info']['rss']} bytes")

# Terminate process
shell_ops.terminate_process(process['pid'])
```

### 2. File and Directory Operations

```python
# Create directory structure
dirs_created = shell_ops.create_directories([
    "/tmp/test_project",
    "/tmp/test_project/src",
    "/tmp/test_project/docs",
    "/tmp/test_project/tests"
])
print(f"Directories created: {dirs_created}")

# Copy files with shell commands
copy_result = shell_ops.copy_files(
    source="/etc/passwd",
    destination="/tmp/passwd_copy",
    preserve_permissions=True
)
print(f"File copied: {copy_result}")

# Remove files and directories
removal_result = shell_ops.remove_paths([
    "/tmp/test_project",
    "/tmp/passwd_copy"
])
print(f"Paths removed: {removal_result}")

# Check file existence
file_exists = shell_ops.file_exists("/etc/passwd")
print(f"File exists: {file_exists}")
```

### 3. System Information

```python
# Get system information
system_info = shell_ops.get_system_info()
print(f"OS: {system_info['os']}")
print(f"Kernel: {system_info['kernel']}")
print(f"Architecture: {system_info['architecture']}")

# Get disk usage
disk_usage = shell_ops.get_disk_usage("/")
print(f"Total: {disk_usage['total']} GB")
print(f"Used: {disk_usage['used']} GB")
print(f"Available: {disk_usage['available']} GB")

# Get memory usage
memory_usage = shell_ops.get_memory_usage()
print(f"Total RAM: {memory_usage['total']} MB")
print(f"Used RAM: {memory_usage['used']} MB")
print(f"Free RAM: {memory_usage['free']} MB")

# Get network information
network_info = shell_ops.get_network_info()
for interface, info in network_info.items():
    print(f"Interface {interface}: {info['addresses']}")
```

## Process Monitoring and Control

### 1. Process Monitoring

```python
# Monitor specific process
def monitor_process(pid):
    while True:
        if shell_ops.is_process_running(pid):
            info = shell_ops.get_process_info(pid)
            print(f"PID {pid}: CPU {info['cpu_percent']}%, "
                  f"Memory {info['memory_info']['rss']} bytes")
        else:
            print(f"Process {pid} is no longer running")
            break
        time.sleep(1)

# Start monitoring in background
import threading
monitor_thread = threading.Thread(
    target=monitor_process,
    args=(process['pid'],)
)
monitor_thread.daemon = True
monitor_thread.start()
```

### 2. Process Control

```python
# Suspend and resume process
shell_ops.suspend_process(process['pid'])
print("Process suspended")

time.sleep(2)
shell_ops.resume_process(process['pid'])
print("Process resumed")

# Change process priority
shell_ops.set_process_priority(process['pid'], priority="high")
print("Process priority set to high")

# Kill process group
shell_ops.kill_process_group(process['pid'])
print("Process group terminated")
```

### 3. Process Discovery

```python
# Find processes by name
python_processes = shell_ops.find_processes_by_name("python")
print(f"Found {len(python_processes)} Python processes")

for proc in python_processes:
    print(f"PID {proc['pid']}: {proc['name']}")

# Find processes by pattern
matching_processes = shell_ops.find_processes_by_pattern(".*python.*")
print(f"Found {len(matching_processes)} matching processes")

# Get all running processes
all_processes = shell_ops.get_all_processes(limit=20)
print("Top 20 processes by CPU usage:")
for proc in sorted(all_processes, key=lambda x: x['cpu_percent'], reverse=True):
    print(f"  {proc['pid']}: {proc['name']} - {proc['cpu_percent']}% CPU")
```

## Shell Scripting and Automation

### 1. Shell Script Execution

```python
# Execute shell script from file
script_result = shell_ops.execute_script_file("scripts/backup.sh")
print(f"Script execution: {script_result['exit_code']}")

# Execute inline script with variables
script_with_vars = """
#!/bin/bash
BACKUP_DIR="$1"
SOURCE_DIR="$2"
DATE=$(date +%Y%m%d_%H%M%S)

echo "Starting backup from $SOURCE_DIR to $BACKUP_DIR"
tar -czf "$BACKUP_DIR/backup_$DATE.tar.gz" "$SOURCE_DIR"
echo "Backup completed: backup_$DATE.tar.gz"
"""

result = shell_ops.execute_script(
    script_with_vars,
    arguments=["/backup", "/home/user"],
    working_directory="/tmp"
)
print(f"Backup script result: {result['output']}")
```

### 2. Conditional Execution

```python
# Execute command only if condition is met
def backup_if_needed():
    # Check if backup is needed
    last_backup = shell_ops.execute_command(
        "find /backup -name '*.tar.gz' -mtime -1 | wc -l"
    )
    
    if int(last_backup['output'].strip()) == 0:
        print("Backup needed, executing...")
        result = shell_ops.execute_command("backup_script.sh")
        return result
    else:
        print("Backup not needed")
        return None

# Execute with error handling
try:
    backup_result = backup_if_needed()
    if backup_result:
        print(f"Backup completed: {backup_result['exit_code']}")
except Exception as e:
    print(f"Backup failed: {e}")
```

### 3. Automated System Maintenance

```python
def system_maintenance():
    """Perform automated system maintenance tasks"""
    
    maintenance_tasks = [
        ("Update package list", "sudo apt update"),
        ("Upgrade packages", "sudo apt upgrade -y"),
        ("Clean package cache", "sudo apt clean"),
        ("Remove old kernels", "sudo apt autoremove -y"),
        ("Check disk usage", "df -h"),
        ("Check memory usage", "free -h")
    ]
    
    results = {}
    
    for task_name, command in maintenance_tasks:
        print(f"Executing: {task_name}")
        try:
            result = shell_ops.execute_command(command, timeout=300)
            results[task_name] = {
                'success': result['exit_code'] == 0,
                'output': result['output'],
                'error': result['error']
            }
            print(f"  {task_name}: {'SUCCESS' if result['exit_code'] == 0 else 'FAILED'}")
        except Exception as e:
            results[task_name] = {
                'success': False,
                'error': str(e)
            }
            print(f"  {task_name}: ERROR - {e}")
    
    return results

# Run maintenance
maintenance_results = system_maintenance()
```

## Performance and Optimization

### 1. Parallel Execution

```python
from concurrent.futures import ThreadPoolExecutor
import threading

def execute_command_parallel(command):
    """Execute command and return result"""
    return shell_ops.execute_command(command)

# Execute multiple commands in parallel
commands = [
    "sleep 2 && echo 'Task 1'",
    "sleep 3 && echo 'Task 2'",
    "sleep 1 && echo 'Task 3'",
    "sleep 4 && echo 'Task 4'"
]

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(execute_command_parallel, cmd)
        for cmd in commands
    ]
    
    results = [future.result() for future in futures]

for i, result in enumerate(results):
    print(f"Task {i+1}: {result['output'].strip()}")
```

### 2. Command Caching

```python
class CommandCache:
    def __init__(self, cache_duration=300):  # 5 minutes
        self.cache = {}
        self.cache_duration = cache_duration
    
    def execute_cached(self, command, **kwargs):
        """Execute command with caching"""
        cache_key = f"{command}_{hash(str(kwargs))}"
        current_time = time.time()
        
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if current_time - timestamp < self.cache_duration:
                print(f"Using cached result for: {command}")
                return cached_result
        
        # Execute command and cache result
        result = shell_ops.execute_command(command, **kwargs)
        self.cache[cache_key] = (result, current_time)
        return result
    
    def clear_cache(self):
        """Clear the command cache"""
        self.cache.clear()

# Use command cache
command_cache = CommandCache()
result1 = command_cache.execute_cached("uname -a")
result2 = command_cache.execute_cached("uname -a")  # Uses cache
```

### 3. Resource Monitoring

```python
def monitor_system_resources(duration=60):
    """Monitor system resources for specified duration"""
    
    start_time = time.time()
    monitoring_data = []
    
    while time.time() - start_time < duration:
        # Collect system metrics
        cpu_percent = shell_ops.get_cpu_usage()
        memory_usage = shell_ops.get_memory_usage()
        disk_usage = shell_ops.get_disk_usage("/")
        
        monitoring_data.append({
            'timestamp': time.time(),
            'cpu_percent': cpu_percent,
            'memory_used': memory_usage['used'],
            'memory_total': memory_usage['total'],
            'disk_used': disk_usage['used'],
            'disk_total': disk_usage['total']
        })
        
        time.sleep(1)
    
    return monitoring_data

# Monitor system for 1 minute
resource_data = monitor_system_resources(60)
print(f"Collected {len(resource_data)} data points")
```

## Error Handling and Recovery

### 1. Command Execution with Retry

```python
def execute_with_retry(command, max_retries=3, delay=5):
    """Execute command with retry logic"""
    
    for attempt in range(max_retries):
        try:
            result = shell_ops.execute_command(command)
            if result['exit_code'] == 0:
                return result
            else:
                print(f"Command failed (attempt {attempt + 1}): {result['error']}")
        except Exception as e:
            print(f"Execution error (attempt {attempt + 1}): {e}")
        
        if attempt < max_retries - 1:
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)
            delay *= 2  # Exponential backoff
    
    raise Exception(f"Command failed after {max_retries} attempts")

# Use retry logic
try:
    result = execute_with_retry("some_command_that_might_fail")
    print(f"Command succeeded: {result['output']}")
except Exception as e:
    print(f"All attempts failed: {e}")
```

### 2. Process Recovery

```python
class ProcessManager:
    def __init__(self, process_name, command, max_restarts=3):
        self.process_name = process_name
        self.command = command
        self.max_restarts = max_restarts
        self.restart_count = 0
        self.process_pid = None
    
    def start_process(self):
        """Start the managed process"""
        try:
            result = shell_ops.start_process(self.command, background=True)
            self.process_pid = result['pid']
            print(f"Started {self.process_name} with PID {self.process_pid}")
            return True
        except Exception as e:
            print(f"Failed to start {self.process_name}: {e}")
            return False
    
    def monitor_and_restart(self):
        """Monitor process and restart if needed"""
        while True:
            if not shell_ops.is_process_running(self.process_pid):
                print(f"{self.process_name} process died")
                
                if self.restart_count < self.max_restarts:
                    self.restart_count += 1
                    print(f"Restarting {self.process_name} (attempt {self.restart_count})")
                    
                    if self.start_process():
                        print(f"{self.process_name} restarted successfully")
                    else:
                        print(f"Failed to restart {self.process_name}")
                else:
                    print(f"Max restart attempts reached for {self.process_name}")
                    break
            
            time.sleep(5)

# Use process manager
manager = ProcessManager("my_service", "python my_service.py")
manager.start_process()
manager.monitor_and_restart()
```

## Integration Examples

### 1. With Configuration Management

```python
import yaml

def load_and_execute_config(config_file):
    """Load configuration and execute commands"""
    
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    results = {}
    
    for section_name, section_config in config.items():
        print(f"Processing section: {section_name}")
        section_results = []
        
        for command_config in section_config['commands']:
            command = command_config['command']
            description = command_config.get('description', '')
            working_dir = command_config.get('working_directory', None)
            
            print(f"  Executing: {description or command}")
            
            try:
                result = shell_ops.execute_command(
                    command,
                    working_directory=working_dir
                )
                
                section_results.append({
                    'command': command,
                    'description': description,
                    'success': result['exit_code'] == 0,
                    'output': result['output'],
                    'error': result['error']
                })
                
            except Exception as e:
                section_results.append({
                    'command': command,
                    'description': description,
                    'success': False,
                    'error': str(e)
                })
        
        results[section_name] = section_results
    
    return results

# Example config.yaml:
# system_checks:
#   commands:
#     - command: "df -h"
#       description: "Check disk usage"
#     - command: "free -h"
#       description: "Check memory usage"
#       working_directory: "/tmp"

# Execute configuration
config_results = load_and_execute_config("config.yaml")
```

### 2. With Logging and Monitoring

```python
from siege_utilities.core.logging import Logger

class LoggedShellOperations:
    def __init__(self):
        self.logger = Logger("shell_operations")
        self.shell_ops = ShellOperations()
    
    def execute_command_logged(self, command, **kwargs):
        """Execute command with comprehensive logging"""
        
        self.logger.info(f"Executing command: {command}")
        start_time = time.time()
        
        try:
            result = self.shell_ops.execute_command(command, **kwargs)
            execution_time = time.time() - start_time
            
            if result['exit_code'] == 0:
                self.logger.info(
                    f"Command completed successfully in {execution_time:.2f}s",
                    extra={
                        'command': command,
                        'execution_time': execution_time,
                        'output_length': len(result['output'])
                    }
                )
            else:
                self.logger.warning(
                    f"Command completed with exit code {result['exit_code']}",
                    extra={
                        'command': command,
                        'exit_code': result['exit_code'],
                        'error': result['error']
                    }
                )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(
                f"Command execution failed: {e}",
                extra={
                    'command': command,
                    'execution_time': execution_time,
                    'error': str(e)
                }
            )
            raise

# Use logged shell operations
logged_shell = LoggedShellOperations()
result = logged_shell.execute_command_logged("ls -la /etc")
```

### 3. With Scheduled Tasks

```python
import schedule
import time

class ScheduledShellTasks:
    def __init__(self):
        self.shell_ops = ShellOperations()
        self.logger = Logger("scheduled_tasks")
    
    def daily_backup(self):
        """Perform daily backup task"""
        self.logger.info("Starting daily backup")
        
        try:
            # Create backup directory
            shell_ops.create_directories(["/backup/daily"])
            
            # Perform backup
            result = shell_ops.execute_command(
                "tar -czf /backup/daily/backup_$(date +%Y%m%d).tar.gz /home/user"
            )
            
            if result['exit_code'] == 0:
                self.logger.info("Daily backup completed successfully")
            else:
                self.logger.error(f"Daily backup failed: {result['error']}")
                
        except Exception as e:
            self.logger.error(f"Daily backup error: {e}")
    
    def weekly_cleanup(self):
        """Perform weekly cleanup task"""
        self.logger.info("Starting weekly cleanup")
        
        try:
            # Remove old backups (older than 30 days)
            result = shell_ops.execute_command(
                "find /backup -name '*.tar.gz' -mtime +30 -delete"
            )
            
            # Clean temporary files
            shell_ops.execute_command("rm -rf /tmp/*")
            
            self.logger.info("Weekly cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Weekly cleanup error: {e}")
    
    def start_scheduler(self):
        """Start the task scheduler"""
        schedule.every().day.at("02:00").do(self.daily_backup)
        schedule.every().sunday.at("03:00").do(self.weekly_cleanup)
        
        self.logger.info("Task scheduler started")
        
        while True:
            schedule.run_pending()
            time.sleep(60)

# Start scheduled tasks
scheduler = ScheduledShellTasks()
scheduler.start_scheduler()
```

## Best Practices

### 1. Security
- Always validate and sanitize command inputs
- Use appropriate user permissions for commands
- Avoid executing commands with user-provided input
- Implement proper access controls

### 2. Performance
- Use parallel execution for independent commands
- Implement command caching for repeated operations
- Monitor resource usage during execution
- Use appropriate timeouts for long-running commands

### 3. Error Handling
- Always check command exit codes
- Implement retry logic for transient failures
- Log all command executions and results
- Provide meaningful error messages

### 4. Monitoring
- Monitor process health and resource usage
- Implement logging for all shell operations
- Track command success rates and execution times
- Set up alerts for critical failures

## Troubleshooting

### Common Issues

1. **Command Not Found**
   ```python
   # Check command availability
   result = shell_ops.execute_command("which command_name")
   if result['exit_code'] != 0:
       print("Command not found in PATH")
   ```

2. **Permission Denied**
   ```python
   # Check user permissions
   result = shell_ops.execute_command("id")
   print(f"Current user: {result['output']}")
   ```

3. **Process Hanging**
   ```python
   # Use timeout for long-running commands
   result = shell_ops.execute_command("long_running_command", timeout=60)
   ```

## Conclusion

The shell operations utilities in `siege_utilities` provide comprehensive tools for executing shell commands and managing processes. By following this recipe, you can:

- Execute shell commands safely and efficiently
- Manage processes and monitor system resources
- Implement automated system maintenance tasks
- Build robust shell automation workflows
- Integrate shell operations with other system components

Remember to always prioritize security, implement proper error handling, and monitor system resources for reliable shell operations.

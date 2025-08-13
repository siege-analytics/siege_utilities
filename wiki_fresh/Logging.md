# Logging Recipe

## Overview
This recipe demonstrates how to use the logging utilities in `siege_utilities` for comprehensive application logging, debugging, monitoring, and audit trails.

## Prerequisites
- Python 3.7+
- `siege_utilities` library installed
- Basic understanding of logging concepts
- Required dependencies: `colorama` (optional, for colored output)

## Installation
```bash
pip install siege_utilities
pip install colorama  # Optional, for colored console output
```

## Basic Logging Setup

### 1. Simple Logger Initialization

```python
from siege_utilities.core.logging import Logger

# Create a basic logger
logger = Logger("my_application")
logger.info("Application started")
logger.warning("This is a warning message")
logger.error("An error occurred")
logger.debug("Debug information")
```

### 2. Logger with Configuration

```python
# Create logger with custom configuration
logger = Logger(
    name="data_processor",
    level="INFO",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    output_file="logs/app.log"
)

# Log different levels
logger.info("Data processing started")
logger.debug("Processing row 1 of 1000")
logger.warning("Missing data in row 45")
logger.error("Failed to process file: data.csv")
```

### 3. Multiple Output Destinations

```python
# Create logger with multiple outputs
logger = Logger(
    name="web_service",
    level="DEBUG",
    console_output=True,
    file_output=True,
    output_file="logs/web_service.log",
    max_file_size="10MB",
    backup_count=5
)

# Log to both console and file
logger.info("Web service started on port 8080")
logger.debug("Received request: GET /api/users")
```

## Advanced Logging Features

### 1. Structured Logging

```python
# Log structured data
user_data = {
    "user_id": 12345,
    "action": "login",
    "ip_address": "192.168.1.100",
    "timestamp": "2024-01-15T10:30:00Z"
}

logger.info("User action", extra=user_data)

# Log with context
logger.info("Database query executed", extra={
    "query": "SELECT * FROM users WHERE id = %s",
    "parameters": [12345],
    "execution_time": 0.045,
    "rows_returned": 1
})
```

### 2. Logging with Exception Handling

```python
try:
    # Some operation that might fail
    result = 10 / 0
except Exception as e:
    logger.error("Division by zero error", exc_info=True)
    logger.error(f"Error details: {str(e)}", extra={
        "operation": "division",
        "operands": [10, 0],
        "error_type": type(e).__name__
    })
```

### 3. Conditional Logging

```python
# Log only when certain conditions are met
if logger.isEnabledFor("DEBUG"):
    logger.debug("Expensive debug operation", extra={
        "memory_usage": get_memory_usage(),
        "cpu_usage": get_cpu_usage()
    })

# Log based on application state
if is_production_environment():
    logger.setLevel("WARNING")  # Reduce log verbosity in production
else:
    logger.setLevel("DEBUG")    # Full logging in development
```

## Logging Configuration

### 1. Configuration from File

```python
# Load configuration from YAML file
logger = Logger.from_config("config/logging_config.yaml")

# Example logging_config.yaml:
# name: application_logger
# level: INFO
# format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# console_output: true
# file_output: true
# output_file: logs/app.log
# max_file_size: 10MB
# backup_count: 5
# date_format: "%Y-%m-%d %H:%M:%S"
```

### 2. Environment-Based Configuration

```python
import os

# Configure logging based on environment
env = os.getenv("ENVIRONMENT", "development")

if env == "production":
    logger = Logger(
        name="production_app",
        level="WARNING",
        console_output=False,
        file_output=True,
        output_file="logs/production.log"
    )
elif env == "staging":
    logger = Logger(
        name="staging_app",
        level="INFO",
        console_output=True,
        file_output=True,
        output_file="logs/staging.log"
    )
else:  # development
    logger = Logger(
        name="dev_app",
        level="DEBUG",
        console_output=True,
        file_output=False
    )
```

### 3. Custom Formatters

```python
# Create custom log format
custom_format = Logger.create_custom_format(
    include_timestamp=True,
    include_level=True,
    include_name=True,
    include_module=True,
    include_function=True,
    include_line_number=True,
    timestamp_format="%Y-%m-%d %H:%M:%S"
)

logger = Logger(
    name="custom_logger",
    format=custom_format,
    console_output=True
)

# Output: 2024-01-15 10:30:00 - INFO - custom_logger - main.py:process_data:25 - Processing started
logger.info("Processing started")
```

## Logging Categories and Context

### 1. Category-Based Logging

```python
# Create loggers for different categories
database_logger = Logger("database", category="database")
api_logger = Logger("api", category="api")
security_logger = Logger("security", category="security")

# Log with category context
database_logger.info("Database connection established")
api_logger.info("API endpoint called: /api/users")
security_logger.warning("Failed login attempt", extra={
    "ip_address": "192.168.1.100",
    "username": "admin"
})
```

### 2. Context Managers for Logging

```python
from siege_utilities.core.logging import LoggingContext

# Use context manager for operation logging
with LoggingContext(logger, "database_operation"):
    logger.info("Starting database transaction")
    
    try:
        # Database operations
        cursor.execute("SELECT * FROM users")
        logger.info("Query executed successfully")
        
    except Exception as e:
        logger.error("Database operation failed", exc_info=True)
        raise
    finally:
        logger.info("Database transaction completed")

# Output will include context information
```

### 3. Request-Specific Logging

```python
# Create request-scoped logger
request_logger = Logger("request_handler", request_id="req_12345")

# Log request details
request_logger.info("Request received", extra={
    "method": "POST",
    "path": "/api/users",
    "client_ip": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
})

# Process request
try:
    # Handle request
    request_logger.info("Request processed successfully")
except Exception as e:
    request_logger.error("Request processing failed", exc_info=True)
```

## Performance and Monitoring

### 1. Performance Logging

```python
import time
from siege_utilities.core.logging import PerformanceLogger

# Create performance logger
perf_logger = PerformanceLogger("data_processing")

# Log operation performance
with perf_logger.timer("database_query"):
    # Database operation
    time.sleep(0.1)  # Simulate database query

# Log memory usage
memory_usage = perf_logger.get_memory_usage()
perf_logger.info("Memory usage", extra={"memory_mb": memory_usage})

# Log custom metrics
perf_logger.log_metric("records_processed", 1000)
perf_logger.log_metric("processing_time_ms", 150)
```

### 2. Log Aggregation and Analysis

```python
# Configure log aggregation
logger = Logger(
    name="aggregated_logger",
    aggregation_enabled=True,
    aggregation_interval=60,  # seconds
    aggregation_batch_size=100
)

# Log messages (will be batched and aggregated)
for i in range(1000):
    logger.info(f"Processing item {i}")

# Aggregated logs will show:
# "INFO: Processing item X (repeated 1000 times in 60s)"
```

### 3. Log Rotation and Management

```python
# Configure log rotation
logger = Logger(
    name="rotating_logger",
    file_output=True,
    output_file="logs/app.log",
    max_file_size="100MB",
    backup_count=10,
    rotation_when="midnight",
    rotation_interval=1
)

# Logs will be rotated daily and keep 10 backup files
logger.info("Application started")
```

## Integration Examples

### 1. With Web Applications

```python
from flask import Flask, request
from siege_utilities.core.logging import Logger

app = Flask(__name__)
logger = Logger("web_app")

@app.before_request
def log_request():
    logger.info("Request received", extra={
        "method": request.method,
        "path": request.path,
        "ip": request.remote_addr,
        "user_agent": request.headers.get('User-Agent')
    })

@app.after_request
def log_response(response):
    logger.info("Response sent", extra={
        "status_code": response.status_code,
        "content_length": len(response.get_data())
    })
    return response

@app.route('/api/users')
def get_users():
    logger.info("Fetching users from database")
    try:
        # Database operation
        users = fetch_users_from_db()
        logger.info(f"Retrieved {len(users)} users")
        return {"users": users}
    except Exception as e:
        logger.error("Failed to fetch users", exc_info=True)
        return {"error": "Internal server error"}, 500
```

### 2. With Data Processing Pipelines

```python
from siege_utilities.core.logging import Logger

class DataProcessor:
    def __init__(self):
        self.logger = Logger("data_processor")
    
    def process_file(self, file_path):
        self.logger.info(f"Starting to process file: {file_path}")
        
        try:
            # Read file
            with open(file_path, 'r') as f:
                data = f.read()
            
            self.logger.info(f"File read successfully, size: {len(data)} bytes")
            
            # Process data
            processed_data = self.transform_data(data)
            self.logger.info(f"Data transformed, {len(processed_data)} records")
            
            # Save results
            self.save_results(processed_data)
            self.logger.info("Results saved successfully")
            
        except FileNotFoundError:
            self.logger.error(f"File not found: {file_path}")
            raise
        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}", exc_info=True)
            raise
    
    def transform_data(self, data):
        self.logger.debug("Transforming data")
        # Data transformation logic
        return data.split('\n')
    
    def save_results(self, data):
        self.logger.debug(f"Saving {len(data)} records")
        # Save logic
        pass

# Use the processor
processor = DataProcessor()
processor.process_file("data/input.csv")
```

### 3. With Background Jobs

```python
from siege_utilities.core.logging import Logger
import schedule
import time

class BackgroundJob:
    def __init__(self):
        self.logger = Logger("background_job")
    
    def run_daily_cleanup(self):
        self.logger.info("Starting daily cleanup job")
        
        try:
            # Cleanup operations
            self.cleanup_old_logs()
            self.cleanup_temp_files()
            self.cleanup_database()
            
            self.logger.info("Daily cleanup completed successfully")
            
        except Exception as e:
            self.logger.error("Daily cleanup failed", exc_info=True)
            # Send alert or notification
    
    def cleanup_old_logs(self):
        self.logger.debug("Cleaning up old log files")
        # Cleanup logic
    
    def cleanup_temp_files(self):
        self.logger.debug("Cleaning up temporary files")
        # Cleanup logic
    
    def cleanup_database(self):
        self.logger.debug("Cleaning up database")
        # Cleanup logic

# Schedule the job
job = BackgroundJob()
schedule.every().day.at("02:00").do(job.run_daily_cleanup)

# Run scheduler
while True:
    schedule.run_pending()
    time.sleep(60)
```

## Error Handling and Recovery

### 1. Logging Error Recovery

```python
from siege_utilities.core.logging import Logger

class ResilientLogger:
    def __init__(self):
        self.logger = Logger("resilient_app")
        self.fallback_logger = self.create_fallback_logger()
    
    def create_fallback_logger(self):
        # Create a simple fallback logger
        return Logger("fallback", console_output=True)
    
    def safe_log(self, level, message, **kwargs):
        try:
            getattr(self.logger, level)(message, **kwargs)
        except Exception as e:
            # Fallback to console logging
            self.fallback_logger.error(f"Primary logging failed: {e}")
            getattr(self.fallback_logger, level)(message, **kwargs)
    
    def info(self, message, **kwargs):
        self.safe_log("info", message, **kwargs)
    
    def error(self, message, **kwargs):
        self.safe_log("error", message, **kwargs)

# Use resilient logger
resilient_logger = ResilientLogger()
resilient_logger.info("This will use primary logger")
```

### 2. Logging Circuit Breaker

```python
class LoggingCircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def can_log(self):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True
    
    def log_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
    
    def log_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

# Use circuit breaker with logger
circuit_breaker = LoggingCircuitBreaker()
logger = Logger("circuit_breaker_app")

def safe_log(level, message, **kwargs):
    if circuit_breaker.can_log():
        try:
            getattr(logger, level)(message, **kwargs)
            circuit_breaker.log_success()
        except Exception as e:
            circuit_breaker.log_failure()
            print(f"Logging failed: {e}")  # Fallback
    else:
        print(f"Logging circuit breaker open: {message}")  # Fallback
```

## Best Practices

### 1. Log Level Guidelines
- **DEBUG**: Detailed information for debugging
- **INFO**: General information about program execution
- **WARNING**: Something unexpected happened but the program can continue
- **ERROR**: A serious problem occurred
- **CRITICAL**: A critical error that may prevent the program from running

### 2. Log Message Structure
- Use clear, descriptive messages
- Include relevant context and metadata
- Use consistent formatting and terminology
- Avoid logging sensitive information

### 3. Performance Considerations
- Use appropriate log levels for production
- Implement log rotation and cleanup
- Consider asynchronous logging for high-volume applications
- Monitor log file sizes and disk usage

### 4. Security and Privacy
- Never log passwords, API keys, or sensitive data
- Sanitize user input before logging
- Use appropriate access controls for log files
- Consider log encryption for sensitive environments

## Troubleshooting

### Common Issues

1. **Log Files Not Created**
   ```python
   # Check directory permissions
   import os
   log_dir = "logs"
   if not os.path.exists(log_dir):
       os.makedirs(log_dir, exist_ok=True)
   ```

2. **Performance Issues with High-Volume Logging**
   ```python
   # Use async logging
   logger = Logger("async_logger", async_logging=True)
   ```

3. **Disk Space Issues**
   ```python
   # Implement log rotation and cleanup
   logger = Logger("rotating_logger", 
                  max_file_size="10MB", 
                  backup_count=5)
   ```

## Conclusion

The logging utilities in `siege_utilities` provide comprehensive tools for application logging and monitoring. By following this recipe, you can:

- Implement robust logging across your applications
- Configure logging based on environment and requirements
- Use structured logging for better analysis and debugging
- Implement performance monitoring and metrics
- Handle logging failures gracefully with fallback mechanisms

Remember to always use appropriate log levels, implement proper log rotation, and follow security best practices when logging sensitive information.

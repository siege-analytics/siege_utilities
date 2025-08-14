# Remote Operations Recipe

## Overview
This recipe demonstrates how to perform efficient remote file transfers, system administration, and distributed computing operations using `siege_utilities`, supporting both Apache Spark and Pandas engines for seamless scalability from single operations to massive distributed remote workflows.

## Prerequisites
- Python 3.7+
- `siege_utilities` library installed
- Apache Spark (optional, for distributed processing)
- SSH access to remote systems
- Basic understanding of remote operations and networking

## Installation
```bash
pip install siege_utilities
pip install pyspark pandas numpy paramiko fabric boto3  # Core dependencies
```

## Multi-Engine Remote Operations Architecture

### 1. Engine-Agnostic Remote Manager

```python
from siege_utilities.files.remote import RemoteOperations, ConnectionPool
from siege_utilities.distributed.spark_utils import SparkUtils
from siege_utilities.core.logging import Logger

class MultiEngineRemoteManager:
    """Remote operations manager that works with both Spark and Pandas engines"""
    
    def __init__(self, default_engine="auto", remote_config=None, spark_config=None):
        self.default_engine = default_engine
        self.remote_config = remote_config or {}
        self.logger = Logger("multi_engine_remote_manager")
        
        # Initialize remote components
        self._setup_remote_components()
        
        # Initialize Spark if needed
        if default_engine in ["spark", "auto"]:
            self.spark_utils = SparkUtils(spark_config)
            self.spark_available = True
        else:
            self.spark_utils = None
            self.spark_available = False
    
    def _setup_remote_components(self):
        """Setup remote components based on configuration"""
        
        # Create connection pool
        self.connection_pool = ConnectionPool(
            max_connections=self.remote_config.get("max_connections", 10),
            connection_timeout=self.remote_config.get("connection_timeout", 30),
            retry_attempts=self.remote_config.get("retry_attempts", 3)
        )
        
        # Create remote operations manager
        self.remote_ops = RemoteOperations(
            connection_pool=self.connection_pool,
            default_user=self.remote_config.get("default_user", "ubuntu"),
            key_file_path=self.remote_config.get("key_file_path"),
            password=self.remote_config.get("password")
        )
    
    def get_optimal_engine(self, operation_complexity="medium", data_size_mb=None):
        """Automatically select the best engine for remote operations"""
        
        # Engine selection logic based on operation complexity
        if operation_complexity == "simple":
            return "pandas"
        elif operation_complexity == "medium":
            return "pandas"
        elif operation_complexity == "complex":
            return "spark" if self.spark_available else "pandas"
        else:
            return "auto"
    
    def execute_remote_command(self, host, command, command_config, engine=None, **kwargs):
        """Execute remote command using specified or auto-detected engine"""
        
        # Select optimal engine
        if engine is None:
            engine = self.get_optimal_engine(command_config.get("complexity", "medium"))
        
        self.logger.info(f"Executing remote command on {host} with {engine} engine: {command}")
        
        # Start performance monitoring
        start_time = time.time()
        
        try:
            if engine == "spark" and self.spark_available:
                result = self._execute_remote_with_spark(host, command, command_config, **kwargs)
            else:
                result = self._execute_remote_with_pandas(host, command, command_config, **kwargs)
            
            # Log successful completion
            execution_time = time.time() - start_time
            self.logger.info(f"Successfully executed remote command on {host} with {engine} engine in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            # Log error with context
            execution_time = time.time() - start_time
            self.logger.error(f"Error executing remote command on {host} with {engine} engine after {execution_time:.2f}s: {str(e)}")
            raise
    
    def transfer_file(self, source_host, source_path, target_host, target_path, transfer_config, engine=None, **kwargs):
        """Transfer file between remote hosts using specified or auto-detected engine"""
        
        # Select optimal engine
        if engine is None:
            engine = self.get_optimal_engine(transfer_config.get("complexity", "medium"))
        
        self.logger.info(f"Transferring file from {source_host}:{source_path} to {target_host}:{target_path} with {engine} engine")
        
        # Start performance monitoring
        start_time = time.time()
        
        try:
            if engine == "spark" and self.spark_available:
                result = self._transfer_file_with_spark(source_host, source_path, target_host, target_path, transfer_config, **kwargs)
            else:
                result = self._transfer_file_with_pandas(source_host, source_path, target_host, target_path, transfer_config, **kwargs)
            
            # Log successful completion
            execution_time = time.time() - start_time
            self.logger.info(f"Successfully transferred file with {engine} engine in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            # Log error with context
            execution_time = time.time() - start_time
            self.logger.error(f"Error transferring file with {engine} engine after {execution_time:.2f}s: {str(e)}")
            raise
    
    def _execute_remote_with_spark(self, host, command, command_config, **kwargs):
        """Execute remote command using Spark for distributed operations"""
        
        # For Spark, we'll use the remote operations but with distributed capabilities
        # This could involve executing commands on multiple nodes in a cluster
        
        # Execute command using remote operations
        result = self.remote_ops.execute_command(
            host,
            command,
            timeout=command_config.get("timeout", 300),
            user=command_config.get("user"),
            environment=command_config.get("environment", {})
        )
        
        # If this is a distributed operation, we could enhance it with Spark
        if command_config.get("distributed", False) and self.spark_available:
            # Execute on multiple nodes using Spark
            result = self._execute_distributed_remote_command(host, command, command_config, **kwargs)
        
        return result
    
    def _execute_remote_with_pandas(self, host, command, command_config, **kwargs):
        """Execute remote command using Pandas for single-node operations"""
        
        # Execute command using remote operations
        result = self.remote_ops.execute_command(
            host,
            command,
            timeout=command_config.get("timeout", 300),
            user=command_config.get("user"),
            environment=command_config.get("environment", {})
        )
        
        return result
    
    def _transfer_file_with_spark(self, source_host, source_path, target_host, target_path, transfer_config, **kwargs):
        """Transfer file using Spark for distributed operations"""
        
        # Use remote operations for file transfer
        result = self.remote_ops.transfer_file(
            source_host,
            source_path,
            target_host,
            target_path,
            recursive=transfer_config.get("recursive", False),
            preserve_permissions=transfer_config.get("preserve_permissions", True)
        )
        
        return result
    
    def _transfer_file_with_pandas(self, source_host, source_path, target_host, target_path, transfer_config, **kwargs):
        """Transfer file using Pandas for single-node operations"""
        
        # Use remote operations for file transfer
        result = self.remote_ops.transfer_file(
            source_host,
            source_path,
            target_host,
            target_path,
            recursive=transfer_config.get("recursive", False),
            preserve_permissions=transfer_config.get("preserve_permissions", True)
        )
        
        return result
    
    def _execute_distributed_remote_command(self, host, command, command_config, **kwargs):
        """Execute command on multiple nodes using Spark"""
        
        # This would involve using Spark to distribute the remote command execution
        # For now, we'll return the single-node result
        return self.remote_ops.execute_command(host, command, **kwargs)
```

### 2. Multi-Engine Remote Batch Processing

```python
class MultiEngineRemoteBatchProcessor:
    """Process multiple remote operations with optimal engine selection"""
    
    def __init__(self, remote_manager):
        self.remote_manager = remote_manager
        self.logger = Logger("remote_batch_processor")
    
    def process_remote_batch(self, remote_operations, output_dir="output", engine="auto"):
        """Process multiple remote operations using optimal engines for each"""
        
        results = {}
        
        for operation_name, operation_config in remote_operations.items():
            try:
                # Process individual operation with optimal engine selection
                result = self._process_single_remote_operation(operation_name, operation_config, output_dir, engine)
                results[operation_name] = result
                
            except Exception as e:
                self.logger.error(f"Error processing {operation_name}: {str(e)}")
                results[operation_name] = {"error": str(e), "status": "failed"}
        
        return results
    
    def _process_single_remote_operation(self, operation_name, operation_config, output_dir, engine):
        """Process a single remote operation with optimal engine selection"""
        
        # Get operation details
        operation_type = operation_config.get("type")
        hosts = operation_config.get("hosts", [])
        commands = operation_config.get("commands", [])
        file_transfers = operation_config.get("file_transfers", [])
        
        operation_results = {}
        
        # Execute remote commands
        if commands:
            for host in hosts:
                host_results = []
                for command in commands:
                    command_config = {
                        "complexity": operation_config.get("complexity", "medium"),
                        "timeout": operation_config.get("timeout", 300),
                        "user": operation_config.get("user"),
                        "environment": operation_config.get("environment", {})
                    }
                    
                    result = self.remote_manager.execute_remote_command(
                        host, command, command_config, engine=engine
                    )
                    host_results.append({
                        "command": command,
                        "result": result
                    })
                
                operation_results[host] = host_results
        
        # Perform file transfers
        if file_transfers:
            transfer_results = []
            for transfer in file_transfers:
                source_host = transfer.get("source_host")
                source_path = transfer.get("source_path")
                target_host = transfer.get("target_host")
                target_path = transfer.get("target_path")
                
                transfer_config = {
                    "complexity": operation_config.get("complexity", "medium"),
                    "recursive": transfer.get("recursive", False),
                    "preserve_permissions": transfer.get("preserve_permissions", True)
                }
                
                result = self.remote_manager.transfer_file(
                    source_host, source_path, target_host, target_path, transfer_config, engine=engine
                )
                transfer_results.append({
                    "source": f"{source_host}:{source_path}",
                    "target": f"{target_host}:{target_path}",
                    "result": result
                })
            
            operation_results["file_transfers"] = transfer_results
        
        # Generate output summary
        output_path = f"{output_dir}/{operation_name}_results.json"
        
        # Save results
        import json
        with open(output_path, 'w') as f:
            json.dump(operation_results, f, indent=2)
        
        return {
            "operation_name": operation_name,
            "output_file": output_path,
            "engine_used": engine,
            "hosts_processed": len(hosts),
            "commands_executed": len(commands),
            "transfers_performed": len(file_transfers),
            "status": "success"
        }
```

### 3. Multi-Engine Remote Data Pipeline

```python
class MultiEngineRemoteDataPipeline:
    """Complete remote data pipeline with multi-engine support"""
    
    def __init__(self, remote_manager):
        self.remote_manager = remote_manager
        self.logger = Logger("remote_data_pipeline")
    
    def run_pipeline(self, pipeline_config, engine="auto"):
        """Run complete remote data pipeline with optimal engine selection"""
        
        pipeline_results = {}
        
        # Stage 1: Data Collection
        if "collection" in pipeline_config:
            collection_results = self._run_collection_stage(pipeline_config["collection"], engine)
            pipeline_results["collection"] = collection_results
        
        # Stage 2: Data Processing
        if "processing" in pipeline_config:
            processing_results = self._run_processing_stage(pipeline_config["processing"], engine)
            pipeline_results["processing"] = processing_results
        
        # Stage 3: Data Transfer
        if "transfer" in pipeline_config:
            transfer_results = self._run_transfer_stage(pipeline_config["transfer"], engine)
            pipeline_results["transfer"] = transfer_results
        
        # Stage 4: Data Validation
        if "validation" in pipeline_config:
            validation_results = self._run_validation_stage(pipeline_config["validation"], engine)
            pipeline_results["validation"] = validation_results
        
        return pipeline_results
    
    def _run_collection_stage(self, collection_config, engine):
        """Run data collection stage"""
        
        collection_results = {}
        
        for source_name, source_config in collection_config.items():
            try:
                # Collect data from remote source
                host = source_config["host"]
                source_path = source_config["source_path"]
                local_path = source_config["local_path"]
                
                # Download file from remote host
                result = self.remote_manager.remote_ops.download_file(
                    host, source_path, local_path
                )
                
                collection_results[source_name] = {
                    "status": "success",
                    "host": host,
                    "source_path": source_path,
                    "local_path": local_path,
                    "result": result
                }
                
            except Exception as e:
                collection_results[source_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return collection_results
    
    def _run_processing_stage(self, processing_config, engine):
        """Run data processing stage"""
        
        processing_results = {}
        
        for process_name, process_config in processing_config.items():
            try:
                # Get input data from collection stage
                input_data = self._get_input_data(process_config["input_sources"])
                
                # Apply processing operations
                processed_data = self._apply_processing_operations(input_data, process_config["operations"], engine)
                
                processing_results[process_name] = {
                    "status": "success",
                    "data": processed_data,
                    "record_count": self._get_record_count(processed_data, engine)
                }
                
            except Exception as e:
                processing_results[process_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return processing_results
    
    def _run_transfer_stage(self, transfer_config, engine):
        """Run data transfer stage"""
        
        transfer_results = {}
        
        for transfer_name, transfer_config in transfer_config.items():
            try:
                # Get input data from processing stage
                input_data = self._get_input_data(transfer_config["input_sources"])
                
                # Transfer to remote destination
                source_host = transfer_config.get("source_host", "localhost")
                source_path = transfer_config["source_path"]
                target_host = transfer_config["target_host"]
                target_path = transfer_config["target_path"]
                
                result = self.remote_manager.transfer_file(
                    source_host, source_path, target_host, target_path, transfer_config, engine=engine
                )
                
                transfer_results[transfer_name] = {
                    "status": "success",
                    "source": f"{source_host}:{source_path}",
                    "target": f"{target_host}:{target_path}",
                    "result": result
                }
                
            except Exception as e:
                transfer_results[transfer_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return transfer_results
    
    def _run_validation_stage(self, validation_config, engine):
        """Run data validation stage"""
        
        validation_results = {}
        
        for validation_name, validation_config in validation_config.items():
            try:
                # Get input data from transfer stage
                input_data = self._get_input_data(validation_config["input_sources"])
                
                # Apply validation checks
                validation_metrics = self._apply_validation_checks(input_data, validation_config["checks"], engine)
                
                validation_results[validation_name] = {
                    "status": "success",
                    "metrics": validation_metrics
                }
                
            except Exception as e:
                validation_results[validation_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return validation_results
    
    def _get_input_data(self, input_sources):
        """Get input data from specified sources"""
        
        # This would integrate with the pipeline context
        # For now, return None as placeholder
        return None
    
    def _apply_processing_operations(self, data, operations, engine):
        """Apply processing operations using specified engine"""
        
        # Implementation similar to other processors
        return data
    
    def _apply_validation_checks(self, data, checks, engine):
        """Apply validation checks using specified engine"""
        
        # Implementation similar to other validators
        return {}
    
    def _get_record_count(self, data, engine):
        """Get record count from any engine"""
        
        if engine == "spark":
            return data.count()
        else:
            return len(data)
```

### 4. Multi-Engine Remote Monitoring

```python
class MultiEngineRemoteMonitor:
    """Monitor remote systems using any engine"""
    
    def __init__(self, remote_manager):
        self.remote_manager = remote_manager
        self.logger = Logger("remote_monitor")
    
    def monitor_remote_systems(self, monitoring_config, engine=None, **kwargs):
        """Monitor remote systems using specified or auto-detected engine"""
        
        # Select optimal engine
        if engine is None:
            engine = self.remote_manager.get_optimal_engine(monitoring_config.get("complexity", "medium"))
        
        self.logger.info(f"Monitoring remote systems with {engine} engine")
        
        if engine == "spark" and self.remote_manager.spark_available:
            return self._monitor_remote_with_spark(monitoring_config, **kwargs)
        else:
            return self._monitor_remote_with_pandas(monitoring_config, **kwargs)
    
    def _monitor_remote_with_spark(self, monitoring_config, **kwargs):
        """Monitor remote systems using Spark for distributed monitoring"""
        
        monitoring_type = monitoring_config.get("type")
        
        if monitoring_type == "health":
            return self._monitor_remote_health_spark(monitoring_config, **kwargs)
        elif monitoring_type == "performance":
            return self._monitor_remote_performance_spark(monitoring_config, **kwargs)
        elif monitoring_type == "security":
            return self._monitor_remote_security_spark(monitoring_config, **kwargs)
        else:
            return {"error": f"Unknown monitoring type: {monitoring_type}"}
    
    def _monitor_remote_with_pandas(self, monitoring_config, **kwargs):
        """Monitor remote systems using Pandas for single-node monitoring"""
        
        monitoring_type = monitoring_config.get("type")
        
        if monitoring_type == "health":
            return self._monitor_remote_health_pandas(monitoring_config, **kwargs)
        elif monitoring_type == "performance":
            return self._monitor_remote_performance_pandas(monitoring_config, **kwargs)
        elif monitoring_type == "security":
            return self._monitor_remote_security_pandas(monitoring_config, **kwargs)
        else:
            return {"error": f"Unknown monitoring type: {monitoring_type}"}
    
    def _monitor_remote_health_spark(self, monitoring_config, **kwargs):
        """Monitor remote health using Spark"""
        
        hosts = monitoring_config.get("hosts", [])
        health_results = {}
        
        for host in hosts:
            try:
                # Execute health check commands
                commands = [
                    "uptime",
                    "df -h",
                    "free -h",
                    "ps aux | wc -l"
                ]
                
                host_results = {}
                for command in commands:
                    result = self.remote_manager.execute_remote_command(
                        host, command, {"complexity": "simple"}
                    )
                    host_results[command] = result
                
                health_results[host] = {
                    "status": "healthy",
                    "results": host_results
                }
                
            except Exception as e:
                health_results[host] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        return {
            "monitoring_type": "health",
            "engine": "spark",
            "results": health_results
        }
    
    def _monitor_remote_health_pandas(self, monitoring_config, **kwargs):
        """Monitor remote health using Pandas"""
        
        hosts = monitoring_config.get("hosts", [])
        health_results = {}
        
        for host in hosts:
            try:
                # Execute health check commands
                commands = [
                    "uptime",
                    "df -h",
                    "free -h",
                    "ps aux | wc -l"
                ]
                
                host_results = {}
                for command in commands:
                    result = self.remote_manager.execute_remote_command(
                        host, command, {"complexity": "simple"}
                    )
                    host_results[command] = result
                
                health_results[host] = {
                    "status": "healthy",
                    "results": host_results
                }
                
            except Exception as e:
                health_results[host] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        return {
            "monitoring_type": "health",
            "engine": "pandas",
            "results": health_results
        }
    
    def _monitor_remote_performance_spark(self, monitoring_config, **kwargs):
        """Monitor remote performance using Spark"""
        
        hosts = monitoring_config.get("hosts", [])
        performance_results = {}
        
        for host in hosts:
            try:
                # Execute performance monitoring commands
                commands = [
                    "vmstat 1 5",
                    "iostat 1 5",
                    "netstat -i"
                ]
                
                host_results = {}
                for command in commands:
                    result = self.remote_manager.execute_remote_command(
                        host, command, {"complexity": "medium"}
                    )
                    host_results[command] = result
                
                performance_results[host] = {
                    "status": "monitored",
                    "results": host_results
                }
                
            except Exception as e:
                performance_results[host] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return {
            "monitoring_type": "performance",
            "engine": "spark",
            "results": performance_results
        }
    
    def _monitor_remote_performance_pandas(self, monitoring_config, **kwargs):
        """Monitor remote performance using Pandas"""
        
        hosts = monitoring_config.get("hosts", [])
        performance_results = {}
        
        for host in hosts:
            try:
                # Execute performance monitoring commands
                commands = [
                    "vmstat 1 5",
                    "iostat 1 5",
                    "netstat -i"
                ]
                
                host_results = {}
                for command in commands:
                    result = self.remote_manager.execute_remote_command(
                        host, command, {"complexity": "medium"}
                    )
                    host_results[command] = result
                
                performance_results[host] = {
                    "status": "monitored",
                    "results": host_results
                }
                
            except Exception as e:
                performance_results[host] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return {
            "monitoring_type": "performance",
            "engine": "pandas",
            "results": performance_results
        }
    
    def _monitor_remote_security_spark(self, monitoring_config, **kwargs):
        """Monitor remote security using Spark"""
        
        hosts = monitoring_config.get("hosts", [])
        security_results = {}
        
        for host in hosts:
            try:
                # Execute security monitoring commands
                commands = [
                    "last | head -20",
                    "who",
                    "netstat -tuln"
                ]
                
                host_results = {}
                for command in commands:
                    result = self.remote_manager.execute_remote_command(
                        host, command, {"complexity": "medium"}
                    )
                    host_results[command] = result
                
                security_results[host] = {
                    "status": "monitored",
                    "results": host_results
                }
                
            except Exception as e:
                security_results[host] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return {
            "monitoring_type": "security",
            "engine": "spark",
            "results": security_results
        }
    
    def _monitor_remote_security_pandas(self, monitoring_config, **kwargs):
        """Monitor remote security using Pandas"""
        
        hosts = monitoring_config.get("hosts", [])
        security_results = {}
        
        for host in hosts:
            try:
                # Execute security monitoring commands
                commands = [
                    "last | head -20",
                    "who",
                    "netstat -tuln"
                ]
                
                host_results = {}
                for command in commands:
                    result = self.remote_manager.execute_remote_command(
                        host, command, {"complexity": "medium"}
                    )
                    host_results[command] = result
                
                security_results[host] = {
                    "status": "monitored",
                    "results": host_results
                }
                
            except Exception as e:
                security_results[host] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return {
            "monitoring_type": "security",
            "engine": "pandas",
            "results": security_results
        }
```

## Integration Examples

### 1. Multi-Engine Remote Operations Pipeline

```python
def create_multi_engine_remote_pipeline():
    """Create a complete multi-engine remote operations pipeline"""
    
    # Initialize remote manager
    remote_config = {
        "max_connections": 20,
        "connection_timeout": 30,
        "retry_attempts": 3,
        "default_user": "ubuntu",
        "key_file_path": "~/.ssh/id_rsa"
    }
    
    remote_manager = MultiEngineRemoteManager(default_engine="auto", remote_config=remote_config)
    
    # Create specialized processors
    batch_processor = MultiEngineRemoteBatchProcessor(remote_manager)
    data_pipeline = MultiEngineRemoteDataPipeline(remote_manager)
    remote_monitor = MultiEngineRemoteMonitor(remote_manager)
    
    # Define remote operations
    remote_operations = {
        "system_maintenance": {
            "type": "maintenance",
            "complexity": "medium",
            "hosts": ["server1.example.com", "server2.example.com", "server3.example.com"],
            "commands": [
                "sudo apt update && sudo apt upgrade -y",
                "sudo systemctl restart ssh",
                "sudo journalctl --vacuum-time=7d"
            ],
            "timeout": 600,
            "user": "ubuntu"
        },
        "data_backup": {
            "type": "backup",
            "complexity": "high",
            "hosts": ["backup-server.example.com"],
            "file_transfers": [
                {
                    "source_host": "server1.example.com",
                    "source_path": "/var/log/",
                    "target_host": "backup-server.example.com",
                    "target_path": "/backups/server1/logs/",
                    "recursive": True
                },
                {
                    "source_host": "server2.example.com",
                    "source_path": "/home/user/data/",
                    "target_host": "backup-server.example.com",
                    "target_path": "/backups/server2/user_data/",
                    "recursive": True
                }
            ],
            "timeout": 1800,
            "user": "backup"
        }
    }
    
    # Process remote operations with optimal engine selection
    batch_results = batch_processor.process_remote_batch(remote_operations, "output/remote")
    
    # Define pipeline configuration
    pipeline_config = {
        "collection": {
            "log_data": {
                "host": "server1.example.com",
                "source_path": "/var/log/",
                "local_path": "/tmp/logs/"
            },
            "config_data": {
                "host": "server2.example.com",
                "source_path": "/etc/",
                "local_path": "/tmp/configs/"
            }
        },
        "transfer": {
            "processed_data": {
                "input_sources": ["log_data", "config_data"],
                "source_host": "localhost",
                "source_path": "/tmp/processed/",
                "target_host": "archive-server.example.com",
                "target_path": "/archive/processed/"
            }
        },
        "validation": {
            "data_integrity": {
                "input_sources": ["processed_data"],
                "checks": {
                    "file_count": {"type": "count_check"},
                    "file_size": {"type": "size_check"}
                }
            }
        }
    }
    
    # Run complete remote data pipeline
    pipeline_results = data_pipeline.run_pipeline(pipeline_config)
    
    # Monitor remote systems
    monitoring_config = {
        "type": "health",
        "complexity": "medium",
        "hosts": ["server1.example.com", "server2.example.com", "server3.example.com"]
    }
    
    monitoring_results = remote_monitor.monitor_remote_systems(monitoring_config)
    
    return batch_results, pipeline_results, monitoring_results

# Run the pipeline
remote_pipeline_results = create_multi_engine_remote_pipeline()
```

### 2. Real-time Remote Operations Dashboard

```python
def create_remote_operations_dashboard():
    """Create a dashboard to monitor remote operations in real-time"""
    
    import dash
    from dash import dcc, html
    from dash.dependencies import Input, Output
    import plotly.graph_objs as go
    
    app = dash.Dash(__name__)
    
    app.layout = html.Div([
        html.H1("Multi-Engine Remote Operations Dashboard"),
        
        html.Div([
            html.Div([
                html.Label("Operation Type:"),
                dcc.Dropdown(
                    id="operation-filter",
                    options=[
                        {"label": "All Operations", "value": "all"},
                        {"label": "Command Execution", "value": "command"},
                        {"label": "File Transfer", "value": "transfer"},
                        {"label": "System Monitoring", "value": "monitoring"}
                    ],
                    value="all",
                    style={"width": "200px"}
                )
            ], style={"width": "250px", "margin": "20px"}),
            
            html.Div([
                html.Label("Engine:"),
                dcc.Dropdown(
                    id="engine-filter",
                    options=[
                        {"label": "All Engines", "value": "all"},
                        {"label": "Pandas", "value": "pandas"},
                        {"label": "Spark", "value": "spark"},
                        {"label": "Auto", "value": "auto"}
                    ],
                    value="all",
                    style={"width": "150px"}
                )
            ], style={"width": "200px", "margin": "20px"}),
            
            html.Div([
                html.Label("Update Frequency (seconds):"),
                dcc.Slider(
                    id="update-frequency",
                    min=5,
                    max=60,
                    step=5,
                    value=30,
                    marks={i: str(i) for i in [5, 15, 30, 45, 60]},
                    tooltip={"placement": "bottom", "always_visible": True}
                )
            ], style={"width": "300px", "margin": "20px"})
        ], style={"display": "flex", "justifyContent": "center", "marginBottom": "20px"}),
        
        html.Div([
            dcc.Graph(id="remote-command-chart"),
            dcc.Graph(id="file-transfer-status-chart"),
            dcc.Graph(id="system-health-chart")
        ]),
        
        dcc.Interval(id="update-interval", interval=30*1000)  # Update every 30 seconds
    ])
    
    @app.callback(
        [Output("remote-command-chart", "figure"),
         Output("file-transfer-status-chart", "figure"),
         Output("system-health-chart", "figure")],
        [Input("update-interval", "n_intervals"),
         Input("operation-filter", "value"),
         Input("engine-filter", "value"),
         Input("update-frequency", "value")]
    )
    def update_charts(n, operation_type, engine, frequency):
        # Get remote operations data (this would come from your actual remote operations system)
        # For demonstration, we'll create sample data
        
        # Remote command execution chart
        time_points = list(range(24))  # Last 24 hours
        command_counts = [np.random.randint(20, 100) for _ in time_points]
        
        command_fig = go.Figure(data=[
            go.Scatter(x=time_points, y=command_counts, mode="lines+markers", name="Remote Commands")
        ])
        command_fig.update_layout(title="Remote Commands Executed Over Time", xaxis_title="Hours Ago", yaxis_title="Command Count")
        
        # File transfer status chart
        transfer_statuses = ["Success", "Failed", "In Progress"]
        transfer_counts = [180, 12, 8]
        
        transfer_fig = go.Figure(data=[
            go.Pie(labels=transfer_statuses, values=transfer_counts, name="File Transfer Status")
        ])
        transfer_fig.update_layout(title="Remote File Transfer Status Distribution")
        
        # System health chart
        systems = ["Server 1", "Server 2", "Server 3", "Server 4"]
        health_scores = [95, 87, 92, 78]  # percentage
        
        health_fig = go.Figure(data=[
            go.Bar(x=systems, y=health_scores, name="System Health")
        ])
        health_fig.update_layout(title="Remote System Health Status", yaxis_title="Health Score (%)")
        
        return command_fig, transfer_fig, health_fig
    
    return app

# Start the dashboard
remote_dashboard = create_remote_operations_dashboard()
remote_dashboard.run_server(debug=True, port=8058)
```

## Best Practices

### 1. Engine Selection
- Use **Pandas** for simple operations and single-host monitoring
- Use **Spark** for complex operations and distributed monitoring
- Use **Auto-detection** for unknown operation complexity
- Consider **network latency** when selecting engine

### 2. Performance Optimization
- **Use connection pooling** for multiple remote operations
- **Implement command caching** for frequently used operations
- **Monitor network performance** during execution
- **Use parallel execution** when possible

### 3. Security
- **Use key-based authentication** instead of passwords
- **Validate all remote commands** before execution
- **Implement proper user permissions** for different operations
- **Log all remote operations** for audit trails

### 4. Error Handling
- **Implement fallback mechanisms** when engines fail
- **Provide meaningful error messages** for debugging
- **Log remote operation decisions** for transparency
- **Retry failed operations** with different engines when possible

## Troubleshooting

### Common Issues

1. **Engine Compatibility Issues**
   ```python
   # Check engine availability
   if remote_manager.spark_available:
       print("Spark is available for distributed remote operations")
   else:
       print("Using Pandas only")
   ```

2. **Connection Issues**
   ```python
   # Check remote connectivity
   try:
       result = remote_manager.execute_remote_command("hostname", {"complexity": "simple"})
       print("Remote connection successful")
   except Exception as e:
       print(f"Remote connection failed: {e}")
   ```

3. **Authentication Issues**
   ```python
   # Check SSH key configuration
   import os
   key_path = os.path.expanduser("~/.ssh/id_rsa")
   if os.path.exists(key_path):
       print("SSH key found")
   else:
       print("SSH key not found")
   ```

## Conclusion

The multi-engine remote operations capabilities in `siege_utilities` provide:

- **Seamless scalability** from single operations to distributed workflows
- **Automatic engine selection** based on operation characteristics
- **Unified remote interfaces** that work with both Spark and Pandas
- **Comprehensive remote monitoring** across all engines
- **Performance optimization** through intelligent engine selection

By following this recipe, you can build robust, scalable remote operation pipelines that automatically adapt to your operation complexity and network requirements while providing comprehensive remote system administration capabilities.

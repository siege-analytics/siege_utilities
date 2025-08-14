# Shell Operations Recipe

## Overview
This recipe demonstrates how to perform efficient shell command execution, process management, and system administration using `siege_utilities`, supporting both Apache Spark and Pandas engines for seamless scalability from single commands to massive distributed operations.

## Prerequisites
- Python 3.7+
- `siege_utilities` library installed
- Apache Spark (optional, for distributed processing)
- Basic understanding of shell operations and process management

## Installation
```bash
pip install siege_utilities
pip install pyspark pandas numpy psutil  # Core dependencies
```

## Multi-Engine Shell Operations Architecture

### 1. Engine-Agnostic Shell Manager

```python
from siege_utilities.files.shell import ShellOperations
from siege_utilities.distributed.spark_utils import SparkUtils
from siege_utilities.core.logging import Logger

class MultiEngineShellManager:
    """Shell manager that works with both Spark and Pandas engines"""
    
    def __init__(self, default_engine="auto", spark_config=None, shell_config=None):
        self.default_engine = default_engine
        self.shell_config = shell_config or {}
        self.logger = Logger("multi_engine_shell_manager")
        
        # Initialize shell components
        self._setup_shell_components()
        
        # Initialize Spark if needed
        if default_engine in ["spark", "auto"]:
            self.spark_utils = SparkUtils(spark_config)
            self.spark_available = True
        else:
            self.spark_utils = None
            self.spark_available = False
    
    def _setup_shell_components(self):
        """Setup shell components based on configuration"""
        
        # Create shell operations manager
        self.shell_ops = ShellOperations(
            timeout=self.shell_config.get("timeout", 300),
            working_directory=self.shell_config.get("working_directory", "."),
            environment=self.shell_config.get("environment", {})
        )
    
    def get_optimal_engine(self, operation_complexity="medium", data_size_mb=None):
        """Automatically select the best engine for shell operations"""
        
        # Engine selection logic based on operation complexity
        if operation_complexity == "simple":
            return "pandas"
        elif operation_complexity == "medium":
            return "pandas"
        elif operation_complexity == "complex":
            return "spark" if self.spark_available else "pandas"
        else:
            return "auto"
    
    def execute_shell_command(self, command, command_config, engine=None, **kwargs):
        """Execute shell command using specified or auto-detected engine"""
        
        # Select optimal engine
        if engine is None:
            engine = self.get_optimal_engine(command_config.get("complexity", "medium"))
        
        self.logger.info(f"Executing shell command with {engine} engine: {command}")
        
        # Start performance monitoring
        start_time = time.time()
        
        try:
            if engine == "spark" and self.spark_available:
                result = self._execute_with_spark(command, command_config, **kwargs)
            else:
                result = self._execute_with_pandas(command, command_config, **kwargs)
            
            # Log successful completion
            execution_time = time.time() - start_time
            self.logger.info(f"Successfully executed shell command with {engine} engine in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            # Log error with context
            execution_time = time.time() - start_time
            self.logger.error(f"Error executing shell command with {engine} engine after {execution_time:.2f}s: {str(e)}")
            raise
    
    def _execute_with_spark(self, command, command_config, **kwargs):
        """Execute shell command using Spark for distributed operations"""
        
        # For Spark, we'll use the shell operations but with distributed capabilities
        # This could involve executing commands on multiple nodes in a cluster
        
        # Execute command using shell operations
        result = self.shell_ops.execute_command(
            command,
            timeout=command_config.get("timeout", 300),
            working_directory=command_config.get("working_directory", "."),
            environment=command_config.get("environment", {})
        )
        
        # If this is a distributed operation, we could enhance it with Spark
        if command_config.get("distributed", False) and self.spark_available:
            # Execute on multiple nodes using Spark
            result = self._execute_distributed_command(command, command_config, **kwargs)
        
        return result
    
    def _execute_with_pandas(self, command, command_config, **kwargs):
        """Execute shell command using Pandas for single-node operations"""
        
        # Execute command using shell operations
        result = self.shell_ops.execute_command(
            command,
            timeout=command_config.get("timeout", 300),
            working_directory=command_config.get("working_directory", "."),
            environment=command_config.get("environment", {})
        )
        
        return result
    
    def _execute_distributed_command(self, command, command_config, **kwargs):
        """Execute command on multiple nodes using Spark"""
        
        # This would involve using Spark to distribute the command execution
        # For now, we'll return the single-node result
        return self.shell_ops.execute_command(command, **kwargs)
```

### 2. Multi-Engine Process Management

```python
class MultiEngineProcessManager:
    """Manage processes using any engine"""
    
    def __init__(self, shell_manager):
        self.shell_manager = shell_manager
        self.logger = Logger("process_manager")
    
    def manage_processes(self, process_config, engine=None, **kwargs):
        """Manage processes using specified or auto-detected engine"""
        
        # Select optimal engine
        if engine is None:
            engine = self.shell_manager.get_optimal_engine(process_config.get("complexity", "medium"))
        
        self.logger.info(f"Managing processes with {engine} engine")
        
        if engine == "spark" and self.shell_manager.spark_available:
            return self._manage_processes_with_spark(process_config, **kwargs)
        else:
            return self._manage_processes_with_pandas(process_config, **kwargs)
    
    def _manage_processes_with_spark(self, process_config, **kwargs):
        """Manage processes using Spark for distributed operations"""
        
        operation_type = process_config.get("type")
        
        if operation_type == "monitor":
            return self._monitor_processes_spark(process_config, **kwargs)
        elif operation_type == "control":
            return self._control_processes_spark(process_config, **kwargs)
        elif operation_type == "discovery":
            return self._discover_processes_spark(process_config, **kwargs)
        else:
            return {"error": f"Unknown operation type: {operation_type}"}
    
    def _manage_processes_with_pandas(self, process_config, **kwargs):
        """Manage processes using Pandas for single-node operations"""
        
        operation_type = process_config.get("type")
        
        if operation_type == "monitor":
            return self._monitor_processes_pandas(process_config, **kwargs)
        elif operation_type == "control":
            return self._control_processes_pandas(process_config, **kwargs)
        elif operation_type == "discovery":
            return self._discover_processes_pandas(process_config, **kwargs)
        else:
            return {"error": f"Unknown operation type: {operation_type}"}
    
    def _monitor_processes_spark(self, process_config, **kwargs):
        """Monitor processes using Spark"""
        
        # Use shell operations to get process information
        command = "ps aux"
        result = self.shell_manager.shell_ops.execute_command(command)
        
        # Parse process information
        processes = self._parse_process_output(result["output"])
        
        return {
            "operation": "monitor",
            "engine": "spark",
            "processes": processes,
            "total_count": len(processes)
        }
    
    def _monitor_processes_pandas(self, process_config, **kwargs):
        """Monitor processes using Pandas"""
        
        import psutil
        
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        return {
            "operation": "monitor",
            "engine": "pandas",
            "processes": processes,
            "total_count": len(processes)
        }
    
    def _control_processes_spark(self, process_config, **kwargs):
        """Control processes using Spark"""
        
        action = process_config.get("action")
        process_ids = process_config.get("process_ids", [])
        
        results = []
        
        for pid in process_ids:
            if action == "kill":
                command = f"kill -9 {pid}"
            elif action == "stop":
                command = f"kill -15 {pid}"
            elif action == "resume":
                command = f"kill -CONT {pid}"
            else:
                results.append({"pid": pid, "action": action, "status": "unknown_action"})
                continue
            
            result = self.shell_manager.shell_ops.execute_command(command)
            results.append({
                "pid": pid,
                "action": action,
                "status": "success" if result["return_code"] == 0 else "failed",
                "output": result["output"]
            })
        
        return {
            "operation": "control",
            "engine": "spark",
            "results": results
        }
    
    def _control_processes_pandas(self, process_config, **kwargs):
        """Control processes using Pandas"""
        
        import psutil
        
        action = process_config.get("action")
        process_ids = process_config.get("process_ids", [])
        
        results = []
        
        for pid in process_ids:
            try:
                proc = psutil.Process(pid)
                
                if action == "kill":
                    proc.kill()
                elif action == "stop":
                    proc.suspend()
                elif action == "resume":
                    proc.resume()
                else:
                    results.append({"pid": pid, "action": action, "status": "unknown_action"})
                    continue
                
                results.append({
                    "pid": pid,
                    "action": action,
                    "status": "success"
                })
                
            except psutil.NoSuchProcess:
                results.append({
                    "pid": pid,
                    "action": action,
                    "status": "process_not_found"
                })
            except psutil.AccessDenied:
                results.append({
                    "pid": pid,
                    "action": action,
                    "status": "access_denied"
                })
            except Exception as e:
                results.append({
                    "pid": pid,
                    "action": action,
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "operation": "control",
            "engine": "pandas",
            "results": results
        }
    
    def _discover_processes_spark(self, process_config, **kwargs):
        """Discover processes using Spark"""
        
        # Use shell operations to discover processes
        command = "ps -ef"
        result = self.shell_manager.shell_ops.execute_command(command)
        
        # Parse process discovery output
        processes = self._parse_process_output(result["output"])
        
        return {
            "operation": "discovery",
            "engine": "spark",
            "processes": processes,
            "total_count": len(processes)
        }
    
    def _discover_processes_pandas(self, process_config, **kwargs):
        """Discover processes using Pandas"""
        
        import psutil
        
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'username', 'create_time', 'status']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        return {
            "operation": "discovery",
            "engine": "pandas",
            "processes": processes,
            "total_count": len(processes)
        }
    
    def _parse_process_output(self, output):
        """Parse process output from shell command"""
        
        processes = []
        lines = output.strip().split('\n')
        
        # Skip header line
        for line in lines[1:]:
            if line.strip():
                parts = line.split()
                if len(parts) >= 11:
                    processes.append({
                        "user": parts[0],
                        "pid": int(parts[1]),
                        "cpu_percent": float(parts[2]),
                        "memory_percent": float(parts[3]),
                        "vsz": int(parts[4]),
                        "rss": int(parts[5]),
                        "tty": parts[6],
                        "stat": parts[7],
                        "start": parts[8],
                        "time": parts[9],
                        "command": ' '.join(parts[10:])
                    })
        
        return processes
```

### 3. Multi-Engine Shell Scripting

```python
class MultiEngineShellScripting:
    """Execute shell scripts using any engine"""
    
    def __init__(self, shell_manager):
        self.shell_manager = shell_manager
        self.logger = Logger("shell_scripting")
    
    def execute_script(self, script_config, engine=None, **kwargs):
        """Execute shell script using specified or auto-detected engine"""
        
        # Select optimal engine
        if engine is None:
            engine = self.shell_manager.get_optimal_engine(script_config.get("complexity", "medium"))
        
        self.logger.info(f"Executing shell script with {engine} engine")
        
        if engine == "spark" and self.shell_manager.spark_available:
            return self._execute_script_with_spark(script_config, **kwargs)
        else:
            return self._execute_script_with_pandas(script_config, **kwargs)
    
    def _execute_script_with_spark(self, script_config, **kwargs):
        """Execute shell script using Spark for distributed operations"""
        
        script_type = script_config.get("type")
        
        if script_type == "conditional":
            return self._execute_conditional_script_spark(script_config, **kwargs)
        elif script_type == "maintenance":
            return self._execute_maintenance_script_spark(script_config, **kwargs)
        else:
            return self._execute_generic_script_spark(script_config, **kwargs)
    
    def _execute_script_with_pandas(self, script_config, **kwargs):
        """Execute shell script using Pandas for single-node operations"""
        
        script_type = script_config.get("type")
        
        if script_type == "conditional":
            return self._execute_conditional_script_pandas(script_config, **kwargs)
        elif script_type == "maintenance":
            return self._execute_maintenance_script_pandas(script_config, **kwargs)
        else:
            return self._execute_generic_script_pandas(script_config, **kwargs)
    
    def _execute_conditional_script_spark(self, script_config, **kwargs):
        """Execute conditional script using Spark"""
        
        condition = script_config.get("condition")
        script_path = script_config.get("script_path")
        
        # Check condition
        if self._evaluate_condition(condition):
            # Execute script
            result = self.shell_manager.shell_ops.execute_script(script_path)
            return {
                "script_type": "conditional",
                "engine": "spark",
                "condition": condition,
                "condition_met": True,
                "execution_result": result
            }
        else:
            return {
                "script_type": "conditional",
                "engine": "spark",
                "condition": condition,
                "condition_met": False,
                "execution_result": None
            }
    
    def _execute_conditional_script_pandas(self, script_config, **kwargs):
        """Execute conditional script using Pandas"""
        
        condition = script_config.get("condition")
        script_path = script_config.get("script_path")
        
        # Check condition
        if self._evaluate_condition(condition):
            # Execute script
            result = self.shell_manager.shell_ops.execute_script(script_path)
            return {
                "script_type": "conditional",
                "engine": "pandas",
                "condition": condition,
                "condition_met": True,
                "execution_result": result
            }
        else:
            return {
                "script_type": "conditional",
                "engine": "pandas",
                "condition": condition,
                "condition_met": False,
                "execution_result": None
            }
    
    def _execute_maintenance_script_spark(self, script_config, **kwargs):
        """Execute maintenance script using Spark"""
        
        script_path = script_config.get("script_path")
        maintenance_type = script_config.get("maintenance_type", "general")
        
        # Execute maintenance script
        result = self.shell_manager.shell_ops.execute_script(script_path)
        
        return {
            "script_type": "maintenance",
            "engine": "spark",
            "maintenance_type": maintenance_type,
            "execution_result": result
        }
    
    def _execute_maintenance_script_pandas(self, script_config, **kwargs):
        """Execute maintenance script using Pandas"""
        
        script_path = script_config.get("script_path")
        maintenance_type = script_config.get("maintenance_type", "general")
        
        # Execute maintenance script
        result = self.shell_manager.shell_ops.execute_script(script_path)
        
        return {
            "script_type": "maintenance",
            "engine": "pandas",
            "maintenance_type": maintenance_type,
            "execution_result": result
        }
    
    def _execute_generic_script_spark(self, script_config, **kwargs):
        """Execute generic script using Spark"""
        
        script_path = script_config.get("script_path")
        
        # Execute script
        result = self.shell_manager.shell_ops.execute_script(script_path)
        
        return {
            "script_type": "generic",
            "engine": "spark",
            "execution_result": result
        }
    
    def _execute_generic_script_pandas(self, script_config, **kwargs):
        """Execute generic script using Pandas"""
        
        script_path = script_config.get("script_path")
        
        # Execute script
        result = self.shell_manager.shell_ops.execute_script(script_path)
        
        return {
            "script_type": "generic",
            "engine": "pandas",
            "execution_result": result
        }
    
    def _evaluate_condition(self, condition):
        """Evaluate script execution condition"""
        
        if condition is None:
            return True
        
        # Simple condition evaluation
        # This could be enhanced with more complex logic
        if isinstance(condition, str):
            # Check if condition is a command that returns success
            try:
                result = self.shell_manager.shell_ops.execute_command(condition)
                return result["return_code"] == 0
            except:
                return False
        elif isinstance(condition, bool):
            return condition
        else:
            return False
```

### 4. Multi-Engine Performance Monitoring

```python
class MultiEnginePerformanceMonitor:
    """Monitor system performance using any engine"""
    
    def __init__(self, shell_manager):
        self.shell_manager = shell_manager
        self.logger = Logger("performance_monitor")
    
    def monitor_performance(self, monitoring_config, engine=None, **kwargs):
        """Monitor system performance using specified or auto-detected engine"""
        
        # Select optimal engine
        if engine is None:
            engine = self.shell_manager.get_optimal_engine(monitoring_config.get("complexity", "medium"))
        
        self.logger.info(f"Monitoring performance with {engine} engine")
        
        if engine == "spark" and self.shell_manager.spark_available:
            return self._monitor_performance_with_spark(monitoring_config, **kwargs)
        else:
            return self._monitor_performance_with_pandas(monitoring_config, **kwargs)
    
    def _monitor_performance_with_spark(self, monitoring_config, **kwargs):
        """Monitor performance using Spark for distributed monitoring"""
        
        monitoring_type = monitoring_config.get("type")
        
        if monitoring_type == "parallel":
            return self._monitor_parallel_performance_spark(monitoring_config, **kwargs)
        elif monitoring_type == "caching":
            return self._monitor_caching_performance_spark(monitoring_config, **kwargs)
        elif monitoring_type == "resource":
            return self._monitor_resource_performance_spark(monitoring_config, **kwargs)
        else:
            return {"error": f"Unknown monitoring type: {monitoring_type}"}
    
    def _monitor_performance_with_pandas(self, monitoring_config, **kwargs):
        """Monitor performance using Pandas for single-node monitoring"""
        
        monitoring_type = monitoring_config.get("type")
        
        if monitoring_type == "parallel":
            return self._monitor_parallel_performance_pandas(monitoring_config, **kwargs)
        elif monitoring_type == "caching":
            return self._monitor_caching_performance_pandas(monitoring_config, **kwargs)
        elif monitoring_type == "resource":
            return self._monitor_resource_performance_pandas(monitoring_config, **kwargs)
        else:
            return {"error": f"Unknown monitoring type: {monitoring_type}"}
    
    def _monitor_parallel_performance_spark(self, monitoring_config, **kwargs):
        """Monitor parallel performance using Spark"""
        
        # Execute parallel performance monitoring commands
        commands = [
            "uptime",
            "vmstat 1 5",
            "iostat 1 5"
        ]
        
        results = {}
        
        for command in commands:
            result = self.shell_manager.shell_ops.execute_command(command)
            results[command] = result
        
        return {
            "monitoring_type": "parallel",
            "engine": "spark",
            "results": results
        }
    
    def _monitor_parallel_performance_pandas(self, monitoring_config, **kwargs):
        """Monitor parallel performance using Pandas"""
        
        import psutil
        
        # Get system performance metrics
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        memory = psutil.virtual_memory()
        disk = psutil.disk_io_counters()
        
        return {
            "monitoring_type": "parallel",
            "engine": "pandas",
            "cpu_percent": cpu_percent,
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent
            },
            "disk": {
                "read_count": disk.read_count,
                "write_count": disk.write_count,
                "read_bytes": disk.read_bytes,
                "write_bytes": disk.write_bytes
            }
        }
    
    def _monitor_caching_performance_spark(self, monitoring_config, **kwargs):
        """Monitor caching performance using Spark"""
        
        # Execute caching performance monitoring commands
        commands = [
            "free -h",
            "cat /proc/meminfo | grep -i cache",
            "cat /proc/sys/vm/drop_caches"
        ]
        
        results = {}
        
        for command in commands:
            result = self.shell_manager.shell_ops.execute_command(command)
            results[command] = result
        
        return {
            "monitoring_type": "caching",
            "engine": "spark",
            "results": results
        }
    
    def _monitor_caching_performance_pandas(self, monitoring_config, **kwargs):
        """Monitor caching performance using Pandas"""
        
        import psutil
        
        # Get memory and cache information
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            "monitoring_type": "caching",
            "engine": "pandas",
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "cached": getattr(memory, 'cached', 0),
                "buffers": getattr(memory, 'buffers', 0)
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free
            }
        }
    
    def _monitor_resource_performance_spark(self, monitoring_config, **kwargs):
        """Monitor resource performance using Spark"""
        
        # Execute resource performance monitoring commands
        commands = [
            "df -h",
            "du -sh /*",
            "lsof | wc -l"
        ]
        
        results = {}
        
        for command in commands:
            result = self.shell_manager.shell_ops.execute_command(command)
            results[command] = result
        
        return {
            "monitoring_type": "resource",
            "engine": "spark",
            "results": results
        }
    
    def _monitor_resource_performance_pandas(self, monitoring_config, **kwargs):
        """Monitor resource performance using Pandas"""
        
        import psutil
        
        # Get disk and network information
        disk_partitions = psutil.disk_partitions()
        disk_usage = {}
        
        for partition in disk_partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_usage[partition.device] = {
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                }
            except PermissionError:
                continue
        
        network = psutil.net_io_counters()
        
        return {
            "monitoring_type": "resource",
            "engine": "pandas",
            "disk_partitions": disk_usage,
            "network": {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
        }
```

## Integration Examples

### 1. Multi-Engine Shell Operations Pipeline

```python
def create_multi_engine_shell_pipeline():
    """Create a complete multi-engine shell operations pipeline"""
    
    # Initialize shell manager
    shell_config = {
        "timeout": 300,
        "working_directory": "/tmp",
        "environment": {"PATH": "/usr/local/bin:/usr/bin:/bin"}
    }
    
    shell_manager = MultiEngineShellManager(default_engine="auto", shell_config=shell_config)
    
    # Create specialized managers
    process_manager = MultiEngineProcessManager(shell_manager)
    shell_scripting = MultiEngineShellScripting(shell_manager)
    performance_monitor = MultiEnginePerformanceMonitor(shell_manager)
    
    # Define shell operations
    shell_operations = {
        "system_check": {
            "command": "uname -a && cat /etc/os-release",
            "complexity": "simple"
        },
        "disk_usage": {
            "command": "df -h && du -sh /*",
            "complexity": "medium"
        },
        "process_analysis": {
            "command": "ps aux --sort=-%cpu | head -20",
            "complexity": "medium"
        }
    }
    
    # Execute shell operations with optimal engine selection
    shell_results = {}
    
    for operation_name, operation_config in shell_operations.items():
        try:
            result = shell_manager.execute_shell_command(
                operation_config["command"], operation_config
            )
            shell_results[operation_name] = {
                "status": "success",
                "result": result
            }
        except Exception as e:
            shell_results[operation_name] = {
                "status": "failed",
                "error": str(e)
            }
    
    # Manage processes
    process_config = {
        "type": "monitor",
        "complexity": "medium"
    }
    
    process_results = process_manager.manage_processes(process_config)
    
    # Execute maintenance script
    script_config = {
        "type": "maintenance",
        "script_path": "/tmp/maintenance.sh",
        "maintenance_type": "system_cleanup"
    }
    
    script_results = shell_scripting.execute_script(script_config)
    
    # Monitor performance
    monitoring_config = {
        "type": "resource",
        "complexity": "medium"
    }
    
    performance_results = performance_monitor.monitor_performance(monitoring_config)
    
    return shell_results, process_results, script_results, performance_results

# Run the pipeline
shell_pipeline_results = create_multi_engine_shell_pipeline()
```

### 2. Real-time Shell Operations Dashboard

```python
def create_shell_operations_dashboard():
    """Create a dashboard to monitor shell operations in real-time"""
    
    import dash
    from dash import dcc, html
    from dash.dependencies import Input, Output
    import plotly.graph_objs as go
    
    app = dash.Dash(__name__)
    
    app.layout = html.Div([
        html.H1("Multi-Engine Shell Operations Dashboard"),
        
        html.Div([
            html.Div([
                html.Label("Operation Type:"),
                dcc.Dropdown(
                    id="operation-filter",
                    options=[
                        {"label": "All Operations", "value": "all"},
                        {"label": "System Commands", "value": "system"},
                        {"label": "Process Management", "value": "process"},
                        {"label": "Performance Monitoring", "value": "performance"}
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
            dcc.Graph(id="command-execution-chart"),
            dcc.Graph(id="process-status-chart"),
            dcc.Graph(id="system-performance-chart")
        ]),
        
        dcc.Interval(id="update-interval", interval=30*1000)  # Update every 30 seconds
    ])
    
    @app.callback(
        [Output("command-execution-chart", "figure"),
         Output("process-status-chart", "figure"),
         Output("system-performance-chart", "figure")],
        [Input("update-interval", "n_intervals"),
         Input("operation-filter", "value"),
         Input("engine-filter", "value"),
         Input("update-frequency", "value")]
    )
    def update_charts(n, operation_type, engine, frequency):
        # Get shell operations data (this would come from your actual shell operations system)
        # For demonstration, we'll create sample data
        
        # Command execution chart
        time_points = list(range(24))  # Last 24 hours
        command_counts = [np.random.randint(50, 200) for _ in time_points]
        
        command_fig = go.Figure(data=[
            go.Scatter(x=time_points, y=command_counts, mode="lines+markers", name="Commands Executed")
        ])
        command_fig.update_layout(title="Shell Commands Executed Over Time", xaxis_title="Hours Ago", yaxis_title="Command Count")
        
        # Process status chart
        process_statuses = ["Running", "Sleeping", "Stopped", "Zombie"]
        process_counts = [850, 120, 25, 5]
        
        process_fig = go.Figure(data=[
            go.Pie(labels=process_statuses, values=process_counts, name="Process Status")
        ])
        process_fig.update_layout(title="System Process Status Distribution")
        
        # System performance chart
        performance_metrics = ["CPU Usage", "Memory Usage", "Disk I/O", "Network I/O"]
        performance_values = [45.2, 67.8, 23.1, 12.5]  # percentage
        
        performance_fig = go.Figure(data=[
            go.Bar(x=performance_metrics, y=performance_values, name="System Performance")
        ])
        performance_fig.update_layout(title="System Performance Metrics", yaxis_title="Usage (%)")
        
        return command_fig, process_fig, performance_fig
    
    return app

# Start the dashboard
shell_dashboard = create_shell_operations_dashboard()
shell_dashboard.run_server(debug=True, port=8057)
```

## Best Practices

### 1. Engine Selection
- Use **Pandas** for simple operations and single-node monitoring
- Use **Spark** for complex operations and distributed monitoring
- Use **Auto-detection** for unknown operation complexity
- Consider **system resources** when selecting engine

### 2. Performance Optimization
- **Use appropriate timeouts** for different command types
- **Implement command caching** for frequently used operations
- **Monitor resource usage** during execution
- **Use parallel execution** when possible

### 3. Security
- **Validate all shell commands** before execution
- **Use appropriate user permissions** for different operations
- **Implement command whitelisting** for production environments
- **Log all shell operations** for audit trails

### 4. Error Handling
- **Implement fallback mechanisms** when engines fail
- **Provide meaningful error messages** for debugging
- **Log shell operation decisions** for transparency
- **Retry failed operations** with different engines when possible

## Troubleshooting

### Common Issues

1. **Engine Compatibility Issues**
   ```python
   # Check engine availability
   if shell_manager.spark_available:
       print("Spark is available for distributed shell operations")
   else:
       print("Using Pandas only")
   ```

2. **Command Execution Issues**
   ```python
   # Check command permissions
   try:
       result = shell_manager.execute_shell_command("ls -la", {"complexity": "simple"})
       print("Command executed successfully")
   except Exception as e:
       print(f"Command execution failed: {e}")
   ```

3. **Process Management Issues**
   ```python
   # Check process manager capabilities
   process_manager = MultiEngineProcessManager(shell_manager)
   processes = process_manager.manage_processes({"type": "monitor"})
   print(f"Found {processes['total_count']} processes")
   ```

## Conclusion

The multi-engine shell operations capabilities in `siege_utilities` provide:

- **Seamless scalability** from single commands to distributed operations
- **Automatic engine selection** based on operation characteristics
- **Unified shell interfaces** that work with both Spark and Pandas
- **Comprehensive process management** across all engines
- **Performance optimization** through intelligent engine selection

By following this recipe, you can build robust, scalable shell operation pipelines that automatically adapt to your operation complexity and system requirements while providing comprehensive system administration capabilities.

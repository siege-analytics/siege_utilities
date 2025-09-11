#!/usr/bin/env python3
"""
Overnight Testing Suite for siege_utilities
===========================================

This script systematically tests all functions in the siege_utilities library
and generates comprehensive reports for morning review.

Usage:
    python overnight_testing_suite.py

Output:
    - overnight_test_results.json: Detailed test results
    - overnight_test_report.md: Human-readable summary
    - function_validation_log.txt: Detailed execution log
"""

import sys
import json
import traceback
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import importlib
import inspect
import time
import signal
from contextlib import contextmanager

# Add current directory to path for siege_utilities import
sys.path.insert(0, str(Path(__file__).parent))

try:
    import siege_utilities
    from siege_utilities import get_package_info
except ImportError as e:
    print(f"Error importing siege_utilities: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('function_validation_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@contextmanager
def timeout(seconds):
    """Context manager for timing out operations."""
    def signal_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Set the signal handler
    old_handler = signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # Restore the old signal handler
        signal.signal(signal.SIGALRM, old_handler)
        signal.alarm(0)

class FunctionTester:
    """Systematic function testing with comprehensive reporting."""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'total_functions': 0,
            'tested_functions': 0,
            'successful_tests': 0,
            'failed_tests': 0,
            'skipped_tests': 0,
            'function_results': {},
            'module_summary': {},
            'recommendations': [],
            'critical_issues': [],
            'performance_notes': []
        }
        
    def test_function_import(self, module_path: str, function_name: str) -> Dict[str, Any]:
        """Test if a function can be imported and basic introspection works."""
        result = {
            'importable': False,
            'callable': False,
            'has_docstring': False,
            'has_type_hints': False,
            'parameter_count': 0,
            'error': None,
            'execution_time': 0
        }
        
        start_time = time.time()
        
        try:
            # Try to import the module with timeout
            with timeout(10):  # 10 second timeout for imports
                module = importlib.import_module(module_path)
            
            # Check if function exists
            if hasattr(module, function_name):
                func = getattr(module, function_name)
                result['importable'] = True
                
                # Check if it's callable
                if callable(func):
                    result['callable'] = True
                    
                    # Get function signature
                    try:
                        sig = inspect.signature(func)
                        result['parameter_count'] = len(sig.parameters)
                        
                        # Check for type hints
                        if sig.return_annotation != inspect.Signature.empty:
                            result['has_type_hints'] = True
                        for param in sig.parameters.values():
                            if param.annotation != inspect.Parameter.empty:
                                result['has_type_hints'] = True
                                break
                                
                    except Exception as e:
                        result['error'] = f"Signature inspection failed: {e}"
                    
                    # Check for docstring
                    if func.__doc__ and func.__doc__.strip():
                        result['has_docstring'] = True
                        
        except TimeoutError as e:
            result['error'] = f"Import timed out: {e}"
        except Exception as e:
            result['error'] = f"Import failed: {e}"
            
        result['execution_time'] = time.time() - start_time
        return result
    
    def test_function_with_sample_data(self, module_path: str, function_name: str) -> Dict[str, Any]:
        """Test function with sample data where possible."""
        result = {
            'tested_with_data': False,
            'success': False,
            'error': None,
            'execution_time': 0,
            'data_types_tested': []
        }
        
        start_time = time.time()
        
        try:
            # Try to import the module with timeout
            with timeout(10):  # 10 second timeout for imports
                module = importlib.import_module(module_path)
            func = getattr(module, function_name)
            
            if not callable(func):
                result['error'] = "Function not callable"
                return result
                
            # Get function signature to understand parameters
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            
            # Skip functions that require complex parameters we can't easily provide
            skip_patterns = ['client_id', 'api_key', 'credentials', 'config', 'file_path', 'url', 'service_account', 'oauth', 'auth']
            if any(pattern in ' '.join(params).lower() for pattern in skip_patterns):
                result['error'] = "Skipped - requires external dependencies"
                return result
                
            # Skip functions that might prompt for user input
            if any(pattern in function_name.lower() for pattern in ['credential', 'auth', 'oauth', 'service_account', '1password', 'prompt']):
                result['error'] = "Skipped - might prompt for user input"
                return result
                
            # Try to call with minimal parameters
            try:
                with timeout(5):  # 5 second timeout for function execution
                    if len(params) == 0:
                        # No parameters
                        func()
                        result['success'] = True
                        result['tested_with_data'] = True
                        result['data_types_tested'] = ['no_params']
                    
                    elif len(params) == 1:
                        # Single parameter - try smart defaults based on function name
                        test_val = self._get_smart_test_value(function_name, params[0])
                        
                        try:
                            func(test_val)
                            result['success'] = True
                            result['tested_with_data'] = True
                            result['data_types_tested'].append(type(test_val).__name__)
                        except Exception as e:
                            # Fallback to common types
                            test_values = ["test_string", 42, [1, 2, 3], {"key": "value"}]
                            
                            for fallback_val in test_values:
                                try:
                                    func(fallback_val)
                                    result['success'] = True
                                    result['tested_with_data'] = True
                                    result['data_types_tested'].append(type(fallback_val).__name__)
                                    break
                                except Exception:
                                    continue
                            else:
                                result['error'] = f"Failed with all test values: {e}"
                                
                    else:
                        # Multiple parameters - try with smart defaults
                        try:
                            args = [self._get_smart_test_value(function_name, param) for param in params]
                            func(*args)
                            result['success'] = True
                            result['tested_with_data'] = True
                            result['data_types_tested'] = ['smart_defaults']
                        except Exception as e:
                            result['error'] = f"Failed with smart defaults: {e}"
                        
            except TimeoutError as e:
                result['error'] = f"Execution timed out: {e}"
            except Exception as e:
                result['error'] = f"Execution failed: {e}"
                
        except TimeoutError as e:
            result['error'] = f"Import timed out: {e}"
        except Exception as e:
            result['error'] = f"Module/function access failed: {e}"
            
        result['execution_time'] = time.time() - start_time
        return result
    
    def _get_smart_test_value(self, function_name: str, param_name: str):
        """Get smart test values based on function name and parameter name."""
        from pathlib import Path
        import tempfile
        
        # Path-related functions
        if 'path' in function_name.lower() or 'path' in param_name.lower():
            return Path('/tmp/test_path')
        
        # Directory functions
        if 'directory' in function_name.lower() or 'dir' in function_name.lower():
            return Path('/tmp/test_dir')
        
        # String functions
        if 'string' in function_name.lower() or param_name.lower() in ['text', 'message', 'name']:
            return "test_string"
        
        # Number functions
        if 'number' in function_name.lower() or param_name.lower() in ['count', 'limit', 'size']:
            return 42
        
        # Boolean functions
        if 'bool' in function_name.lower() or param_name.lower() in ['enabled', 'active', 'force']:
            return True
        
        # List functions
        if 'list' in function_name.lower() or param_name.lower() in ['items', 'values', 'data']:
            return [1, 2, 3]
        
        # Dict functions
        if 'dict' in function_name.lower() or param_name.lower() in ['config', 'options', 'params']:
            return {"key": "value"}
        
        # Default fallback
        return "test_string"
    
    def analyze_module_structure(self, module_path: str) -> Dict[str, Any]:
        """Analyze the structure and health of a module."""
        result = {
            'importable': False,
            'function_count': 0,
            'class_count': 0,
            'has_init': False,
            'error': None
        }
        
        try:
            module = importlib.import_module(module_path)
            result['importable'] = True
            
            # Count functions and classes
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) and not name.startswith('_'):
                    result['function_count'] += 1
                elif inspect.isclass(obj) and not name.startswith('_'):
                    result['class_count'] += 1
                    
            # Check for __init__.py
            module_file = Path(module.__file__) if hasattr(module, '__file__') else None
            if module_file and module_file.name == '__init__.py':
                result['has_init'] = True
                
        except Exception as e:
            result['error'] = f"Module analysis failed: {e}"
            
        return result
    
    def run_comprehensive_test(self):
        """Run comprehensive testing of all siege_utilities functions."""
        logger.info("Starting comprehensive siege_utilities testing...")
        
        # Get package info
        try:
            package_info = get_package_info()
            self.results['total_functions'] = package_info['total_functions']
            logger.info(f"Found {package_info['total_functions']} total functions")
        except Exception as e:
            logger.error(f"Failed to get package info: {e}")
            return
            
        # Test each module systematically
        modules_to_test = [
            'siege_utilities.analytics',
            'siege_utilities.config',
            'siege_utilities.core',
            'siege_utilities.data',
            'siege_utilities.distributed',
            'siege_utilities.files',
            'siege_utilities.geo',
            'siege_utilities.git',
            'siege_utilities.reporting',
            'siege_utilities.testing'
        ]
        
        for module_path in modules_to_test:
            logger.info(f"Testing module: {module_path}")
            
            # Analyze module structure
            module_analysis = self.analyze_module_structure(module_path)
            self.results['module_summary'][module_path] = module_analysis
            
            if not module_analysis['importable']:
                logger.warning(f"Module {module_path} not importable: {module_analysis['error']}")
                continue
                
            # Get all functions in the module
            try:
                module = importlib.import_module(module_path)
                functions = [name for name, obj in inspect.getmembers(module) 
                           if inspect.isfunction(obj) and not name.startswith('_')]
                
                logger.info(f"Found {len(functions)} functions in {module_path}")
                
                for func_name in functions:
                    logger.info(f"  Testing function: {func_name}")
                    
                    # Test import and basic properties
                    import_result = self.test_function_import(module_path, func_name)
                    
                    # Test with sample data
                    execution_result = self.test_function_with_sample_data(module_path, func_name)
                    
                    # Combine results
                    function_result = {
                        'module': module_path,
                        'import_test': import_result,
                        'execution_test': execution_result,
                        'overall_status': 'unknown'
                    }
                    
                    # Determine overall status
                    if import_result['importable'] and import_result['callable']:
                        if execution_result['success']:
                            function_result['overall_status'] = 'working'
                            self.results['successful_tests'] += 1
                        elif execution_result['error'] and 'Skipped' in execution_result['error']:
                            function_result['overall_status'] = 'skipped'
                            self.results['skipped_tests'] += 1
                        else:
                            function_result['overall_status'] = 'failed'
                            self.results['failed_tests'] += 1
                    else:
                        function_result['overall_status'] = 'broken'
                        self.results['failed_tests'] += 1
                        
                    self.results['function_results'][f"{module_path}.{func_name}"] = function_result
                    self.results['tested_functions'] += 1
                    
            except Exception as e:
                logger.error(f"Error testing module {module_path}: {e}")
                self.results['critical_issues'].append(f"Module {module_path}: {e}")
                
        # Generate recommendations
        self.generate_recommendations()
        
        logger.info("Testing completed!")
        logger.info(f"Total functions tested: {self.results['tested_functions']}")
        logger.info(f"Successful: {self.results['successful_tests']}")
        logger.info(f"Failed: {self.results['failed_tests']}")
        logger.info(f"Skipped: {self.results['skipped_tests']}")
    
    def generate_recommendations(self):
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Analyze failed functions
        failed_functions = [name for name, result in self.results['function_results'].items() 
                          if result['overall_status'] in ['failed', 'broken']]
        
        if failed_functions:
            recommendations.append({
                'priority': 'high',
                'category': 'broken_functions',
                'title': f'Fix {len(failed_functions)} broken functions',
                'description': f'Functions that failed testing: {", ".join(failed_functions[:10])}',
                'action': 'Review and fix import/execution issues'
            })
            
        # Analyze functions without docstrings
        no_docstring = [name for name, result in self.results['function_results'].items() 
                       if not result['import_test']['has_docstring']]
        
        if no_docstring:
            recommendations.append({
                'priority': 'medium',
                'category': 'documentation',
                'title': f'Add docstrings to {len(no_docstring)} functions',
                'description': f'Functions missing docstrings: {", ".join(no_docstring[:10])}',
                'action': 'Add comprehensive docstrings'
            })
            
        # Analyze functions without type hints
        no_type_hints = [name for name, result in self.results['function_results'].items() 
                        if not result['import_test']['has_type_hints']]
        
        if no_type_hints:
            recommendations.append({
                'priority': 'medium',
                'category': 'type_hints',
                'title': f'Add type hints to {len(no_type_hints)} functions',
                'description': f'Functions missing type hints: {", ".join(no_type_hints[:10])}',
                'action': 'Add comprehensive type annotations'
            })
            
        # Analyze performance
        slow_functions = [name for name, result in self.results['function_results'].items() 
                         if result['import_test']['execution_time'] > 0.1]
        
        if slow_functions:
            recommendations.append({
                'priority': 'low',
                'category': 'performance',
                'title': f'Optimize {len(slow_functions)} slow functions',
                'description': f'Functions with slow import/execution: {", ".join(slow_functions[:5])}',
                'action': 'Profile and optimize performance'
            })
            
        self.results['recommendations'] = recommendations
    
    def save_results(self):
        """Save test results to files."""
        # Save JSON results
        with open('overnight_test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
            
        # Generate markdown report
        self.generate_markdown_report()
        
    def generate_markdown_report(self):
        """Generate a human-readable markdown report."""
        report = f"""# Overnight Testing Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

- **Total Functions**: {self.results['total_functions']}
- **Tested Functions**: {self.results['tested_functions']}
- **Successful Tests**: {self.results['successful_tests']}
- **Failed Tests**: {self.results['failed_tests']}
- **Skipped Tests**: {self.results['skipped_tests']}

## Module Summary

"""
        
        for module, summary in self.results['module_summary'].items():
            report += f"### {module}\n"
            report += f"- Importable: {summary['importable']}\n"
            report += f"- Functions: {summary['function_count']}\n"
            report += f"- Classes: {summary['class_count']}\n"
            if summary['error']:
                report += f"- Error: {summary['error']}\n"
            report += "\n"
            
        # Add recommendations
        report += "## Recommendations\n\n"
        for rec in self.results['recommendations']:
            report += f"### {rec['title']} (Priority: {rec['priority']})\n"
            report += f"- **Category**: {rec['category']}\n"
            report += f"- **Description**: {rec['description']}\n"
            report += f"- **Action**: {rec['action']}\n\n"
            
        # Add critical issues
        if self.results['critical_issues']:
            report += "## Critical Issues\n\n"
            for issue in self.results['critical_issues']:
                report += f"- {issue}\n"
            report += "\n"
            
        # Add detailed function results
        report += "## Detailed Function Results\n\n"
        for func_name, result in self.results['function_results'].items():
            report += f"### {func_name}\n"
            report += f"- **Status**: {result['overall_status']}\n"
            report += f"- **Importable**: {result['import_test']['importable']}\n"
            report += f"- **Callable**: {result['import_test']['callable']}\n"
            report += f"- **Has Docstring**: {result['import_test']['has_docstring']}\n"
            report += f"- **Has Type Hints**: {result['import_test']['has_type_hints']}\n"
            report += f"- **Parameters**: {result['import_test']['parameter_count']}\n"
            if result['import_test']['error']:
                report += f"- **Import Error**: {result['import_test']['error']}\n"
            if result['execution_test']['error']:
                report += f"- **Execution Error**: {result['execution_test']['error']}\n"
            report += "\n"
            
        with open('overnight_test_report.md', 'w') as f:
            f.write(report)

def main():
    """Main execution function."""
    print("Starting Overnight Testing Suite for siege_utilities...")
    print("=" * 60)
    
    tester = FunctionTester()
    
    try:
        tester.run_comprehensive_test()
        tester.save_results()
        
        print("\n" + "=" * 60)
        print("Testing completed successfully!")
        print(f"Results saved to:")
        print("- overnight_test_results.json")
        print("- overnight_test_report.md")
        print("- function_validation_log.txt")
        
    except Exception as e:
        logger.error(f"Testing suite failed: {e}")
        logger.error(traceback.format_exc())
        print(f"\nTesting suite failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

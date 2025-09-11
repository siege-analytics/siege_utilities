#!/usr/bin/env python3
"""
Critical Untested Functions Testing Script

This script focuses on testing the most critical functions that have been identified
as needing real-world testing based on the function status tracking.

Priority: Functions that are marked as "❌ None" (not tested in real tasks)
"""

import sys
import os
import json
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add current directory to path
sys.path.append('.')

def test_critical_untested_functions():
    """Test the most critical untested functions."""
    
    print("🔬 Testing Critical Untested Functions")
    print("=" * 50)
    
    results = {
        "start_time": datetime.now().isoformat(),
        "tests": {},
        "errors": [],
        "summary": {}
    }
    
    # Define critical untested functions by module
    critical_functions = {
        "geo": [
            "get_census_data_selector",
            "select_census_datasets", 
            "get_analysis_approach",
            "concatenate_addresses",
            "use_nominatim_geocoder",
            "get_census_boundaries",
            "download_osm_data"
        ],
        "data": [
            "load_sample_data",
            "generate_synthetic_population",
            "generate_synthetic_businesses",
            "create_sample_dataset"
        ],
        "development": [
            "generate_architecture_diagram",
            "analyze_package_structure",
            "analyze_module",
            "analyze_function",
            "analyze_class"
        ],
        "files": [
            "calculate_file_hash",
            "generate_sha256_hash_for_file",
            "get_file_hash",
            "download_file",
            "download_file_with_retry",
            "copy_file",
            "move_file"
        ],
        "distributed": [
            "repartition_and_cache",
            "write_df_to_parquet",
            "upload_to_hdfs",
            "download_from_hdfs"
        ],
        "analytics": [
            "get_datadotworld_connector",
            "get_snowflake_connector"
        ]
    }
    
    total_tests = 0
    successful_tests = 0
    
    # Test each module
    for module, functions in critical_functions.items():
        print(f"\n📦 Testing {module.upper()} module ({len(functions)} functions)")
        print("-" * 40)
        
        module_results = {}
        
        for func_name in functions:
            total_tests += 1
            print(f"Testing {func_name}...", end=" ")
            
            try:
                # Try to import and test the function
                result = test_single_function(func_name, module)
                
                if result["success"]:
                    print("✅")
                    successful_tests += 1
                else:
                    print(f"❌ ({result['error']})")
                
                module_results[func_name] = result
                
            except Exception as e:
                print(f"❌ (Exception: {e})")
                module_results[func_name] = {
                    "success": False,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
                results["errors"].append({
                    "function": func_name,
                    "module": module,
                    "error": str(e)
                })
        
        results["tests"][module] = module_results
    
    # Calculate summary
    failed_tests = total_tests - successful_tests
    success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
    
    results["summary"] = {
        "total_tests": total_tests,
        "successful_tests": successful_tests,
        "failed_tests": failed_tests,
        "success_rate": success_rate
    }
    
    results["end_time"] = datetime.now().isoformat()
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 CRITICAL FUNCTIONS TEST SUMMARY")
    print("=" * 50)
    print(f"Total Tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Print module breakdown
    print("\n📦 MODULE BREAKDOWN:")
    for module, module_results in results["tests"].items():
        module_success = sum(1 for r in module_results.values() if r["success"])
        module_total = len(module_results)
        module_rate = (module_success / module_total * 100) if module_total > 0 else 0
        print(f"  {module.upper()}: {module_success}/{module_total} ({module_rate:.1f}%)")
    
    # Save results
    results_file = Path("overnight_results") / "critical_functions_test_results.json"
    results_file.parent.mkdir(exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    return results

def test_single_function(func_name: str, module: str) -> Dict[str, Any]:
    """Test a single function and return results."""
    
    try:
        # Import siege_utilities
        import siege_utilities as su
        
        # Check if function exists
        if not hasattr(su, func_name):
            return {
                "success": False,
                "error": f"Function {func_name} not found in siege_utilities",
                "module": module
            }
        
        # Get the function
        func = getattr(su, func_name)
        
        # Try to call the function with no arguments first
        try:
            result = func()
            return {
                "success": True,
                "result": str(result)[:200] + "..." if len(str(result)) > 200 else str(result),
                "module": module,
                "test_type": "no_args"
            }
        except TypeError as e:
            # Function requires arguments, try with smart defaults
            return test_function_with_args(func, func_name, module)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "module": module,
                "test_type": "no_args"
            }
    
    except ImportError as e:
        return {
            "success": False,
            "error": f"Import error: {e}",
            "module": module
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "module": module,
            "traceback": traceback.format_exc()
        }

def test_function_with_args(func, func_name: str, module: str) -> Dict[str, Any]:
    """Test a function that requires arguments with smart defaults."""
    
    import inspect
    
    try:
        # Get function signature
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        
        # Generate smart test arguments
        args = []
        for param in params:
            arg = get_smart_test_arg(param, func_name, module)
            args.append(arg)
        
        # Call function with arguments
        result = func(*args)
        
        return {
            "success": True,
            "result": str(result)[:200] + "..." if len(str(result)) > 200 else str(result),
            "module": module,
            "test_type": "with_args",
            "args_used": args
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "module": module,
            "test_type": "with_args"
        }

def get_smart_test_arg(param_name: str, func_name: str, module: str):
    """Generate smart test arguments based on parameter name and context."""
    
    # File-related parameters
    if 'file' in param_name.lower() or 'path' in param_name.lower():
        return "/tmp/test_file.txt"
    
    # URL parameters
    if 'url' in param_name.lower():
        return "https://example.com"
    
    # Data parameters
    if 'data' in param_name.lower():
        return {"test": "data"}
    
    # Config parameters
    if 'config' in param_name.lower():
        return {"setting": "value"}
    
    # String parameters
    if param_name.lower() in ['name', 'title', 'description', 'text']:
        return "test_string"
    
    # Number parameters
    if param_name.lower() in ['count', 'limit', 'size', 'year']:
        return 42
    
    # Boolean parameters
    if param_name.lower() in ['enabled', 'active', 'force']:
        return True
    
    # List parameters
    if param_name.lower() in ['items', 'values', 'list']:
        return [1, 2, 3]
    
    # Default fallback
    return "test_value"

def main():
    """Main entry point."""
    print("🌙 Critical Untested Functions Testing")
    print("Focusing on functions marked as '❌ None' in status tracking")
    print()
    
    results = test_critical_untested_functions()
    
    print("\n🌅 Critical functions testing completed!")
    print("Check overnight_results/critical_functions_test_results.json for details")

if __name__ == "__main__":
    main()

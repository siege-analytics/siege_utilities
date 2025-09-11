#!/usr/bin/env python3
"""
Test the Overnight Testing System

This script tests the overnight testing system components to ensure they work correctly.
"""

import sys
import os
import subprocess
from pathlib import Path

def test_overnight_system():
    """Test the overnight testing system components."""
    
    print("🧪 Testing Overnight Testing System Components")
    print("=" * 50)
    
    # Test scripts to run
    test_scripts = [
        ("test_critical_untested_functions.py", "Critical Functions Test"),
        ("convert_notebooks_to_scripts.py", "Notebook Conversion"),
        ("test_recipe_code.py", "Recipe Code Test"),
        ("generate_comprehensive_morning_report.py", "Morning Report Generator")
    ]
    
    results = {}
    
    for script_name, description in test_scripts:
        print(f"\n🧪 Testing: {description}")
        print(f"Script: {script_name}")
        
        script_path = Path(script_name)
        if not script_path.exists():
            print(f"❌ Script not found: {script_name}")
            results[script_name] = {"success": False, "error": "Script not found"}
            continue
        
        try:
            # Run the script with a short timeout
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=60,  # 1 minute timeout for testing
                cwd=Path.cwd()
            )
            
            if result.returncode == 0:
                print(f"✅ {description} - SUCCESS")
                results[script_name] = {
                    "success": True,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            else:
                print(f"❌ {description} - FAILED (exit code: {result.returncode})")
                print(f"Error: {result.stderr[:200]}...")
                results[script_name] = {
                    "success": False,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
        
        except subprocess.TimeoutExpired:
            print(f"⏰ {description} - TIMEOUT")
            results[script_name] = {
                "success": False,
                "error": "Script timed out"
            }
        
        except Exception as e:
            print(f"❌ {description} - EXCEPTION: {e}")
            results[script_name] = {
                "success": False,
                "error": str(e)
            }
    
    # Summary
    print(f"\n📊 TEST SUMMARY")
    print("=" * 30)
    
    successful = sum(1 for r in results.values() if r["success"])
    total = len(results)
    
    print(f"Total Tests: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    print(f"Success Rate: {(successful/total*100):.1f}%")
    
    print(f"\n📋 DETAILED RESULTS:")
    for script_name, result in results.items():
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {script_name}")
        if not result["success"]:
            error = result.get("error", "Unknown error")
            print(f"      Error: {error}")
    
    # Check if results directory exists
    results_dir = Path("overnight_results")
    if results_dir.exists():
        print(f"\n📁 Results directory exists: {results_dir}")
        result_files = list(results_dir.glob("*"))
        print(f"   Found {len(result_files)} result files")
    else:
        print(f"\n📁 Results directory will be created: {results_dir}")
    
    return results

def main():
    """Main entry point."""
    print("🌙 Overnight Testing System Test")
    print("Testing all components of the overnight testing system")
    print()
    
    results = test_overnight_system()
    
    print(f"\n🌅 Overnight system test completed!")
    
    # Check if we should run the full system
    successful = sum(1 for r in results.values() if r["success"])
    total = len(results)
    
    if successful == total:
        print("✅ All components working - ready for overnight testing!")
        print("Run './run_overnight_comprehensive.sh' to start full testing")
    else:
        print("⚠️  Some components have issues - review before running full system")
        print("Check the errors above and fix before running overnight tests")

if __name__ == "__main__":
    main()

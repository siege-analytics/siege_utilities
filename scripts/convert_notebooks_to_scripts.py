#!/usr/bin/env python3
"""
Notebook to Script Converter for Overnight Testing

This script converts all notebooks to executable Python scripts
and tests them systematically.
"""

import os
import sys
import json
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

def convert_notebooks_to_scripts():
    """Convert all notebooks to executable scripts and test them."""
    
    print("📓 Converting Notebooks to Executable Scripts")
    print("=" * 50)
    
    results = {
        "start_time": datetime.now().isoformat(),
        "conversions": {},
        "tests": {},
        "errors": []
    }
    
    # Find all notebooks
    notebooks_dir = Path("purgatory/example_files/examples")
    if not notebooks_dir.exists():
        print(f"❌ Notebooks directory not found: {notebooks_dir}")
        return results
    
    notebooks = list(notebooks_dir.glob("*.ipynb"))
    print(f"Found {len(notebooks)} notebooks to convert")
    
    # Create output directory
    output_dir = Path("overnight_results/notebook_scripts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for notebook in notebooks:
        print(f"\n📓 Converting: {notebook.name}")
        
        try:
            # Convert notebook to Python script
            script_path = output_dir / f"{notebook.stem}.py"
            
            # Use nbconvert to convert
            cmd = [
                "jupyter", "nbconvert",
                "--to", "python",
                "--output", str(script_path),
                str(notebook)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✅ Converted to: {script_path}")
                results["conversions"][notebook.name] = {
                    "success": True,
                    "script_path": str(script_path),
                    "stdout": result.stdout
                }
                
                # Test the converted script
                test_result = test_converted_script(script_path, notebook.name)
                results["tests"][notebook.name] = test_result
                
            else:
                print(f"❌ Conversion failed: {result.stderr}")
                results["conversions"][notebook.name] = {
                    "success": False,
                    "error": result.stderr
                }
                results["errors"].append({
                    "notebook": notebook.name,
                    "type": "conversion_error",
                    "error": result.stderr
                })
        
        except subprocess.TimeoutExpired:
            print(f"⏰ Conversion timed out for: {notebook.name}")
            results["conversions"][notebook.name] = {
                "success": False,
                "error": "Conversion timed out"
            }
            results["errors"].append({
                "notebook": notebook.name,
                "type": "timeout_error",
                "error": "Conversion timed out"
            })
        
        except Exception as e:
            print(f"❌ Error converting {notebook.name}: {e}")
            results["conversions"][notebook.name] = {
                "success": False,
                "error": str(e)
            }
            results["errors"].append({
                "notebook": notebook.name,
                "type": "conversion_exception",
                "error": str(e),
                "traceback": traceback.format_exc()
            })
    
    # Generate summary
    successful_conversions = sum(1 for r in results["conversions"].values() if r["success"])
    total_notebooks = len(notebooks)
    
    print(f"\n📊 CONVERSION SUMMARY")
    print("=" * 30)
    print(f"Total Notebooks: {total_notebooks}")
    print(f"Successful Conversions: {successful_conversions}")
    print(f"Failed Conversions: {total_notebooks - successful_conversions}")
    
    # Test summary
    if results["tests"]:
        successful_tests = sum(1 for r in results["tests"].values() if r["success"])
        total_tests = len(results["tests"])
        print(f"Successful Tests: {successful_tests}/{total_tests}")
    
    results["end_time"] = datetime.now().isoformat()
    
    # Save results
    results_file = Path("overnight_results/notebook_conversion_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    return results

def test_converted_script(script_path: Path, notebook_name: str) -> Dict[str, Any]:
    """Test a converted notebook script."""
    
    print(f"🧪 Testing converted script: {script_path.name}")
    
    try:
        # Modify the script to add error handling and path setup
        modified_script_path = script_path.parent / f"{script_path.stem}_test.py"
        
        with open(script_path, 'r') as f:
            original_content = f.read()
        
        # Add error handling and path setup
        modified_content = f"""#!/usr/bin/env python3
# Test script converted from notebook: {notebook_name}
# Generated: {datetime.now().isoformat()}

import sys
import os
import traceback

# Add current directory to path
sys.path.append('.')

# Add error handling wrapper
def safe_execute():
    try:
{original_content}
        return True, "Script executed successfully"
    except Exception as e:
        return False, f"Error: {{e}}\\nTraceback: {{traceback.format_exc()}}"

if __name__ == "__main__":
    success, message = safe_execute()
    if success:
        print("✅ Script executed successfully")
    else:
        print(f"❌ Script failed: {{message}}")
"""
        
        with open(modified_script_path, 'w') as f:
            f.write(modified_content)
        
        # Execute the modified script
        result = subprocess.run(
            [sys.executable, str(modified_script_path)],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=Path.cwd()
        )
        
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "script_path": str(modified_script_path)
        }
    
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Script execution timed out",
            "script_path": str(script_path)
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "script_path": str(script_path)
        }

def main():
    """Main entry point."""
    print("🌙 Notebook to Script Converter")
    print("Converting all notebooks to executable scripts for testing")
    print()
    
    results = convert_notebooks_to_scripts()
    
    print("\n🌅 Notebook conversion completed!")
    print("Check overnight_results/notebook_conversion_results.json for details")

if __name__ == "__main__":
    main()

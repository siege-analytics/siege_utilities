#!/usr/bin/env python3
"""
Recipe Code Testing Script

This script extracts code blocks from recipe markdown files
and tests them systematically.
"""

import os
import sys
import json
import re
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

def test_recipe_code():
    """Extract and test code from all recipe files."""
    
    print("📚 Testing Recipe Code")
    print("=" * 40)
    
    results = {
        "start_time": datetime.now().isoformat(),
        "recipes": {},
        "code_blocks": {},
        "tests": {},
        "errors": []
    }
    
    # Find all recipe files
    recipes_dir = Path("wiki/Recipes")
    if not recipes_dir.exists():
        print(f"❌ Recipes directory not found: {recipes_dir}")
        return results
    
    recipe_files = list(recipes_dir.glob("*.md"))
    print(f"Found {len(recipe_files)} recipe files")
    
    # Create output directory
    output_dir = Path("overnight_results/recipe_scripts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for recipe_file in recipe_files:
        print(f"\n📚 Processing recipe: {recipe_file.name}")
        
        try:
            # Extract code blocks from recipe
            code_blocks = extract_code_blocks(recipe_file)
            
            if not code_blocks:
                print(f"⚠️  No code blocks found in: {recipe_file.name}")
                results["recipes"][recipe_file.name] = {
                    "success": True,
                    "code_blocks_found": 0,
                    "message": "No code blocks to test"
                }
                continue
            
            print(f"Found {len(code_blocks)} code blocks")
            results["recipes"][recipe_file.name] = {
                "success": True,
                "code_blocks_found": len(code_blocks)
            }
            
            # Create test script for this recipe
            script_path = output_dir / f"{recipe_file.stem}_test.py"
            test_result = create_and_test_recipe_script(recipe_file, code_blocks, script_path)
            
            results["code_blocks"][recipe_file.name] = code_blocks
            results["tests"][recipe_file.name] = test_result
            
        except Exception as e:
            print(f"❌ Error processing {recipe_file.name}: {e}")
            results["recipes"][recipe_file.name] = {
                "success": False,
                "error": str(e)
            }
            results["errors"].append({
                "recipe": recipe_file.name,
                "type": "processing_error",
                "error": str(e),
                "traceback": traceback.format_exc()
            })
    
    # Generate summary
    total_recipes = len(recipe_files)
    successful_recipes = sum(1 for r in results["recipes"].values() if r["success"])
    total_code_blocks = sum(len(blocks) for blocks in results["code_blocks"].values())
    
    print(f"\n📊 RECIPE TESTING SUMMARY")
    print("=" * 35)
    print(f"Total Recipes: {total_recipes}")
    print(f"Successful Processing: {successful_recipes}")
    print(f"Total Code Blocks: {total_code_blocks}")
    
    # Test summary
    if results["tests"]:
        successful_tests = sum(1 for r in results["tests"].values() if r["success"])
        total_tests = len(results["tests"])
        print(f"Successful Tests: {successful_tests}/{total_tests}")
    
    results["end_time"] = datetime.now().isoformat()
    
    # Save results
    results_file = Path("overnight_results/recipe_test_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    return results

def extract_code_blocks(recipe_file: Path) -> List[str]:
    """Extract Python code blocks from a markdown file."""
    
    code_blocks = []
    
    with open(recipe_file, 'r') as f:
        content = f.read()
    
    # Find all code blocks
    # Pattern to match ```python ... ``` blocks
    pattern = r'```python\s*\n(.*?)\n```'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for match in matches:
        # Clean up the code block
        code = match.strip()
        if code:
            code_blocks.append(code)
    
    # Also look for ``` blocks without language specification
    pattern = r'```\s*\n(.*?)\n```'
    matches = re.findall(pattern, content, re.DOTALL)
    
    for match in matches:
        code = match.strip()
        # Check if it looks like Python code
        if (code.startswith('import ') or 
            code.startswith('from ') or 
            'def ' in code or 
            'class ' in code or
            '=' in code):
            code_blocks.append(code)
    
    return code_blocks

def create_and_test_recipe_script(recipe_file: Path, code_blocks: List[str], script_path: Path) -> Dict[str, Any]:
    """Create a test script from code blocks and test it."""
    
    print(f"🧪 Creating test script: {script_path.name}")
    
    try:
        # Create the test script
        with open(script_path, 'w') as f:
            f.write(f"""#!/usr/bin/env python3
# Test script extracted from recipe: {recipe_file.name}
# Generated: {datetime.now().isoformat()}

import sys
import os
import traceback

# Add current directory to path
sys.path.append('.')

# Add error handling wrapper
def safe_execute():
    try:
        print("Testing recipe code blocks...")
        
""")
            
            # Add each code block
            for i, code_block in enumerate(code_blocks):
                f.write(f"        # Code block {i+1}\n")
                f.write(f"        print('Executing code block {i+1}...')\n")
                
                # Indent the code block
                indented_code = '\n'.join('        ' + line for line in code_block.split('\n'))
                f.write(indented_code)
                f.write("\n\n")
            
            f.write("""        return True, "All code blocks executed successfully"
    except Exception as e:
        return False, f"Error: {e}\\nTraceback: {traceback.format_exc()}"

if __name__ == "__main__":
    success, message = safe_execute()
    if success:
        print("✅ Recipe code executed successfully")
    else:
        print(f"❌ Recipe code failed: {message}")
""")
        
        # Execute the test script
        result = subprocess.run(
            [sys.executable, str(script_path)],
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
            "script_path": str(script_path),
            "code_blocks_count": len(code_blocks)
        }
    
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Script execution timed out",
            "script_path": str(script_path),
            "code_blocks_count": len(code_blocks)
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "script_path": str(script_path),
            "code_blocks_count": len(code_blocks)
        }

def main():
    """Main entry point."""
    print("🌙 Recipe Code Testing")
    print("Extracting and testing code from all recipe files")
    print()
    
    results = test_recipe_code()
    
    print("\n🌅 Recipe code testing completed!")
    print("Check overnight_results/recipe_test_results.json for details")

if __name__ == "__main__":
    main()

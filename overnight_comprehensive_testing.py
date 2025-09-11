#!/usr/bin/env python3
"""
Comprehensive Overnight Testing System for Siege Utilities

This script systematically tests functions that have been improved but not yet
tested in real tasks, focusing on notebooks/recipes and untested functions.

Features:
- Converts notebooks/recipes into executable scripts
- Tests functions prioritized by status tracking
- Comprehensive error capture and reporting
- Automated morning report generation
- All operations run via scripts to prevent terminal hanging
"""

import os
import sys
import json
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import traceback

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('overnight_testing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OvernightTestingSystem:
    """Comprehensive overnight testing system for siege_utilities."""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.results_dir = self.base_dir / "overnight_results"
        self.results_dir.mkdir(exist_ok=True)
        
        self.test_results = {
            "start_time": datetime.now().isoformat(),
            "notebook_tests": {},
            "recipe_tests": {},
            "function_tests": {},
            "errors": [],
            "summary": {}
        }
        
        # Load function status tracking
        self.function_status = self._load_function_status()
        
        # Define test priorities based on status tracking
        self.test_priorities = {
            "critical_gaps": [
                "geo", "data", "development", "analytics_connectors"
            ],
            "high_priority": [
                "distributed", "git", "hygiene"
            ],
            "medium_priority": [
                "files", "core"
            ]
        }
    
    def _load_function_status(self) -> Dict[str, Any]:
        """Load function status tracking data."""
        try:
            status_file = self.base_dir / "FUNCTION_STATUS_TRACKING.md"
            if status_file.exists():
                # Parse the markdown to extract function status
                return self._parse_function_status(status_file)
            return {}
        except Exception as e:
            logger.error(f"Failed to load function status: {e}")
            return {}
    
    def _parse_function_status(self, status_file: Path) -> Dict[str, Any]:
        """Parse function status from markdown file."""
        # This is a simplified parser - in practice, you'd want more robust parsing
        status = {
            "untested_functions": [],
            "needs_testing": [],
            "production_ready": []
        }
        
        try:
            with open(status_file, 'r') as f:
                content = f.read()
                
            # Extract functions that need testing
            lines = content.split('\n')
            for line in lines:
                if '❌' in line and 'None' in line:
                    # Function that hasn't been tested in real tasks
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) > 1:
                            func_name = parts[1].strip()
                            if func_name and not func_name.startswith('-'):
                                status["untested_functions"].append(func_name)
                
                elif '🟡' in line and 'Needs Testing' in line:
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) > 1:
                            func_name = parts[1].strip()
                            if func_name and not func_name.startswith('-'):
                                status["needs_testing"].append(func_name)
                
                elif '✅' in line and 'Production Ready' in line:
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) > 1:
                            func_name = parts[1].strip()
                            if func_name and not func_name.startswith('-'):
                                status["production_ready"].append(func_name)
        
        except Exception as e:
            logger.error(f"Error parsing function status: {e}")
        
        return status
    
    def run_comprehensive_tests(self):
        """Run all comprehensive tests."""
        logger.info("🚀 Starting Comprehensive Overnight Testing")
        
        try:
            # 1. Test notebooks
            self._test_notebooks()
            
            # 2. Test recipes
            self._test_recipes()
            
            # 3. Test untested functions
            self._test_untested_functions()
            
            # 4. Generate morning report
            self._generate_morning_report()
            
        except Exception as e:
            logger.error(f"Critical error in comprehensive testing: {e}")
            self.test_results["errors"].append({
                "type": "critical_error",
                "error": str(e),
                "traceback": traceback.format_exc()
            })
        
        finally:
            self._save_results()
    
    def _test_notebooks(self):
        """Test all notebooks by converting to scripts and executing."""
        logger.info("📓 Testing Notebooks")
        
        notebooks_dir = self.base_dir / "purgatory" / "example_files" / "examples"
        if not notebooks_dir.exists():
            logger.warning(f"Notebooks directory not found: {notebooks_dir}")
            return
        
        notebook_files = list(notebooks_dir.glob("*.ipynb"))
        logger.info(f"Found {len(notebook_files)} notebooks to test")
        
        for notebook in notebook_files:
            try:
                self._test_single_notebook(notebook)
            except Exception as e:
                logger.error(f"Error testing notebook {notebook.name}: {e}")
                self.test_results["errors"].append({
                    "type": "notebook_error",
                    "notebook": notebook.name,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
    
    def _test_single_notebook(self, notebook_path: Path):
        """Test a single notebook by converting to script and executing."""
        logger.info(f"Testing notebook: {notebook_path.name}")
        
        # Convert notebook to Python script
        script_path = self.results_dir / f"{notebook_path.stem}_test.py"
        
        try:
            # Use nbconvert to convert notebook to script
            cmd = [
                "jupyter", "nbconvert", 
                "--to", "python",
                "--output", str(script_path),
                str(notebook_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                raise Exception(f"nbconvert failed: {result.stderr}")
            
            # Execute the converted script
            self._execute_test_script(script_path, "notebook")
            
        except subprocess.TimeoutExpired:
            raise Exception("Notebook conversion timed out")
        except Exception as e:
            raise Exception(f"Failed to test notebook: {e}")
    
    def _test_recipes(self):
        """Test all recipes by converting to scripts and executing."""
        logger.info("📚 Testing Recipes")
        
        recipes_dir = self.base_dir / "wiki" / "Recipes"
        if not recipes_dir.exists():
            logger.warning(f"Recipes directory not found: {recipes_dir}")
            return
        
        recipe_files = list(recipes_dir.glob("*.md"))
        logger.info(f"Found {len(recipe_files)} recipes to test")
        
        for recipe in recipe_files:
            try:
                self._test_single_recipe(recipe)
            except Exception as e:
                logger.error(f"Error testing recipe {recipe.name}: {e}")
                self.test_results["errors"].append({
                    "type": "recipe_error",
                    "recipe": recipe.name,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
    
    def _test_single_recipe(self, recipe_path: Path):
        """Test a single recipe by extracting code and executing."""
        logger.info(f"Testing recipe: {recipe_path.name}")
        
        # Extract code blocks from markdown
        script_path = self.results_dir / f"{recipe_path.stem}_test.py"
        
        try:
            with open(recipe_path, 'r') as f:
                content = f.read()
            
            # Extract Python code blocks
            code_blocks = self._extract_code_blocks(content)
            
            if not code_blocks:
                logger.warning(f"No code blocks found in recipe: {recipe_path.name}")
                return
            
            # Create test script
            with open(script_path, 'w') as f:
                f.write("# Recipe Test Script\n")
                f.write("import sys\n")
                f.write("import os\n")
                f.write("sys.path.append('.')\n\n")
                
                for i, code_block in enumerate(code_blocks):
                    f.write(f"# Code block {i+1}\n")
                    f.write(code_block)
                    f.write("\n\n")
            
            # Execute the test script
            self._execute_test_script(script_path, "recipe")
            
        except Exception as e:
            raise Exception(f"Failed to test recipe: {e}")
    
    def _extract_code_blocks(self, content: str) -> List[str]:
        """Extract Python code blocks from markdown content."""
        code_blocks = []
        lines = content.split('\n')
        in_code_block = False
        current_block = []
        
        for line in lines:
            if line.strip().startswith('```python'):
                in_code_block = True
                current_block = []
            elif line.strip().startswith('```') and in_code_block:
                in_code_block = False
                if current_block:
                    code_blocks.append('\n'.join(current_block))
                current_block = []
            elif in_code_block:
                current_block.append(line)
        
        return code_blocks
    
    def _test_untested_functions(self):
        """Test functions that haven't been tested in real tasks."""
        logger.info("🔬 Testing Untested Functions")
        
        # Get list of untested functions from status tracking
        untested_functions = self.function_status.get("untested_functions", [])
        needs_testing = self.function_status.get("needs_testing", [])
        
        all_untested = list(set(untested_functions + needs_testing))
        logger.info(f"Found {len(all_untested)} functions that need testing")
        
        # Group functions by module
        functions_by_module = {}
        for func in all_untested:
            if '.' in func:
                module = func.split('.')[0] + '.' + func.split('.')[1]
                if module not in functions_by_module:
                    functions_by_module[module] = []
                functions_by_module[module].append(func)
        
        # Test functions by priority
        for priority, modules in self.test_priorities.items():
            logger.info(f"Testing {priority} modules: {modules}")
            
            for module in modules:
                if module in functions_by_module:
                    self._test_module_functions(module, functions_by_module[module])
    
    def _test_module_functions(self, module: str, functions: List[str]):
        """Test functions in a specific module."""
        logger.info(f"Testing {len(functions)} functions in module: {module}")
        
        # Create test script for this module
        script_path = self.results_dir / f"{module.replace('.', '_')}_test.py"
        
        try:
            with open(script_path, 'w') as f:
                f.write(f"# Test script for {module}\n")
                f.write("import sys\n")
                f.write("import os\n")
                f.write("sys.path.append('.')\n\n")
                f.write("import siege_utilities as su\n")
                f.write("import traceback\n\n")
                
                f.write("results = {}\n\n")
                
                for func in functions:
                    f.write(f"# Testing {func}\n")
                    f.write("try:\n")
                    f.write(f"    # Import and test {func}\n")
                    f.write(f"    result = su.{func}()\n")
                    f.write(f"    results['{func}'] = {{'status': 'success', 'result': str(result)}}\n")
                    f.write("except Exception as e:\n")
                    f.write(f"    results['{func}'] = {{'status': 'error', 'error': str(e)}}\n")
                    f.write("\n")
                
                f.write("# Print results\n")
                f.write("for func, result in results.items():\n")
                f.write("    status = result['status']\n")
                f.write("    if status == 'success':\n")
                f.write("        print(f'✅ {func}: OK')\n")
                f.write("    else:\n")
                f.write("        print(f'❌ {func}: {result[\"error\"]}')\n")
            
            # Execute the test script
            self._execute_test_script(script_path, "function_test")
            
        except Exception as e:
            logger.error(f"Error testing module {module}: {e}")
            self.test_results["errors"].append({
                "type": "module_test_error",
                "module": module,
                "error": str(e),
                "traceback": traceback.format_exc()
            })
    
    def _execute_test_script(self, script_path: Path, test_type: str):
        """Execute a test script and capture results."""
        logger.info(f"Executing {test_type} script: {script_path.name}")
        
        try:
            # Run the script with timeout
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=self.base_dir
            )
            
            # Store results
            test_key = f"{script_path.stem}_{test_type}"
            self.test_results[f"{test_type}_tests"][test_key] = {
                "script": str(script_path),
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
            if result.returncode == 0:
                logger.info(f"✅ {test_type} script completed successfully")
            else:
                logger.error(f"❌ {test_type} script failed with return code {result.returncode}")
                logger.error(f"Error output: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            logger.error(f"⏰ {test_type} script timed out")
            self.test_results[f"{test_type}_tests"][f"{script_path.stem}_{test_type}"] = {
                "script": str(script_path),
                "returncode": -1,
                "stdout": "",
                "stderr": "Script timed out after 5 minutes",
                "success": False
            }
        
        except Exception as e:
            logger.error(f"Error executing {test_type} script: {e}")
            self.test_results["errors"].append({
                "type": f"{test_type}_execution_error",
                "script": str(script_path),
                "error": str(e),
                "traceback": traceback.format_exc()
            })
    
    def _generate_morning_report(self):
        """Generate comprehensive morning report."""
        logger.info("📊 Generating Morning Report")
        
        try:
            # Calculate summary statistics
            self._calculate_summary()
            
            # Generate markdown report
            report_path = self.results_dir / "morning_report.md"
            
            with open(report_path, 'w') as f:
                f.write("# 🌅 Morning Testing Report\n\n")
                f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Summary
                f.write("## 📊 Summary\n\n")
                summary = self.test_results["summary"]
                f.write(f"- **Total Tests Run**: {summary.get('total_tests', 0)}\n")
                f.write(f"- **Successful Tests**: {summary.get('successful_tests', 0)}\n")
                f.write(f"- **Failed Tests**: {summary.get('failed_tests', 0)}\n")
                f.write(f"- **Error Rate**: {summary.get('error_rate', 0):.1f}%\n\n")
                
                # Notebook Results
                f.write("## 📓 Notebook Test Results\n\n")
                notebook_tests = self.test_results.get("notebook_tests", {})
                if notebook_tests:
                    for test_name, result in notebook_tests.items():
                        status = "✅" if result["success"] else "❌"
                        f.write(f"- {status} **{test_name}**\n")
                        if not result["success"]:
                            f.write(f"  - Error: {result['stderr'][:200]}...\n")
                else:
                    f.write("No notebook tests were run.\n")
                f.write("\n")
                
                # Recipe Results
                f.write("## 📚 Recipe Test Results\n\n")
                recipe_tests = self.test_results.get("recipe_tests", {})
                if recipe_tests:
                    for test_name, result in recipe_tests.items():
                        status = "✅" if result["success"] else "❌"
                        f.write(f"- {status} **{test_name}**\n")
                        if not result["success"]:
                            f.write(f"  - Error: {result['stderr'][:200]}...\n")
                else:
                    f.write("No recipe tests were run.\n")
                f.write("\n")
                
                # Function Test Results
                f.write("## 🔬 Function Test Results\n\n")
                function_tests = self.test_results.get("function_tests", {})
                if function_tests:
                    for test_name, result in function_tests.items():
                        status = "✅" if result["success"] else "❌"
                        f.write(f"- {status} **{test_name}**\n")
                        if not result["success"]:
                            f.write(f"  - Error: {result['stderr'][:200]}...\n")
                else:
                    f.write("No function tests were run.\n")
                f.write("\n")
                
                # Errors
                f.write("## ❌ Errors and Issues\n\n")
                errors = self.test_results.get("errors", [])
                if errors:
                    for error in errors:
                        f.write(f"- **{error['type']}**: {error['error']}\n")
                else:
                    f.write("No critical errors occurred.\n")
                f.write("\n")
                
                # Recommendations
                f.write("## 🎯 Recommendations\n\n")
                f.write("Based on the overnight testing results:\n\n")
                
                if summary.get('error_rate', 0) > 50:
                    f.write("- 🔴 **High Error Rate**: Focus on fixing critical issues first\n")
                elif summary.get('error_rate', 0) > 20:
                    f.write("- 🟡 **Moderate Error Rate**: Address failing tests systematically\n")
                else:
                    f.write("- 🟢 **Low Error Rate**: Continue with planned improvements\n")
                
                f.write("- Review failed tests and fix underlying issues\n")
                f.write("- Update documentation for functions that worked\n")
                f.write("- Create unit tests for newly validated functions\n")
                f.write("- Plan next phase of testing based on results\n\n")
            
            logger.info(f"Morning report generated: {report_path}")
            
        except Exception as e:
            logger.error(f"Error generating morning report: {e}")
            self.test_results["errors"].append({
                "type": "report_generation_error",
                "error": str(e),
                "traceback": traceback.format_exc()
            })
    
    def _calculate_summary(self):
        """Calculate summary statistics."""
        total_tests = 0
        successful_tests = 0
        
        # Count notebook tests
        for result in self.test_results.get("notebook_tests", {}).values():
            total_tests += 1
            if result["success"]:
                successful_tests += 1
        
        # Count recipe tests
        for result in self.test_results.get("recipe_tests", {}).values():
            total_tests += 1
            if result["success"]:
                successful_tests += 1
        
        # Count function tests
        for result in self.test_results.get("function_tests", {}).values():
            total_tests += 1
            if result["success"]:
                successful_tests += 1
        
        failed_tests = total_tests - successful_tests
        error_rate = (failed_tests / total_tests * 100) if total_tests > 0 else 0
        
        self.test_results["summary"] = {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "error_rate": error_rate
        }
    
    def _save_results(self):
        """Save all test results to JSON file."""
        self.test_results["end_time"] = datetime.now().isoformat()
        
        results_file = self.results_dir / "overnight_test_results.json"
        
        try:
            with open(results_file, 'w') as f:
                json.dump(self.test_results, f, indent=2)
            
            logger.info(f"Test results saved to: {results_file}")
            
        except Exception as e:
            logger.error(f"Error saving test results: {e}")

def main():
    """Main entry point for overnight testing."""
    print("🌙 Starting Comprehensive Overnight Testing System")
    print("=" * 60)
    
    # Create and run testing system
    testing_system = OvernightTestingSystem()
    testing_system.run_comprehensive_tests()
    
    print("=" * 60)
    print("🌅 Overnight testing completed!")
    print("Check the 'overnight_results' directory for detailed reports.")

if __name__ == "__main__":
    main()

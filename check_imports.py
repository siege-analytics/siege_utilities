#!/usr/bin/env python3
"""
Comprehensive import diagnostic for siege_utilities
Finds exactly what's broken and what needs fixing
"""

import sys
import importlib
import traceback
from pathlib import Path
import ast
import re

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))


def find_python_files():
    """Find all Python files in the package."""
    current_dir = Path(__file__).parent
    python_files = []

    for py_file in current_dir.rglob("*.py"):
        if "__pycache__" not in str(py_file):
            python_files.append(py_file)

    return python_files


def analyze_imports_in_file(file_path):
    """Analyze what imports a file is trying to make."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        tree = ast.parse(content)
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(('import', alias.name))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append(('from', module, alias.name))

        return imports

    except Exception as e:
        return [('ERROR', str(e))]


def test_individual_module_import(module_path):
    """Test importing a single module and report issues."""
    try:
        module = importlib.import_module(module_path)

        # Get all functions in the module
        functions = []
        errors = []

        for name in dir(module):
            if not name.startswith('_'):
                obj = getattr(module, name)
                if callable(obj):
                    functions.append(name)

        return {
            'success': True,
            'functions': functions,
            'errors': errors,
            'module': module
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def check_function_dependencies(module, function_name):
    """Check if a function can actually run by testing its dependencies."""
    try:
        func = getattr(module, function_name)

        # Try to get the function's source to see what it calls
        import inspect
        try:
            source = inspect.getsource(func)

            # Look for function calls that might be missing
            missing_deps = []

            # Common patterns that might be missing
            patterns = [
                r'log_info\(',
                r'log_error\(',
                r'log_warning\(',
                r'log_debug\(',
                r'ensure_path_exists\(',
                r'get_file_hash\(',
                r'check_if_file_exists_at_path\(',
            ]

            for pattern in patterns:
                if re.search(pattern, source):
                    func_name = pattern.replace('(', '').replace('\\', '')
                    if not hasattr(module, func_name):
                        missing_deps.append(func_name)

            return missing_deps

        except:
            return ['Could not analyze source']

    except Exception as e:
        return [f'Error accessing function: {e}']


def main():
    print("🔍 Siege Utilities Import Diagnostic")
    print("=" * 50)

    # 1. Find all Python files
    python_files = find_python_files()
    print(f"📁 Found {len(python_files)} Python files")

    # 2. Try to import the main package
    print("\n📦 Testing main package import...")
    try:
        import siege_utilities
        print("✅ Main package imported successfully")
        main_attrs = len(dir(siege_utilities))
        print(f"📊 Main package has {main_attrs} attributes")

        # Check if diagnostic functions work
        if hasattr(siege_utilities, 'get_package_info'):
            try:
                info = siege_utilities.get_package_info()
                print(f"📊 Package reports {info.get('total_functions', 0)} functions")
                print(f"📊 Package reports {info.get('total_modules', 0)} modules")

                failed = info.get('failed_imports', {})
                if failed:
                    print(f"⚠️  Package reports {len(failed)} failed imports:")
                    for module, error in failed.items():
                        print(f"   ❌ {module}: {error}")

            except Exception as e:
                print(f"❌ get_package_info failed: {e}")
        else:
            print("⚠️  No get_package_info function available")

    except Exception as e:
        print(f"❌ Main package import failed: {e}")
        print(traceback.format_exc())

    # 3. Test individual modules
    print("\n🔍 Testing individual modules...")

    modules_to_test = [
        'siege_utilities.core.logging',
        'siege_utilities.core.string_utils',
        'siege_utilities.files.hashing',
        'siege_utilities.files.operations',
        'siege_utilities.files.paths',
        'siege_utilities.files.remote',
        'siege_utilities.files.shell',
        'siege_utilities.geo.geocoding',
        'siege_utilities.distributed.hdfs_config',
        'siege_utilities.distributed.spark_utils',
    ]

    module_results = {}

    for module_name in modules_to_test:
        print(f"\n📋 Testing {module_name}...")
        result = test_individual_module_import(module_name)
        module_results[module_name] = result

        if result['success']:
            print(f"   ✅ Imported successfully")
            print(f"   📊 {len(result['functions'])} functions found")

            # Check function dependencies
            if result['functions']:
                print(f"   🔍 Checking function dependencies...")
                for func_name in result['functions'][:3]:  # Check first 3 functions
                    missing = check_function_dependencies(result['module'], func_name)
                    if missing:
                        print(f"      ❌ {func_name} missing: {missing}")
                    else:
                        print(f"      ✅ {func_name} dependencies OK")
        else:
            print(f"   ❌ Import failed: {result['error']}")

    # 4. Analyze import statements in files
    print("\n📋 Analyzing import statements in files...")

    for py_file in python_files:
        if '__init__' in py_file.name:
            continue  # Skip __init__ files for now

        rel_path = py_file.relative_to(Path(__file__).parent)
        print(f"\n📄 {rel_path}")

        imports = analyze_imports_in_file(py_file)

        siege_imports = []
        external_imports = []
        errors = []

        for imp in imports:
            if len(imp) == 2 and imp[0] == 'ERROR':
                errors.append(imp[1])
            elif 'siege_utilities' in str(imp):
                siege_imports.append(imp)
            else:
                external_imports.append(imp)

        if errors:
            print(f"   ❌ Parse errors: {errors}")

        if siege_imports:
            print(f"   🔗 Siege imports: {len(siege_imports)}")
            for imp in siege_imports:
                print(f"      {imp}")

        if external_imports:
            print(f"   📦 External imports: {len(external_imports)}")

    # 5. Summary and recommendations
    print("\n" + "=" * 50)
    print("📋 SUMMARY & RECOMMENDATIONS")
    print("=" * 50)

    successful_modules = sum(1 for r in module_results.values() if r['success'])
    total_modules = len(module_results)

    print(f"📊 Module import success rate: {successful_modules}/{total_modules}")

    if successful_modules == 0:
        print("🚨 CRITICAL: No modules can be imported")
        print("💡 Check your __init__.py files for syntax errors")
    elif successful_modules < total_modules * 0.5:
        print("⚠️  Many modules failing - likely systematic import issues")
        print("💡 Focus on fixing core.logging first")
    else:
        print("✅ Most modules importing successfully")
        print("💡 Check function dependencies and mutual availability")


if __name__ == "__main__":
    main()
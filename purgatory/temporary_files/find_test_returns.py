#!/usr/bin/env python3
"""
Script to find test functions that return values instead of using assertions.
"""

import ast
import sys
from pathlib import Path


def find_test_functions_with_returns(file_path):
    """Find test functions that have return statements."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()

        tree = ast.parse(content)

        problematic_functions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                # Check if this function has return statements
                returns = []
                for child in ast.walk(node):
                    if isinstance(child, ast.Return) and child != node:
                        returns.append(child.lineno)

                if returns:
                    problematic_functions.append({
                        'file': str(file_path),
                        'function': node.name,
                        'line': node.lineno,
                        'returns': returns
                    })

        return problematic_functions

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []


def main():
    """Main function."""
    # Look for test files in common locations
    potential_test_files = [
        'test_siege_utilities.py',
        'tests/test_siege_utilities.py',
        'tests/test_*.py',
    ]

    # Find all Python test files
    test_files = []

    # Check specific files
    for pattern in ['test_siege_utilities.py', 'tests/test_siege_utilities.py']:
        if Path(pattern).exists():
            test_files.append(Path(pattern))

    # Check tests directory for any test_*.py files
    tests_dir = Path('tests')
    if tests_dir.exists():
        test_files.extend(tests_dir.glob('test_*.py'))

    # Also check current directory for test_*.py files
    test_files.extend(Path('.').glob('test_*.py'))

    # Remove duplicates
    test_files = list(set(test_files))

    if not test_files:
        print("❌ Could not find any test files")
        print("💡 Run this script from the project root directory")
        print("💡 Looking for: test_*.py or tests/test_*.py")
        return

    print(f"🔍 Analyzing {len(test_files)} test file(s):")
    for f in test_files:
        print(f"   📄 {f}")
    print()

    all_problematic_functions = []

    for test_file in test_files:
        problematic_functions = find_test_functions_with_returns(test_file)
        all_problematic_functions.extend(problematic_functions)

    if not all_problematic_functions:
        print("✅ No test functions with return statements found in any files!")
        return

    print(f"❌ Found {len(all_problematic_functions)} test functions that return values:")
    print("=" * 80)

    # Group by file for cleaner output
    files_with_issues = {}
    for func in all_problematic_functions:
        file_name = func['file']
        if file_name not in files_with_issues:
            files_with_issues[file_name] = []
        files_with_issues[file_name].append(func)

    for file_name, functions in files_with_issues.items():
        print(f"\n📁 File: {file_name}")
        print("-" * 40)

        for func in functions:
            print(f"📍 Function: {func['function']} (line {func['line']})")
            print(f"   Returns on lines: {func['returns']}")
        print()

    print("🔧 Fix these functions by:")
    print("  1. Replace 'return True' with 'assert True' or proper assertions")
    print("  2. Replace 'return False' with 'assert False' or let exceptions bubble up")
    print("  3. Remove 'return' statements that don't add value")

    print(f"\n💡 Quick fix commands:")
    for file_name in files_with_issues.keys():
        print(f"   grep -n 'return ' {file_name}")

    print(f"\n📝 Summary by file:")
    for file_name, functions in files_with_issues.items():
        func_names = [f['function'] for f in functions]
        print(f"   {file_name}: {', '.join(func_names)}")


if __name__ == "__main__":
    main()
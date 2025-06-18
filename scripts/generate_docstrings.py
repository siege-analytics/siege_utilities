#!/usr/bin/env python3
"""
Auto-generate docstrings for functions missing them in siege_utilities
"""

import ast
import os
import inspect
import textwrap
from pathlib import Path
from typing import get_type_hints


def analyze_function_signature(func):
    """Analyze a function to generate a docstring template."""
    try:
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)

        # Get parameters
        params = []
        for name, param in sig.parameters.items():
            param_type = type_hints.get(name, 'Any')
            param_desc = f"{name} ({param_type.__name__ if hasattr(param_type, '__name__') else str(param_type)}): Description needed"

            # Add default value info
            if param.default != inspect.Parameter.empty:
                param_desc += f", defaults to {param.default}"

            params.append(param_desc)

        # Get return type
        return_type = type_hints.get('return', 'Any')
        return_desc = f"{return_type.__name__ if hasattr(return_type, '__name__') else str(return_type)}: Description needed"

        return params, return_desc

    except Exception as e:
        return [], "Description needed"


def generate_docstring_template(func_name, func_obj=None):
    """Generate a comprehensive docstring template."""

    # Try to analyze function signature if object is available
    params, return_desc = [], "Description needed"
    if func_obj:
        params, return_desc = analyze_function_signature(func_obj)

    # Generate docstring based on function name patterns
    if 'log_' in func_name:
        brief = f"Log a message using the {func_name.replace('log_', '')} level."
        category = "Logging"
    elif 'file' in func_name or 'path' in func_name:
        brief = f"Perform file operations: {func_name.replace('_', ' ')}."
        category = "File Operations"
    elif 'hash' in func_name:
        brief = f"Generate or verify hash: {func_name.replace('_', ' ')}."
        category = "Hashing"
    elif 'geo' in func_name or 'coord' in func_name:
        brief = f"Geographic processing: {func_name.replace('_', ' ')}."
        category = "Geospatial"
    elif 'spark' in func_name or 'hdfs' in func_name:
        brief = f"Distributed computing: {func_name.replace('_', ' ')}."
        category = "Distributed Computing"
    else:
        brief = f"Utility function: {func_name.replace('_', ' ')}."
        category = "Utilities"

    # Build docstring
    docstring_parts = [
        f'"""',
        f'{brief}',
        f'',
        f'Part of Siege Utilities {category} module.',
        f'Auto-discovered and available at package level.',
        f''
    ]

    # Add parameters if any
    if params:
        docstring_parts.extend([
            'Args:',
            *[f'    {param}' for param in params],
            ''
        ])

    # Add returns
    docstring_parts.extend([
        'Returns:',
        f'    {return_desc}',
        ''
    ])

    # Add example
    docstring_parts.extend([
        'Example:',
        f'    >>> import siege_utilities',
        f'    >>> result = siege_utilities.{func_name}()',
        f'    >>> print(result)',
        '',
    ])

    # Add note about auto-discovery
    docstring_parts.extend([
        'Note:',
        '    This function is auto-discovered and available without imports',
        '    across all siege_utilities modules.',
        '"""'
    ])

    return '\n'.join(docstring_parts)


class DocstringAdder(ast.NodeTransformer):
    """AST transformer to add docstrings to functions."""

    def __init__(self, module_functions=None):
        self.module_functions = module_functions or {}

    def visit_FunctionDef(self, node):
        # Check if function already has a docstring
        has_docstring = (
                node.body and
                isinstance(node.body[0], ast.Expr) and
                isinstance(node.body[0].value, ast.Constant) and
                isinstance(node.body[0].value.value, str)
        )

        if not has_docstring:
            # Get function object if available
            func_obj = self.module_functions.get(node.name)

            # Generate docstring
            docstring = generate_docstring_template(node.name, func_obj)

            # Create docstring node
            docstring_node = ast.Expr(value=ast.Constant(value=docstring))

            # Insert at beginning of function body
            node.body.insert(0, docstring_node)

            print(f"✅ Added docstring to {node.name}")
        else:
            print(f"⏭️  {node.name} already has docstring")

        return self.generic_visit(node)


def process_python_file(file_path):
    """Process a single Python file to add missing docstrings."""
    print(f"\n🔍 Processing {file_path}")

    try:
        # Read the file
        with open(file_path, 'r') as f:
            content = f.read()

        # Parse AST
        tree = ast.parse(content)

        # Try to import the module to get function objects
        module_functions = {}
        try:
            # Convert file path to module path
            relative_path = file_path.relative_to(Path.cwd())
            module_path = str(relative_path).replace('/', '.').replace('.py', '')

            # Import and get functions
            module = __import__(module_path, fromlist=[''])
            module_functions = {
                name: obj for name, obj in inspect.getmembers(module)
                if inspect.isfunction(obj) and not name.startswith('_')
            }
        except Exception as e:
            print(f"⚠️  Could not import module for type hints: {e}")

        # Transform AST
        transformer = DocstringAdder(module_functions)
        new_tree = transformer.visit(tree)

        # Convert back to source code
        import astor  # You'll need: pip install astor
        new_content = astor.to_source(new_tree)

        # Write back to file
        with open(file_path, 'w') as f:
            f.write(new_content)

        print(f"✅ Updated {file_path}")

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")


def main():
    """Main function to process all Python files in siege_utilities."""

    print("🚀 Auto-generating docstrings for siege_utilities")
    print("=" * 50)

    # Find all Python files
    siege_utils_path = Path('siege_utilities')
    python_files = list(siege_utils_path.rglob('*.py'))

    # Filter out __init__.py and other special files
    python_files = [
        f for f in python_files
        if f.name not in ['__init__.py', 'setup.py']
           and '__pycache__' not in str(f)
    ]

    print(f"📁 Found {len(python_files)} Python files to process")

    # Process each file
    for file_path in python_files:
        process_python_file(file_path)

    print(f"\n🎉 Docstring generation complete!")
    print(f"📝 Processed {len(python_files)} files")
    print(f"💡 Rebuild docs with: cd docs && make html")


if __name__ == "__main__":
    main()
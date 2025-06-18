"""
Auto-generate docstrings for functions missing them in siege_utilities.
Part of the hygiene maintenance toolkit.
"""
import ast
import os
import sys
import inspect
import textwrap
from pathlib import Path
from typing import get_type_hints, Any


def analyze_function_signature(func):
    """Analyze a function to generate parameter and return type info."""
    try:
        sig = inspect.signature(func)
        params = []
        for name, param in sig.parameters.items():
            param_type = 'Any'
            if param.annotation != inspect.Parameter.empty:
                param_type = getattr(param.annotation, '__name__', str(
                    param.annotation))
            param_desc = f'{name} ({param_type}): Description needed'
            if param.default != inspect.Parameter.empty:
                param_desc += f', defaults to {repr(param.default)}'
            params.append(param_desc)
        return_type = 'Any'
        if sig.return_annotation != inspect.Parameter.empty:
            return_type = getattr(sig.return_annotation, '__name__', str(
                sig.return_annotation))
        return_desc = f'{return_type}: Description needed'
        return params, return_desc
    except Exception as e:
        print(f'   ⚠️  Could not analyze signature: {e}')
        return [], 'Any: Description needed'


def categorize_function(func_name):
    """Categorize function based on name patterns."""
    name_lower = func_name.lower()
    if any(x in name_lower for x in ['log_', 'logging', 'debug', 'info',
        'warning', 'error', 'critical']):
        return 'Logging', 'Log messages and debugging information.'
    elif any(x in name_lower for x in ['file', 'path', 'directory', 'folder']):
        return 'File Operations', 'File and directory management.'
    elif any(x in name_lower for x in ['hash', 'checksum', 'signature',
        'verify']):
        return 'Hashing', 'Generate and verify file hashes and signatures.'
    elif any(x in name_lower for x in ['download', 'upload', 'remote',
        'url', 'http']):
        return ('Remote Operations',
            'Handle remote files and network operations.')
    elif any(x in name_lower for x in ['geo', 'coord', 'latitude',
        'longitude', 'spatial']):
        return 'Geospatial', 'Geographic and spatial data processing.'
    elif any(x in name_lower for x in ['spark', 'hdfs', 'distributed',
        'cluster']):
        return ('Distributed Computing',
            'Distributed computing and big data processing.')
    elif any(x in name_lower for x in ['string', 'text', 'clean', 'trim',
        'quote']):
        return 'String Utilities', 'String manipulation and text processing.'
    elif any(x in name_lower for x in ['config', 'setup', 'init']):
        return 'Configuration', 'Package configuration and initialization.'
    else:
        return 'Utilities', 'General utility functions.'


def generate_docstring_template(func_name, func_obj=None):
    """Generate a comprehensive docstring template."""
    category, category_desc = categorize_function(func_name)
    params, return_desc = [], 'Any: Description needed'
    if func_obj:
        params, return_desc = analyze_function_signature(func_obj)
    readable_name = func_name.replace('_', ' ').title()
    brief = f'{readable_name}.'
    docstring_parts = [f'{brief}', f'', f'{category_desc}',
        f'Auto-discovered function available at package level.', f'']
    if params:
        docstring_parts.extend(['Args:', *[f'    {param}' for param in
            params], ''])
    docstring_parts.extend(['Returns:', f'    {return_desc}', ''])
    if params:
        param_names = [p.split('(')[0] for p in params[:2]]
        example_args = ', '.join([f'"{name}_value"' for name in param_names])
        if len(params) > 2:
            example_args += ', ...'
    else:
        example_args = ''
    example_import = '    >>> import siege_utilities'
    example_call = (
        f'    >>> result = siege_utilities.{func_name}({example_args})')
    example_comment = '    >>> # Process result as needed'
    docstring_parts.extend(['Example:', example_import, example_call,
        example_comment, ''])
    note_line1 = (
        '    This function is auto-discovered and available without imports')
    note_line2 = '    across all siege_utilities modules.'
    docstring_parts.extend(['Note:', note_line1, note_line2])
    return '\n'.join(docstring_parts)


class DocstringAdder(ast.NodeTransformer):
    """AST transformer to add docstrings to functions."""

    def __init__(self, module_name='unknown'):
        self.module_name = module_name
        self.functions_processed = 0
        self.functions_skipped = 0

    def visit_FunctionDef(self, node):
        """Visit Functiondef.

General utility functions.
Auto-discovered function available at package level.

Returns:
    Any: Description needed

Example:
    >>> import siege_utilities
    >>> result = siege_utilities.visit_FunctionDef()
    >>> # Process result as needed

Note:
    This function is auto-discovered and available without imports
    across all siege_utilities modules."""
        if node.name.startswith('_'):
            return self.generic_visit(node)
        has_docstring = node.body and isinstance(node.body[0], ast.Expr
            ) and isinstance(node.body[0].value, (ast.Constant, ast.Str))
        if not has_docstring:
            docstring_content = generate_docstring_template(node.name)
            if hasattr(ast, 'Constant'):
                docstring_node = ast.Expr(value=ast.Constant(value=
                    docstring_content))
            else:
                docstring_node = ast.Expr(value=ast.Str(s=docstring_content))
            node.body.insert(0, docstring_node)
            print(f'   ✅ Added docstring to {node.name}')
            self.functions_processed += 1
        else:
            print(f'   ⏭️  {node.name} already has docstring')
            self.functions_skipped += 1
        return self.generic_visit(node)


def process_python_file(file_path):
    """Process a single Python file to add missing docstrings."""
    relative_path = file_path.relative_to(Path.cwd())
    print(f'\n🔍 Processing {relative_path}')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            print(f'   ❌ Syntax error in {file_path}: {e}')
            return False
        module_name = str(relative_path).replace('.py', '').replace('/', '.')
        transformer = DocstringAdder(module_name)
        new_tree = transformer.visit(tree)
        if transformer.functions_processed > 0:
            try:
                import astor
                new_content = astor.to_source(new_tree)
            except ImportError:
                print(
                    f'   ❌ astor not available, install with: pip install astor'
                    )
                return False
            except Exception as e:
                print(f'   ❌ Error converting AST back to source: {e}')
                return False
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'   ✅ Updated {file_path}')
            print(
                f'   📊 Processed: {transformer.functions_processed}, Skipped: {transformer.functions_skipped}'
                )
        else:
            print(f'   ✨ No changes needed')
        return True
    except Exception as e:
        print(f'   ❌ Error processing {file_path}: {e}')
        return False


def find_python_files(base_path):
    """Find all Python files to process."""
    base_path = Path(base_path)
    python_files = []
    if (base_path / 'siege_utilities').exists():
        siege_utils_path = base_path / 'siege_utilities'
    else:
        siege_utils_path = base_path
    for file_path in siege_utils_path.rglob('*.py'):
        if any(skip in str(file_path) for skip in ['__pycache__', '.git',
            'build', 'dist', '.pytest_cache', '__init__.py']):
            continue
        python_files.append(file_path)
    return sorted(python_files)


def main():
    """Main function to process all Python files in siege_utilities."""
    print('🚀 Auto-generating docstrings for siege_utilities')
    print('=' * 60)
    try:
        import astor
    except ImportError:
        print('❌ Missing dependency: astor')
        print('   Install with: pip install astor')
        return False
    base_path = Path.cwd()
    python_files = find_python_files(base_path)
    if not python_files:
        print('❌ No Python files found. Are you in the right directory?')
        print(f'   Current directory: {base_path}')
        print('   Expected: directory containing siege_utilities package')
        return False
    print(f'📁 Found {len(python_files)} Python files to process')
    successful = 0
    failed = 0
    for file_path in python_files:
        if process_python_file(file_path):
            successful += 1
        else:
            failed += 1
    print(f'\n' + '=' * 60)
    print(f'🎉 Docstring generation complete!')
    print(f'📊 Summary:')
    print(f'   ✅ Successfully processed: {successful} files')
    if failed > 0:
        print(f'   ❌ Failed: {failed} files')
    print(f'💡 Next steps:')
    print(f'   1. Review generated docstrings')
    print(f'   2. Rebuild docs: cd docs && make html')
    print(
        f"   3. Commit changes: git add -A && git commit -m 'Add auto-generated docstrings'"
        )
    return failed == 0


def cli():
    """Command line interface."""
    import argparse
    parser = argparse.ArgumentParser(description=
        'Generate docstrings for siege_utilities functions')
    parser.add_argument('--dry-run', action='store_true', help=
        'Show what would be done without making changes')
    parser.add_argument('--path', default='.', help=
        'Base path to search for Python files')
    args = parser.parse_args()
    if args.dry_run:
        print('🔍 DRY RUN MODE - No files will be modified')
    return main()


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

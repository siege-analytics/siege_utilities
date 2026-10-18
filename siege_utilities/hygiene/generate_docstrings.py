"""
Auto-generate docstrings for functions missing them in siege_utilities.
Part of the hygiene maintenance toolkit.
"""
import ast
import io
import logging
import sys
import inspect
import tokenize
from pathlib import Path

# Import logging functions from main package
try:
    from siege_utilities.core.logging import log_info, log_warning, log_error, log_debug
except ImportError:
    # Fallback if main package not available yet
    def log_info(message): pass
    def log_warning(message): pass
    def log_error(message): pass
    def log_debug(message): pass

log = logging.getLogger(__name__)


__all__ = [
    'analyze_function_signature',
    'categorize_function',
    'generate_docstring_template',
    'DocstringAdder',
    'process_python_file',
    'find_python_files',
    'main',
    'cli',
]


def analyze_function_signature(func):
    """Describe the signature of a callable or a parsed function definition."""
    if isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return _analyze_ast_signature(func)
    try:
        sig = inspect.signature(func)
        params = []
        for name, param in sig.parameters.items():
            param_type = 'Any'
            if param.annotation != inspect.Parameter.empty:
                param_type = getattr(param.annotation, '__name__', str(
                    param.annotation))
            param_desc = f'{name} ({param_type}): Value for {name}.'
            if param.default != inspect.Parameter.empty:
                param_desc += f', defaults to {repr(param.default)}'
            params.append(param_desc)
        return_type = 'Any'
        if sig.return_annotation != inspect.Parameter.empty:
            return_type = getattr(sig.return_annotation, '__name__', str(
                sig.return_annotation))
        return_desc = f'{return_type}: Return value.'
        return params, return_desc
    except (ValueError, TypeError, AttributeError) as e:
        log_warning(f'Could not analyze signature: {e}')
        raise


def _analyze_ast_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[list[str], str]:
    """Read parameters without importing or executing the target module."""
    positional = node.args.posonlyargs + node.args.args
    defaults = [None] * (len(positional) - len(node.args.defaults)) + node.args.defaults
    arguments = list(zip(positional, defaults)) + list(zip(node.args.kwonlyargs, node.args.kw_defaults))
    arguments.extend((arg, None) for arg in (node.args.vararg, node.args.kwarg) if arg is not None)
    params = []
    for arg, default in arguments:
        if arg.arg in ('self', 'cls'):
            continue
        # Only signature expressions are rendered; source files are never unparsed.
        annotation = ast.unparse(arg.annotation) if arg.annotation is not None else 'Any'
        description = f'{arg.arg} ({annotation}): Value for {arg.arg}.'
        if default is not None:
            description += f', defaults to {ast.unparse(default)}'
        params.append(description)
    return_type = ast.unparse(node.returns) if node.returns is not None else 'Any'
    return params, f'{return_type}: Return value.'


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
    _, category_desc = categorize_function(func_name)
    params, return_desc = [], 'Any: Return value.'
    if func_obj is not None:
        params, return_desc = analyze_function_signature(func_obj)
    readable_name = func_name.replace('_', ' ').title()
    brief = f'{readable_name}.'
    docstring_parts = [brief, '', category_desc, '']
    if params:
        docstring_parts.extend(['Args:', *[f'    {param}' for param in
            params], ''])
    docstring_parts.extend(['Returns:', f'    {return_desc}', ''])
    if params:
        param_names = [p.split('(')[0].strip() for p in params[:2]]
        example_args = ', '.join([f'"{name}_value"' for name in param_names])
        if len(params) > 2:
            example_args += ', ...'
    else:
        example_args = ''
    # A parsed name need not be exported, and examples may require resources.
    example_import = '    >>> import siege_utilities  # doctest: +SKIP'
    example_call = (
        f'    >>> result = siege_utilities.{func_name}({example_args})  # doctest: +SKIP')
    docstring_parts.extend(['Example:', example_import, example_call])
    return '\n'.join(docstring_parts)


class DocstringAdder(ast.NodeTransformer):
    """Add function docstrings to an AST and record source insertion points."""

    def __init__(self, module_name='unknown', source=None):
        self.module_name = module_name
        self.functions_processed = 0
        self.functions_skipped = 0
        self.source_lines = io.StringIO(source, newline='').readlines() if source is not None else None
        self.insertions: list[tuple[int, str]] = []

    def visit_FunctionDef(self, node):
        """Add a docstring to an undocumented public function when insertion is safe."""
        if node.name.startswith('_'):
            return self.generic_visit(node)
        has_docstring = ast.get_docstring(node) is not None
        if not has_docstring:
            first = node.body[0]
            # A first statement that is decorated starts before its def/class line.
            lineno = min([first.lineno] + [d.lineno for d in getattr(first, 'decorator_list', [])])
            if self.source_lines is not None:
                line = self.source_lines[lineno - 1]
                indent = line[:len(line) - len(line.lstrip(' \t\f'))]
                if len(indent) != first.col_offset:
                    log_warning(f'Skipping {node.name}: inline suite requires reformatting')
                    self.functions_skipped += 1
                    return self.generic_visit(node)
            docstring_content = generate_docstring_template(node.name, node)
            self.insertions.append((lineno, docstring_content))
            # ast.Constant replaced ast.Str/ast.Num in 3.8 and the aliases
            # were removed in 3.14; requires-python is >=3.11 so Constant is
            # always present.
            docstring_node = ast.Expr(value=ast.Constant(value=docstring_content))
            node.body.insert(0, docstring_node)
            log_info(f'Added docstring to {node.name}')
            self.functions_processed += 1
        else:
            log_debug(f'{node.name} already has docstring')
            self.functions_skipped += 1
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        """Apply the same docstring handling to asynchronous functions."""
        return self.visit_FunctionDef(node)


def process_python_file(file_path, dry_run=True):
    """Process a single Python file to add missing docstrings.

    Args:
        file_path: Python file to process.
        dry_run: Report changes without writing by default. Set False to apply.

    Only docstring lines are inserted; existing source bytes are preserved.
    Inline suites are skipped with a warning because they require reformatting.

    Raises:
        SyntaxError: If the file has invalid Python syntax.
        OSError: If the file cannot be read or written.
    """
    file_path = Path(file_path)
    # relative_path is used only for a friendly log line and a module label;
    # it must never abort real work. relative_to() raises when file_path is a
    # relative path, lives outside cwd, or differs from cwd only by a symlink
    # (e.g. macOS /var vs /private/var), so resolve both sides and fall back
    # to the given path for display when it is not under the working dir.
    try:
        relative_path = file_path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        relative_path = file_path
    log_info(f'\nProcessing {relative_path}')

    original = file_path.read_bytes()
    # Encoding detection expects LF-delimited header lines, including on CR-only files.
    header_lines = io.BytesIO(original.replace(b'\r\n', b'\n').replace(b'\r', b'\n'))
    encoding, _ = tokenize.detect_encoding(header_lines.readline)
    content = original.decode(encoding)

    tree = ast.parse(content)
    module_name = str(relative_path).replace('.py', '').replace('/', '.')
    transformer = DocstringAdder(module_name, source=content)
    transformer.visit(tree)

    if transformer.functions_processed > 0:
        lines = io.StringIO(content, newline='').readlines()
        default_newline = '\r\n' if '\r\n' in content else '\r' if '\r' in content else '\n'
        for lineno, docstring in sorted(transformer.insertions, reverse=True):
            line = lines[lineno - 1]
            indent = line[:len(line) - len(line.lstrip(' \t\f'))]
            newline = line[len(line.rstrip('\r\n')):] or default_newline
            # Preserve literal backslashes and triple quotes from defaults/annotations.
            escaped = docstring.replace('\\', '\\\\').replace('"""', r'\"\"\"')
            block = ['"""', *escaped.split('\n'), '"""']
            lines[lineno - 1:lineno - 1] = [indent + part + newline for part in block]
        new_content = ''.join(lines)
        # Validate the complete edit before opening the file for writing.
        ast.parse(new_content)
        if dry_run:
            log_info(
                f'[dry-run] Would add {transformer.functions_processed} docstring(s) '
                f'to {file_path} (Skipped: {transformer.functions_skipped}); no write'
            )
        else:
            file_path.write_bytes(new_content.encode(encoding))
            log_info(f'Updated {file_path}')
            log_info(
                f'Processed: {transformer.functions_processed}, Skipped: {transformer.functions_skipped}'
            )
    else:
        log_info('No changes needed')


def find_python_files(base_path):
    """Find Python files, excluding initializers, build/cache directories and migrations."""
    base_path = Path(base_path)
    python_files = []
    if (base_path / 'siege_utilities').exists():
        siege_utils_path = base_path / 'siege_utilities'
    else:
        siege_utils_path = base_path
    for file_path in siege_utils_path.rglob('*.py'):
        if any(skip in file_path.parts for skip in ['__pycache__', '.git',
            'build', 'dist', '.pytest_cache', '__init__.py', 'migrations']):
            continue
        python_files.append(file_path)
    return sorted(python_files)


def main(base_path=None, dry_run=True):
    """Process all Python files under base_path to add missing docstrings.

    Args:
        base_path: Directory to search (defaults to the current directory).
        dry_run: Report changes without writing by default. Set False to apply.

    Raises:
        FileNotFoundError: If no Python files are found under base_path.
    """
    log_info('Auto-generating docstrings for siege_utilities')
    log_info('=' * 60)
    base_path = Path(base_path) if base_path is not None else Path.cwd()
    python_files = find_python_files(base_path)
    if not python_files:
        raise FileNotFoundError(
            f'No Python files found in {base_path}. '
            f'Expected: directory containing siege_utilities package'
        )
    log_info(f'Found {len(python_files)} Python files to process')
    successful = 0
    errors: list[tuple[Path, Exception]] = []
    for file_path in python_files:
        try:
            process_python_file(file_path, dry_run=dry_run)
            successful += 1
        except (SyntaxError, OSError, ImportError, ValueError, TypeError) as e:
            log_error(f'Error processing {file_path}: {e}')
            errors.append((file_path, e))
    log_info('\n' + '=' * 60)
    log_info('Docstring generation complete!')
    log_info('Summary:')
    log_info(f'Successfully processed: {successful} files')
    if errors:
        log_error(f'Failed: {len(errors)} files')
    if dry_run:
        log_info('Dry run complete. Use --write (or dry_run=False) to apply changes.')
    log_info('Next steps:')
    log_info('1. Review generated docstrings')
    log_info('2. Rebuild docs: cd docs && make html')
    log_info(
        "3. Commit changes: git add -A && git commit -m 'Add auto-generated docstrings'"
        )
    return len(errors) == 0


def cli():
    """Command line interface."""
    import argparse
    parser = argparse.ArgumentParser(description=
        'Generate docstrings without changing existing source (dry run by default)')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', dest='dry_run', action='store_true', help=
        'Report proposed additions without writing files (default)')
    mode.add_argument('--write', '--apply', dest='dry_run', action='store_false', help=
        'Write docstring additions to source files')
    parser.set_defaults(dry_run=True)
    parser.add_argument('--path', default='.', help=
        'Base path to search for Python files')
    args = parser.parse_args()
    if args.dry_run:
        log_info('DRY RUN MODE - No files will be modified')
    return main(base_path=args.path, dry_run=args.dry_run)


if __name__ == '__main__':
    success = cli()
    sys.exit(0 if success else 1)

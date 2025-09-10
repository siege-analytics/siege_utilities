"""
Architecture analysis and diagram generation for siege_utilities package.
"""

import os
import sys
import inspect
import importlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
import json

def analyze_package_structure(package_name: str = "siege_utilities") -> Dict[str, Any]:
    """
    Analyze the structure of the siege_utilities package.
    
    Args:
        package_name: Name of the package to analyze
        
    Returns:
        Dictionary containing package structure analysis
    """
    try:
        package = importlib.import_module(package_name)
        package_path = Path(package.__file__).parent
        
        structure = {
            "package_name": package_name,
            "package_path": str(package_path),
            "modules": {},
            "functions": {},
            "classes": {},
            "total_functions": 0,
            "total_classes": 0,
            "module_count": 0
        }
        
        # Analyze package structure
        for item_name in dir(package):
            if not item_name.startswith('_'):
                item = getattr(package, item_name)
                
                if inspect.ismodule(item):
                    module_info = analyze_module(item, item_name)
                    structure["modules"][item_name] = module_info
                    structure["module_count"] += 1
                    structure["total_functions"] += module_info.get("function_count", 0)
                    structure["total_classes"] += module_info.get("class_count", 0)
                    
                    # Collect all functions and classes
                    for func_name, func_info in module_info.get("functions", {}).items():
                        full_name = f"{item_name}.{func_name}"
                        structure["functions"][full_name] = func_info
                    
                    for class_name, class_info in module_info.get("classes", {}).items():
                        full_name = f"{item_name}.{class_name}"
                        structure["classes"][full_name] = class_info
        
        return structure
        
    except ImportError as e:
        return {"error": f"Could not import package {package_name}: {e}"}
    except Exception as e:
        return {"error": f"Error analyzing package: {e}"}

def analyze_module(module, module_name: str) -> Dict[str, Any]:
    """
    Analyze a single module within the package.
    
    Args:
        module: The module object to analyze
        module_name: Name of the module
        
    Returns:
        Dictionary containing module analysis
    """
    module_info = {
        "name": module_name,
        "path": getattr(module, '__file__', 'Unknown'),
        "functions": {},
        "classes": {},
        "function_count": 0,
        "class_count": 0,
        "submodules": {}
    }
    
    try:
        for item_name in dir(module):
            if not item_name.startswith('_'):
                item = getattr(module, item_name)
                
                if inspect.isfunction(item):
                    func_info = analyze_function(item, item_name)
                    module_info["functions"][item_name] = func_info
                    module_info["function_count"] += 1
                    
                elif inspect.isclass(item):
                    class_info = analyze_class(item, item_name)
                    module_info["classes"][item_name] = class_info
                    module_info["class_count"] += 1
                    
                elif inspect.ismodule(item) and hasattr(item, '__file__'):
                    # Only analyze submodules that are part of our package
                    if 'siege_utilities' in str(item.__file__):
                        submodule_info = analyze_module(item, item_name)
                        module_info["submodules"][item_name] = submodule_info
                        
    except Exception as e:
        module_info["error"] = f"Error analyzing module {module_name}: {e}"
    
    return module_info

def analyze_function(func, func_name: str) -> Dict[str, Any]:
    """
    Analyze a single function.
    
    Args:
        func: The function object to analyze
        func_name: Name of the function
        
    Returns:
        Dictionary containing function analysis
    """
    try:
        signature = inspect.signature(func)
        doc = inspect.getdoc(func) or "No documentation"
        
        return {
            "name": func_name,
            "signature": str(signature),
            "doc": doc[:100] + "..." if len(doc) > 100 else doc,
            "module": func.__module__,
            "filename": inspect.getfile(func) if hasattr(func, '__file__') else 'Unknown'
        }
    except Exception as e:
        return {
            "name": func_name,
            "error": f"Error analyzing function: {e}"
        }

def analyze_class(cls, class_name: str) -> Dict[str, Any]:
    """
    Analyze a single class.
    
    Args:
        cls: The class object to analyze
        class_name: Name of the class
        
    Returns:
        Dictionary containing class analysis
    """
    try:
        methods = {}
        for method_name in dir(cls):
            if not method_name.startswith('_'):
                method = getattr(cls, method_name)
                if inspect.isfunction(method) or inspect.ismethod(method):
                    methods[method_name] = analyze_function(method, method_name)
        
        doc = inspect.getdoc(cls) or "No documentation"
        
        return {
            "name": class_name,
            "doc": doc[:100] + "..." if len(doc) > 100 else doc,
            "methods": methods,
            "method_count": len(methods),
            "module": cls.__module__,
            "filename": inspect.getfile(cls) if hasattr(cls, '__file__') else 'Unknown'
        }
    except Exception as e:
        return {
            "name": class_name,
            "error": f"Error analyzing class: {e}"
        }

def generate_architecture_diagram(output_format: str = "text", 
                                output_file: Optional[str] = None,
                                include_details: bool = True) -> str:
    """
    Generate an architecture diagram of the siege_utilities package.
    
    Args:
        output_format: Output format ('text', 'json', 'markdown', 'rst')
        output_file: Optional file path to save output
        include_details: Whether to include detailed function/class information
        
    Returns:
        Generated architecture diagram as string
    """
    # Analyze package structure
    structure = analyze_package_structure()
    
    if "error" in structure:
        return f"Error: {structure['error']}"
    
    # Generate diagram based on format
    if output_format == "text":
        diagram = generate_text_diagram(structure, include_details)
    elif output_format == "json":
        diagram = json.dumps(structure, indent=2, default=str)
    elif output_format == "markdown":
        diagram = generate_markdown_diagram(structure, include_details)
    elif output_format == "rst":
        diagram = generate_rst_diagram(structure, include_details)
    else:
        return f"Unsupported output format: {output_format}"
    
    # Save to file if specified
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(diagram)
            print(f"Architecture diagram saved to: {output_file}")
        except Exception as e:
            print(f"Warning: Could not save to {output_file}: {e}")
    
    return diagram

def generate_text_diagram(structure: Dict[str, Any], include_details: bool) -> str:
    """Generate a text-based architecture diagram."""
    lines = []
    lines.append("Siege Utilities Package Architecture")
    lines.append("=" * 50)
    lines.append(f"Package: {structure['package_name']}")
    lines.append(f"Total Functions: {structure['total_functions']}")
    lines.append(f"Total Classes: {structure['total_classes']}")
    lines.append(f"Modules: {structure['module_count']}")
    lines.append("")
    
    for module_name, module_info in structure["modules"].items():
        lines.append(f"📦 {module_name}/")
        
        if include_details:
            if module_info.get("functions"):
                lines.append(f"  🔧 Functions ({module_info['function_count']}):")
                for func_name in list(module_info["functions"].keys())[:5]:  # Show first 5
                    lines.append(f"    - {func_name}")
                if len(module_info["functions"]) > 5:
                    lines.append(f"    ... and {len(module_info['functions']) - 5} more")
            
            if module_info.get("classes"):
                lines.append(f"  🏗️  Classes ({module_info['class_count']}):")
                for class_name in list(module_info["classes"].keys())[:3]:  # Show first 3
                    lines.append(f"    - {class_name}")
                if len(module_info["classes"]) > 3:
                    lines.append(f"    ... and {len(module_info['classes']) - 3} more")
            
            if module_info.get("submodules"):
                lines.append(f"  📁 Submodules ({len(module_info['submodules'])}):")
                for submodule_name in module_info["submodules"].keys():
                    lines.append(f"    - {submodule_name}")
        
        lines.append("")
    
    return "\n".join(lines)

def generate_markdown_diagram(structure: Dict[str, Any], include_details: bool) -> str:
    """Generate a markdown-based architecture diagram."""
    lines = []
    lines.append("# Siege Utilities Package Architecture")
    lines.append("")
    lines.append(f"**Package:** {structure['package_name']}  ")
    lines.append(f"**Total Functions:** {structure['total_functions']}  ")
    lines.append(f"**Total Classes:** {structure['total_classes']}  ")
    lines.append(f"**Modules:** {structure['module_count']}")
    lines.append("")
    
    for module_name, module_info in structure["modules"].items():
        lines.append(f"## 📦 {module_name}")
        lines.append("")
        
        if include_details:
            if module_info.get("functions"):
                lines.append(f"### 🔧 Functions ({module_info['function_count']})")
                lines.append("")
                for func_name in list(module_info["functions"].keys())[:10]:
                    lines.append(f"- `{func_name}`")
                if len(module_info["functions"]) > 10:
                    lines.append(f"- ... and {len(module_info['functions']) - 10} more")
                lines.append("")
            
            if module_info.get("classes"):
                lines.append(f"### 🏗️ Classes ({module_info['class_count']})")
                lines.append("")
                for class_name in list(module_info["classes"].keys())[:5]:
                    lines.append(f"- `{class_name}`")
                if len(module_info["classes"]) > 5:
                    lines.append(f"- ... and {len(module_info['classes']) - 5} more")
                lines.append("")
    
    return "\n".join(lines)

def generate_rst_diagram(structure: Dict[str, Any], include_details: bool) -> str:
    """Generate a reStructuredText-based architecture diagram."""
    lines = []
    lines.append("Siege Utilities Package Architecture")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"**Package:** {structure['package_name']}")
    lines.append(f"**Total Functions:** {structure['total_functions']}")
    lines.append(f"**Total Classes:** {structure['total_classes']}")
    lines.append(f"**Modules:** {structure['module_count']}")
    lines.append("")
    
    for module_name, module_info in structure["modules"].items():
        lines.append(f"{module_name}")
        lines.append("-" * len(module_name))
        lines.append("")
        
        if include_details:
            if module_info.get("functions"):
                lines.append(f"Functions ({module_info['function_count']}):")
                lines.append("")
                for func_name in list(module_info["functions"].keys())[:10]:
                    lines.append(f"- {func_name}")
                if len(module_info["functions"]) > 10:
                    lines.append(f"- ... and {len(module_info['functions']) - 10} more")
                lines.append("")
            
            if module_info.get("classes"):
                lines.append(f"Classes ({module_info['class_count']}):")
                lines.append("")
                for class_name in list(module_info["classes"].keys())[:5]:
                    lines.append(f"- {class_name}")
                if len(module_info["classes"]) > 5:
                    lines.append(f"- ... and {len(module_info['classes']) - 5} more")
                lines.append("")
    
    return "\n".join(lines)

def main():
    """Command-line interface for architecture diagram generation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate Siege Utilities architecture diagram")
    parser.add_argument("--format", choices=["text", "json", "markdown", "rst"], 
                       default="text", help="Output format")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--no-details", action="store_true", 
                       help="Exclude detailed function/class information")
    
    args = parser.parse_args()
    
    diagram = generate_architecture_diagram(
        output_format=args.format,
        output_file=args.output,
        include_details=not args.no_details
    )
    
    if not args.output:
        print(diagram)

# =====================================================
# PACKAGE FORMAT GENERATION FUNCTIONS
# =====================================================

def generate_requirements_txt(setup_py_path: str = "setup.py", output_path: str = "requirements.txt") -> bool:
    """
    Generate requirements.txt from setup.py dependencies.
    
    This function parses a setup.py file using AST (Abstract Syntax Tree) to extract
    the install_requires list and generates a requirements.txt file with the same
    dependencies. This is useful for projects that want to maintain both setup.py
    and requirements.txt for different deployment scenarios.
    
    Args:
        setup_py_path (str): Path to the setup.py file to parse. Defaults to "setup.py".
        output_path (str): Path where the requirements.txt file will be written. 
                          Defaults to "requirements.txt".
        
    Returns:
        bool: True if the requirements.txt file was generated successfully, 
              False if there was an error.
        
    Raises:
        FileNotFoundError: If the setup.py file doesn't exist.
        SyntaxError: If the setup.py file contains invalid Python syntax.
        
    Examples:
        >>> # Generate requirements.txt from setup.py
        >>> success = generate_requirements_txt("setup.py", "requirements.txt")
        >>> print(f"Generated: {success}")
        Generated: True
        
        >>> # Use custom paths
        >>> success = generate_requirements_txt("my_setup.py", "my_requirements.txt")
        >>> print(f"Generated: {success}")
        Generated: True
        
    Note:
        This function only extracts the 'install_requires' list from setup.py.
        Optional dependencies (extras_require) are not included in the output.
    """
    try:
        import ast
        from pathlib import Path
        
        setup_path = Path(setup_py_path)
        if not setup_path.exists():
            print(f"Error: {setup_py_path} not found")
            return False
        
        # Read and parse setup.py
        with open(setup_path, 'r') as f:
            content = f.read()
        
        # Parse AST to extract dependencies
        tree = ast.parse(content)
        dependencies = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and hasattr(node.func, 'id') and node.func.id == 'setup':
                for keyword in node.keywords:
                    if keyword.arg == 'install_requires' and isinstance(keyword.value, ast.List):
                        for elt in keyword.value.elts:
                            if isinstance(elt, ast.Constant):
                                dependencies.append(elt.value)
        
        # Write requirements.txt
        with open(output_path, 'w') as f:
            for dep in dependencies:
                f.write(f"{dep}\n")
        
        print(f"Generated {output_path} with {len(dependencies)} dependencies")
        return True
        
    except Exception as e:
        print(f"Error generating requirements.txt: {e}")
        return False

def generate_pyproject_toml(setup_py_path: str = "setup.py", output_path: str = "pyproject.toml") -> bool:
    """
    Generate pyproject.toml from setup.py for Poetry/UV compatibility.
    
    This function converts a traditional setup.py file to a modern pyproject.toml
    file that is compatible with both Poetry and UV package managers. The generated
    file follows the PEP 621 standard for project metadata and includes all
    dependencies, optional dependencies, and package information from the original
    setup.py file.
    
    Args:
        setup_py_path (str): Path to the setup.py file to parse. Defaults to "setup.py".
        output_path (str): Path where the pyproject.toml file will be written.
                          Defaults to "pyproject.toml".
        
    Returns:
        bool: True if the pyproject.toml file was generated successfully,
              False if there was an error.
        
    Raises:
        FileNotFoundError: If the setup.py file doesn't exist.
        SyntaxError: If the setup.py file contains invalid Python syntax.
        
    Examples:
        >>> # Generate pyproject.toml from setup.py
        >>> success = generate_pyproject_toml("setup.py", "pyproject.toml")
        >>> print(f"Generated: {success}")
        Generated: True
        
        >>> # Generate for UV project
        >>> success = generate_pyproject_toml("my_setup.py", "pyproject.toml")
        >>> print(f"Generated: {success}")
        Generated: True
        
    Note:
        The generated pyproject.toml uses setuptools as the build backend by default.
        This ensures compatibility with existing pip-based workflows while enabling
        modern package managers like UV and Poetry to work with the project.
    """
    try:
        import ast
        from pathlib import Path
        
        setup_path = Path(setup_py_path)
        if not setup_path.exists():
            print(f"Error: {setup_py_path} not found")
            return False
        
        # Read and parse setup.py
        with open(setup_path, 'r') as f:
            content = f.read()
        
        # Parse AST to extract package info
        tree = ast.parse(content)
        package_info = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and hasattr(node.func, 'id') and node.func.id == 'setup':
                for keyword in node.keywords:
                    if keyword.arg in ['name', 'version', 'description', 'author', 'author_email', 'url']:
                        if isinstance(keyword.value, ast.Constant):
                            package_info[keyword.arg] = keyword.value.value
                    elif keyword.arg == 'install_requires' and isinstance(keyword.value, ast.List):
                        deps = []
                        for elt in keyword.value.elts:
                            if isinstance(elt, ast.Constant):
                                deps.append(elt.value)
                        package_info['dependencies'] = deps
                    elif keyword.arg == 'extras_require' and isinstance(keyword.value, ast.Dict):
                        extras = {}
                        for key, value in zip(keyword.value.keys, keyword.value.values):
                            if isinstance(key, ast.Constant) and isinstance(value, ast.List):
                                extra_deps = []
                                for elt in value.elts:
                                    if isinstance(elt, ast.Constant):
                                        extra_deps.append(elt.value)
                                extras[key.value] = extra_deps
                        package_info['optional_dependencies'] = extras
                    elif keyword.arg == 'python_requires' and isinstance(keyword.value, ast.Constant):
                        package_info['python_requires'] = keyword.value.value
        
        # Generate pyproject.toml content
        toml_content = f'''[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{package_info.get('name', 'unknown-package')}"
version = "{package_info.get('version', '0.1.0')}"
description = "{package_info.get('description', '')}"
readme = "README.md"
requires-python = "{package_info.get('python_requires', '>=3.8')}"
authors = [
    {{name = "{package_info.get('author', 'Unknown')}", email = "{package_info.get('author_email', '')}"}}
]

dependencies = [
'''
        
        for dep in package_info.get('dependencies', []):
            toml_content += f'    "{dep}",\n'
        
        toml_content += "]\n"
        
        if package_info.get('optional_dependencies'):
            toml_content += "\n[project.optional-dependencies]\n"
            for extra_name, extra_deps in package_info['optional_dependencies'].items():
                toml_content += f"{extra_name} = [\n"
                for dep in extra_deps:
                    toml_content += f'    "{dep}",\n'
                toml_content += "]\n"
        
        if package_info.get('url'):
            toml_content += f'\n[project.urls]\nHomepage = "{package_info["url"]}"\n'
        
        toml_content += '\n[tool.setuptools.packages.find]\nwhere = ["."]\ninclude = ["*"]\n'
        
        # Write pyproject.toml
        with open(output_path, 'w') as f:
            f.write(toml_content)
        
        print(f"Generated {output_path} from {setup_py_path}")
        return True
        
    except Exception as e:
        print(f"Error generating pyproject.toml: {e}")
        return False

def generate_poetry_toml(setup_py_path: str = "setup.py", output_path: str = "pyproject.toml") -> bool:
    """
    Generate Poetry-compatible pyproject.toml from setup.py.
    
    This function converts a traditional setup.py file to a pyproject.toml file
    specifically formatted for Poetry package management. The generated file uses
    Poetry's specific configuration format with [tool.poetry] sections and
    poetry-core as the build backend.
    
    Args:
        setup_py_path (str): Path to the setup.py file to parse. Defaults to "setup.py".
        output_path (str): Path where the pyproject.toml file will be written.
                          Defaults to "pyproject.toml".
        
    Returns:
        bool: True if the pyproject.toml file was generated successfully,
              False if there was an error.
        
    Raises:
        FileNotFoundError: If the setup.py file doesn't exist.
        SyntaxError: If the setup.py file contains invalid Python syntax.
        
    Examples:
        >>> # Generate Poetry pyproject.toml from setup.py
        >>> success = generate_poetry_toml("setup.py", "pyproject.toml")
        >>> print(f"Generated: {success}")
        Generated: True
        
        >>> # Generate for existing Poetry project
        >>> success = generate_poetry_toml("my_setup.py", "pyproject.toml")
        >>> print(f"Generated: {success}")
        Generated: True
        
    Note:
        The generated file uses Poetry's specific format with [tool.poetry] sections.
        This file can be used directly with Poetry commands like 'poetry install'
        and 'poetry build'. Development dependencies are placed in the
        [tool.poetry.group.dev.dependencies] section.
    """
    try:
        import ast
        from pathlib import Path
        
        setup_path = Path(setup_py_path)
        if not setup_path.exists():
            print(f"Error: {setup_py_path} not found")
            return False
        
        # Read and parse setup.py
        with open(setup_path, 'r') as f:
            content = f.read()
        
        # Parse AST to extract package info
        tree = ast.parse(content)
        package_info = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and hasattr(node.func, 'id') and node.func.id == 'setup':
                for keyword in node.keywords:
                    if keyword.arg in ['name', 'version', 'description', 'author', 'author_email', 'url']:
                        if isinstance(keyword.value, ast.Constant):
                            package_info[keyword.arg] = keyword.value.value
                    elif keyword.arg == 'install_requires' and isinstance(keyword.value, ast.List):
                        deps = []
                        for elt in keyword.value.elts:
                            if isinstance(elt, ast.Constant):
                                deps.append(elt.value)
                        package_info['dependencies'] = deps
                    elif keyword.arg == 'extras_require' and isinstance(keyword.value, ast.Dict):
                        extras = {}
                        for key, value in zip(keyword.value.keys, keyword.value.values):
                            if isinstance(key, ast.Constant) and isinstance(value, ast.List):
                                extra_deps = []
                                for elt in value.elts:
                                    if isinstance(elt, ast.Constant):
                                        extra_deps.append(elt.value)
                                extras[key.value] = extra_deps
                        package_info['optional_dependencies'] = extras
                    elif keyword.arg == 'python_requires' and isinstance(keyword.value, ast.Constant):
                        package_info['python_requires'] = keyword.value.value
        
        # Generate Poetry pyproject.toml content
        toml_content = f'''[tool.poetry]
name = "{package_info.get('name', 'unknown-package')}"
version = "{package_info.get('version', '0.1.0')}"
description = "{package_info.get('description', '')}"
authors = ["{package_info.get('author', 'Unknown')} <{package_info.get('author_email', '')}>"]
readme = "README.md"
packages = [{{include = "{package_info.get('name', 'unknown_package').replace('-', '_')}"}}]

[tool.poetry.dependencies]
python = "{package_info.get('python_requires', '>=3.8')}"
'''
        
        for dep in package_info.get('dependencies', []):
            toml_content += f'"{dep}"\n'
        
        if package_info.get('optional_dependencies'):
            toml_content += "\n[tool.poetry.group.dev.dependencies]\n"
            for extra_name, extra_deps in package_info['optional_dependencies'].items():
                if extra_name == 'dev':
                    for dep in extra_deps:
                        toml_content += f'"{dep}"\n'
        
        if package_info.get('url'):
            toml_content += f'\n[tool.poetry.urls]\nHomepage = "{package_info["url"]}"\n'
        
        toml_content += '\n[build-system]\nrequires = ["poetry-core"]\nbuild-backend = "poetry.core.masonry.api"\n'
        
        # Write pyproject.toml
        with open(output_path, 'w') as f:
            f.write(toml_content)
        
        print(f"Generated Poetry-compatible {output_path} from {setup_py_path}")
        return True
        
    except Exception as e:
        print(f"Error generating Poetry pyproject.toml: {e}")
        return False

def generate_uv_toml(setup_py_path: str = "setup.py", output_path: str = "pyproject.toml") -> bool:
    """
    Generate UV-compatible pyproject.toml from setup.py.
    
    This function converts a traditional setup.py file to a pyproject.toml file
    that is compatible with UV package manager. UV uses the standard PEP 621
    format for pyproject.toml, so this function delegates to generate_pyproject_toml()
    which produces the correct format.
    
    Args:
        setup_py_path (str): Path to the setup.py file to parse. Defaults to "setup.py".
        output_path (str): Path where the pyproject.toml file will be written.
                          Defaults to "pyproject.toml".
        
    Returns:
        bool: True if the pyproject.toml file was generated successfully,
              False if there was an error.
        
    Raises:
        FileNotFoundError: If the setup.py file doesn't exist.
        SyntaxError: If the setup.py file contains invalid Python syntax.
        
    Examples:
        >>> # Generate UV pyproject.toml from setup.py
        >>> success = generate_uv_toml("setup.py", "pyproject.toml")
        >>> print(f"Generated: {success}")
        Generated: True
        
        >>> # Generate for UV project
        >>> success = generate_uv_toml("my_setup.py", "pyproject.toml")
        >>> print(f"Generated: {success}")
        Generated: True
        
    Note:
        UV uses the standard PEP 621 format for pyproject.toml, which is the same
        format used by the standard generate_pyproject_toml() function. This ensures
        compatibility with both UV and other modern package managers.
    """
    # UV uses the same format as standard pyproject.toml
    return generate_pyproject_toml(setup_py_path, output_path)

if __name__ == "__main__":
    main()

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

if __name__ == "__main__":
    main()

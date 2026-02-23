# Development Module

The `development` module provides tools for package management, architecture analysis, and development workflow automation.

## 📦 Package Format Generation

Convert traditional `setup.py` files to modern package management formats.

### Functions

#### `generate_requirements_txt(setup_py_path, output_path)`

Generate a `requirements.txt` file from `setup.py` dependencies.

```python
from siege_utilities.development.architecture import generate_requirements_txt

# Generate requirements.txt from setup.py
success = generate_requirements_txt("setup.py", "requirements.txt")
print(f"Generated: {success}")
```

**Parameters:**
- `setup_py_path` (str): Path to setup.py file (default: "setup.py")
- `output_path` (str): Path for output requirements.txt (default: "requirements.txt")

**Returns:** `bool` - True if successful, False otherwise

#### `generate_pyproject_toml(setup_py_path, output_path)`

Generate a UV/Setuptools compatible `pyproject.toml` file.

```python
from siege_utilities.development.architecture import generate_pyproject_toml

# Generate pyproject.toml for UV
success = generate_pyproject_toml("setup.py", "pyproject.toml")
print(f"Generated: {success}")
```

**Parameters:**
- `setup_py_path` (str): Path to setup.py file (default: "setup.py")
- `output_path` (str): Path for output pyproject.toml (default: "pyproject.toml")

**Returns:** `bool` - True if successful, False otherwise

#### `generate_poetry_toml(setup_py_path, output_path)`

Generate a Poetry-compatible `pyproject.toml` file.

```python
from siege_utilities.development.architecture import generate_poetry_toml

# Generate Poetry configuration
success = generate_poetry_toml("setup.py", "pyproject_poetry.toml")
print(f"Generated: {success}")
```

**Parameters:**
- `setup_py_path` (str): Path to setup.py file (default: "setup.py")
- `output_path` (str): Path for output pyproject.toml (default: "pyproject.toml")

**Returns:** `bool` - True if successful, False otherwise

#### `generate_uv_toml(setup_py_path, output_path)`

Generate a UV-compatible `pyproject.toml` file (same as standard format).

```python
from siege_utilities.development.architecture import generate_uv_toml

# Generate UV configuration
success = generate_uv_toml("setup.py", "pyproject.toml")
print(f"Generated: {success}")
```

**Parameters:**
- `setup_py_path` (str): Path to setup.py file (default: "setup.py")
- `output_path` (str): Path for output pyproject.toml (default: "pyproject.toml")

**Returns:** `bool` - True if successful, False otherwise

## 🏗️ Architecture Analysis

Analyze package structure and generate documentation.

### Functions

#### `analyze_package_structure(package_name)`

Analyze the structure of a Python package.

```python
from siege_utilities.development.architecture import analyze_package_structure

# Analyze siege_utilities package
analysis = analyze_package_structure("siege_utilities")
print(f"Total modules: {len(analysis['modules'])}")
print(f"Total functions: {analysis['total_functions']}")
```

**Parameters:**
- `package_name` (str): Name of the package to analyze (default: "siege_utilities")

**Returns:** `Dict[str, Any]` - Package analysis results

#### `generate_package_diagram(package_name, output_path)`

Generate a Mermaid diagram of package structure.

```python
from siege_utilities.development.architecture import generate_package_diagram

# Generate package diagram
success = generate_package_diagram("siege_utilities", "package_diagram.md")
print(f"Generated diagram: {success}")
```

**Parameters:**
- `package_name` (str): Name of the package to analyze
- `output_path` (str): Path for output diagram file

**Returns:** `bool` - True if successful, False otherwise

#### `get_function_signatures(module_name)`

Get function signatures from a module.

```python
from siege_utilities.development.architecture import get_function_signatures

# Get signatures from logging module
signatures = get_function_signatures("siege_utilities.core.logging")
for func_name, signature in signatures.items():
    print(f"{func_name}{signature}")
```

**Parameters:**
- `module_name` (str): Name of the module to analyze

**Returns:** `Dict[str, str]` - Function name to signature mapping

## 🔧 Development Utilities

### Functions

#### `create_development_environment(project_path)`

Create a development environment with proper structure.

```python
from siege_utilities.development.architecture import create_development_environment

# Create dev environment
success = create_development_environment("./my_project")
print(f"Created environment: {success}")
```

**Parameters:**
- `project_path` (str): Path where to create the environment

**Returns:** `bool` - True if successful, False otherwise

#### `validate_package_structure(package_path)`

Validate that a package follows proper Python packaging standards.

```python
from siege_utilities.development.architecture import validate_package_structure

# Validate package structure
is_valid, issues = validate_package_structure("./siege_utilities")
if is_valid:
    print("✅ Package structure is valid")
else:
    print(f"❌ Issues found: {issues}")
```

**Parameters:**
- `package_path` (str): Path to the package to validate

**Returns:** `Tuple[bool, List[str]]` - (is_valid, list_of_issues)

## 📋 Usage Examples

### Complete Package Modernization

```python
from siege_utilities.development.architecture import (
    generate_requirements_txt,
    generate_pyproject_toml,
    generate_poetry_toml,
    generate_uv_toml
)

# Modernize a package
def modernize_package(setup_py_path="setup.py"):
    """Convert a traditional setup.py to modern package formats."""
    
    print("🔄 Modernizing package...")
    
    # Generate requirements.txt
    req_success = generate_requirements_txt(setup_py_path, "requirements.txt")
    print(f"📄 Requirements.txt: {'✅' if req_success else '❌'}")
    
    # Generate UV/Setuptools pyproject.toml
    uv_success = generate_pyproject_toml(setup_py_path, "pyproject.toml")
    print(f"🚀 UV pyproject.toml: {'✅' if uv_success else '❌'}")
    
    # Generate Poetry pyproject.toml
    poetry_success = generate_poetry_toml(setup_py_path, "pyproject_poetry.toml")
    print(f"📦 Poetry pyproject.toml: {'✅' if poetry_success else '❌'}")
    
    return all([req_success, uv_success, poetry_success])

# Use the function
success = modernize_package()
print(f"🎉 Package modernization: {'Complete' if success else 'Failed'}")
```

### Package Analysis Workflow

```python
from siege_utilities.development.architecture import (
    analyze_package_structure,
    generate_package_diagram,
    get_function_signatures
)

def analyze_my_package(package_name="siege_utilities"):
    """Comprehensive package analysis."""
    
    print(f"🔍 Analyzing {package_name}...")
    
    # Analyze structure
    analysis = analyze_package_structure(package_name)
    print(f"📊 Found {analysis['total_functions']} functions in {len(analysis['modules'])} modules")
    
    # Generate diagram
    diagram_success = generate_package_diagram(package_name, f"{package_name}_diagram.md")
    print(f"📈 Package diagram: {'✅' if diagram_success else '❌'}")
    
    # Show function signatures for core modules
    for module in analysis['modules'][:3]:  # First 3 modules
        signatures = get_function_signatures(module)
        print(f"\n🔧 {module} functions:")
        for func_name, signature in list(signatures.items())[:5]:  # First 5 functions
            print(f"  - {func_name}{signature}")
    
    return analysis

# Run analysis
analysis = analyze_my_package()
```

## 🧪 Testing

The development module includes comprehensive tests:

```bash
# Run development module tests
pytest tests/test_package_format_generation.py -v

# Run with coverage
pytest tests/test_package_format_generation.py --cov=siege_utilities.development
```

## 📚 Dependencies

The development module requires:
- `ast` (built-in) - For parsing Python code
- `pathlib` (built-in) - For path operations
- `typing` (built-in) - For type hints

## 🤝 Contributing

When adding new development utilities:

1. **Follow the existing patterns** for function documentation
2. **Add comprehensive tests** in `tests/test_package_format_generation.py`
3. **Update this README** with new function documentation
4. **Ensure error handling** with clear error messages
5. **Test with real packages** to ensure compatibility

## 📖 Related Documentation

- [UV Package Management Guide](../../wiki/UV-Package-Management.md)
- [Getting Started Guide](../../wiki/Getting-Started.md)
- [Main README](../../README.md)
- [Architecture Documentation](../../wiki/Architecture/)

---

**Happy developing! 🚀**

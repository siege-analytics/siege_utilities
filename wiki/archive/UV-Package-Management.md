# UV Package Management with Siege Utilities

## 🚀 Introduction

UV is a fast, modern Python package manager that provides superior dependency resolution, faster installs, and better project management compared to traditional pip-based workflows. Siege Utilities now includes comprehensive support for UV and modern Python packaging standards.

## 📦 What is UV?

UV is a Python package installer and resolver, written in Rust, that provides:
- **10-100x faster** package installation than pip
- **Better dependency resolution** with conflict detection
- **Modern project management** with pyproject.toml support
- **Virtual environment management** built-in
- **Lock file support** for reproducible builds

## 🛠️ Installation

### Install UV

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip (if you prefer)
pip install uv
```

### Verify Installation

```bash
uv --version
```

## 🏗️ Setting Up a Siege Utilities Project

### 1. Create a New UV Project

```bash
# Create a new project directory
uv init my-siege-project
cd my-siege-project

# This creates:
# - pyproject.toml (project configuration)
# - README.md
# - .python-version (Python version specification)
```

### 2. Add Siege Utilities

```bash
# Add siege_utilities as an editable dependency
uv add --editable ../siege_utilities

# Or if siege_utilities is in a different location
uv add --editable /path/to/siege_utilities
```

### 3. Install with Specific Extras

```bash
# Install with geospatial support
uv add --extra geo ../siege_utilities

# Install with distributed computing support
uv add --extra distributed ../siege_utilities

# Install with analytics support
uv add --extra analytics ../siege_utilities

# Install with reporting support
uv add --extra reporting ../siege_utilities

# Install with streamlit support
uv add --extra streamlit ../siege_utilities

# Install everything
uv add --extra all ../siege_utilities
```

## 📋 Available Extras

Siege Utilities provides organized dependency groups:

| Extra | Description | Key Dependencies |
|-------|-------------|------------------|
| `geo` | Geospatial functionality | geopandas, shapely, folium, geopy |
| `distributed` | Big data processing | pyspark |
| `analytics` | Data science | scipy, scikit-learn, sqlalchemy |
| `reporting` | Visualization | matplotlib, seaborn, plotly |
| `streamlit` | Interactive apps | streamlit, altair, bokeh |
| `export` | Data export | openpyxl, xlsxwriter |
| `performance` | Performance tools | duckdb, psutil |
| `dev` | Development tools | pytest, black, flake8 |
| `all` | Everything included | All above dependencies |

## 🔧 Package Format Generation

Siege Utilities includes powerful functions for generating modern package configuration files:

### Generate Requirements.txt

```python
from siege_utilities.development.architecture import generate_requirements_txt

# Generate requirements.txt from setup.py
success = generate_requirements_txt("setup.py", "requirements.txt")
print(f"Generated requirements.txt: {success}")
```

### Generate pyproject.toml (UV/Setuptools)

```python
from siege_utilities.development.architecture import generate_pyproject_toml

# Generate UV-compatible pyproject.toml
success = generate_pyproject_toml("setup.py", "pyproject.toml")
print(f"Generated pyproject.toml: {success}")
```

### Generate Poetry Configuration

```python
from siege_utilities.development.architecture import generate_poetry_toml

# Generate Poetry-compatible pyproject.toml
success = generate_poetry_toml("setup.py", "pyproject_poetry.toml")
print(f"Generated Poetry config: {success}")
```

### Generate UV Configuration

```python
from siege_utilities.development.architecture import generate_uv_toml

# Generate UV-compatible pyproject.toml (same as standard)
success = generate_uv_toml("setup.py", "pyproject.toml")
print(f"Generated UV config: {success}")
```

## 🚀 Running Your Code

### Using UV Run

```bash
# Run Python scripts with UV
uv run python my_script.py

# Run with specific Python version
uv run --python 3.11 python my_script.py

# Run Jupyter notebooks
uv run jupyter notebook

# Run Streamlit apps
uv run streamlit run my_app.py
```

### Using UV Shell

```bash
# Activate UV environment
uv shell

# Now you can use python directly
python my_script.py
```

## 📊 Project Management

### View Dependencies

```bash
# Show dependency tree
uv tree

# Show only top-level dependencies
uv tree --depth 1

# Show specific package info
uv show siege-utilities
```

### Add Additional Dependencies

```bash
# Add a new package
uv add pandas

# Add with specific version
uv add "pandas>=2.0.0"

# Add development dependency
uv add --dev pytest

# Add from requirements file
uv add --requirements requirements.txt
```

### Update Dependencies

```bash
# Update all dependencies
uv sync --upgrade

# Update specific package
uv add --upgrade siege-utilities

# Update to latest version
uv add --upgrade-package siege-utilities
```

## 🔒 Lock Files and Reproducibility

UV automatically generates lock files for reproducible builds:

```bash
# Generate lock file
uv lock

# Install from lock file
uv sync --frozen

# Update lock file
uv lock --upgrade
```

## 🧪 Testing with UV

### Run Tests

```bash
# Run tests with UV
uv run pytest tests/

# Run with coverage
uv run pytest --cov=siege_utilities tests/

# Run specific test file
uv run pytest tests/test_core_logging.py -v
```

### Install Test Dependencies

```bash
# Install with dev extras (includes pytest, etc.)
uv add --extra dev ../siege_utilities

# Or add specific test packages
uv add pytest pytest-cov pytest-mock
```

## 🐛 Troubleshooting

### Common Issues

1. **Virtual Environment Conflicts**
   ```bash
   # Clear UV cache
   uv cache clean
   
   # Remove existing environment
   rm -rf .venv
   
   # Recreate environment
   uv sync
   ```

2. **Dependency Resolution Issues**
   ```bash
   # Show dependency conflicts
   uv tree --incompatible
   
   # Force reinstall
   uv sync --reinstall
   ```

3. **Python Version Issues**
   ```bash
   # Check available Python versions
   uv python list
   
   # Install specific Python version
   uv python install 3.11
   
   # Use specific Python version
   uv run --python 3.11 python my_script.py
   ```

### Debug Information

```bash
# Show detailed dependency resolution
uv tree --show-version

# Show environment info
uv run python -c "import sys; print(sys.executable)"

# Show package locations
uv run python -c "import siege_utilities; print(siege_utilities.__file__)"
```

## 📚 Best Practices

### 1. Use Lock Files
Always commit `uv.lock` to version control for reproducible builds.

### 2. Pin Dependencies
Use specific version constraints in your `pyproject.toml`:
```toml
dependencies = [
    "siege-utilities>=1.0.0",
    "pandas>=2.0.0,<3.0.0",
]
```

### 3. Separate Development Dependencies
Use `[project.optional-dependencies]` for dev tools:
```toml
[project.optional-dependencies]
dev = ["pytest", "black", "flake8"]
```

### 4. Use UV for CI/CD
```yaml
# GitHub Actions example
- name: Install dependencies
  run: uv sync --frozen

- name: Run tests
  run: uv run pytest tests/
```

## 🎯 Migration from Pip

### From requirements.txt

```bash
# Convert existing requirements.txt
uv add --requirements requirements.txt

# Or generate from setup.py
uv add --editable .
```

### From Poetry

```bash
# If you have pyproject.toml with Poetry config
uv add --editable .
```

## 🚀 Advanced Usage

### Custom Python Versions

```bash
# Install specific Python version
uv python install 3.11.5

# Use in project
uv run --python 3.11.5 python my_script.py
```

### Workspace Management

```bash
# Create workspace with multiple projects
uv init --workspace my-workspace
cd my-workspace
uv init project1
uv init project2

# Add siege_utilities to workspace
uv add --workspace ../siege_utilities
```

### Environment Variables

```bash
# Set environment variables for UV runs
UV_INDEX_URL=https://pypi.org/simple uv add package

# Or use .env files
echo "UV_INDEX_URL=https://pypi.org/simple" > .env
uv run python my_script.py
```

## 📖 Additional Resources

- [UV Documentation](https://docs.astral.sh/uv/)
- [UV GitHub Repository](https://github.com/astral-sh/uv)
- [Python Packaging User Guide](https://packaging.python.org/)
- [Siege Utilities Documentation](../README.md)

## 🤝 Contributing

If you encounter issues with UV integration or have suggestions for improvement, please:

1. Check the [troubleshooting section](#-troubleshooting)
2. Search existing [GitHub issues](https://github.com/siege-analytics/siege_utilities/issues)
3. Create a new issue with detailed information
4. Submit a pull request with your improvements

---

**Happy coding with UV and Siege Utilities! 🚀**

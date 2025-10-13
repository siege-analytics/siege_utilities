# Hygiene Module

The `hygiene` module provides comprehensive tools for maintaining the `siege_utilities` package, including documentation generation, code quality management, and PyPI release automation.

## 📋 Table of Contents

- [Documentation Generation](#documentation-generation)
- [PyPI Release Management](#pypi-release-management)
- [Usage Examples](#usage-examples)
- [Testing](#testing)
- [Contributing](#contributing)

## 📚 Documentation Generation

### `generate_docstrings`

Automatically generates docstrings for functions that lack them.

```python
from siege_utilities.hygiene import generate_docstrings

# Generate docstrings for all modules
generate_docstrings()
```

## 🚀 PyPI Release Management

The PyPI release management system provides comprehensive functions for publishing packages to PyPI with proper version management, validation, and automation.

### Core Functions

#### Version Management

##### `get_current_version(setup_py_path="setup.py") -> str`

Extract the current version from setup.py.

```python
from siege_utilities.hygiene import get_current_version

version = get_current_version()
print(f"Current version: {version}")
# Output: Current version: 1.0.0
```

**Parameters:**
- `setup_py_path` (str): Path to setup.py file (default: "setup.py")

**Returns:**
- `str`: Current version string

**Raises:**
- `FileNotFoundError`: If setup.py doesn't exist
- `ValueError`: If version cannot be extracted

##### `increment_version(version, increment_type="patch") -> str`

Increment version number by major, minor, or patch.

```python
from siege_utilities.hygiene import increment_version

# Patch increment (1.2.3 -> 1.2.4)
new_version = increment_version("1.2.3", "patch")

# Minor increment (1.2.3 -> 1.3.0)
new_version = increment_version("1.2.3", "minor")

# Major increment (1.2.3 -> 2.0.0)
new_version = increment_version("1.2.3", "major")
```

**Parameters:**
- `version` (str): Current version string (e.g., "1.2.3")
- `increment_type` (str): Type of increment ("major", "minor", "patch")

**Returns:**
- `str`: New version string

**Raises:**
- `ValueError`: If version format is invalid or increment_type is unknown

##### `update_version_in_setup_py(setup_py_path, new_version) -> bool`

Update version in setup.py file.

```python
from siege_utilities.hygiene import update_version_in_setup_py

success = update_version_in_setup_py("setup.py", "1.1.0")
if success:
    print("Version updated successfully")
```

**Parameters:**
- `setup_py_path` (str): Path to setup.py file
- `new_version` (str): New version string

**Returns:**
- `bool`: True if successful, False otherwise

##### `update_version_in_pyproject_toml(pyproject_toml_path, new_version) -> bool`

Update version in pyproject.toml file.

```python
from siege_utilities.hygiene import update_version_in_pyproject_toml

success = update_version_in_pyproject_toml("pyproject.toml", "1.1.0")
if success:
    print("Version updated successfully")
```

**Parameters:**
- `pyproject_toml_path` (str): Path to pyproject.toml file
- `new_version` (str): New version string

**Returns:**
- `bool`: True if successful, False otherwise

#### Build Management

##### `clean_build_artifacts() -> bool`

Clean build artifacts and temporary files.

```python
from siege_utilities.hygiene import clean_build_artifacts

success = clean_build_artifacts()
if success:
    print("Build artifacts cleaned")
```

**Returns:**
- `bool`: True if successful, False otherwise

**Cleans:**
- `build/` directory
- `dist/` directory
- `*.egg-info/` directories
- `__pycache__/` directories
- `*.pyc` files

##### `build_package() -> Tuple[bool, str]`

Build the package for distribution.

```python
from siege_utilities.hygiene import build_package

success, message = build_package()
if success:
    print(f"Package built: {message}")
else:
    print(f"Build failed: {message}")
```

**Returns:**
- `Tuple[bool, str]`: (success, output_message)

**Creates:**
- Source distribution (`.tar.gz`)
- Wheel distribution (`.whl`)

##### `validate_package() -> Tuple[bool, List[str]]`

Validate the built package.

```python
from siege_utilities.hygiene import validate_package

is_valid, issues = validate_package()
if is_valid:
    print("Package is valid")
else:
    print("Validation issues:")
    for issue in issues:
        print(f"  - {issue}")
```

**Returns:**
- `Tuple[bool, List[str]]`: (is_valid, list_of_issues)

**Validates:**
- Source distribution exists
- Wheel distribution exists
- Wheel format using twine

#### PyPI Upload

##### `upload_to_pypi(repository="pypi", username=None, password=None, token=None) -> Tuple[bool, str]`

Upload package to PyPI.

```python
from siege_utilities.hygiene import upload_to_pypi

# Using API token (recommended)
success, message = upload_to_pypi(token="pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")

# Using username/password
success, message = upload_to_pypi(username="username", password="password")

# Upload to TestPyPI
success, message = upload_to_pypi(repository="testpypi", token="test-token")
```

**Parameters:**
- `repository` (str): Repository to upload to ("pypi" or "testpypi")
- `username` (str, optional): PyPI username (if not using token)
- `password` (str, optional): PyPI password (if not using token)
- `token` (str, optional): PyPI API token (preferred)

**Returns:**
- `Tuple[bool, str]`: (success, output_message)

#### Release Notes

##### `create_release_notes(version, changes) -> str`

Create release notes for the version.

```python
from siege_utilities.hygiene import create_release_notes

changes = [
    "Fixed critical bug in data processing",
    "Added new geospatial functions",
    "Updated documentation"
]

notes = create_release_notes("1.1.0", changes)
print(notes)
```

**Parameters:**
- `version` (str): Version string
- `changes` (List[str]): List of changes/features

**Returns:**
- `str`: Formatted release notes

#### Complete Workflow

##### `full_release_workflow(increment_type="patch", changes=None, repository="pypi", token=None, dry_run=False) -> Tuple[bool, str]`

Execute complete release workflow.

```python
from siege_utilities.hygiene import full_release_workflow

# Dry run (recommended first)
success, message = full_release_workflow(
    increment_type="patch",
    changes=["Fixed bug", "Added feature"],
    dry_run=True
)

# Actual release
if success:
    success, message = full_release_workflow(
        increment_type="patch",
        changes=["Fixed bug", "Added feature"],
        token="pypi-token"
    )
```

**Parameters:**
- `increment_type` (str): Type of version increment ("major", "minor", "patch")
- `changes` (List[str], optional): List of changes for release notes
- `repository` (str): Repository to upload to ("pypi" or "testpypi")
- `token` (str, optional): PyPI API token
- `dry_run` (bool): If True, don't actually upload

**Returns:**
- `Tuple[bool, str]`: (success, output_message)

**Workflow Steps:**
1. Get current version
2. Calculate new version
3. Update version in setup.py and pyproject.toml
4. Clean build artifacts
5. Build package
6. Validate package
7. Upload to PyPI (if not dry run)
8. Create release notes

##### `check_release_readiness() -> Tuple[bool, List[str]]`

Check if package is ready for release.

```python
from siege_utilities.hygiene import check_release_readiness

is_ready, issues = check_release_readiness()
if is_ready:
    print("✅ Package is ready for release!")
else:
    print("❌ Package readiness issues:")
    for issue in issues:
        print(f"  - {issue}")
```

**Returns:**
- `Tuple[bool, List[str]]`: (is_ready, list_of_issues)

**Checks:**
- setup.py exists
- pyproject.toml exists
- README.md exists
- tests directory exists
- Version format is valid
- Package can be imported

## 💡 Usage Examples

### Basic Release Process

```python
from siege_utilities.hygiene import (
    check_release_readiness,
    full_release_workflow
)

# 1. Check if ready for release
is_ready, issues = check_release_readiness()
if not is_ready:
    print("Fix issues before releasing:")
    for issue in issues:
        print(f"  - {issue}")
    exit(1)

# 2. Dry run first
success, message = full_release_workflow(
    increment_type="patch",
    changes=["Fixed critical bug", "Added new feature"],
    dry_run=True
)

if success:
    print("Dry run successful!")
    
    # 3. Actual release
    success, message = full_release_workflow(
        increment_type="patch",
        changes=["Fixed critical bug", "Added new feature"],
        token="pypi-your-token-here"
    )
    
    if success:
        print("Release successful!")
    else:
        print(f"Release failed: {message}")
```

### Manual Step-by-Step Release

```python
from siege_utilities.hygiene import (
    get_current_version,
    increment_version,
    update_version_in_setup_py,
    update_version_in_pyproject_toml,
    clean_build_artifacts,
    build_package,
    validate_package,
    upload_to_pypi
)

# 1. Get current version
current_version = get_current_version()
print(f"Current version: {current_version}")

# 2. Calculate new version
new_version = increment_version(current_version, "minor")
print(f"New version: {new_version}")

# 3. Update version files
update_version_in_setup_py("setup.py", new_version)
update_version_in_pyproject_toml("pyproject.toml", new_version)

# 4. Clean and build
clean_build_artifacts()
success, message = build_package()
if not success:
    print(f"Build failed: {message}")
    exit(1)

# 5. Validate
is_valid, issues = validate_package()
if not is_valid:
    print("Validation failed:")
    for issue in issues:
        print(f"  - {issue}")
    exit(1)

# 6. Upload
success, message = upload_to_pypi(token="your-token")
if success:
    print("Upload successful!")
else:
    print(f"Upload failed: {message}")
```

### Version Management Only

```python
from siege_utilities.hygiene import (
    get_current_version,
    increment_version,
    update_version_in_setup_py,
    update_version_in_pyproject_toml
)

# Get current version
version = get_current_version()
print(f"Current: {version}")

# Increment patch version
new_version = increment_version(version, "patch")
print(f"New: {new_version}")

# Update both files
update_version_in_setup_py("setup.py", new_version)
update_version_in_pyproject_toml("pyproject.toml", new_version)
```

## 🧪 Testing

Run the tests for the hygiene module:

```bash
# Run all hygiene tests
python -m pytest tests/test_pypi_release.py -v

# Run specific test class
python -m pytest tests/test_pypi_release.py::TestVersionManagement -v

# Run with coverage
python -m pytest tests/test_pypi_release.py --cov=siege_utilities.hygiene
```

## 🔧 Dependencies

The PyPI release functions require:

- `setuptools` - For building packages
- `twine` - For uploading packages (install with `pip install twine`)
- `subprocess` - For running build commands
- `pathlib` - For file path operations
- `re` - For version parsing

Install required dependencies:

```bash
pip install twine
```

## 🚨 Important Notes

### Security

- **Never commit PyPI tokens or passwords** to version control
- Use environment variables for sensitive credentials:
  ```bash
  export PYPI_TOKEN="your-token-here"
  ```
- Use TestPyPI for testing before uploading to production PyPI

### Best Practices

1. **Always run dry run first** before actual release
2. **Check release readiness** before starting
3. **Use semantic versioning** (major.minor.patch)
4. **Test the package** after building
5. **Keep release notes** up to date

### Error Handling

All functions return success/failure status and detailed error messages. Always check the return values:

```python
success, message = build_package()
if not success:
    print(f"Error: {message}")
    # Handle error appropriately
```

## 🤝 Contributing

When adding new functions to the hygiene module:

1. **Add comprehensive docstrings** with examples
2. **Write tests** in `tests/test_pypi_release.py`
3. **Update this README** with usage examples
4. **Handle errors gracefully** with meaningful messages
5. **Follow the existing code style**

## 📚 Related Documentation

- [PyPI Upload Guide](https://packaging.python.org/tutorials/packaging-projects/)
- [Semantic Versioning](https://semver.org/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [Setuptools Documentation](https://setuptools.readthedocs.io/)

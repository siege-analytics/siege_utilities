# Developer Guide - Siege Utilities

This guide is for developers who want to contribute to Siege Utilities, extend its functionality, or understand its architecture.

## 🏗️ Architecture Overview

Siege Utilities uses a **hybrid functional + data models** approach:

- **Functional API**: Most functions are available directly from `siege_utilities` namespace
- **Pydantic Models**: Type-safe configuration and data validation
- **Hydra Integration**: Advanced configuration composition and overrides
- **Dynamic Discovery**: Automatic function discovery and availability reporting

## 📁 Project Structure

```
siege_utilities/
├── __init__.py                 # Main package initialization and function discovery
├── core/                       # Core utilities (logging, strings)
│   ├── logging.py             # Advanced logging system
│   └── string_utils.py        # String manipulation utilities
├── config/                     # Configuration management
│   ├── models/                # Pydantic models for validation
│   │   ├── user_profile.py    # User configuration model
│   │   ├── client_profile.py  # Client configuration model
│   │   ├── branding_config.py # Branding configuration model
│   │   └── ...
│   ├── hydra_manager.py       # Hydra configuration manager
│   ├── migration.py           # Legacy configuration migration
│   └── ...
├── geo/                       # Geospatial utilities
│   ├── census_utilities.py    # Census data operations
│   ├── geocoding.py          # Address geocoding
│   └── spatial_data.py       # Spatial data processing
├── distributed/               # Big data processing
│   ├── spark_utils.py        # Spark utilities (500+ functions)
│   ├── hdfs_operations.py    # HDFS operations
│   └── hdfs_config.py        # HDFS configuration
├── analytics/                 # Analytics integrations
│   ├── google_analytics.py   # Google Analytics integration
│   ├── facebook_business.py  # Facebook Business API
│   └── ...
├── reporting/                 # Report generation
│   ├── chart_generator.py    # Chart creation utilities
│   ├── content_page_template.py # Page templates
│   └── ...
├── testing/                   # Testing utilities
│   ├── environment.py        # Test environment setup
│   └── runner.py             # Test runners
└── configs/                   # Hydra configuration files
    ├── default/              # Default configurations
    ├── client/               # Client-specific overrides
    └── experiments/          # Experimental configurations
```

## External Contributor Quickstart (Fork -> Merge)

Follow this flow for external contributions:

### 1. Fork and Clone

```bash
git clone https://github.com/<your-user>/siege_utilities.git
cd siege_utilities
git remote add upstream https://github.com/siege-analytics/siege_utilities.git
```

### 2. Install in a Local Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Validate Notebook Policy and Outputs

```bash
python -m pytest -q --no-cov tests/test_notebooks_output_policy.py
```

If your change affects user-facing behavior or APIs, update relevant notebooks and keep `notebooks/output/` artifacts reviewer-visible.

### 4. File an Issue for Merge and Link Your PR

Open an issue in `siege-analytics/siege_utilities` and include:
- Problem statement and change scope
- Link to your branch/PR from your fork
- Test evidence
- Documentation and notebook updates

## 🔧 Development Setup

### 1. Clone and Install

```bash
git clone https://github.com/siege-analytics/siege_utilities.git
cd siege_utilities
pip install -e ".[dev,geo,distributed]"
```

### 2. Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test category
python -m pytest tests/test_core_logging.py -v

# Run with coverage
python -m pytest tests/ --cov=siege_utilities --cov-report=html

# Run script-level import diagnostics
python scripts/check_imports.py

# Enforce test filename/location hygiene
python scripts/check_test_file_hygiene.py

# Phase 1 lint ratchet on touched Python files
python scripts/check_lint_ratchet_phase1.py

# Phase 2 lint ratchet on touched Python files
python scripts/check_lint_ratchet.py --phase phase2

# Phase 3 lint ratchet for touched high-change domains (config/geo/files)
python scripts/check_lint_ratchet.py --phase phase3

# Phase 4 full-repo ratchet against baseline
python scripts/check_lint_ratchet.py --phase phase4
```

### 3. Verify Installation

```bash
# Check function availability
python -c "import siege_utilities; print(siege_utilities.get_package_info())"

# Run comprehensive check
python scripts/check_imports.py
```

## 🤖 Automated Review

CodeRabbit is part of the required PR workflow.

- Review policy is defined in `.coderabbit.yaml`
- `CodeRabbit` status must pass before merge to `main`
- See `docs/CODERABBIT_WORKFLOW.md` for merge-readiness expectations

## 🎯 Adding New Functions

### 1. Create Function in Appropriate Module

```python
# siege_utilities/core/new_utils.py
def my_new_function(param1: str, param2: int = 42) -> str:
    """
    My new utility function.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
    """
    # Function implementation
    return f"Processed {param1} with {param2}"
```

### 2. Update Module's `__init__.py`

```python
# siege_utilities/core/__init__.py
from .new_utils import my_new_function

__all__ = ['my_new_function']
```

### 3. Update Main Package `__init__.py`

```python
# siege_utilities/__init__.py

# Add to function_categories mapping
function_categories = {
    # ... existing functions ...
    'my_new_function': 'core',
    # ...
}
```

### 4. Add Tests

```python
# tests/test_new_utils.py
import pytest
from siege_utilities.core.new_utils import my_new_function

class TestNewUtils:
    def test_my_new_function_basic(self):
        result = my_new_function("test", 10)
        assert result == "Processed test with 10"
    
    def test_my_new_function_default(self):
        result = my_new_function("test")
        assert result == "Processed test with 42"
```

## 🏗️ Adding New Pydantic Models

### 1. Create Model

```python
# siege_utilities/config/models/new_config.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional

class NewConfig(BaseModel):
    """Configuration for new feature."""
    
    name: str = Field(
        min_length=1, 
        max_length=50,
        description="Name of the configuration"
    )
    
    enabled: bool = Field(
        default=True,
        description="Whether the feature is enabled"
    )
    
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Timeout in seconds"
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate name format."""
        if not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()
```

### 2. Add to Hydra Configuration

```yaml
# siege_utilities/configs/default/new_config.yaml
defaults:
  - _self_

name: ""
enabled: true
timeout: 30
```

### 3. Update HydraConfigManager

```python
# siege_utilities/config/hydra_manager.py
from .models.new_config import NewConfig

class HydraConfigManager:
    def load_new_config(self, client_code: Optional[str] = None) -> NewConfig:
        """Load new configuration with client overrides."""
        config_data = self.load_config("default/new_config", 
                                      overrides=[f"+client={client_code}"] if client_code else [])
        
        return NewConfig(**config_data)
```

### 4. Add Tests

```python
# tests/test_new_config.py
import pytest
from siege_utilities.config.models.new_config import NewConfig

class TestNewConfig:
    def test_new_config_creation(self):
        config = NewConfig(name="test")
        assert config.name == "test"
        assert config.enabled is True
        assert config.timeout == 30
    
    def test_new_config_validation(self):
        with pytest.raises(ValueError):
            NewConfig(name="")  # Empty name should fail
```

## 🔄 Migration System

### Adding Migration Support

```python
# siege_utilities/config/migration.py
class ConfigurationMigrator:
    def migrate_new_config(self, legacy_data: dict) -> NewConfig:
        """Migrate legacy configuration to new format."""
        return NewConfig(
            name=legacy_data.get('old_name', 'default'),
            enabled=legacy_data.get('is_enabled', True),
            timeout=legacy_data.get('wait_time', 30)
        )
```

## 🧪 Testing Guidelines

### 1. Unit Tests

- Test individual functions with various inputs
- Test edge cases and error conditions
- Use mocks for external dependencies
- Aim for 100% function coverage

### 2. Integration Tests

- Test function interactions
- Test configuration loading and validation
- Test migration workflows
- Test error handling and recovery

### 3. Battle Testing

```python
# tests/test_new_feature.py
def test_new_feature_comprehensive():
    """Comprehensive test of new feature."""
    
    # Test basic functionality
    result = my_new_function("test")
    assert result is not None
    
    # Test configuration loading
    with HydraConfigManager() as manager:
        config = manager.load_new_config()
        assert config.name is not None
    
    # Test migration
    migrator = ConfigurationMigrator()
    migrated = migrator.migrate_new_config({"old_name": "test"})
    assert migrated.name == "test"
```

## 📚 Documentation Guidelines

### 1. Function Documentation

```python
def example_function(param1: str, param2: Optional[int] = None) -> Dict[str, Any]:
    """
    Brief description of what the function does.
    
    Args:
        param1: Description of parameter with type and constraints
        param2: Optional parameter with default behavior
        
    Returns:
        Description of return value structure
        
    Raises:
        ValueError: When input validation fails
        ImportError: When required dependencies are missing
        
    Example:
        >>> result = example_function("test", 42)
        >>> print(result['status'])
        'success'
    """
```

### 2. Configuration Documentation

```yaml
# siege_utilities/configs/default/example_config.yaml
defaults:
  - _self_

# Example Configuration
# This configuration controls the example feature behavior

# Feature name (required, 1-50 characters)
name: "example"

# Whether feature is enabled (boolean)
enabled: true

# Timeout in seconds (1-300 seconds)
timeout: 30
```

## 🚀 Performance Guidelines

### 1. Lazy Loading

```python
# Use lazy imports for heavy dependencies
def heavy_function():
    try:
        import pandas as pd
        import numpy as np
        # Heavy computation
    except ImportError:
        raise ImportError("pandas and numpy required for this function")
```

### 2. Caching

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_computation(param: str) -> str:
    """Expensive computation with caching."""
    # Heavy computation here
    return result
```

### 3. Async Support

```python
import asyncio
from typing import AsyncGenerator

async def async_data_processing(items: list) -> AsyncGenerator[dict, None]:
    """Process items asynchronously."""
    for item in items:
        # Async processing
        yield processed_item
```

## 🔍 Debugging and Development

### 1. Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use siege_utilities logging
import siege_utilities as su
su.configure_shared_logging(level="DEBUG")
```

### 2. Function Discovery

```python
# Check what functions are available
info = su.get_package_info()
print(f"Total functions: {info['total_functions']}")

# Check specific category
core_functions = info['categories']['core']
print(f"Core functions: {core_functions}")
```

### 3. Configuration Debugging

```python
# Test configuration loading
with HydraConfigManager() as manager:
    # Load with debugging
    config = manager.load_config("default/user_profile", overrides=[])
    print(f"Loaded config: {config}")
```

## 📋 Code Review Checklist

- Follow repository coding standards in `CODING_STYLE.md` (canonical) and `docs/CODING_STYLE.md`.
- Use `PR_REVIEW_RUBRIC.md` for reviewer severity and merge readiness criteria.
- Use `CHANGE_CLASSIFICATION_AND_RELEASE_POLICY.md` to classify bug/feature/breaking changes and release impact.
- [ ] Function has proper docstring with examples
- [ ] Type hints are complete and accurate
- [ ] Error handling covers edge cases
- [ ] Tests cover normal and error cases
- [ ] Configuration follows Hydra patterns
- [ ] Migration support is included
- [ ] Performance implications considered
- [ ] Documentation is updated
- [ ] Battle tests pass

## 🎯 Best Practices

1. **Fail Gracefully**: Always provide helpful error messages for missing dependencies
2. **Type Safety**: Use Pydantic models for configuration validation
3. **Consistent API**: Follow existing patterns for function signatures
4. **Comprehensive Testing**: Include unit, integration, and battle tests
5. **Documentation**: Document everything with examples
6. **Performance**: Consider caching and lazy loading for expensive operations
7. **Migration**: Always provide migration paths for configuration changes

---

**Ready to contribute?** Check out the [Contributing Guide](CONTRIBUTING.md) for more details!

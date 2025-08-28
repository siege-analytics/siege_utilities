# Siege Utilities Testing Guide

## Overview

Siege Utilities uses a comprehensive testing framework to ensure reliability and functionality across all 260+ functions.

## Test Structure

### Location
- **Proper tests**: `tests/` directory with structured unit and integration tests
- **Validation scripts**: Simple dependency-free validation in root directory

### Test Categories

| Category | Description | Dependencies |
|----------|-------------|-------------|
| **Unit** | Fast, isolated function tests | None |
| **Integration** | Cross-module functionality | Varies |
| **Core** | Logging, strings, files | None |
| **Config** | Configuration management | None |
| **Geo** | Spatial data functions | pandas, geopandas |
| **Analytics** | Data analysis functions | pandas, various APIs |
| **Reporting** | Chart and report generation | matplotlib, requests |

## Running Tests

### Option 1: Test Runner (Recommended)
```bash
python run_tests.py
```

Interactive menu with options:
- Basic tests (core functionality)
- Category-specific tests (geo, analytics, etc.)
- Coverage analysis
- Debug mode

### Option 2: Direct Validation
```bash
python validate_new_functionality.py
```

Dependency-free validation of key improvements:
- Dynamic function registry
- Graceful dependency handling
- Core utility functions
- FIPS data structure

### Option 3: Individual Test Files
```bash
python tests/test_core_logging.py
python tests/test_file_operations.py
```

## Test Results Interpretation

### Success Indicators
- ✅ **260+ functions available**: Dynamic registry working
- ✅ **0 unavailable functions**: All functions provide helpful guidance
- ✅ **100% reliability**: Functions work or give clear installation instructions

### What Tests Validate

#### 1. Function Registry Integrity
```python
# Tests that function counting is accurate
assert info['total_functions'] >= 260
assert 'categories' in info
assert len(info['categories']) >= 10
```

#### 2. Dependency Wrapper System
```python
# Tests that missing dependencies give helpful errors
try:
    su.get_census_data()
except ImportError as e:
    assert "pandas" in str(e)  # Helpful error message
```

#### 3. Core Function Reliability
```python
# Tests that core functions work without dependencies
result = su.remove_wrapping_quotes_and_trim('"test"')
assert result == "test"
```

## Test Coverage Expectations

### High Coverage (>90%)
- Core utilities (logging, strings)
- File operations
- Configuration management
- Function registry system

### Medium Coverage (>70%)
- Dependency wrapper functions
- Error handling systems
- Validation functions

### Lower Coverage (>50%)
- External API integrations
- Optional dependency functions
- Complex data processing workflows

## Adding New Tests

### For New Functions
1. Add tests to appropriate `tests/test_*.py` file
2. Include both success and failure cases
3. Test dependency handling if applicable
4. Update function registry tests if exposing new functions

### Test Template
```python
def test_new_function():
    """Test description."""
    # Test successful case
    result = su.new_function("input")
    assert result == "expected"
    
    # Test error handling
    with pytest.raises(ValueError):
        su.new_function(None)
```

## Continuous Validation

### Pre-Commit Checks
1. Run `python validate_new_functionality.py`
2. Verify all 5 core tests pass
3. Check function count hasn't decreased unexpectedly

### Development Workflow
1. Make changes
2. Run relevant test category: `python run_tests.py`
3. Check test results and coverage
4. Fix any failing tests
5. Update tests if adding new functionality

## Troubleshooting

### Common Issues

**"pytest not found"**
- Install: `sudo apt install python3-pytest` (or pip in venv)
- Use validation script instead: `python validate_new_functionality.py`

**"Missing dependencies"**
- Expected for optional features
- Tests should verify helpful error messages
- Install specific dependencies for full testing

**"Function count decreased"**
- Check if functions were accidentally removed from `__init__.py`
- Verify import statements are correct
- Run function discovery: `su.get_package_info()`

## Quality Metrics

The testing framework maintains:
- **100% import success**: Library loads without crashes
- **260+ function availability**: All functions discoverable
- **0 broken functions**: All functions work or provide helpful guidance
- **Comprehensive coverage**: All major functionality tested

This ensures the siege_utilities library maintains professional quality standards.

# siege_utilities Restoration Plan

**Date:** January 17, 2026
**Branch:** `dheerajchand/sketch/siege-utilities-restoration`
**Initial State:** 265 passing, 27 failing, 2 errors
**After First Pass:** 272 passing, 24 skipped, 2 errors
**After Second Pass:** 314 passing, 2 skipped
**Current State:** 418 passing (all tests running)

---

## Session 2: January 17, 2026 (Afternoon)

### Fixes Applied

1. **`get_download_directory()` API Mismatch** - `user_config.py` was calling `enhanced_get_download_directory(client_code, specific_path, config_dir)` but the actual signature is `(username, config_dir)`. This broke all Census downloads. Fixed by rewriting the function to use the local `UserConfigManager` directly.

2. **Missing Geocoding Exports** - Functions like `get_country_name`, `get_country_code`, `list_countries`, `get_coordinates` were defined but not exported from `siege_utilities/__init__.py`. Added proper exports with fallback wrappers.

3. **Hardcoded Census Years** - `census_constants.py` had years hardcoded to 2025. Changed to dynamically calculate using `datetime.now().year`.

4. **Test Year Assertions** - Tests were asserting `year <= 2025` which fails in 2026. Fixed to use `current_year`.

### Commits
- `f10cbe1` - fix: Rewrite config tests to match current API (314 pass, 2 skip)
- `9395d4a` - fix: Fix broken API calls and make census years dynamic (418 tests pass)

---

## CI/CD Analysis

### Why GitHub Actions Will Fail

#### 1. **run_overnight_comprehensive.sh has hardcoded macOS paths** (CRITICAL)
**File:** `run_overnight_comprehensive.sh:12-13`
```bash
export PATH="/Users/dheerajchand/Library/Python/3.9/bin:$PATH"
cd /Users/dheerajchand/Desktop/in_process/code/siege_utilities_verify
```
- These paths don't exist on GitHub Actions Ubuntu runners
- Script will fail immediately with "No such file or directory"

#### 2. **Missing Python scripts referenced by battle tests**
Scripts that the overnight test expects but don't exist:
- `test_critical_untested_functions.py` - MISSING
- `test_recipe_code.py` - MISSING

Scripts that exist:
- `overnight_comprehensive_testing.py` ✓
- `overnight_testing_suite.py` ✓
- `generate_comprehensive_morning_report.py` ✓
- `morning_recommendations_generator.py` ✓
- `convert_notebooks_to_scripts.py` ✓

#### 3. **No Sphinx documentation setup**
The CI documentation job expects:
```bash
cd docs && make html
```
But `docs/` contains only markdown files - no `Makefile`, `conf.py`, or Sphinx setup.

#### 4. **Coverage threshold at 85%**
`pytest.ini:18` requires `--cov-fail-under=85`. Current coverage likely lower.

#### 5. **`safety check` deprecated free API**
The security job runs `safety check --json` which now requires a paid subscription.

#### 6. **Python 3.8 compatibility issues**
Some dependencies (osmnx, notebook>=7) may not work on Python 3.8.

---

## Code Review Findings (Thorough Analysis)

### HIGH SEVERITY

#### 1. `download_data()` Never Implemented
**File:** `siege_utilities/geo/spatial_data.py`
- Line 523: `SpatialDataSource.download_data()` raises `NotImplementedError`
- Line 1098: Module-level `download_data()` wrapper calls this unimplemented method
- `CensusDataSource` never overrides it - implements `get_geographic_boundaries()` instead
- **Impact:** Calling `download_data()` always fails with NotImplementedError

#### 2. O(n²) Complexity Bug in `generate_synthetic_population()`
**File:** `siege_utilities/data/sample_data.py:487-515`
```python
for ethnicity, percentage in demographics.items():
    for _ in range(ethnic_count):
        person = _generate_synthetic_person(...)
        population_data.append(person)

        # BUG: These are INSIDE the inner loop!
        if tract_info:
            for person in population_data:  # Re-processes ALL persons each iteration
                person.update({...})
```
- For each person generated, it re-processes ALL previous persons
- 1000 people = 500,000+ unnecessary iterations
- **Impact:** Severe performance degradation at scale

#### 3. Parameter Order Mismatch in `get_optimal_year()`
**File:** `siege_utilities/geo/spatial_data.py`
- Line 483 (class method): `get_optimal_year(requested_year: int, boundary_type: str)`
- Line 1094 (module function): `get_optimal_year(geographic_level: str, preferred_year: Optional[int])`
- **Impact:** Wrong parameter order causes incorrect behavior

### MEDIUM SEVERITY

#### 4. Duplicate `get_download_directory()` Definitions
- `user_config.py:294`: `get_download_directory(specific_path, client_code, config_dir)`
- `enhanced_config.py:444`: `get_download_directory(username, config_dir)`
- **Impact:** Import order determines which version wins

#### 5. Wrong Return Type Annotations
**File:** `siege_utilities/geo/spatial_data.py`
- Line 1197: `get_state_abbreviations() -> List[str]` but returns `Dict[str, str]`
- Line 1193: `get_available_state_fips() -> List[str]` but returns `Dict[str, str]`

#### 6. Missing Exports in `__all__`
Functions defined but not exported:
- `normalize_state_input()` - Line 1123
- `normalize_state_name()` - Line 1150
- `normalize_state_abbreviation()` - Line 1162
- `normalize_fips_code()` - Line 1174
- `get_census_county_sample()` - data module
- `get_metropolitan_sample()` - data module

#### 7. Wildcard Imports in `__init__.py`
Lines 70-73 use `from .distributed.* import *` which causes namespace pollution.

### LOW SEVERITY

#### 8. Hardcoded LA-Centric Sample Data
**File:** `siege_utilities/data/sample_data.py`
- Line 314: Default state_fips='06' (California)
- Line 315: Default county_fips='037' (Los Angeles)
- Lines 708-709: Hardcoded LA coordinates (33.5-34.5, -118.5 to -117.5)
- Lines 461-467: Hardcoded demographics matching LA demographics

---

## Session 1: January 17, 2026 (Morning)

### Tests Rewritten
All 24 skipped tests have been rewritten to match the current API:
- `tests/test_enhanced_config.py` - 42 tests, all passing
- `tests/test_admin_profile_manager.py` - 15 tests, all passing

### API Bugs Fixed
1. **YAML Serialization Bug** - `save_user_profile()` and `save_client_profile()` were serializing Python tuples and enums in non-YAML-safe format. Fixed with `_convert_to_yaml_safe()` helper function.

2. **API Signature Mismatch in profile_manager.py** - `create_default_profiles()` was calling `save_user_profile(profile, user_dir)` but the signature is `save_user_profile(profile, username, config_dir)`.

3. **Deprecated ClientProfile Fields** - `create_default_profiles()` was using old fields (`download_directory`, `data_format`, `brand_colors`) that no longer exist. Updated to use current model with `ContactInfo`, `BrandingConfig`, `ReportPreferences`.

---

## Critical Finding: Code/Test Divergence

The codebase and tests have **significantly diverged**. The tests were written for an earlier, simpler API that no longer exists. Key observations:

### What Changed
1. **ClientProfile model** - Was simple with fields like `download_directory`, `data_format`, `brand_colors`
   - Now requires nested types: `ContactInfo`, `BrandingConfig`, `ReportPreferences`
   - Many fields that were optional are now required
   - "TEST" is now a reserved client code

2. **Config functions** - Function signatures changed
   - `load_user_profile(config_dir)` → `load_user_profile(username, config_dir)`
   - `save_user_profile(profile, config_dir)` → `save_user_profile(profile, username, config_dir)`

3. **Security updates** - Shell commands now use `shell=False` with allowlist validation

### Immediate Action Taken
- 24 tests skipped with clear documentation of why
- Core functionality (file operations, core utils, distributed) still works
- Package is now pip-installable

### What Needs Deciding
The skipped tests expose a fundamental question: **What is the intended API?**

Options:
1. **Keep current model, rewrite tests** - More work but preserves enhanced validation
2. **Simplify model to match tests** - Less work but loses Pydantic validation
3. **Deprecate config module** - If not being used, remove it

Recommendation: Review which features of the config module are actually being used in production, then decide

---

## Executive Summary

The siege_utilities library has accumulated several issues that prevent clean pip installation and cause test failures. This plan addresses critical issues in priority order.

---

## Issue Categories

### Critical (Blocking pip install)
| # | Issue | Impact | Files Affected |
|---|-------|--------|----------------|
| 1 | Duplicate " 2.py" files | Import conflicts, wrong modules loaded | 17 files in config/, reporting/ |
| 2 | API signature mismatch | Tests call non-existent function signatures | enhanced_config.py, admin/ |
| 3 | Missing pydantic constraint | Breaks on pydantic v1 | setup.py |

### High (Causing test failures)
| # | Issue | Impact | Tests Affected |
|---|-------|--------|----------------|
| 4 | Reserved "TEST" client code | Validation error | test_enhanced_config.py |
| 5 | Missing ClientProfile defaults | Pydantic validation fails | test_enhanced_config.py |
| 6 | Shell security transition | Tests expect old shell=True | test_shell.py |
| 7 | Hardcoded path assumptions | Path mismatch | test_admin_profile_manager.py |

### Medium (Code quality)
| # | Issue | Impact |
|---|-------|--------|
| 8 | Unregistered pytest marks | Warnings during test runs |
| 9 | Duplicate config implementations | Maintainability |
| 10 | Unclear module hierarchy | Developer confusion |

---

## Phase 1: Critical Cleanup (Do First)

### 1.1 Delete Duplicate Files

These files are Windows merge conflict artifacts and must be removed:

```bash
# Find and delete all " 2.py" files
find siege_utilities -name "* 2.py" -type f -delete
find siege_utilities -name "* 2.yaml" -type f -delete
```

**Files to delete:**
- siege_utilities/config/enhanced_config 2.py
- siege_utilities/config/models/user_profile 2.py
- siege_utilities/config/models/client_profile 2.py
- siege_utilities/geo/census_constants 2.py
- (and 13 more similar files)

### 1.2 Add Pydantic Version Constraint

**File:** `setup.py` or `pyproject.toml`

```python
install_requires=[
    # ... existing deps
    "pydantic>=2.0",
]
```

### 1.3 Fix Optional Dependency Handling

Already fixed: `sample_data.py` - added `from __future__ import annotations` and `gpd = None` fallback.

---

## Phase 2: Test Fixes

### 2.1 Fix test_shell.py (Security Transition)

The code correctly switched from `shell=True` to `shell=False` for security. Update tests to expect this:

**File:** `tests/test_shell.py`

```python
# OLD (line ~45):
@patch('subprocess.run')
def test_run_subprocess_success(self, mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="success", stderr="")
    # ...
    mock_run.assert_called_once()
    call_args = mock_run.call_args
    assert call_args.kwargs.get('shell') == True  # OLD expectation

# NEW:
    assert call_args.kwargs.get('shell') == False  # Correct security behavior
```

### 2.2 Fix test_enhanced_config.py

#### A. Fix reserved client code

**File:** `tests/test_enhanced_config.py`

```python
# OLD (multiple locations):
client = ClientProfile(client_code="TEST", ...)

# NEW:
client = ClientProfile(client_code="TESTCLIENT", ...)  # Not reserved
```

#### B. Fix function signature mismatches

The tests expect a different API than what's implemented. Options:

**Option A (Recommended):** Update tests to match implementation
```python
# OLD:
profile = load_user_profile(config_dir)

# NEW (match implementation):
profile = load_user_profile(username="default", config_dir=config_dir)
```

**Option B:** Update implementation to match tests (more invasive)

### 2.3 Fix test_admin_profile_manager.py

**File:** `tests/test_admin_profile_manager.py`, line 34

```python
# OLD:
assert location.parent.name == "siege_utilities_verify"

# NEW (flexible):
assert "siege_utilities" in str(location)
```

---

## Phase 3: Model Fixes

### 3.1 Add Defaults to ClientProfile

**File:** `siege_utilities/config/models/client_profile.py`

```python
# Add defaults for optional fields:
class ClientProfile(BaseModel):
    client_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    contact_info: Optional[ContactInfo] = None  # Make optional
    industry: str = "General"  # Default value
    project_count: int = 0  # Default value
    status: str = "active"  # Default value
    branding_config: Optional[BrandingConfig] = None  # Make optional
    report_preferences: Optional[ReportPreferences] = None  # Make optional
```

### 3.2 Update Reserved Codes

**File:** `siege_utilities/config/models/client_profile.py`, line 173

Consider whether "TEST" really needs to be reserved. Options:
1. Remove "TEST" from reserved codes (for testing convenience)
2. Keep it reserved and update all tests to use different codes

---

## Phase 4: Cleanup (Post-fix)

### 4.1 Register pytest marks

**File:** `pytest.ini`

```ini
[pytest]
markers =
    admin: Admin module tests
    config: Configuration tests
    svg_markers: SVG marker tests
    integration: Integration tests
    slow: Slow tests
```

### 4.2 Consolidate Config Implementation

Long-term: Decide between:
- `enhanced_config.py` (migration/legacy)
- `admin/profile_manager.py` (new design)

Recommendation: Keep one, deprecate the other.

---

## Implementation Order

1. [ ] Delete duplicate " 2.py" files
2. [ ] Add pydantic>=2.0 to setup.py
3. [ ] Fix test_shell.py shell=False assertions
4. [ ] Fix test_enhanced_config.py client codes
5. [ ] Fix test_enhanced_config.py function signatures
6. [ ] Fix test_admin_profile_manager.py path assertions
7. [ ] Add defaults to ClientProfile model
8. [ ] Register pytest marks
9. [ ] Run full test suite
10. [ ] Commit and push

---

## Expected Outcome

After completing this plan:
- All 27 failing tests should pass
- 2 errors should be resolved
- Package should be pip-installable
- No duplicate file warnings
- Clean test output with no unregistered mark warnings

---

## Commands

```bash
# Run tests after fixes
cd /home/dheerajchand/git/siege-analytics/siege_utilities
python -m pytest tests/ --tb=short -v

# Check for remaining issues
python -c "import siege_utilities; print(siege_utilities.get_package_info())"

# Verify no duplicate files
find siege_utilities -name "* 2.*" -type f
```

---

## Recommended Action Order

### Phase 1: Fix CI/CD (Blocking GitHub Actions)
1. [ ] Fix `run_overnight_comprehensive.sh` - remove hardcoded paths, use `$PWD`
2. [ ] Create missing scripts (`test_critical_untested_functions.py`, `test_recipe_code.py`) or remove references
3. [ ] Set up Sphinx docs or skip documentation job
4. [ ] Replace `safety check` with `pip-audit` (free alternative)
5. [ ] Consider dropping Python 3.8 from matrix

### Phase 2: Fix High-Severity Code Issues
6. [ ] Fix O(n²) bug in `generate_synthetic_population()` - move nested loops outside inner loop
7. [ ] Implement `CensusDataSource.download_data()` or remove the wrapper function
8. [ ] Fix `get_optimal_year()` parameter order to be consistent

### Phase 3: Clean Up Medium-Severity Issues
9. [ ] Consolidate `get_download_directory()` - keep one implementation
10. [ ] Fix return type annotations in `spatial_data.py`
11. [ ] Add missing functions to `__all__` exports
12. [ ] Remove wildcard imports from `__init__.py`

### Phase 4: Optional Improvements
13. [ ] Make sample data configurable (not hardcoded to LA)
14. [ ] Remove deprecated function wrappers or add deprecation warnings
15. [ ] Add proper Sphinx documentation setup

---

## Test Status Summary

| Metric | Before | After Session 1 | After Session 2 |
|--------|--------|-----------------|-----------------|
| Passing | 265 | 314 | 418 |
| Failing | 27 | 0 | 0 |
| Skipped | 0 | 2 | 0 |
| Errors | 2 | 2 | 0 |

---

*Generated by Claude Code session on 2026-01-17*

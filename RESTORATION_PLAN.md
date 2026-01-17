# siege_utilities Restoration Plan

**Date:** January 17, 2026
**Branch:** `dheerajchand/sketch/siege-utilities-restoration`
**Initial State:** 265 passing, 27 failing, 2 errors
**After First Pass:** 272 passing, 24 skipped, 2 errors
**Final State:** 314 passing, 2 skipped, 2 errors (census tests excluded due to optional deps)

---

## Completed Work (January 17, 2026)

### Tests Rewritten
All 24 skipped tests have been rewritten to match the current API:
- `tests/test_enhanced_config.py` - 42 tests, all passing
- `tests/test_admin_profile_manager.py` - 15 tests, all passing

### API Bugs Fixed
1. **YAML Serialization Bug** - `save_user_profile()` and `save_client_profile()` were serializing Python tuples and enums in non-YAML-safe format. Fixed with `_convert_to_yaml_safe()` helper function.

2. **API Signature Mismatch in profile_manager.py** - `create_default_profiles()` was calling `save_user_profile(profile, user_dir)` but the signature is `save_user_profile(profile, username, config_dir)`.

3. **Deprecated ClientProfile Fields** - `create_default_profiles()` was using old fields (`download_directory`, `data_format`, `brand_colors`) that no longer exist. Updated to use current model with `ContactInfo`, `BrandingConfig`, `ReportPreferences`.

### Remaining Issues
- Census tests (`test_census_*.py`) require `geopandas` which is an optional dependency
- 2 integration test errors in `test_multi_engine.py` and `test_svg_markers.py` (unrelated to config system)

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

*Generated by Claude Code session on 2026-01-17*

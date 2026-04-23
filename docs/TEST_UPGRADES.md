# siege_utilities — Test Upgrade Plan

Roadmap for raising test quality from "exists" to "catches regressions." Per **ELE-2419** (audit sub-issue 4/6). Skill rubric: `coding/python/SKILL.md` testing section, `coding/python-exceptions/SKILL.md` (negative-test discipline), `coding/python-patterns/SKILL.md` (interface-integrity tests).

## Current state — scorecard

Counts are `.py` files in the target source tree vs. test files named `test_<module>*.py`.

| Module | Src files | Test files | Coverage gap |
|---|---:|---:|---|
| `admin/` | 2 | 0 | **Zero tests** |
| `analytics/` | 11 | 0 | **Zero tests** |
| `config/` | 34 | 11 | Low |
| `core/` | 4 | 8 | Reasonable |
| `data/` | 11 | 20 | Reasonable |
| `databricks/` | 8 | 10 | Reasonable |
| `distributed/` | 4 | 2 | Low |
| `files/` | 8 | 0 | **Zero tests** |
| `geo/` | 123 | 15 | **Critical gap** |
| `git/` | 6 | 9 | Reasonable |
| `hygiene/` | 3 | 0 | **Zero tests** |
| `reporting/` | 39 | 2 | **Critical gap** |
| `survey/` | 12 | 10 | Good (recently upgraded #391) |
| `testing/` | 3 | 4 | Reasonable |

**Hotspots to fix first**: `admin/`, `analytics/`, `files/`, `hygiene/`, `reporting/`, `geo/`.

## Library-wide signal

| Pattern | Count | Implication |
|---|---:|---|
| `assert isinstance` (weak assertion) | 273 | Many tests pass regardless of behavior; strengthen to behavior assertions |
| `pytest.importorskip` (good pattern) | 13 | Pattern exists; spread it to the other dep-gated test files |
| fake-module / monkeypatch.setitem sys.modules | 175 | Strong signal; use as templates for the untested-success-path gaps |
| bare `isinstance` without `is True`/`is False` | (subset of 273) | Often hides type-only checks where a value check would be more meaningful |

273 `isinstance`-only assertions is the biggest finding. Each is a test that passes whether or not the function produced the right answer — only type is being checked.

## Five pattern upgrades (apply per module)

### PU1. Replace `isinstance`-only assertions with behavior assertions

```python
# BEFORE — passes if the function returns anything of the right type
def test_performance_rankings_shape():
    out = analyzer.create_performance_rankings(df, dimensions=["region"])
    assert isinstance(out, dict)

# AFTER — passes only when the return value is structurally correct
def test_performance_rankings_shape():
    out = analyzer.create_performance_rankings(df, dimensions=["region"])
    assert list(out.keys()) == ["region"]
    assert len(out["region"]) > 0
    first = out["region"][0]
    assert isinstance(first, tuple) and len(first) == 3
    value, summed, pct = first
    assert isinstance(summed, float)
    assert 0.0 <= pct <= 100.0
```

### PU2. Fake-module success-path tests for dep-gated code

Pattern proven in `tests/test_survey_weights.py::TestApplyRimWeightsWithFakeWeightipy` (#391). Where a test currently looks like `@pytest.mark.skipif(not DEP_AVAILABLE, ...)` and the skipped branch is the only success-path coverage, add a companion test that monkeypatches a fake module into `sys.modules` and asserts the wrapper calls the documented API.

Apply to (at minimum):
- `geo/*` — fake-geopandas, fake-shapely, fake-pyproj variants for code that degrades gracefully
- `analytics/*` — fake-googleapiclient, fake-facebook-business, fake-snowflake variants
- `reporting/*` — fake-reportlab for PDF paths, fake-pptx for PowerPoint paths

### PU3. Negative tests for every `raise` in the codebase

Every public function that raises a domain exception should have a test that exercises the raise path. Today most tests only cover the happy path.

```python
def test_rdh_provider_raises_on_unknown_level():
    provider = RDHProvider(username=TEST_USERNAME, password=TEST_PASSWORD)
    with pytest.raises(ValueError, match='Unknown RDH level'):
        provider.get_boundary('county', identifier='TX')
```

### PU4. Boundary / property-based tests via `hypothesis`

For parsers, CRS transforms, crosstab builders, and anywhere input space is large — use `hypothesis` to generate edge cases (empty, single-element, NaN-heavy, ordering variants, encoding variants).

```python
from hypothesis import given, strategies as st

@given(st.lists(st.floats(min_value=-180, max_value=180), min_size=2, max_size=2))
def test_crs_transform_inverse_is_identity(coords):
    lng, lat = coords
    x, y = project(lng, lat, src="EPSG:4326", dst="EPSG:5070")
    lng2, lat2 = project(x, y, src="EPSG:5070", dst="EPSG:4326")
    assert abs(lng - lng2) < 1e-9
    assert abs(lat - lat2) < 1e-9
```

### PU5. Order-independent test suite (`pytest-randomly`)

Adds random ordering on every test run so order-dependent failures surface immediately. Landing in this PR:

- `pyproject.toml` dev deps: `pytest-randomly>=3.15.0`
- CI: no config needed — picked up automatically

Sites that may be order-dependent (to watch after landing):
- Tests that mutate global state (working directory, env vars) without explicit isolation
- Tests that rely on `os.environ` being clean (use the `_isolate_rdh_env` pattern from #386)

## Infrastructure changes in this PR

1. Add dev dependencies: `pytest-randomly`, `hypothesis`, `nbmake`
2. Ship `tests/conftest.py` already exists — leaves it untouched (its current env-bootstrap is load-bearing)
3. Raise `[tool.coverage.report] fail_under` from 20 to 40 (two-stage: exit criterion is 80% per module, but library-wide we're not there yet)

## Exit criteria for ELE-2419

- [ ] Every module ≥80% branch coverage
- [ ] Zero `assert isinstance(x, T)` as the sole assertion in a test (273 today)
- [ ] Every public raise path has a negative test
- [ ] `pytest-randomly` enabled; suite passes under random order (3 runs minimum)
- [ ] Zero-test modules (`admin/`, `analytics/`, `files/`, `hygiene/`) have at least smoke tests

## Follow-up structure

Per-module PRs under this epic. Suggested order (smallest first to validate the process):

1. `admin/` — 2 src files, zero tests; quick win
2. `hygiene/` — 3 src files, zero tests; quick win
3. `files/` — 8 src files, zero tests
4. `distributed/` — 4 src files, 2 test files; easy expansion
5. `analytics/` — 11 src files, zero tests; major coverage gain
6. `config/` — 34 src files, partial coverage; focus on credential_manager
7. `reporting/` — 39 src files, 2 test files; largest gap
8. `geo/` — 123 src files, 15 test files; largest surface; parallel sub-sprints by subfolder

Each per-module PR:
- Applies PU1 (behavior > isinstance) to all existing tests in that module
- Adds PU2 (fake-module coverage) where the skip-pattern exists
- Adds PU3 (negative tests) for every raise in the module's source
- Adds PU4 (property-based) where appropriate
- Reports coverage delta in PR body

## Attribution

Per `skills/_output-rules.md`: no AI attribution.

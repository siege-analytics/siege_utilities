# siege_utilities — Test Upgrade Plan

**Goal:** raise test quality from "exists" to "catches regressions."

**Scope:** ELE-2419 (audit sub-issue 4/6). Rubrics: `coding/python/SKILL.md` (testing), `coding/python-exceptions/SKILL.md` (negative tests), `coding/python-patterns/SKILL.md` (interface integrity). Snapshot: 2026-04-22.

## Coverage scorecard

| Module | Src files | Test files | Gap |
|---|---:|---:|---|
| `admin/` | 2 | 0 → 1 | **Was zero** — seeded #402 |
| `hygiene/` | 3 | 0 → 1 | **Was zero** — seeded #403 |
| `files/paths` | — | 0 → 1 | **Was zero** — seeded #404 |
| `analytics/` | 11 | 0 | Zero tests |
| `reporting/` | 39 | 2 | Critical gap (partial fixes #397/#399/#400) |
| `geo/` | 123 | 15 | Critical gap (partial fixes #401/#405) |
| `config/` | 34 | 11 | Low coverage — focus on `credential_manager` |
| `distributed/` | 4 | 2 | Low |
| `core/` | 4 | 8 | Reasonable |
| `data/` | 11 | 20 | Reasonable |
| `databricks/` | 8 | 10 | Reasonable |
| `git/` | 6 | 9 | Reasonable |
| `survey/` | 12 | 10 | Good (upgraded #391) |
| `testing/` | 3 | 4 | Reasonable |

## Library-wide signals

| Signal | Count | Meaning |
|---|---:|---|
| `assert isinstance(x, T)` alone | 273 | Weak assertions — upgrade to behavior checks (PU1) |
| `pytest.importorskip` | 13 | Good pattern — spread it to other dep-gated tests |
| `sys.modules` fake-module monkeypatch | 175 | Strong pattern — template for untested success paths (PU2) |

## Five upgrade patterns

| ID | Name | What | Applied to |
|---|---|---|---|
| **PU1** | Behavior over isinstance | Replace type-only assertions with field / value / shape checks | All 273 sites |
| **PU2** | Fake-module success path | When dep-gated skip hides the success path, add a `sys.modules`-faked companion test | `geo/*`, `analytics/*`, `reporting/*` |
| **PU3** | Negative test per raise | Every public raise path gets a `pytest.raises(...)` | Paired with every ELE-2420 rewrite PR |
| **PU4** | Property-based with `hypothesis` | Generate edge cases (empty, NaN, ordering, encoding) | Parsers, CRS transforms, crosstab builders |
| **PU5** | Order-independent suite | `pytest-randomly` surfaces order-dependent failures | Whole suite |

### PU1 example

```python
# Before — passes for any dict return, regardless of content
assert isinstance(out, dict)

# After — fails if the shape regresses
assert list(out.keys()) == ["region"]
value, summed, pct = out["region"][0]
assert isinstance(summed, float)
assert 0.0 <= pct <= 100.0
```

### PU2 example

Pattern proven in `tests/test_survey_weights.py::TestApplyRimWeightsWithFakeWeightipy` (#391) — monkeypatch a fake module into `sys.modules` and assert the wrapper calls the documented API.

### PU3 example

```python
def test_rdh_provider_raises_on_unknown_level():
    provider = RDHProvider(username=TEST_USERNAME, password=TEST_PASSWORD)
    with pytest.raises(ValueError, match="Unknown RDH level"):
        provider.get_boundary("county", identifier="TX")
```

### PU4 example

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

### PU5 notes

`pytest-randomly` added to dev extras in this PR. Watch for order-dependent failures from:
- Tests that mutate global state (working directory, env vars) without explicit isolation
- Tests that assume clean `os.environ` (use `_isolate_rdh_env` pattern from #386)

## Infrastructure changes in this PR

| Change | What |
|---|---|
| Dev deps | `pytest-randomly`, `hypothesis`, `nbmake` |
| `conftest.py` | Unchanged — existing env bootstrap is load-bearing |
| Coverage floor | Raise `[tool.coverage.report] fail_under` 20 → 40 (toward 80% per-module exit criterion) |

## Exit criteria

- [ ] Every module ≥ 80% branch coverage
- [ ] Zero `assert isinstance(x, T)` as sole assertion (273 → 0)
- [ ] Every public raise path has a negative test
- [ ] Suite passes under random order (3 runs)
- [ ] Zero-test modules (`admin/`, `analytics/`, `files/`, `hygiene/`) have at least smoke tests

## Per-module sweep order

Smallest first to validate the process, largest last.

| Order | Module | Status |
|---|---|---|
| 1 | `admin/` | **Seeded #402** (16 tests) |
| 2 | `hygiene/` | **Seeded #403** (22 tests) |
| 3 | `files/` | **Partial #404** (28 tests, `paths` only) |
| 4 | `distributed/` | Pending |
| 5 | `analytics/` | Pending |
| 6 | `config/` | Pending (focus `credential_manager`) |
| 7 | `reporting/` | Pending |
| 8 | `geo/` | Pending (parallel sub-sprints by subfolder) |

Each per-module PR applies PU1 to existing tests, adds PU2 where needed, PU3 for every raise, PU4 where input-space is large. Reports coverage delta in PR body.

See also: [INTENT.md](INTENT.md) · [FAILURE_MODES.md](FAILURE_MODES.md) · [ARCHITECTURE.md](ARCHITECTURE.md)

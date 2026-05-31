# Property Testing Guide for siege_utilities

This guide covers adopting [Hypothesis](https://hypothesis.readthedocs.io/)
for property-based testing in siege_utilities. Property tests complement
example-based tests by generating random inputs and checking that
invariants hold across the input space.

## Setup

Hypothesis is already in `[project.optional-dependencies] dev`. The
pytest integration works automatically — just use the `@given` decorator.

### Profiles in conftest.py

Add to `conftest.py`:

```python
from hypothesis import settings, HealthCheck

settings.register_profile("ci", max_examples=100)
settings.register_profile("dev", max_examples=50)
settings.register_profile("thorough", max_examples=1000)
settings.load_profile("ci")
```

Select a profile with `HYPOTHESIS_PROFILE=thorough pytest`.

## When to Use Property Tests

Use property tests when:

1. **The input domain is large or combinatorial** — GEOIDs, CRS codes,
   coordinate pairs, date ranges, Census variable names.
2. **You can state an invariant** — "normalized output is idempotent,"
   "total population >= 0," "geocoded result is within state bounds."
3. **Example-based tests feel like guessing** — if you're picking
   arbitrary test values and hoping they cover edge cases, a property
   test will find the edges for you.

## Property Patterns

### 1. Round-trip (encode/decode, serialize/deserialize)

```python
from hypothesis import given
import hypothesis.strategies as st

@given(st.text(min_size=1, max_size=100))
def test_normalize_state_roundtrip(name):
    """Normalizing a state identifier twice gives the same result."""
    from siege_utilities.config.census_constants import normalize_state_identifier
    try:
        result = normalize_state_identifier(name)
        assert normalize_state_identifier(result) == result
    except (ValueError, KeyError):
        pass  # invalid input is fine — we're testing idempotency of valid ones
```

### 2. Invariant preservation

```python
@given(
    st.floats(min_value=-90, max_value=90),
    st.floats(min_value=-180, max_value=180),
)
def test_geocoding_coordinates_in_bounds(lat, lon):
    """get_coordinates should never return coordinates outside WGS84 bounds."""
    from siege_utilities.geo.geocoding import get_coordinates
    try:
        result = get_coordinates(f"{lat},{lon}")
        if result and result.get("lat") is not None:
            assert -90 <= result["lat"] <= 90
            assert -180 <= result["lon"] <= 180
    except (ValueError, TypeError, KeyError, AttributeError):
        pass  # invalid input handling is tested elsewhere
```

### 3. No-crash (defensive)

```python
@given(st.text(max_size=200))
def test_path_sanitizer_never_crashes(raw_path):
    """ensure_path_exists should not raise on arbitrary string input."""
    from siege_utilities.files.paths import sanitize_path
    try:
        sanitize_path(raw_path)
    except (ValueError, OSError):
        pass  # expected rejections
    # No bare Exception should escape
```

### 4. Oracle comparison

```python
import math

@given(st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=1))
def test_survey_weight_sum(weights):
    """Normalized survey weights must sum to the original count."""
    from siege_utilities.survey.weights import normalize_weights
    try:
        normalized = normalize_weights(weights)
        assert math.isclose(sum(normalized), len(weights), rel_tol=1e-6)
    except (ValueError, ZeroDivisionError):
        pass  # zero-sum weights are a known rejection
```

## Custom Strategies

Build domain-specific strategies for reuse:

```python
import hypothesis.strategies as st

# Valid 2-digit state FIPS codes
state_fips = st.sampled_from([
    "01", "02", "04", "05", "06", "08", "09", "10", "11", "12",
    "13", "15", "16", "17", "18", "19", "20", "21", "22", "23",
    "24", "25", "26", "27", "28", "29", "30", "31", "32", "33",
    "34", "35", "36", "37", "38", "39", "40", "41", "42", "44",
    "45", "46", "47", "48", "49", "50", "51", "53", "54", "55", "56",
])

# Valid Census geography levels
geography_level = st.sampled_from([
    "state", "county", "tract", "block_group", "block", "place", "zcta",
])

# WGS84 coordinate pairs
wgs84_point = st.tuples(
    st.floats(min_value=-90, max_value=90),
    st.floats(min_value=-180, max_value=180),
)
```

## Health Checks and Slow Tests

For tests that need expensive setup (database, large fixtures):

```python
from hypothesis import given, settings, HealthCheck

@settings(
    suppress_health_check=[HealthCheck.too_slow],
    max_examples=20,
)
@given(state_fips)
def test_boundary_fetch_idempotent(fips):
    ...
```

Mark slow property tests:

```python
import pytest

@pytest.mark.slow
@given(...)
def test_expensive_property(...):
    ...
```

## File Organization

Place property tests alongside their example-based counterparts:

```
tests/
  test_geocoding.py             # example-based tests
  test_geocoding_properties.py  # property tests
  test_census_constants.py
  test_census_constants_properties.py
  strategies.py                 # shared custom strategies
```

## Running

```bash
# Default CI profile (100 examples)
pytest tests/test_geocoding_properties.py

# Thorough run (1000 examples)
HYPOTHESIS_PROFILE=thorough pytest tests/test_geocoding_properties.py

# Only property tests
pytest -k properties

# Reproduce a specific failure (Hypothesis caches the seed)
pytest tests/test_geocoding_properties.py --hypothesis-seed=12345
```

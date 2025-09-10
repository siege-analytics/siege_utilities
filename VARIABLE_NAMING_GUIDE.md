# Variable Naming & Constants Guide

## Philosophy
Clear, consistent naming is crucial for maintainable code. This guide establishes conventions for the siege_utilities library.

## Constants

### 1. Module-Level Constants
```python
# siege_utilities/config/constants.py
# Use SCREAMING_SNAKE_CASE for true constants
DEFAULT_TIMEOUT = 30
MAX_RETRY_ATTEMPTS = 3
SUPPORTED_FILE_FORMATS = ['csv', 'json', 'parquet', 'xlsx']

# Group related constants
CENSUS_CONFIG = {
    'base_url': 'https://www2.census.gov/geo/tiger',
    'timeout': 30,
    'supported_years': range(2000, 2025)
}

NCES_CONFIG = {
    'base_url': 'https://nces.ed.gov/programs/edge/data',
    'locale_types': {
        'city': {'large': 11, 'midsize': 12, 'small': 13},
        'suburban': {'large': 21, 'midsize': 22, 'small': 23},
        'town': {'fringe': 31, 'distant': 32, 'remote': 33},
        'rural': {'fringe': 41, 'distant': 42, 'remote': 43}
    }
}
```

### 2. Environment-Based Configuration
```python
# siege_utilities/config/paths.py
import os
from pathlib import Path

# Follow user's zsh pattern for environment variables
SIEGE_UTILITIES_HOME = Path(os.getenv('SIEGE_UTILITIES', Path.home() / 'siege_utilities'))
SIEGE_CACHE_DIR = Path(os.getenv('SIEGE_CACHE', Path.home() / '.siege_cache'))
SIEGE_OUTPUT_DIR = Path(os.getenv('SIEGE_OUTPUT', Path.home() / 'Downloads'))

# State/geography constants
STATE_FIPS_CODES = {
    'AL': '01', 'AK': '02', 'AZ': '04', 'AR': '05', 'CA': '06',
    'CO': '08', 'CT': '09', 'DE': '10', 'FL': '12', 'GA': '13',
    # ... complete mapping
}
```

## Variable Naming Conventions

### 1. Functions
```python
# Use snake_case, be descriptive
def get_census_boundaries(year, geographic_level, state_fips=None):
    pass

def download_nces_locale_boundaries(year, state=None, output_dir=None):
    pass

def classify_geography_by_nces_locale(geography_gdf, year=2024):
    pass
```

### 2. Variables
```python
# snake_case for variables
state_fips = "06"
geographic_level = "county"
download_url = construct_url(base_url, year, boundary_type)

# Be specific about data types in names
census_gdf = gpd.GeoDataFrame()  # Geographic data
results_df = pd.DataFrame()      # Tabular data
file_path = Path("data.csv")     # File paths
```

### 3. Class Names
```python
# PascalCase for classes
class CensusDataSource:
    pass

class NCESLocaleClassifier:
    pass

class GeographicBoundaryProcessor:
    pass
```

### 4. Parameters - Be Explicit
```python
# ✅ Good - explicit parameter names
def get_geographic_data(
    year: int = 2020,
    geographic_level: str = 'county',
    state_fips: Optional[str] = None,  # Always use state_fips, not state
    output_format: str = 'geopandas'
):
    pass

# ❌ Bad - ambiguous parameters
def get_data(yr, lvl, st=None):
    pass
```

## Common Anti-Patterns to Avoid

### 1. Inconsistent Parameter Names
```python
# ❌ Bad - mixing state/state_fips in same codebase
def function_a(state):
    pass

def function_b(state_fips):
    pass

# ✅ Good - consistent throughout
def function_a(state_fips):
    pass

def function_b(state_fips):
    pass
```

### 2. Magic Numbers/Strings
```python
# ❌ Bad
if boundary_type in ['tract', 'block_group', 'block']:
    # requires state
    
# ✅ Good
from siege_utilities.config.constants import CENSUS_CONFIG

if boundary_type in CENSUS_CONFIG['geographic_levels']['state_required']:
    # requires state
```

### 3. Unclear Abbreviations
```python
# ❌ Bad
def proc_geo_data(gdf, yr, lvl):
    pass

# ✅ Good
def process_geographic_data(geo_dataframe, year, geographic_level):
    pass
```

## File Organization

### Constants Structure
```
siege_utilities/
├── config/
│   ├── __init__.py
│   ├── constants.py          # Global constants
│   ├── census_constants.py   # Census-specific
│   ├── nces_constants.py     # NCES-specific  
│   ├── paths.py             # Path configurations
│   └── logging_config.py    # Logging setup
```

### Import Patterns
```python
# ✅ Explicit imports
from siege_utilities.config.constants import DEFAULT_TIMEOUT, MAX_RETRIES
from siege_utilities.config.census_constants import CENSUS_CONFIG
from siege_utilities.config.paths import SIEGE_OUTPUT_DIR

# ✅ Namespace imports for large configs
from siege_utilities.config import census_constants as census
url = census.BASE_URL

# ❌ Avoid star imports
from siege_utilities.config.constants import *  # Don't do this
```

## Benefits of This Approach

1. **Maintainability**: Easy to update URLs, timeouts, etc. in one place
2. **Consistency**: Enforces uniform naming across the codebase  
3. **Environment Flexibility**: Follows your zsh pattern for environment variables
4. **Documentation**: Constants file serves as configuration documentation
5. **Testing**: Easy to mock/override constants for testing

## Implementation Priority

1. **Phase 1**: Create `siege_utilities/config/constants.py` with core constants
2. **Phase 2**: Refactor existing functions to use centralized constants
3. **Phase 3**: Add domain-specific constant files (census, nces, etc.)
4. **Phase 4**: Update documentation and add linting rules for naming conventions

## Linting Rules

Add to your `.flake8` or `pyproject.toml`:
```toml
[tool.flake8]
# Enforce naming conventions
select = ["N"]  # pep8-naming plugin

[tool.pylint]
# Variable naming patterns
variable-rgx = "^[a-z_][a-z0-9_]*$"
const-rgx = "^[A-Z_][A-Z0-9_]*$"
```

This approach combines the best of your zsh centralization pattern with Python best practices.



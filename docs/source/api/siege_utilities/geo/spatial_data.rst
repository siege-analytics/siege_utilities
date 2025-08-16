Enhanced Census Utilities
==========================

The enhanced Census utilities provide dynamic discovery and intelligent data access to U.S. Census Bureau TIGER/Line shapefiles. Unlike traditional approaches that rely on hardcoded URLs, this system automatically discovers available data and constructs the correct download URLs based on the actual directory structure.

Key Features
-----------

- **Dynamic Discovery**: Automatically discovers available Census years and boundary types
- **Intelligent URL Construction**: Builds correct URLs based on discovered directory structures
- **Comprehensive Boundary Support**: Supports all major Census boundary types
- **State FIPS Validation**: Built-in validation for state FIPS codes
- **Caching**: Intelligent caching with configurable timeouts
- **Fallback Mechanisms**: Graceful fallbacks when requested data isn't available
- **Parameter Validation**: Robust validation with helpful error messages

CensusDirectoryDiscovery
------------------------

The core discovery service that automatically finds available Census data.

.. autoclass:: siege_utilities.geo.spatial_data.CensusDirectoryDiscovery
   :members:
   :undoc-members:
   :show-inheritance:

Methods
~~~~~~~

.. automethod:: get_available_years
.. automethod:: get_year_directory_contents
.. automethod:: discover_boundary_types
.. automethod:: construct_download_url
.. automethod:: validate_download_url
.. automethod:: get_optimal_year

CensusDataSource
----------------

Enhanced data source that provides intelligent access to Census boundaries.

.. autoclass:: siege_utilities.geo.spatial_data.CensusDataSource
   :members:
   :undoc-members:
   :show-inheritance:

Methods
~~~~~~~

.. automethod:: get_geographic_boundaries
.. automethod:: get_available_boundary_types
.. automethod:: refresh_discovery_cache
.. automethod:: get_available_state_fips
.. automethod:: validate_state_fips
.. automethod:: get_state_name

Supported Boundary Types
-----------------------

The system supports a comprehensive range of Census boundary types:

Core Geographic Boundaries
~~~~~~~~~~~~~~~~~~~~~~~~~~

- **state**: State boundaries
- **county**: County boundaries
- **tract**: Census tracts
- **block_group**: Census block groups
- **block**: Census blocks (tabblock20, tabblock10)
- **place**: Census designated places
- **zcta**: ZIP Code Tabulation Areas

Legislative Boundaries
~~~~~~~~~~~~~~~~~~~~~~

- **cd**: Congressional districts
- **cd108-cd119**: Specific Congress sessions
- **sldu**: State Legislative District Upper
- **sldl**: State Legislative District Lower

Special Purpose Boundaries
~~~~~~~~~~~~~~~~~~~~~~~~~~

- **cbsa**: Core Based Statistical Areas
- **csa**: Combined Statistical Areas
- **metdiv**: Metropolitan Divisions
- **micro**: Micropolitan Statistical Areas
- **necta**: New England City and Town Areas
- **nectadiv**: NECTA Divisions
- **cnecta**: Combined NECTAs

Tribal Boundaries
~~~~~~~~~~~~~~~~~

- **aiannh**: American Indian/Alaska Native/Native Hawaiian Areas
- **aitsce**: American Indian Tribal Subdivisions
- **ttract**: Tribal Census Tracts
- **tbg**: Tribal Block Groups

School Districts
~~~~~~~~~~~~~~~~

- **elsd**: Elementary School Districts
- **scsd**: Secondary School Districts
- **unsd**: Unified School Districts

Transportation & Infrastructure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **roads**: Road networks
- **rails**: Railroad networks
- **edges**: Boundary edges
- **linear_water**: Linear water features
- **area_water**: Area water features
- **address_features**: Address features

Special Areas
~~~~~~~~~~~~~

- **anrc**: Alaska Native Regional Corporations
- **concity**: Consolidated Cities
- **submcd**: Subminor Civil Divisions
- **cousub**: County Subdivisions
- **vtd**: Voting Districts
- **uac**: Urban Areas

Usage Examples
--------------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

    from siege_utilities.geo.spatial_data import CensusDataSource
    
    # Initialize the data source
    census = CensusDataSource()
    
    # Get available years
    years = census.discovery.get_available_years()
    print(f"Available years: {years}")
    
    # Get available boundary types for 2020
    boundary_types = census.get_available_boundary_types(2020)
    print(f"Available boundary types: {boundary_types}")

Downloading Boundaries
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Download national county boundaries
    counties = census.get_geographic_boundaries(2020, 'county')
    
    # Download state-specific tract boundaries
    california_tracts = census.get_geographic_boundaries(
        2020, 'tract', state_fips='06'
    )
    
    # Download congressional districts
    congress_118 = census.get_geographic_boundaries(
        2020, 'cd118'
    )

State FIPS Management
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Get all available state FIPS codes
    state_fips = census.get_available_state_fips()
    
    # Validate a FIPS code
    if census.validate_state_fips('06'):
        state_name = census.get_state_name('06')
        print(f"California: {state_name}")
    
    # Find state by name
    for fips, name in state_fips.items():
        if 'California' in name:
            print(f"California FIPS: {fips}")

Advanced Discovery
~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Force refresh of discovery cache
    census.refresh_discovery_cache()
    
    # Get optimal year when requested year isn't available
    optimal_year = census.discovery.get_optimal_year(2018, 'county')
    print(f"Optimal year for 2018: {optimal_year}")
    
    # Validate a download URL before attempting download
    url = census.discovery.construct_download_url(2020, 'county')
    if census.discovery.validate_download_url(url):
        print(f"URL is valid: {url}")

Error Handling
--------------

The system provides comprehensive error handling and validation:

.. code-block:: python

    try:
        # This will fail - tract level requires state FIPS
        tracts = census.get_geographic_boundaries(2020, 'tract')
    except ValueError as e:
        print(f"Validation error: {e}")
        # Output: "State FIPS required for tract-level data"
    
    try:
        # This will fail - invalid state FIPS
        tracts = census.get_geographic_boundaries(2020, 'tract', state_fips='99')
    except ValueError as e:
        print(f"Validation error: {e}")
        # Output: "Invalid state FIPS code: 99. Use get_available_state_fips() to see valid codes."
    
    try:
        # This will fail - invalid geographic level
        data = census.get_geographic_boundaries(2020, 'invalid_type')
    except ValueError as e:
        print(f"Validation error: {e}")
        # Output: "Invalid geographic level: invalid_type. Available for year 2020: ['state', 'county']..."

Configuration
------------

The system automatically uses user configuration for:

- Download directories
- API keys (when applicable)
- Cache timeouts
- Network timeouts

Cache Management
----------------

The discovery system uses intelligent caching to minimize network requests:

- **Default timeout**: 1 hour (3600 seconds)
- **Configurable**: Can be adjusted per instance
- **Automatic refresh**: Available via `refresh_discovery_cache()`
- **Force refresh**: Available via `force_refresh` parameter

Performance Considerations
-------------------------

- **Lazy loading**: Discovery only happens when needed
- **Caching**: Results are cached to avoid repeated requests
- **Batch operations**: Multiple operations can share discovery results
- **Network optimization**: Minimal HTTP requests with intelligent caching

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

1. **Network timeouts**: Increase timeout values for slow connections
2. **Cache issues**: Use `refresh_discovery_cache()` to clear stale data
3. **Invalid parameters**: Check error messages for specific validation failures
4. **Missing data**: Verify year and boundary type availability

Debug Mode
~~~~~~~~~~

Enable debug logging to see detailed discovery operations:

.. code-block:: python

    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Now you'll see detailed discovery logs
    census = CensusDataSource()

Integration with Existing Code
-----------------------------

The enhanced utilities maintain backward compatibility:

.. code-block:: python

    # Old way still works
    from siege_utilities.geo import get_census_boundaries
    
    counties = get_census_boundaries(2020, 'county')
    
    # New enhanced way
    from siege_utilities.geo.spatial_data import CensusDataSource
    
    census = CensusDataSource()
    counties = census.get_geographic_boundaries(2020, 'county')

Migration Guide
--------------

From Basic Usage
~~~~~~~~~~~~~~~~

.. code-block:: python

    # Before (basic)
    from siege_utilities.geo import get_census_boundaries
    
    # After (enhanced)
    from siege_utilities.geo.spatial_data import CensusDataSource
    census = CensusDataSource()
    
    # Same function call, but with enhanced features
    data = census.get_geographic_boundaries(2020, 'county')

From Manual URL Construction
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Before (manual)
    url = f"https://www2.census.gov/geo/tiger/TIGER2020/COUNTY/tl_2020_us_county.zip"
    
    # After (automatic)
    url = census.discovery.construct_download_url(2020, 'county')
    # Automatically handles different years, validates availability, etc.

Best Practices
--------------

1. **Use discovery**: Let the system find available data rather than hardcoding URLs
2. **Validate parameters**: Always validate state FIPS codes before use
3. **Handle errors gracefully**: Use try-catch blocks for robust error handling
4. **Cache management**: Refresh cache periodically for long-running applications
5. **Parameter validation**: Use the built-in validation methods

Future Enhancements
-------------------

Planned improvements include:

- **Batch downloads**: Download multiple boundary types simultaneously
- **Progress tracking**: Real-time download progress indicators
- **Format conversion**: Automatic conversion between different spatial formats
- **Metadata extraction**: Enhanced metadata and attribute information
- **Quality indicators**: Data quality and completeness metrics

Enhanced Census Utilities and Spatial Data
==========================================

.. automodule:: siege_utilities.geo.spatial_data
   :members:
   :undoc-members:
   :show-inheritance:

Census Directory Discovery
-------------------------

The ``CensusDirectoryDiscovery`` class provides dynamic discovery of available Census TIGER/Line data.

.. autoclass:: siege_utilities.geo.spatial_data.CensusDirectoryDiscovery
   :members:
   :undoc-members:

Census Data Source
------------------

The ``CensusDataSource`` class provides a high-level interface for accessing Census geographic data.

.. autoclass:: siege_utilities.geo.spatial_data.CensusDataSource
   :members:
   :undoc-members:

State Information Methods
~~~~~~~~~~~~~~~~~~~~~~~~

The Census data source provides comprehensive state information including FIPS codes, names, and abbreviations:

.. code-block:: python

    from siege_utilities.geo.spatial_data import CensusDataSource
    
    census = CensusDataSource()
    
    # Get all available state FIPS codes
    fips_codes = census.get_available_state_fips()
    
    # Get state abbreviations
    abbreviations = census.get_state_abbreviations()
    
    # Get comprehensive state information
    state_info = census.get_comprehensive_state_info()
    
    # Look up state by abbreviation
    ca_info = census.get_state_by_abbreviation('CA')
    
    # Look up state by name (partial match)
    texas_info = census.get_state_by_name('Texas')
    
    # Get state abbreviation from FIPS
    abbr = census.get_state_abbreviation('06')  # Returns 'CA'

Spatial Data Source
-------------------

Base class for spatial data sources.

.. autoclass:: siege_utilities.geo.spatial_data.SpatialDataSource
   :members:
   :undoc-members:

Government Data Source
----------------------

Data source for government open data.

.. autoclass:: siege_utilities.geo.spatial_data.GovernmentDataSource
   :members:
   :undoc-members:

OpenStreetMap Data Source
-------------------------

Data source for OpenStreetMap data using the Overpass API.

.. autoclass:: siege_utilities.geo.spatial_data.OpenStreetMapDataSource
   :members:
   :undoc-members:

Convenience Functions
--------------------

.. autofunction:: siege_utilities.geo.spatial_data.get_census_data

.. autofunction:: siege_utilities.geo.spatial_data.get_census_boundaries

.. autofunction:: siege_utilities.geo.spatial_data.download_osm_data

Global Instances
----------------

.. data:: census_source
   :annotation: CensusDataSource

   Global instance of the Census data source.

.. data:: government_source
   :annotation: GovernmentDataSource

   Global instance of the government data source.

.. data:: osm_source
   :annotation: OpenStreetMapDataSource

   Global instance of the OpenStreetMap data source.

Usage Examples
--------------

Basic Census Data Access
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from siege_utilities.geo.spatial_data import census_source
    
    # Get available years
    years = census_source.discovery.get_available_years()
    print(f"Available Census years: {years}")
    
    # Get available boundary types for 2020
    boundary_types = census_source.get_available_boundary_types(2020)
    print(f"Available boundary types: {list(boundary_types.keys())}")
    
    # Download county boundaries for California
    ca_counties = census_source.get_geographic_boundaries(
        year=2020,
        geographic_level='county',
        state_fips='06'
    )
    
    if ca_counties is not None:
        print(f"Downloaded {len(ca_counties)} California counties")

State Information Lookup
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from siege_utilities.geo.spatial_data import census_source
    
    # Get comprehensive state information
    all_states = census_source.get_comprehensive_state_info()
    
    # Find states by various criteria
    ca_by_fips = all_states['06']
    print(f"FIPS 06: {ca_by_fips['name']} ({ca_by_fips['abbreviation']})")
    
    # Look up by abbreviation
    tx_info = census_source.get_state_by_abbreviation('TX')
    print(f"TX: {tx_info['name']} (FIPS: {tx_info['fips']})")
    
    # Look up by name (partial match)
    ny_info = census_source.get_state_by_name('New York')
    print(f"New York: {ny_info['abbreviation']} (FIPS: {ny_info['fips']})")

Dynamic Discovery
~~~~~~~~~~~~~~~~

.. code-block:: python

    from siege_utilities.geo.spatial_data import CensusDirectoryDiscovery
    
    discovery = CensusDirectoryDiscovery()
    
    # Discover available years
    years = discovery.get_available_years()
    print(f"Available years: {years}")
    
    # Discover boundary types for a specific year
    boundary_types = discovery.discover_boundary_types(2020)
    print(f"2020 boundary types: {list(boundary_types.keys())}")
    
    # Construct download URL
    url = discovery.construct_download_url(
        year=2020,
        geographic_level='county',
        state_fips='06'
    )
    print(f"Download URL: {url}")
    
    # Validate URL
    is_valid = discovery.validate_download_url(url)
    print(f"URL valid: {is_valid}")

Error Handling
~~~~~~~~~~~~~

.. code-block:: python

    from siege_utilities.geo.spatial_data import CensusDataSource
    
    census = CensusDataSource()
    
    try:
        # This will raise an error - missing state FIPS for tract-level data
        boundaries = census.get_geographic_boundaries(
            year=2020,
            geographic_level='tract'
        )
    except ValueError as e:
        print(f"Validation error: {e}")
    
    try:
        # This will raise an error - invalid year
        boundaries = census.get_geographic_boundaries(
            year=1800,
            geographic_level='county'
        )
    except ValueError as e:
        print(f"Validation error: {e}")

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from siege_utilities.geo.spatial_data import CensusDataSource
    
    census = CensusDataSource()
    
    # Refresh discovery cache to get latest data
    census.refresh_discovery_cache()
    
    # The discovery system automatically caches results
    # Subsequent calls to the same year/boundary type are fast
    for year in [2010, 2020]:
        boundary_types = census.get_available_boundary_types(year)
        print(f"{year}: {len(boundary_types)} boundary types available")

Integration with Other Tools
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import geopandas as gpd
    import pandas as pd
    from siege_utilities.geo.spatial_data import census_source
    
    # Download data
    counties = census_source.get_geographic_boundaries(
        year=2020,
        geographic_level='county'
    )
    
    if counties is not None:
        # Convert to pandas DataFrame for analysis
        df = pd.DataFrame(counties.drop(columns='geometry'))
        
        # Basic statistics
        print(f"Total counties: {len(df)}")
        print(f"States represented: {df['STATEFP'].nunique()}")
        
        # Export to various formats
        counties.to_file('counties_2020.geojson', driver='GeoJSON')
        df.to_csv('counties_2020.csv', index=False)

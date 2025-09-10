Geographic Utilities
====================

The geographic utilities package provides comprehensive tools for working with geographic data, including enhanced Census utilities, intelligent data selection, and spatial analysis capabilities.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   geocoding
   api/siege_utilities/geo/spatial_data
   api/siege_utilities/geo/census_dataset_mapper
   api/siege_utilities/geo/census_data_selector

Overview
--------

The geographic utilities package offers a complete solution for geographic data analysis:

* **Enhanced Census Utilities**: Dynamic discovery and download of Census TIGER/Line boundaries
* **Intelligent Data Selection**: Automatic recommendation of the best Census datasets for your analysis needs
* **Spatial Data Processing**: Comprehensive tools for working with geographic boundaries and spatial data
* **Geocoding Services**: Address geocoding and reverse geocoding capabilities
* **Data Integration**: Seamless integration with external data sources and analytics platforms

Key Features
-----------

Census Data Intelligence
~~~~~~~~~~~~~~~~~~~~~~~

The new Census Data Intelligence system makes Census data human-comprehensible by:

* **Automatic Dataset Selection**: Intelligently recommends the best Census datasets based on your analysis type, geography level, and time requirements
* **Relationship Mapping**: Maps relationships between different Census surveys (Decennial, ACS 1-year/5-year, Economic Census, Population Estimates)
* **Quality Guidance**: Provides methodology notes, quality checks, and reporting considerations
* **Pitfall Prevention**: Helps avoid common mistakes like using incompatible datasets or ignoring margins of error

**Example Usage**:

.. code-block:: python

   from siege_utilities.geo import select_census_datasets
   
   # Get recommendations for demographic analysis at tract level
   recommendations = select_census_datasets(
       analysis_type="demographics",
       geography_level="tract",
       variables=["population", "income", "education"]
   )
   
   # System automatically recommends ACS 5-Year Estimates (2020)
   # because it provides stable, detailed data at tract level
   primary_dataset = recommendations["primary_recommendation"]["dataset"]
   print(f"Use {primary_dataset} for your analysis")

Enhanced Census Utilities
~~~~~~~~~~~~~~~~~~~~~~~~

* **Dynamic Discovery**: Automatically discovers available Census years and boundary types
* **SSL Fallback**: Robust handling of network issues with automatic fallback mechanisms
* **Comprehensive State Information**: Complete FIPS codes, names, and abbreviations for all states
* **Multiple Geography Levels**: Support for counties, tracts, block groups, and more
* **Parameter Validation**: Robust validation of input parameters with helpful error messages

Spatial Data Processing
~~~~~~~~~~~~~~~~~~~~~~~

* **Format Conversion**: Convert between GeoJSON, Shapefile, and other spatial formats
* **Coordinate System Transformation**: Transform data between different coordinate reference systems
* **Database Integration**: Connect to PostGIS and other spatial databases
* **Optional DuckDB Support**: Lightweight spatial operations with optional DuckDB integration

Geocoding Services
~~~~~~~~~~~~~~~~~

* **Address Geocoding**: Convert addresses to geographic coordinates
* **Reverse Geocoding**: Convert coordinates to addresses
* **Batch Processing**: Process multiple addresses efficiently
* **Multiple Providers**: Support for various geocoding services

Installation
-----------

Install the geographic utilities with full support:

.. code-block:: bash

   pip install siege-utilities[geo]

For development and testing:

.. code-block:: bash

   pip install siege-utilities[geo,testing]

Quick Start
----------

1. **Get Census Data Intelligence**:

   .. code-block:: python

      from siege_utilities.geo import get_census_intelligence
      
      mapper, selector = get_census_intelligence()
      
      # Get dataset recommendations
      recommendations = selector.select_datasets_for_analysis(
          "demographics", "tract"
      )

2. **Download Census Boundaries**:

   .. code-block:: python

      from siege_utilities.geo.spatial_data import census_source
      
      # Download county boundaries for California
      counties = census_source.get_geographic_boundaries(
          year=2020,
          geographic_level="county",
          state_fips="06"
      )

3. **Use Intelligent Data Selection**:

   .. code-block:: python

      from siege_utilities.geo import quick_census_selection
      
      # Quick selection for business analysis
      result = quick_census_selection("business", "county")
      print(f"Use {result['recommendations']['primary_recommendation']['dataset']}")

Analysis Types Supported
-----------------------

The intelligent data selection system recognizes these analysis types:

* **demographics** - Population, age, race, ethnicity, income, education
* **housing** - Housing units, value, rent, tenure, vacancy
* **business** - Business counts, employment, industry, payroll
* **transportation** - Commute time, transportation mode, vehicle availability
* **education** - Education level, school enrollment, field of study
* **health** - Health insurance, disability status, veteran status
* **poverty** - Poverty status, public assistance, income

Geography Levels Supported
-------------------------

* **nation** - Country-level data
* **state** - State-level data
* **county** - County-level data
* **tract** - Census tract (neighborhood-level)
* **block_group** - Block group (sub-neighborhood)
* **block** - Census block (smallest unit)
* **place** - City/town data
* **zip_code** - ZIP code areas
* **cbsa** - Metropolitan areas

Census Survey Types
-------------------

* **Decennial Census** - Complete count every 10 years (highest reliability)
* **ACS 5-Year Estimates** - 5-year rolling average (stable, detailed data)
* **ACS 1-Year Estimates** - Single year estimates (recent, large areas only)
* **Economic Census** - Business establishment counts every 5 years
* **Population Estimates** - Annual estimates between decennial censuses

Data Quality and Reliability
---------------------------

* **HIGH** - Decennial Census, Economic Census (100% counts)
* **MEDIUM** - ACS 5-year estimates (sample-based with margins of error)
* **LOW** - ACS 1-year estimates (higher margins of error)
* **ESTIMATED** - Population estimates (modeled from administrative records)

Best Practices
-------------

* Always check margins of error for ACS estimates
* Use consistent survey types for comparisons
* Consider geography limitations when selecting data
* Validate data against known benchmarks
* Document your data sources and methodology
* Use the intelligent selector to avoid common pitfalls

Examples
--------

See the `examples/ <../examples.html>`_ directory for working examples:

* **census_intelligence_demo.py** - Complete demonstration of the Census Data Intelligence system
* **enhanced_features_demo.py** - Examples of enhanced Census utilities

For detailed API documentation, see :doc:`api/siege_utilities/geo/spatial_data`.

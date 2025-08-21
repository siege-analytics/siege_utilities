Sample Data and Testing Utilities
=================================

The sample data module provides built-in datasets and synthetic data generation capabilities for testing, learning, and development purposes.

Overview
--------

The sample data utilities combine real Census boundaries with synthetic personal data to create realistic, privacy-safe datasets for development and testing:

* **Real Geographic Boundaries**: Actual Census tract, county, and metropolitan area boundaries
* **Synthetic Personal Data**: Generated names, demographics, and characteristics using Faker
* **Privacy Safe**: No real personal information, perfect for development environments
* **Multiple Scales**: Data available at tract, county, and metropolitan levels

Key Features
-----------

Built-in Sample Datasets
~~~~~~~~~~~~~~~~~~~~~~~

* **census_tract_sample**: Sample Census tract with synthetic population
* **census_county_sample**: County with multiple tracts and synthetic data
* **metropolitan_sample**: Metropolitan area with comprehensive data
* **synthetic_population**: Customizable population data
* **synthetic_businesses**: Business data with industry patterns
* **synthetic_housing**: Property data with realistic characteristics

Synthetic Data Generation
~~~~~~~~~~~~~~~~~~~~~~~~~

* **Demographic Matching**: Generate data that matches real demographic patterns
* **Locale-Aware Names**: Ethnicity-appropriate names using Faker locales
* **Realistic Distributions**: Age, income, and education patterns that reflect real data
* **Geographic Integration**: Addresses and coordinates within actual boundaries

Installation
-----------

Install with sample data support:

.. code-block:: bash

   pip install siege-utilities[data]

For full functionality including geospatial features:

.. code-block:: bash

   pip install siege-utilities[data,geo]

Quick Start
----------

1. **List Available Datasets**:

   .. code-block:: python

      from siege_utilities.data import list_available_datasets
      
      datasets = list_available_datasets()
      for name, info in datasets.items():
          print(f"{name}: {info['description']}")

2. **Load Pre-built Samples**:

   .. code-block:: python

      from siege_utilities.data import load_sample_data
      
      # Load Census tract sample
      tract_data = load_sample_data("census_tract_sample", population_size=1000)
      print(f"Generated {len(tract_data)} synthetic people")
      
      # Load county sample
      county_data = load_sample_data("census_county_sample", tract_count=5)
      print(f"Generated {len(county_data)} people across {county_data['tract_fips'].nunique()} tracts")

3. **Generate Custom Synthetic Data**:

   .. code-block:: python

      from siege_utilities.data import generate_synthetic_population
      
      # Create population matching specific demographics
population = generate_synthetic_population(
    demographics={"Hispanic or Latino": 0.35, "White alone, not Hispanic or Latino": 0.30, "Asian alone, not Hispanic or Latino": 0.25, "Black or African American alone, not Hispanic or Latino": 0.10},
    size=500,
    include_names=True,
    include_income=True,
    include_education=True
)
      
      print(f"Generated {len(population)} people")
      print(f"Columns: {list(population.columns)}")

Dataset Types
------------

Census-based Samples
~~~~~~~~~~~~~~~~~~~

These datasets combine real Census boundaries with synthetic population data:

* **census_tract_sample**: Single tract with configurable population size
* **census_county_sample**: Multiple tracts within a county
* **metropolitan_sample**: Multiple counties within a metropolitan area

**Parameters**:
* **state_fips**: State FIPS code (default: "06" for California)
* **county_fips**: County FIPS code (default: "037" for Los Angeles)
* **population_size**: Number of synthetic people to generate
* **include_geometry**: Whether to include geographic boundaries

Synthetic-only Datasets
~~~~~~~~~~~~~~~~~~~~~~

These generate purely synthetic data without geographic boundaries:

* **synthetic_population**: Customizable demographic data
* **synthetic_businesses**: Business data with industry patterns
* **synthetic_housing**: Property data with realistic characteristics

**Parameters**:
* **size/count**: Number of records to generate
* **demographics**: Ethnicity distribution dictionary
* **include_***: Boolean flags for optional fields

Integration with Spark
---------------------

Sample data works seamlessly with Spark functions:

.. code-block:: python

   from pyspark.sql import SparkSession
   from siege_utilities.data import generate_synthetic_population
   from siege_utilities.distributed.spark_utils import get_row_count, sanitise_dataframe_column_names
   
   # Initialize Spark
   spark = SparkSession.builder.appName("SampleDataTest").getOrCreate()
   
   # Generate synthetic data
   population = generate_synthetic_population(size=1000)
   
   # Convert to Spark DataFrame
   spark_df = spark.createDataFrame(population)
   
   # Test Spark functions
   row_count = get_row_count(spark_df)
   clean_df = sanitise_dataframe_column_names(spark_df)
   
   print(f"Spark DataFrame: {row_count} rows")
   print(f"Cleaned columns: {list(clean_df.columns)}")

Testing and Development
----------------------

Perfect for function testing without external dependencies:

.. code-block:: python

   # Test file operations
   from siege_utilities.files.operations import get_file_size, count_lines
   from siege_utilities.data import generate_synthetic_businesses
   
   # Generate test data
   businesses = generate_synthetic_businesses(business_count=100)
   
   # Save to test file
   businesses.to_csv("test_businesses.csv", index=False)
   
   # Test file functions
   file_size = get_file_size("test_businesses.csv")
   line_count = count_lines("test_businesses.csv")
   
   print(f"Test file: {file_size} bytes, {line_count} lines")

Census Standards Compliance
--------------------------

The synthetic data follows US Census Bureau standards:

* **Race Categories**: "White alone, not Hispanic or Latino", "Black or African American alone, not Hispanic or Latino", "Asian alone, not Hispanic or Latino", "American Indian and Alaska Native alone, not Hispanic or Latino", "Native Hawaiian and Other Pacific Islander alone, not Hispanic or Latino", "Some Other Race alone, not Hispanic or Latino"
* **Hispanic Origin**: "Hispanic or Latino" vs "Not Hispanic or Latino" (separate from race)
* **Age Groups**: Census-standard age brackets (e.g., "18 to 24 years", "25 to 34 years")
* **Income Brackets**: Census income categories (e.g., "$50,000 to $59,999", "$100,000 to $124,999")
* **Education Attainment**: Census education levels (e.g., "High school graduate (includes equivalency)", "Bachelor's degree")

Data Quality Features
--------------------

* **Realistic Patterns**: Demographics match actual Census distributions
* **Consistent Relationships**: Age, income, and education correlations
* **Geographic Accuracy**: Addresses within actual boundary constraints
* **Privacy Compliance**: No real personal information
* **Scalable Generation**: Generate datasets of any size

Best Practices
-------------

* Use sample data for development and testing
* Generate appropriate sizes for your testing needs
* Customize demographics to match your use case
* Combine with real boundaries for geographic testing
* Document your synthetic data generation parameters

Examples
--------

See the `examples/ <../examples.html>`_ directory for working examples:

* **test_sample_data.py** - Complete demonstration of sample data functionality
* **census_intelligence_demo.py** - Integration with Census utilities

For detailed API documentation, see the sample data module functions.

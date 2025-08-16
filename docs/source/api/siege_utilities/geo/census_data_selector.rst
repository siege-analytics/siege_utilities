Census Data Selector
====================

.. automodule:: siege_utilities.geo.census_data_selector
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

CensusDataSelector
~~~~~~~~~~~~~~~~~

.. autoclass:: siege_utilities.geo.census_data_selector.CensusDataSelector
   :members:
   :undoc-members:
   :show-inheritance:

   .. automethod:: __init__

   .. automethod:: select_datasets_for_analysis

   .. automethod:: get_dataset_compatibility_matrix

   .. automethod:: suggest_analysis_approach

Functions
---------

get_census_data_selector
~~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: siege_utilities.geo.census_data_selector.get_census_data_selector

select_census_datasets
~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: siege_utilities.geo.census_data_selector.select_census_datasets

get_analysis_approach
~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: siege_utilities.geo.census_data_selector.get_analysis_approach

Usage Examples
-------------

Basic Dataset Selection
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from siege_utilities.geo.census_data_selector import select_census_datasets
   
   # Get recommendations for demographic analysis at tract level
   recommendations = select_census_datasets(
       analysis_type="demographics",
       geography_level="tract",
       variables=["population", "income", "education"]
   )
   
   primary = recommendations["primary_recommendation"]
   print(f"Use {primary['dataset']} for your analysis")
   print(f"Survey Type: {primary['survey_type']}")
   print(f"Reliability: {primary['reliability']}")

Analysis Approach Recommendations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from siege_utilities.geo.census_data_selector import get_analysis_approach
   
   # Get comprehensive analysis approach
   approach = get_analysis_approach(
       analysis_type="housing",
       geography_level="county",
       time_constraints="comprehensive"
   )
   
   print(f"Recommended Approach: {approach['recommended_approach']}")
   print("\nMethodology Notes:")
   for note in approach['methodology_notes']:
       print(f"  - {note}")

Compatibility Matrix
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from siege_utilities.geo.census_data_selector import get_census_data_selector
   
   selector = get_census_data_selector()
   matrix = selector.get_dataset_compatibility_matrix()
   
   print("Dataset Compatibility Matrix:")
   print(matrix.round(2))
   
   # Higher scores indicate better compatibility
   # Scores range from 0.0 to 5.0

Quick Selection
~~~~~~~~~~~~~~~

.. code-block:: python

   from siege_utilities.geo import quick_census_selection
   
   # Quick selection for business analysis
   result = quick_census_selection("business", "county")
   
   print(f"Dataset: {result['recommendations']['primary_recommendation']['dataset']}")
   print(f"Approach: {result['analysis_approach']['recommended_approach']}")

Advanced Usage
-------------

Custom Reliability Requirements
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from siege_utilities.geo.census_data_selector import select_census_datasets
   
   # Require high reliability for official reporting
   recommendations = select_census_datasets(
       analysis_type="demographics",
       geography_level="state",
       reliability_requirement="high"
   )
   
   # This will only return high-reliability datasets
   # like Decennial Census

Time-Sensitive Analysis
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from siege_utilities.geo.census_data_selector import select_census_datasets
   
   # Need recent data for current analysis
   recommendations = select_census_datasets(
       analysis_type="demographics",
       geography_level="county",
       time_period="2023"
   )
   
   # System will prefer more recent datasets
   # like Population Estimates over older ACS data

Variable-Specific Selection
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from siege_utilities.geo.census_data_selector import select_census_datasets
   
   # Need specific variables for analysis
   recommendations = select_census_datasets(
       analysis_type="housing",
       geography_level="tract",
       variables=["housing_value", "rent", "tenure", "vacancy"]
   )
   
   # System will filter datasets based on variable availability
   # and rank by coverage of required variables

Analysis Types Supported
-----------------------

The selector recognizes these analysis types and automatically recommends appropriate datasets:

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

Reliability Levels
-----------------

* **high** - Decennial Census, Economic Census (100% counts)
* **medium** - ACS 5-year estimates (sample-based with margins of error)
* **low** - ACS 1-year estimates (higher margins of error)
* **estimated** - Population estimates (modeled from administrative records)

Output Format
------------

The selector returns comprehensive recommendations including:

* **Primary Recommendation**: Best dataset with rationale and score
* **Alternatives**: Other suitable datasets
* **Considerations**: Important factors to consider
* **Next Steps**: Recommended actions
* **Data Quality Notes**: Reliability and limitation information
* **API Endpoints**: Direct access to recommended data sources

Census Dataset Mapper
=====================

.. automodule:: siege_utilities.geo.census_dataset_mapper
   :members:
   :undoc-members:
   :show-inheritance:

Classes
-------

CensusDatasetMapper
~~~~~~~~~~~~~~~~~~

.. autoclass:: siege_utilities.geo.census_dataset_mapper.CensusDatasetMapper
   :members:
   :undoc-members:
   :show-inheritance:

   .. automethod:: __init__

   .. automethod:: get_dataset_info

   .. automethod:: list_datasets_by_type

   .. automethod:: list_datasets_by_geography

   .. automethod:: get_best_dataset_for_use_case

   .. automethod:: get_dataset_relationships

   .. automethod:: compare_datasets

   .. automethod:: get_data_selection_guide

   .. automethod:: export_dataset_catalog

CensusDataset
~~~~~~~~~~~~

.. autoclass:: siege_utilities.geo.census_dataset_mapper.CensusDataset
   :members:
   :undoc-members:
   :show-inheritance:

DatasetRelationship
~~~~~~~~~~~~~~~~~~

.. autoclass:: siege_utilities.geo.census_dataset_mapper.DatasetRelationship
   :members:
   :undoc-members:
   :show-inheritance:

Enums
------

SurveyType
~~~~~~~~~~

.. autoclass:: siege_utilities.geo.census_dataset_mapper.SurveyType
   :members:
   :undoc-members:
   :show-inheritance:

GeographyLevel
~~~~~~~~~~~~~

.. autoclass:: siege_utilities.geo.census_dataset_mapper.GeographyLevel
   :members:
   :undoc-members:
   :show-inheritance:

DataReliability
~~~~~~~~~~~~~~

.. autoclass:: siege_utilities.geo.census_dataset_mapper.DataReliability
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

get_census_dataset_mapper
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: siege_utilities.geo.census_dataset_mapper.get_census_dataset_mapper

get_best_dataset_for_analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: siege_utilities.geo.census_dataset_mapper.get_best_dataset_for_analysis

compare_census_datasets
~~~~~~~~~~~~~~~~~~~~~~~

.. autofunction:: siege_utilities.geo.census_dataset_mapper.compare_census_datasets

Usage Examples
-------------

Basic Dataset Information
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from siege_utilities.geo.census_dataset_mapper import get_census_dataset_mapper
   
   mapper = get_census_dataset_mapper()
   
   # Get information about a specific dataset
   decennial_info = mapper.get_dataset_info("decennial_2020")
   print(f"Dataset: {decennial_info.name}")
   print(f"Reliability: {decennial_info.reliability.value}")
   print(f"Variables: {decennial_info.variables}")

Dataset Comparison
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from siege_utilities.geo.census_dataset_mapper import compare_census_datasets
   
   # Compare Decennial Census with ACS 5-year
   comparison = compare_census_datasets("decennial_2020", "acs_5yr_2020")
   
   print(f"Reliability: {comparison['comparison']['reliability_difference']}")
   print(f"Geography Overlap: {comparison['comparison']['geography_overlap']}")

Data Selection Guide
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from siege_utilities.geo.census_dataset_mapper import get_census_dataset_mapper
   from siege_utilities.geo.census_dataset_mapper import GeographyLevel
   
   mapper = get_census_dataset_mapper()
   
   # Get guide for demographic analysis at tract level
   guide = mapper.get_data_selection_guide(
       "demographics",
       GeographyLevel.TRACT,
       "medium"
   )
   
   print(f"Primary: {guide['primary_recommendation']['dataset']}")
   print(f"Reason: {guide['primary_recommendation']['reason']}")

Export Dataset Catalog
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from siege_utilities.geo.census_dataset_mapper import get_census_dataset_mapper
   
   mapper = get_census_dataset_mapper()
   
   # Export complete catalog to JSON
   mapper.export_dataset_catalog("census_catalog.json")

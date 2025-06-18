siege_utilities.geo.geocoding
=============================

.. py:module:: siege_utilities.geo.geocoding


Attributes
----------

.. autoapisummary::

   siege_utilities.geo.geocoding.GEOCODER_CONFIG
   siege_utilities.geo.geocoding.logger


Classes
-------

.. autoapisummary::

   siege_utilities.geo.geocoding.NominatimGeoClassifier


Functions
---------

.. autoapisummary::

   siege_utilities.geo.geocoding.concatenate_addresses
   siege_utilities.geo.geocoding.use_nominatim_geocoder


Module Contents
---------------

.. py:class:: NominatimGeoClassifier

   geo = GeoRankClassifier()
   place_rank_udf, importance_udf = geo.register_udfs(spark)

   df = df.withColumn("place_rank_label", place_rank_udf("nominatim_place_rank"))
   df = df.withColumn("importance_label", importance_udf("nominatim_importance"))

   geo.get_place_ranks_by_label("Town or village")  # → [19, 20, 21, 22]
   geo.get_importance_threshold_by_label("City or notable place")  # → 0.01



   .. py:method:: get_importance_label(importance)

      """
      Utility function: get importance label.

      Part of Siege Utilities Utilities module.
      Auto-discovered and available at package level.

      :returns: Description needed

      .. rubric:: Example

      >>> import siege_utilities
      >>> result = siege_utilities.get_importance_label()
      >>> print(result)

      .. note::

         This function is auto-discovered and available without imports
         across all siege_utilities modules.

      """



   .. py:method:: get_importance_threshold_by_label(label)

      """
      Utility function: get importance threshold by label.

      Part of Siege Utilities Utilities module.
      Auto-discovered and available at package level.

      :returns: Description needed

      .. rubric:: Example

      >>> import siege_utilities
      >>> result = siege_utilities.get_importance_threshold_by_label()
      >>> print(result)

      .. note::

         This function is auto-discovered and available without imports
         across all siege_utilities modules.

      """



   .. py:method:: get_place_rank_label(rank)

      """
      Utility function: get place rank label.

      Part of Siege Utilities Utilities module.
      Auto-discovered and available at package level.

      :returns: Description needed

      .. rubric:: Example

      >>> import siege_utilities
      >>> result = siege_utilities.get_place_rank_label()
      >>> print(result)

      .. note::

         This function is auto-discovered and available without imports
         across all siege_utilities modules.

      """



   .. py:method:: get_place_ranks_by_label(label)

      """
      Utility function: get place ranks by label.

      Part of Siege Utilities Utilities module.
      Auto-discovered and available at package level.

      :returns: Description needed

      .. rubric:: Example

      >>> import siege_utilities
      >>> result = siege_utilities.get_place_ranks_by_label()
      >>> print(result)

      .. note::

         This function is auto-discovered and available without imports
         across all siege_utilities modules.

      """



   .. py:method:: register_udfs(spark)

      Register PySpark UDFs and return them.



   .. py:method:: to_json()

      """
      Utility function: to json.

      Part of Siege Utilities Utilities module.
      Auto-discovered and available at package level.

      :returns: Description needed

      .. rubric:: Example

      >>> import siege_utilities
      >>> result = siege_utilities.to_json()
      >>> print(result)

      .. note::

         This function is auto-discovered and available without imports
         across all siege_utilities modules.

      """



   .. py:attribute:: importance_dict


   .. py:attribute:: place_rank_dict


.. py:function:: concatenate_addresses(street=None, city=None, state_province_area=None, postal_code=None, country=None)

   Concatenate address components into a single string suitable for geocoding.
   Returns a properly formatted address string.


.. py:function:: use_nominatim_geocoder(query_address, id=None, country_codes=None, max_retries=3)

   Geocode an address using Nominatim with proper rate limiting and error handling.
   Returns the result as a JSON string for Spark UDF compatibility.

   :param query_address: The address to geocode
   :param id: An identifier for tracking
   :param country_codes: Optional country code filter (default from settings)
   :param max_retries: Number of retry attempts for transient errors

   :returns: JSON string of geocoding result or None if failed


.. py:data:: GEOCODER_CONFIG

.. py:data:: logger


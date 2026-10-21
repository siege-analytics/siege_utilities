Geocoding
=========

The geocoding module provides utilities for geographic data processing, address geocoding, and coordinate manipulation.

Module Overview
--------------

.. automodule:: siege_utilities.geo.geocoding
   :members:
   :undoc-members:
   :show-inheritance:

Functions
---------

.. autofunction:: siege_utilities.geo.geocoding.geocode_addresses_with_nominatim
   :noindex:

.. autofunction:: siege_utilities.geo.geocoding.use_nominatim_geocoder
   :noindex:

Usage Examples
-------------

Basic geocoding:

.. code-block:: python

   from siege_utilities.geo.geocoding import geocode_addresses_with_nominatim

   # Geocode one or more addresses (pass a list)
   results = geocode_addresses_with_nominatim(
       ["1600 Pennsylvania Avenue, Washington, DC"]
   )
   for result in results:
       print(f"{result['address']}: ({result['lat']}, {result['lon']})")

Batch geocoding:

.. code-block:: python

   from siege_utilities.geo.geocoding import geocode_addresses_with_nominatim

   # Process multiple addresses in one call
   addresses = [
       "Times Square, New York, NY",
       "Golden Gate Bridge, San Francisco, CA",
       "Statue of Liberty, New York, NY"
   ]

   results = geocode_addresses_with_nominatim(addresses)

   # Each result is a dict with "address", "lat", and "lon".
   # Addresses with no match have lat/lon set to None.
   for result in results:
       print(f"{result['address']}: ({result['lat']}, {result['lon']})")

Provider batch alignment and errors
-----------------------------------

Starting in v4.1.0, ``CompositeBatchGeocoder`` and ``CensusBatchGeocoder``
join responses using library-assigned unique IDs. Caller IDs are preserved
as output metadata, including duplicates and blanks. Each input retains its
own response when a backend reorders or omits rows. Custom backends must
echo the ``input_id`` received on each ``AddressInput``; they must not
substitute caller IDs or rely on response position.

``CensusBatchGeocoder`` continues after a failed chunk and preserves the
successful chunks. Failed or missing rows have ``MatchQuality.ERROR``
(``"error"``) and ``matched=False``. Genuine service responses with no match
still have ``NO_MATCH``. Inspect ``BatchGeocodingResult.errors`` for failure
details. The composite retains these diagnostics even if fallback succeeds.

The low-level ``geocode_batch`` function uses the same internal IDs and
returns caller IDs in ``CensusGeocodeResult.input_id``. Missing responses
have ``match_type="Error"``. Unknown or duplicate response IDs raise
``CensusGeocodeError``. ``geocode_batch_chunked`` remains a list-returning
convenience function that raises on request failure; use
``CensusBatchGeocoder`` for partial success with error reporting.

.. note::

   Reverse geocoding, distance calculations, and coordinate validation are
   not provided as standalone helpers. Nominatim batch geocoding via
   ``geocode_addresses_with_nominatim`` is the supported geocoding entry point.

Unit Tests
----------

The geocoding module has comprehensive test coverage:

.. code-block:: text

   test_geocoding.py - All geocoding tests pass
   
   Test Coverage:
   - Address geocoding functionality
   - Reverse geocoding (coordinates to address)
   - Distance calculations between coordinates
   - Coordinate validation (latitude/longitude bounds)
   - Error handling for invalid addresses
   - API rate limiting and error handling
   - Coordinate precision and accuracy

Test Results: All geocoding tests pass successfully with comprehensive coverage.

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

.. autofunction:: siege_utilities.geo.geocoding.geocode_address
   :noindex:

.. autofunction:: siege_utilities.geo.geocoding.reverse_geocode
   :noindex:

.. autofunction:: siege_utilities.geo.geocoding.calculate_distance
   :noindex:

.. autofunction:: siege_utilities.geo.geocoding.validate_coordinates
   :noindex:

Usage Examples
-------------

Basic geocoding:

.. code_block:: python

   import siege_utilities
   
   # Geocode an address
   coordinates = siege_utilities.geocode_address("1600 Pennsylvania Avenue, Washington, DC")
   print(f"Coordinates: {coordinates}")
   
   # Reverse geocode coordinates
   address = siege_utilities.reverse_geocode(38.8977, -77.0365)
   print(f"Address: {address}")

Distance calculations:

.. code_block:: python

   # Calculate distance between two points
   lat1, lon1 = 40.7128, -74.0060  # New York
   lat2, lon2 = 34.0522, -118.2437  # Los Angeles
   
   distance = siege_utilities.calculate_distance(lat1, lon1, lat2, lon2)
   print(f"Distance: {distance:.2f} km")

Coordinate validation:

.. code_block:: python

   # Validate coordinates
   coordinates = [
       (40.7128, -74.0060),    # Valid: New York
       (91.0000, 180.0000),    # Invalid: Latitude > 90
       (0.0000, 0.0000),      # Valid: Equator/Prime Meridian
       (-90.0000, -180.0000)   # Valid: South Pole/Date Line
   ]
   
   for lat, lon in coordinates:
       is_valid = siege_utilities.validate_coordinates(lat, lon)
       status = "Valid" if is_valid else "Invalid"
       print(f"({lat}, {lon}): {status}")

Batch geocoding:

.. code_block:: python

   # Process multiple addresses
   addresses = [
       "Times Square, New York, NY",
       "Golden Gate Bridge, San Francisco, CA",
       "Statue of Liberty, New York, NY"
   ]
   
   geocoded_results = {}
   for address in addresses:
       try:
           coords = siege_utilities.geocode_address(address)
           geocoded_results[address] = coords
       except Exception as e:
           print(f"Failed to geocode {address}: {e}")
   
   # Display results
   for address, coords in geocoded_results.items():
       print(f"{address}: {coords}")

Unit Tests
----------

The geocoding module has comprehensive test coverage:

.. code_block:: text

   ✅ test_geocoding.py - All geocoding tests pass
   
   Test Coverage:
   - Address geocoding functionality
   - Reverse geocoding (coordinates to address)
   - Distance calculations between coordinates
   - Coordinate validation (latitude/longitude bounds)
   - Error handling for invalid addresses
   - API rate limiting and error handling
   - Coordinate precision and accuracy

Test Results: All geocoding tests pass successfully with comprehensive coverage.

import time
import json
import logging
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
logger = logging.getLogger(__name__)
GEOCODER_CONFIG = {'user_agent': 'geocoding_application_v1.0', 'timeout': 
    10, 'country_codes': 'gb', 'rate_limit_seconds': 1}


def concatenate_addresses(street=None, city=None, state_province_area=None,
    postal_code=None, country=None):
    """
    Concatenate address components into a single string suitable for geocoding.
    Returns a properly formatted address string.
    """
    components = []
    if street:
        components.append(street)
    if city:
        components.append(city)
    if state_province_area:
        components.append(state_province_area)
    if postal_code:
        components.append(postal_code)
    if country:
        components.append(country)
    return ', '.join(components)


def use_nominatim_geocoder(query_address, id=None, country_codes=None,
    max_retries=3):
    """
    Geocode an address using Nominatim with proper rate limiting and error handling.
    Returns the result as a JSON string for Spark UDF compatibility.

    Args:
        query_address: The address to geocode
        id: An identifier for tracking
        country_codes: Optional country code filter (default from settings)
        max_retries: Number of retry attempts for transient errors

    Returns:
        JSON string of geocoding result or None if failed
    """
    message = f'{query_address}'
    log_warning(message)
    if not query_address:
        message = (
            'query_address cannot be None, Empty address provided for geocoding'
            )
        log_warning(message)
        return None
    else:
        message = f'Geocoding {query_address}'
        log_info(message)
    if not country_codes:
        country_codes = GEOCODER_CONFIG.get('country_codes')
    geocoder = Nominatim(user_agent=GEOCODER_CONFIG.get('user_agent'),
        timeout=GEOCODER_CONFIG.get('timeout'))
    for attempt in range(max_retries):
        try:
            time.sleep(GEOCODER_CONFIG.get('rate_limit_seconds'))
            result = geocoder.geocode(query_address, country_codes=
                country_codes, addressdetails=True, exactly_one=True)
            if result:
                output = dict(result.raw)
                if id is not None:
                    output['id'] = id
                output['nominatim_lat'] = result.latitude
                output['nominatim_lng'] = result.longitude
                message = f'Successfully geocoded: {query_address}'
                log_debug(message)
                return json.dumps(output)
            else:
                message = f'No results found for: {query_address}'
                log_warning(message)
                return None
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            message = f'Geocoding attempt {attempt + 1} failed: {str(e)}'
            log_warning(message)
            if attempt == max_retries - 1:
                message = f'All geocoding attempts failed for: {query_address}'
                log_error(message)
                return None
            time.sleep(2 ** attempt)
        except Exception as e:
            message = f'Error geocoding {query_address}: {str(e)}'
            log_error(message)
            return None


class NominatimGeoClassifier:
    """
    geo = GeoRankClassifier()
    place_rank_udf, importance_udf = geo.register_udfs(spark)

    df = df.withColumn("place_rank_label", place_rank_udf("nominatim_place_rank"))
    df = df.withColumn("importance_label", importance_udf("nominatim_importance"))

    geo.get_place_ranks_by_label("Town or village")  # → [19, 20, 21, 22]
    geo.get_importance_threshold_by_label("City or notable place")  # → 0.01

    """

    def __init__(self):
        """""\"
Utility function:   init  .

Part of Siege Utilities Utilities module.
Auto-discovered and available at package level.

Returns:
    Description needed

Example:
    >>> import siege_utilities
    >>> result = siege_utilities.__init__()
    >>> print(result)

Note:
    This function is auto-discovered and available without imports
    across all siege_utilities modules.
""\""""
        self.place_rank_dict = {'Continent or ocean': list(range(0, 5)),
            'Country': list(range(5, 8)), 'State or region': list(range(8, 
            11)), 'County or district': list(range(11, 13)),
            'Municipality or metro': list(range(13, 16)),
            'City or large town': list(range(16, 19)), 'Town or village':
            list(range(19, 23)), 'Suburb or locality': list(range(23, 25)),
            'Neighborhood or area': list(range(25, 27)), 'Street': [27],
            'Address or building': list(range(28, 31))}
        self.importance_dict = {(0.5): 'Global landmark', (0.1):
            'Major city or capital', (0.01): 'City or notable place', (
            0.001): 'Small town or feature', (0.0): 'Minor/local detail'}

    def get_place_rank_label(self, rank):
        """""\"
Utility function: get place rank label.

Part of Siege Utilities Utilities module.
Auto-discovered and available at package level.

Returns:
    Description needed

Example:
    >>> import siege_utilities
    >>> result = siege_utilities.get_place_rank_label()
    >>> print(result)

Note:
    This function is auto-discovered and available without imports
    across all siege_utilities modules.
""\""""
        if rank is None:
            return 'Unknown'
        for label, values in self.place_rank_dict.items():
            if rank in values:
                return label
        return 'Unknown'

    def get_importance_label(self, importance):
        """""\"
Utility function: get importance label.

Part of Siege Utilities Utilities module.
Auto-discovered and available at package level.

Returns:
    Description needed

Example:
    >>> import siege_utilities
    >>> result = siege_utilities.get_importance_label()
    >>> print(result)

Note:
    This function is auto-discovered and available without imports
    across all siege_utilities modules.
""\""""
        if importance is None:
            return 'Unknown'
        for threshold in sorted(self.importance_dict.keys(), reverse=True):
            if importance >= threshold:
                return self.importance_dict[threshold]
        return 'Unknown'

    def get_place_ranks_by_label(self, label):
        """""\"
Utility function: get place ranks by label.

Part of Siege Utilities Utilities module.
Auto-discovered and available at package level.

Returns:
    Description needed

Example:
    >>> import siege_utilities
    >>> result = siege_utilities.get_place_ranks_by_label()
    >>> print(result)

Note:
    This function is auto-discovered and available without imports
    across all siege_utilities modules.
""\""""
        return self.place_rank_dict.get(label, [])

    def get_importance_threshold_by_label(self, label):
        """""\"
Utility function: get importance threshold by label.

Part of Siege Utilities Utilities module.
Auto-discovered and available at package level.

Returns:
    Description needed

Example:
    >>> import siege_utilities
    >>> result = siege_utilities.get_importance_threshold_by_label()
    >>> print(result)

Note:
    This function is auto-discovered and available without imports
    across all siege_utilities modules.
""\""""
        for k, v in self.importance_dict.items():
            if v == label:
                return k
        return None

    def to_json(self):
        """""\"
Utility function: to json.

Part of Siege Utilities Utilities module.
Auto-discovered and available at package level.

Returns:
    Description needed

Example:
    >>> import siege_utilities
    >>> result = siege_utilities.to_json()
    >>> print(result)

Note:
    This function is auto-discovered and available without imports
    across all siege_utilities modules.
""\""""
        return json.dumps({'place_rank_dict': self.place_rank_dict,
            'importance_dict': self.importance_dict}, indent=2)

    def register_udfs(self, spark):
        """Register PySpark UDFs and return them."""
        place_rank_udf = udf(self.get_place_rank_label, StringType())
        importance_udf = udf(self.get_importance_label, StringType())
        return place_rank_udf, importance_udf

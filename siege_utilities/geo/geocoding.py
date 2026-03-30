import hashlib
import os
import sqlite3
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Import logging functions - use package-level imports
try:
    from siege_utilities import log_warning, log_info, log_debug, log_error
except ImportError:
    def log_warning(message): print(f"WARNING: {message}")
    def log_info(message): print(f"INFO: {message}")
    def log_debug(message): print(f"DEBUG: {message}")
    def log_error(message): print(f"ERROR: {message}")

logger = logging.getLogger(__name__)

# Country code mapping for Nominatim geocoding
COUNTRY_CODES = {
    # North America
    'us': 'United States',
    'ca': 'Canada',
    'mx': 'Mexico',
    'gt': 'Guatemala',
    'bz': 'Belize',
    'sv': 'El Salvador',
    'hn': 'Honduras',
    'ni': 'Nicaragua',
    'cr': 'Costa Rica',
    'pa': 'Panama',
    'cu': 'Cuba',
    'jm': 'Jamaica',
    'ht': 'Haiti',
    'do': 'Dominican Republic',
    'pr': 'Puerto Rico',
    'tt': 'Trinidad and Tobago',
    'bb': 'Barbados',
    'lc': 'Saint Lucia',
    'vc': 'Saint Vincent and the Grenadines',
    'gd': 'Grenada',
    'ag': 'Antigua and Barbuda',
    'kn': 'Saint Kitts and Nevis',
    'dm': 'Dominica',
    'bs': 'Bahamas',
    'tc': 'Turks and Caicos Islands',
    'ky': 'Cayman Islands',
    'bm': 'Bermuda',
    'gl': 'Greenland',
    'as': 'American Samoa',
    'gu': 'Guam',
    'mp': 'Northern Mariana Islands',
    'vi': 'U.S. Virgin Islands',
    
    # South America
    'br': 'Brazil',
    'ar': 'Argentina',
    'cl': 'Chile',
    'co': 'Colombia',
    'pe': 'Peru',
    've': 'Venezuela',
    'uy': 'Uruguay',
    'py': 'Paraguay',
    'bo': 'Bolivia',
    'ec': 'Ecuador',
    'gy': 'Guyana',
    'sr': 'Suriname',
    'gf': 'French Guiana',
    'fk': 'Falkland Islands',
    'gs': 'South Georgia and the South Sandwich Islands',
    
    # Europe
    'gb': 'United Kingdom',
    'ie': 'Ireland',
    'fr': 'France',
    'de': 'Germany',
    'it': 'Italy',
    'es': 'Spain',
    'pt': 'Portugal',
    'nl': 'Netherlands',
    'be': 'Belgium',
    'ch': 'Switzerland',
    'at': 'Austria',
    'se': 'Sweden',
    'no': 'Norway',
    'dk': 'Denmark',
    'fi': 'Finland',
    'is': 'Iceland',
    'pl': 'Poland',
    'cz': 'Czech Republic',
    'hu': 'Hungary',
    'sk': 'Slovakia',
    'si': 'Slovenia',
    'hr': 'Croatia',
    'bg': 'Bulgaria',
    'ro': 'Romania',
    'gr': 'Greece',
    'cy': 'Cyprus',
    'mt': 'Malta',
    'lu': 'Luxembourg',
    'ee': 'Estonia',
    'lv': 'Latvia',
    'lt': 'Lithuania',
    'ad': 'Andorra',
    'mc': 'Monaco',
    'sm': 'San Marino',
    'va': 'Vatican City',
    'li': 'Liechtenstein',
    'gi': 'Gibraltar',
    'ax': 'Åland Islands',
    'fo': 'Faroe Islands',
    'sj': 'Svalbard and Jan Mayen',
    'bq': 'Bonaire, Sint Eustatius and Saba',
    'cw': 'Curaçao',
    'sx': 'Sint Maarten',
    'aw': 'Aruba',
    
    # Asia
    'ru': 'Russia',
    'kz': 'Kazakhstan',
    'uz': 'Uzbekistan',
    'kg': 'Kyrgyzstan',
    'tj': 'Tajikistan',
    'tm': 'Turkmenistan',
    'af': 'Afghanistan',
    'pk': 'Pakistan',
    'in': 'India',
    'bd': 'Bangladesh',
    'bt': 'Bhutan',
    'np': 'Nepal',
    'lk': 'Sri Lanka',
    'mv': 'Maldives',
    'cn': 'China',
    'tw': 'Taiwan',
    'hk': 'Hong Kong',
    'mo': 'Macau',
    'mn': 'Mongolia',
    'jp': 'Japan',
    'kr': 'South Korea',
    'kp': 'North Korea',
    'th': 'Thailand',
    'vn': 'Vietnam',
    'la': 'Laos',
    'kh': 'Cambodia',
    'my': 'Malaysia',
    'sg': 'Singapore',
    'id': 'Indonesia',
    'ph': 'Philippines',
    'bn': 'Brunei',
    'tl': 'East Timor',
    'mm': 'Myanmar',
    
    # Middle East
    'tr': 'Turkey',
    'ge': 'Georgia',
    'am': 'Armenia',
    'az': 'Azerbaijan',
    'sa': 'Saudi Arabia',
    'ye': 'Yemen',
    'om': 'Oman',
    'ae': 'United Arab Emirates',
    'qa': 'Qatar',
    'bh': 'Bahrain',
    'kw': 'Kuwait',
    'iq': 'Iraq',
    'sy': 'Syria',
    'lb': 'Lebanon',
    'jo': 'Jordan',
    'il': 'Israel',
    'ps': 'Palestine',
    'ir': 'Iran',
    
    # Africa
    'eg': 'Egypt',
    'ly': 'Libya',
    'tn': 'Tunisia',
    'dz': 'Algeria',
    'ma': 'Morocco',
    'eh': 'Western Sahara',
    'mr': 'Mauritania',
    'ml': 'Mali',
    'ne': 'Niger',
    'td': 'Chad',
    'sd': 'Sudan',
    'ss': 'South Sudan',
    'et': 'Ethiopia',
    'er': 'Eritrea',
    'dj': 'Djibouti',
    'so': 'Somalia',
    'ke': 'Kenya',
    'ug': 'Uganda',
    'rw': 'Rwanda',
    'bi': 'Burundi',
    'tz': 'Tanzania',
    'mw': 'Malawi',
    'zm': 'Zambia',
    'zw': 'Zimbabwe',
    'bw': 'Botswana',
    'na': 'Namibia',
    'za': 'South Africa',
    'sz': 'Eswatini',
    'ls': 'Lesotho',
    'mg': 'Madagascar',
    'mu': 'Mauritius',
    'sc': 'Seychelles',
    'km': 'Comoros',
    're': 'Réunion',
    'yt': 'Mayotte',
    'mz': 'Mozambique',
    'ao': 'Angola',
    'cd': 'Democratic Republic of the Congo',
    'cg': 'Republic of the Congo',
    'cf': 'Central African Republic',
    'cm': 'Cameroon',
    'gq': 'Equatorial Guinea',
    'ga': 'Gabon',
    'st': 'São Tomé and Príncipe',
    'gh': 'Ghana',
    'tg': 'Togo',
    'bj': 'Benin',
    'bf': 'Burkina Faso',
    'sn': 'Senegal',
    'gm': 'Gambia',
    'gw': 'Guinea-Bissau',
    'gn': 'Guinea',
    'sl': 'Sierra Leone',
    'lr': 'Liberia',
    'ci': 'Ivory Coast',
    'ng': 'Nigeria',
    
    # Oceania
    'au': 'Australia',
    'nz': 'New Zealand',
    'fj': 'Fiji',
    'pg': 'Papua New Guinea',
    'sb': 'Solomon Islands',
    'vu': 'Vanuatu',
    'nc': 'New Caledonia',
    'pf': 'French Polynesia',
    'ws': 'Samoa',
    'to': 'Tonga',
    'ki': 'Kiribati',
    'tv': 'Tuvalu',
    'nr': 'Nauru',
    'pw': 'Palau',
    'fm': 'Micronesia',
    'mh': 'Marshall Islands',
    'nf': 'Norfolk Island',
    'pn': 'Pitcairn Islands',
    'cc': 'Cocos (Keeling) Islands',
    'cx': 'Christmas Island',
    'ck': 'Cook Islands',
    'nu': 'Niue',
    'tk': 'Tokelau',
    'wf': 'Wallis and Futuna',
    'sh': 'Saint Helena, Ascension and Tristan da Cunha',
    'ac': 'Ascension Island',
    'ta': 'Tristan da Cunha',
    
    # Other territories
    'io': 'British Indian Ocean Territory',
    'bv': 'Bouvet Island',
    'hm': 'Heard Island and McDonald Islands',
    'tf': 'French Southern Territories',
    'aq': 'Antarctica'
}

# Default country code (US)
DEFAULT_COUNTRY_CODE = 'us'

# Internal Kubernetes service URL for self-hosted Nominatim (elect.info cluster)
NOMINATIM_INTERNAL_URL = 'http://nominatim.nominatim.svc.cluster.local:80'

GEOCODER_CONFIG = {
    'user_agent': 'geocoding_application_v1.0', 
    'timeout': 10, 
    'country_codes': DEFAULT_COUNTRY_CODE, 
    'rate_limit_seconds': 1
}


def get_country_name(country_code):
    """
    Get the full country name from a country code.
    
    Args:
        country_code: Two-letter country code (e.g., 'us', 'gb', 'ca')
        
    Returns:
        str: Full country name or the code if not found
    """
    return COUNTRY_CODES.get(country_code.lower(), country_code)


def get_country_code(country_name):
    """
    Get the country code from a country name.
    
    Args:
        country_name: Full country name (e.g., 'United States', 'Canada')
        
    Returns:
        str: Two-letter country code or None if not found
    """
    for code, name in COUNTRY_CODES.items():
        if name.lower() == country_name.lower():
            return code
    return None


def list_countries():
    """
    Get a list of all available countries with their codes.
    
    Returns:
        dict: Dictionary mapping country codes to country names
    """
    return COUNTRY_CODES.copy()


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


def get_coordinates(query_address, country_codes=None, max_retries=3, server_url=None):
    """
    Get coordinates (latitude, longitude) for an address using Nominatim.
    Returns a tuple of (latitude, longitude) or None if geocoding fails.

    Args:
        query_address: The address to geocode
        country_codes: Optional country code filter (defaults to US)
        max_retries: Maximum number of retry attempts
        server_url: Optional custom Nominatim server URL (e.g.,
            "http://nominatim.nominatim.svc.cluster.local" for self-hosted).
            Defaults to None (public OSM Nominatim).

    Returns:
        tuple: (latitude, longitude) or None if geocoding fails
    """
    try:
        result_json = use_nominatim_geocoder(
            query_address, country_codes=country_codes,
            max_retries=max_retries, server_url=server_url,
        )
        if result_json:
            data = json.loads(result_json)
            lat = data.get('nominatim_lat')
            lng = data.get('nominatim_lng')
            if lat and lng:
                return (float(lat), float(lng))
        return None
    except Exception as e:
        log_error(f"Geocoding failed for {query_address}: {e}")
        return None


def use_nominatim_geocoder(query_address, id=None, country_codes=None,
    max_retries=3, server_url=None):
    """
    Geocode an address using Nominatim with proper rate limiting and error handling.
    Returns the result as a JSON string for Spark UDF compatibility.

    Args:
        query_address: The address to geocode
        id: An identifier for tracking
        country_codes: Optional country code filter (defaults to US)
        max_retries: Number of retry attempts for transient errors
        server_url: Optional custom Nominatim server URL (e.g.,
            "http://nominatim.nominatim.svc.cluster.local" for self-hosted).
            Defaults to None (public OSM Nominatim with rate limiting).
            When set, rate limiting is skipped (self-hosted servers
            don't require it).

    Returns:
        JSON string of geocoding result or None if failed
    """
    log_debug(f'Geocoding address: {query_address}')
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
    # Build geocoder — use custom server domain if provided
    geocoder_kwargs = {
        'user_agent': GEOCODER_CONFIG.get('user_agent'),
        'timeout': GEOCODER_CONFIG.get('timeout'),
    }
    if server_url:
        # Strip protocol for geopy's domain parameter
        domain = server_url.replace('http://', '').replace('https://', '').rstrip('/')
        geocoder_kwargs['domain'] = domain
        geocoder_kwargs['scheme'] = 'https' if server_url.startswith('https') else 'http'
    geocoder = Nominatim(**geocoder_kwargs)
    for attempt in range(max_retries):
        try:
            # Skip rate limiting for self-hosted servers
            if not server_url:
                time.sleep(GEOCODER_CONFIG.get('rate_limit_seconds'))
            else:
                time.sleep(0.05)  # Minimal delay for self-hosted
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
            message = f'Unexpected error during geocoding: {str(e)}'
            log_error(message)
            return None
    return None


class NominatimGeoClassifier:
    """
    A classifier for geocoding results using Nominatim.
    Provides methods to categorize and analyze geocoding results.
    """
    
    def __init__(self):
        self.place_rank_dict = {
            0: 'Country',
            1: 'State',
            2: 'County',
            3: 'City',
            4: 'Town',
            5: 'Village',
            6: 'Hamlet',
            7: 'Suburb',
            8: 'Neighbourhood',
            9: 'Street',
            10: 'Building'
        }
        
        self.importance_dict = {
            0.9: 'Country',
            0.8: 'State',
            0.7: 'County',
            0.6: 'City',
            0.5: 'Town',
            0.4: 'Village',
            0.3: 'Hamlet',
            0.2: 'Suburb',
            0.1: 'Neighbourhood',
            0.05: 'Street',
            0.01: 'Building'
        }

    def get_place_ranks_by_label(self, label):
        """
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
        """
        return self.place_rank_dict.get(label, [])

    def get_importance_threshold_by_label(self, label):
        """
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
        """
        for k, v in self.importance_dict.items():
            if v == label:
                return k
        return None

    def to_json(self):
        """
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
        """
        return json.dumps({
            'place_ranks': self.place_rank_dict,
            'importance_thresholds': self.importance_dict
        })

    def from_json(self, json_string):
        """
        Utility function: from json.

        Part of Siege Utilities Utilities module.
        Auto-discovered and available at package level.

        Returns:
            Description needed

        Example:
            >>> import siege_utilities
            >>> result = siege_utilities.from_json()
            >>> print(result)

        Note:
            This function is auto-discovered and available without imports
            across all siege_utilities modules.
        """
        data = json.loads(json_string)
        self.place_rank_dict = data.get('place_ranks', {})
        self.importance_dict = data.get('importance_thresholds', {})
        return self


# =============================================================================
# Geocode validation (Pandas)
# =============================================================================

def _get_crs_bounds(crs) -> Tuple[float, float, float, float]:
    """Extract (lat_min, lat_max, lon_min, lon_max) from a CRS.

    Uses pyproj's ``area_of_use`` when available, falling back to WGS84
    geographic bounds (-90..90, -180..180).

    Parameters:
        crs: A pyproj CRS, an EPSG integer, or a string accepted by
             ``pyproj.CRS.from_user_input``.

    Returns:
        (lat_min, lat_max, lon_min, lon_max) tuple.
    """
    try:
        from pyproj import CRS as ProjCRS

        if not isinstance(crs, ProjCRS):
            crs = ProjCRS.from_user_input(crs)
        aou = crs.area_of_use
        if aou is not None:
            return (aou.south, aou.north, aou.west, aou.east)
    except Exception:
        pass
    return (-90.0, 90.0, -180.0, 180.0)


def validate_geocode_data_pandas(
    df: pd.DataFrame,
    lat_col: str,
    lon_col: str,
    crs=None,
) -> pd.DataFrame:
    """Filter rows with invalid geographic coordinates.

    Pandas equivalent of ``spark_utils.validate_geocode_data()``.

    Parameters:
        df: Input DataFrame.
        lat_col: Name of the latitude column.
        lon_col: Name of the longitude column.
        crs: Optional CRS (pyproj CRS, EPSG int, or string).  When supplied,
             the valid coordinate bounds are derived from the CRS area of use.
             Defaults to WGS84 (-90..90, -180..180).

    Returns:
        DataFrame with only rows whose coordinates fall within the valid range.
    """
    lat_min, lat_max, lon_min, lon_max = _get_crs_bounds(crs) if crs else (-90, 90, -180, 180)
    mask = (
        df[lat_col].notna()
        & df[lon_col].notna()
        & df[lat_col].between(lat_min, lat_max)
        & df[lon_col].between(lon_min, lon_max)
    )
    return df[mask].reset_index(drop=True)


def mark_valid_geocode_data_pandas(
    df: pd.DataFrame,
    lat_col: str,
    lon_col: str,
    output_col: str = "is_valid",
    crs=None,
) -> pd.DataFrame:
    """Add a boolean validity column without removing rows.

    Pandas equivalent of ``spark_utils.mark_valid_geocode_data()``.

    Parameters:
        df: Input DataFrame.
        lat_col: Name of the latitude column.
        lon_col: Name of the longitude column.
        output_col: Name of the boolean column to add.
        crs: Optional CRS (pyproj CRS, EPSG int, or string).  When supplied,
             the valid coordinate bounds are derived from the CRS area of use.
             Defaults to WGS84 (-90..90, -180..180).

    Returns:
        Copy of *df* with *output_col* appended.
    """
    lat_min, lat_max, lon_min, lon_max = _get_crs_bounds(crs) if crs else (-90, 90, -180, 180)
    result = df.copy()
    result[output_col] = (
        result[lat_col].notna()
        & result[lon_col].notna()
        & result[lat_col].between(lat_min, lat_max)
        & result[lon_col].between(lon_min, lon_max)
    )
    return result


# =============================================================================
# SpatiaLite Geocoding Cache
# =============================================================================

_DEFAULT_CACHE_PATH = os.path.expanduser("~/.cache/siege_utilities/geocode_cache.db")


def _address_hash(address: str) -> str:
    """Deterministic SHA-256 hash of a normalized address string."""
    normalized = " ".join(address.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class SpatiaLiteCache:
    """SpatiaLite-backed local cache for geocoding results and boundary lookups.

    Stores:
    - geocode results: address_hash → (lat, lon, WKT point, source, timestamp)
    - boundary lookups: geoid → (point WKT, boundary WKT, vintage_year)
    - crosswalk mappings: (source_geoid, target_geoid) → weight

    Spatial index on point geometry enables bounding-box queries.
    The database file is portable across machines.

    Usage::

        cache = SpatiaLiteCache()
        cache.put_geocode("123 Main St, Springfield, IL 62701", 39.7817, -89.6501, source="nominatim")
        result = cache.get_geocode("123 Main St, Springfield, IL 62701")
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _DEFAULT_CACHE_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            # Try to load SpatiaLite extension
            try:
                self._conn.enable_load_extension(True)
                self._conn.load_extension("mod_spatialite")
            except Exception:
                # SpatiaLite not available — fall back to plain SQLite
                # Spatial index won't work, but the cache is still functional
                pass
        return self._conn

    def _init_db(self):
        conn = self._get_conn()
        cur = conn.cursor()

        # Check if SpatiaLite is available
        try:
            cur.execute("SELECT spatialite_version()")
            has_spatialite = True
        except sqlite3.OperationalError:
            has_spatialite = False

        # Geocode results table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS geocode_cache (
                address_hash TEXT PRIMARY KEY,
                address_raw TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                point_wkt TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'nominatim',
                raw_response TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # Boundary lookup table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS boundary_cache (
                geoid TEXT NOT NULL,
                vintage_year INTEGER NOT NULL,
                point_wkt TEXT,
                boundary_wkt TEXT,
                source TEXT NOT NULL DEFAULT 'tiger',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (geoid, vintage_year)
            )
        """)

        # Crosswalk mapping table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crosswalk_cache (
                source_geoid TEXT NOT NULL,
                target_geoid TEXT NOT NULL,
                weight REAL NOT NULL DEFAULT 1.0,
                source TEXT NOT NULL DEFAULT 'census',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (source_geoid, target_geoid)
            )
        """)

        # Indexes
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_geocode_source
            ON geocode_cache(source)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_geocode_lat_lon
            ON geocode_cache(latitude, longitude)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_boundary_vintage
            ON boundary_cache(vintage_year)
        """)

        conn.commit()

    # ------------------------------------------------------------------
    # Geocode cache operations
    # ------------------------------------------------------------------

    def put_geocode(
        self,
        address: str,
        latitude: float,
        longitude: float,
        source: str = "nominatim",
        raw_response: Optional[str] = None,
    ) -> str:
        """Store a geocoding result. Returns the address hash."""
        addr_hash = _address_hash(address)
        point_wkt = f"POINT({longitude} {latitude})"
        now = datetime.utcnow().isoformat()

        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO geocode_cache
                (address_hash, address_raw, latitude, longitude, point_wkt,
                 source, raw_response, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (addr_hash, address, latitude, longitude, point_wkt,
             source, raw_response, now, now),
        )
        conn.commit()
        return addr_hash

    def get_geocode(self, address: str) -> Optional[Dict]:
        """Look up a cached geocoding result by address string."""
        addr_hash = _address_hash(address)
        conn = self._get_conn()
        row = conn.execute(
            """
            SELECT address_raw, latitude, longitude, point_wkt, source,
                   raw_response, created_at, updated_at
            FROM geocode_cache WHERE address_hash = ?
            """,
            (addr_hash,),
        ).fetchone()

        if row is None:
            return None

        return {
            "address": row[0],
            "latitude": row[1],
            "longitude": row[2],
            "point_wkt": row[3],
            "source": row[4],
            "raw_response": row[5],
            "created_at": row[6],
            "updated_at": row[7],
        }

    def get_geocode_or_fetch(
        self,
        address: str,
        country_codes: Optional[str] = None,
        server_url: Optional[str] = None,
    ) -> Optional[Dict]:
        """Look up cache, falling back to Nominatim if not cached."""
        cached = self.get_geocode(address)
        if cached is not None:
            return cached

        result_json = use_nominatim_geocoder(
            address, country_codes=country_codes, server_url=server_url,
        )
        if result_json is None:
            return None

        data = json.loads(result_json)
        lat = data.get("nominatim_lat")
        lon = data.get("nominatim_lng")
        if lat is None or lon is None:
            return None

        self.put_geocode(
            address, float(lat), float(lon),
            source="nominatim", raw_response=result_json,
        )
        return self.get_geocode(address)

    def get_geocodes_in_bbox(
        self,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
    ) -> List[Dict]:
        """Return all cached geocodes within a bounding box."""
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT address_raw, latitude, longitude, point_wkt, source,
                   created_at
            FROM geocode_cache
            WHERE latitude BETWEEN ? AND ?
              AND longitude BETWEEN ? AND ?
            """,
            (lat_min, lat_max, lon_min, lon_max),
        ).fetchall()

        return [
            {
                "address": r[0],
                "latitude": r[1],
                "longitude": r[2],
                "point_wkt": r[3],
                "source": r[4],
                "created_at": r[5],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Boundary cache operations
    # ------------------------------------------------------------------

    def put_boundary(
        self,
        geoid: str,
        vintage_year: int,
        point_wkt: Optional[str] = None,
        boundary_wkt: Optional[str] = None,
        source: str = "tiger",
    ):
        """Cache a boundary lookup result."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO boundary_cache
                (geoid, vintage_year, point_wkt, boundary_wkt, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (geoid, vintage_year, point_wkt, boundary_wkt, source,
             datetime.utcnow().isoformat()),
        )
        conn.commit()

    def get_boundary(
        self, geoid: str, vintage_year: int,
    ) -> Optional[Dict]:
        """Look up a cached boundary by GEOID and vintage year."""
        conn = self._get_conn()
        row = conn.execute(
            """
            SELECT geoid, vintage_year, point_wkt, boundary_wkt, source, created_at
            FROM boundary_cache WHERE geoid = ? AND vintage_year = ?
            """,
            (geoid, vintage_year),
        ).fetchone()

        if row is None:
            return None

        return {
            "geoid": row[0],
            "vintage_year": row[1],
            "point_wkt": row[2],
            "boundary_wkt": row[3],
            "source": row[4],
            "created_at": row[5],
        }

    # ------------------------------------------------------------------
    # Crosswalk cache operations
    # ------------------------------------------------------------------

    def put_crosswalk(
        self,
        source_geoid: str,
        target_geoid: str,
        weight: float = 1.0,
        source: str = "census",
    ):
        """Cache a crosswalk mapping."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO crosswalk_cache
                (source_geoid, target_geoid, weight, source, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (source_geoid, target_geoid, weight, source,
             datetime.utcnow().isoformat()),
        )
        conn.commit()

    def get_crosswalk(
        self, source_geoid: str,
    ) -> List[Dict]:
        """Get all crosswalk targets for a source GEOID."""
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT source_geoid, target_geoid, weight, source
            FROM crosswalk_cache WHERE source_geoid = ?
            """,
            (source_geoid,),
        ).fetchall()

        return [
            {
                "source_geoid": r[0],
                "target_geoid": r[1],
                "weight": r[2],
                "source": r[3],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, int]:
        """Return row counts for all cache tables."""
        conn = self._get_conn()
        return {
            "geocodes": conn.execute("SELECT COUNT(*) FROM geocode_cache").fetchone()[0],
            "boundaries": conn.execute("SELECT COUNT(*) FROM boundary_cache").fetchone()[0],
            "crosswalks": conn.execute("SELECT COUNT(*) FROM crosswalk_cache").fetchone()[0],
        }

    def clear(self, table: Optional[str] = None):
        """Clear cache tables. If table is None, clear all."""
        conn = self._get_conn()
        tables = [table] if table else ["geocode_cache", "boundary_cache", "crosswalk_cache"]
        for t in tables:
            conn.execute(f"DELETE FROM {t}")  # noqa: S608 — table names are hardcoded
        conn.commit()

    def close(self):
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
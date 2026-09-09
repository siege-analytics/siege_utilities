"""Stdlib-only geocoding constants and helper contracts."""

from __future__ import annotations

from typing import Optional

__all__ = [
    "GeocodingError",
    "COUNTRY_CODES",
    "DEFAULT_COUNTRY_CODE",
    "NOMINATIM_INTERNAL_URL",
    "get_country_name",
    "get_country_code",
    "list_countries",
    "concatenate_addresses",
]


class GeocodingError(RuntimeError):
    """Raised when Nominatim geocoding fails for reasons other than 'no match'.

    Covers network timeouts (after retries exhausted), service errors,
    parse errors, and other unexpected failures from the geocoder.
    Distinct from a legitimate "no result found" outcome, which still
    returns ``None``. Use ``__cause__`` to inspect the underlying
    exception.

    Mirrors
    :class:`siege_utilities.geo.providers.census_geocoder.CensusGeocodeError`.
    """


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

def get_country_name(country_code) -> Optional[str]:
    """
    Get the full country name from a country code.

    Args:
        country_code: Two-letter country code (e.g., 'us', 'gb', 'ca'), or
            ``None`` for missing data.

    Returns:
        Full country name, the original unknown string, or ``None`` when the
        input is ``None``.
    """
    if country_code is None:
        return None
    if not isinstance(country_code, str):
        raise TypeError("country_code must be a string or None")
    return COUNTRY_CODES.get(country_code.lower(), country_code)


def get_country_code(country_name) -> Optional[str]:
    """
    Get the country code from a country name.

    Args:
        country_name: Full country name (e.g., 'United States', 'Canada'), or
            ``None`` for missing data.

    Returns:
        Two-letter country code, or None if not found/missing.
    """
    if country_name is None:
        return None
    if not isinstance(country_name, str):
        raise TypeError("country_name must be a string or None")
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
    for component in (street, city, state_province_area, postal_code, country):
        if component is None:
            continue
        value = str(component).strip()
        if value:
            components.append(value)
    return ', '.join(components)

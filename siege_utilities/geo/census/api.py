"""
HTTP transport, caching, and response processing for Census API queries.

Handles all I/O: network requests, file/Django caching, rate limiting,
retry logic, and DataFrame post-processing.
"""

import hashlib
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

import pandas as pd
import requests

from siege_utilities.config import (
    CENSUS_API_BASE_URL,
    get_service_timeout,
    CENSUS_RETRY_ATTEMPTS,
)
from siege_utilities.config.user_config import get_user_config
from .variable_registry import VariableRegistry
from .dataset_selector import DatasetSelector

log = logging.getLogger(__name__)

# Cache timeout for API responses (24 hours, matches geometry cache)
CENSUS_API_CACHE_TIMEOUT = 86400  # seconds

# Default API timeout
CENSUS_API_DEFAULT_TIMEOUT = 30  # seconds

# Rate limit handling
CENSUS_API_RATE_LIMIT_RETRY_DELAY = 60  # seconds


class CensusAPI:
    """
    HTTP transport layer for Census Bureau API.

    Responsibilities: API key resolution, request building, retry/rate-limit
    handling, caching (parquet or Django), and response normalization.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        cache_dir: Optional[Union[str, Path]] = None,
        cache_backend: str = 'parquet',
        cache_ttl: int = CENSUS_API_CACHE_TIMEOUT,
    ):
        self.api_key = self._resolve_api_key(api_key)
        self.timeout = timeout or get_service_timeout('census_api') or CENSUS_API_DEFAULT_TIMEOUT
        self.base_url = CENSUS_API_BASE_URL
        self.cache_backend = cache_backend
        self.cache_ttl = cache_ttl
        self._registry = VariableRegistry()

        # Setup cache directory (parquet backend only)
        if cache_backend == 'parquet':
            if cache_dir:
                self.cache_dir = Path(cache_dir)
            else:
                self.cache_dir = Path.home() / '.siege_utilities' / 'cache' / 'census_api'
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.cache_dir = None

        log.info(
            f"Initialized CensusAPI "
            f"(API key: {'provided' if self.api_key else 'not set'}, "
            f"cache: {cache_backend})"
        )

    # ------------------------------------------------------------------
    # API key resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_api_key(explicit_key: Optional[str]) -> Optional[str]:
        """Resolve API key: explicit → UserProfile → env → None."""
        if explicit_key:
            return explicit_key

        try:
            user_config = get_user_config()
            profile_key = user_config.get_api_key('census')
            if profile_key:
                return profile_key
        except Exception as e:
            log.debug(f"Could not get API key from user profile: {e}")

        env_key = os.environ.get('CENSUS_API_KEY')
        if env_key:
            return env_key

        return None

    # ------------------------------------------------------------------
    # Core fetch
    # ------------------------------------------------------------------

    def fetch_data(
        self,
        variables: Union[str, List[str]],
        year: int,
        dataset: str = 'acs5',
        geography: str = 'county',
        state_fips: Optional[str] = None,
        county_fips: Optional[str] = None,
        include_moe: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch demographic data from the Census API.

        Delegates variable resolution to VariableRegistry and geography
        validation to DatasetSelector, then handles the HTTP round-trip.
        """
        # Resolve variables via registry
        var_list = self._registry.resolve_variables(variables)

        if include_moe and dataset.startswith('acs'):
            var_list = self._registry.add_moe_variables(var_list)

        # Validate geography via selector
        geography = DatasetSelector.validate_geography(geography, state_fips, county_fips)

        if state_fips:
            state_fips = DatasetSelector.normalize_state(state_fips)

        # Check cache
        cache_key = self._generate_cache_key(var_list, year, dataset, geography, state_fips, county_fips)
        cached_df = self._get_from_cache(cache_key)
        if cached_df is not None:
            log.info(f"Returning cached data for {geography} ({len(cached_df)} rows)")
            return cached_df

        # Build URL
        url = self._build_url(var_list, year, dataset, geography, state_fips, county_fips)

        # Request with retry
        df = self._make_request_with_retry(url)

        # Process response
        df = self._process_response(df, geography, state_fips, county_fips)

        # Cache
        self._save_to_cache(cache_key, df)

        log.info(f"Fetched {len(df)} rows of {geography}-level data for year {year}")
        return df

    # ------------------------------------------------------------------
    # URL building
    # ------------------------------------------------------------------

    def _build_url(
        self,
        variables: List[str],
        year: int,
        dataset: str,
        geography: str,
        state_fips: Optional[str],
        county_fips: Optional[str],
    ) -> str:
        dataset_path = DatasetSelector.get_dataset_path(year, dataset)
        var_str = ','.join(['NAME'] + variables)
        geo_clause = DatasetSelector.build_geography_clause(geography, state_fips, county_fips)

        url = f"{self.base_url}/{dataset_path}?get={var_str}&{geo_clause}"

        if self.api_key:
            url += f"&key={self.api_key}"

        return url

    # ------------------------------------------------------------------
    # HTTP + retry
    # ------------------------------------------------------------------

    def _make_request_with_retry(self, url: str) -> pd.DataFrame:
        last_exception = None

        for attempt in range(CENSUS_RETRY_ATTEMPTS):
            try:
                log.debug(f"Making Census API request (attempt {attempt + 1})")
                response = requests.get(url, timeout=self.timeout)

                if response.status_code == 429:
                    from siege_utilities.geo.census_api_client import CensusRateLimitError
                    raise CensusRateLimitError("Census API rate limit exceeded")

                response.raise_for_status()

                data = response.json()

                if not data or len(data) < 2:
                    from siege_utilities.exceptions import SiegeAPIError, handle_error
                    return handle_error(
                        SiegeAPIError("Census API returned empty response (< 2 rows)"),
                        on_error=getattr(self, '_on_error', 'skip'),
                        fallback=pd.DataFrame(),
                        context="Census API query",
                    )

                df = pd.DataFrame(data[1:], columns=data[0])
                return df

            except Exception as e:
                from siege_utilities.geo.census_api_client import (
                    CensusRateLimitError, CensusAPIError,
                )
                if isinstance(e, CensusRateLimitError):
                    log.warning(f"Rate limit hit, waiting {CENSUS_API_RATE_LIMIT_RETRY_DELAY}s...")
                    time.sleep(CENSUS_API_RATE_LIMIT_RETRY_DELAY)
                    last_exception = CensusRateLimitError("Census API rate limit exceeded after retries")
                elif isinstance(e, requests.exceptions.Timeout):
                    log.warning(f"Request timeout (attempt {attempt + 1})")
                    last_exception = CensusAPIError("Census API request timed out")
                    time.sleep(2 ** attempt)
                elif isinstance(e, requests.exceptions.RequestException):
                    log.warning(f"Request failed: {e}")
                    last_exception = CensusAPIError(f"Census API request failed: {e}")
                    time.sleep(2 ** attempt)
                elif isinstance(e, ValueError):
                    log.error(f"Failed to parse API response: {e}")
                    raise CensusAPIError(f"Invalid API response: {e}")
                else:
                    raise

        if last_exception:
            raise last_exception
        from siege_utilities.geo.census_api_client import CensusAPIError as _CAE
        raise _CAE("Census API request failed after all retries")

    # ------------------------------------------------------------------
    # Response processing
    # ------------------------------------------------------------------

    def _process_response(
        self,
        df: pd.DataFrame,
        geography: str,
        state_fips: Optional[str],
        county_fips: Optional[str],
    ) -> pd.DataFrame:
        if df.empty:
            return df

        df = self._construct_geoid(df, geography)
        df = self._convert_numeric_columns(df)

        cols = df.columns.tolist()
        priority_cols = ['GEOID', 'NAME']
        other_cols = [c for c in cols if c not in priority_cols]
        df = df[priority_cols + other_cols]

        return df

    @staticmethod
    def _construct_geoid(df: pd.DataFrame, geography: str) -> pd.DataFrame:
        if geography == 'state':
            df['GEOID'] = df['state']
        elif geography == 'county':
            df['GEOID'] = df['state'] + df['county']
        elif geography == 'tract':
            df['GEOID'] = df['state'] + df['county'] + df['tract']
        elif geography == 'block_group':
            df['GEOID'] = df['state'] + df['county'] + df['tract'] + df['block group']
        elif geography == 'place':
            df['GEOID'] = df['state'] + df['place']
        elif geography == 'zcta':
            zcta_col = None
            for col in df.columns:
                if 'zip' in col.lower() or 'zcta' in col.lower():
                    zcta_col = col
                    break
            if zcta_col:
                df['GEOID'] = df[zcta_col]
            else:
                df['GEOID'] = ''

        cols_to_drop = ['state', 'county', 'tract', 'block group', 'place']
        cols_to_drop = [c for c in cols_to_drop if c in df.columns]
        df = df.drop(columns=cols_to_drop, errors='ignore')

        return df

    @staticmethod
    def _convert_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
        skip_cols = {'GEOID', 'NAME'}
        for col in df.columns:
            if col in skip_cols:
                continue
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception:
                pass
        return df

    # ------------------------------------------------------------------
    # Caching
    # ------------------------------------------------------------------

    def _generate_cache_key(
        self,
        variables: List[str],
        year: int,
        dataset: str,
        geography: str,
        state_fips: Optional[str],
        county_fips: Optional[str],
    ) -> str:
        key_parts = [
            ','.join(sorted(variables)),
            str(year),
            dataset,
            geography,
            state_fips or '',
            county_fips or '',
        ]
        key_str = '|'.join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        if self.cache_backend == 'django':
            return self._django_cache_get(cache_key)
        return self._parquet_cache_get(cache_key)

    def _save_to_cache(self, cache_key: str, df: pd.DataFrame) -> None:
        if self.cache_backend == 'django':
            return self._django_cache_set(cache_key, df)
        return self._parquet_cache_set(cache_key, df)

    def _parquet_cache_get(self, cache_key: str) -> Optional[pd.DataFrame]:
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        if not cache_file.exists():
            return None

        file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - file_mtime > timedelta(seconds=self.cache_ttl):
            log.debug(f"Cache expired for {cache_key}")
            cache_file.unlink()
            return None

        try:
            return pd.read_parquet(cache_file)
        except Exception as e:
            log.warning(f"Failed to read cache file: {e}")
            return None

    def _parquet_cache_set(self, cache_key: str, df: pd.DataFrame) -> None:
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        try:
            df.to_parquet(cache_file, index=False)
            log.debug(f"Cached data to {cache_file}")
        except Exception as e:
            log.warning(f"Failed to cache data: {e}")

    def _django_cache_get(self, cache_key: str) -> Optional[pd.DataFrame]:
        try:
            from django.core.cache import cache
            data = cache.get(f"census_api:{cache_key}")
            if data is not None:
                log.debug(f"Django cache hit for {cache_key}")
                return pd.DataFrame(data)
            return None
        except Exception as e:
            log.warning(f"Django cache get failed: {e}")
            return None

    def _django_cache_set(self, cache_key: str, df: pd.DataFrame) -> None:
        try:
            from django.core.cache import cache
            cache.set(
                f"census_api:{cache_key}",
                df.to_dict(orient='list'),
                timeout=self.cache_ttl,
            )
            log.debug(f"Django cache set for {cache_key}")
        except Exception as e:
            log.warning(f"Django cache set failed: {e}")

    def clear_cache(self) -> None:
        """Clear all cached API responses."""
        if self.cache_dir is None:
            return
        try:
            for cache_file in self.cache_dir.glob('*.parquet'):
                cache_file.unlink()
            log.info("Cleared Census API cache")
        except Exception as e:
            log.warning(f"Failed to clear cache: {e}")

    # ------------------------------------------------------------------
    # Variable metadata (delegates to registry)
    # ------------------------------------------------------------------

    def get_variable_metadata(
        self, variable: str, year: int, dataset: str = 'acs5',
    ) -> Dict[str, Any]:
        return self._registry.get_variable_metadata(
            variable, year, dataset, base_url=self.base_url, timeout=self.timeout,
        )

    def list_available_variables(
        self, year: int, dataset: str = 'acs5', search: Optional[str] = None,
    ) -> pd.DataFrame:
        return self._registry.list_available_variables(
            year, dataset, search, base_url=self.base_url, timeout=self.timeout,
        )

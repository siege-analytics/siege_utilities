"""
Dataset selection and geography validation for Census API queries.

Pure logic — no I/O, no network calls. Fully unit-testable without mocks.
"""

from typing import Optional


class DatasetSelector:
    """
    Handles dataset path resolution and geography validation/normalization
    for Census API queries. All methods are stateless class/static methods.
    """

    # Supported Census API geography levels
    API_SUPPORTED_GEOGRAPHIES = frozenset({
        'state', 'county', 'tract', 'block_group', 'place', 'zcta',
    })

    @staticmethod
    def get_dataset_path(year: int, dataset: str) -> str:
        """
        Map a dataset identifier + year to the Census API URL path segment.

        Args:
            year: Census year (e.g. 2020)
            dataset: One of 'acs5', 'acs1', 'dec', 'pep'

        Returns:
            URL path segment, e.g. '2020/acs/acs5'

        Raises:
            ValueError: If dataset is unknown.
        """
        dataset_paths = {
            'acs5': f'{year}/acs/acs5',
            'acs1': f'{year}/acs/acs1',
            'dec': f'{year}/dec/pl',
            'pep': f'{year}/pep/population',
        }

        if dataset not in dataset_paths:
            raise ValueError(
                f"Unknown dataset '{dataset}'. Valid options: {list(dataset_paths.keys())}"
            )

        return dataset_paths[dataset]

    @classmethod
    def validate_geography(
        cls,
        geography: str,
        state_fips: Optional[str],
        county_fips: Optional[str],
    ) -> str:
        """
        Validate and normalize a geography string to its canonical form.

        Args:
            geography: Raw geography level (may be an alias like 'bg')
            state_fips: State FIPS code (required for tract/block_group)
            county_fips: County FIPS code

        Returns:
            Canonical geography string (e.g. 'block_group')

        Raises:
            ValueError: If geography is invalid or required FIPS codes are missing.
        """
        from siege_utilities.config.census_constants import resolve_geographic_level

        try:
            canonical = resolve_geographic_level(geography)
        except ValueError:
            raise ValueError(
                f"Invalid geography '{geography}'. "
                f"Valid options: {sorted(cls.API_SUPPORTED_GEOGRAPHIES)}"
            )

        if canonical not in cls.API_SUPPORTED_GEOGRAPHIES:
            raise ValueError(
                f"Census API does not support geography '{geography}' "
                f"(resolved to '{canonical}'). "
                f"Supported: {sorted(cls.API_SUPPORTED_GEOGRAPHIES)}"
            )

        if canonical in ('tract', 'block_group') and not state_fips:
            raise ValueError(
                f"State FIPS code is required for {canonical}-level data"
            )

        if county_fips and not state_fips:
            raise ValueError(
                "County FIPS requires state FIPS to be specified"
            )

        return canonical

    @staticmethod
    def build_geography_clause(
        geography: str,
        state_fips: Optional[str],
        county_fips: Optional[str],
    ) -> str:
        """
        Build the ``for=``/``in=`` geography clause for the Census API URL.

        Args:
            geography: Canonical geography level (already validated)
            state_fips: State FIPS code
            county_fips: County FIPS code

        Returns:
            URL query-string fragment, e.g. ``for=county:*&in=state:06``
        """
        if geography == 'state':
            if state_fips:
                return f"for=state:{state_fips}"
            return "for=state:*"

        elif geography == 'county':
            if county_fips and state_fips:
                return f"for=county:{county_fips}&in=state:{state_fips}"
            elif state_fips:
                return f"for=county:*&in=state:{state_fips}"
            return "for=county:*"

        elif geography == 'tract':
            if county_fips:
                return f"for=tract:*&in=state:{state_fips}%20county:{county_fips}"
            return f"for=tract:*&in=state:{state_fips}"

        elif geography == 'block_group':
            if county_fips:
                return f"for=block%20group:*&in=state:{state_fips}%20county:{county_fips}"
            return f"for=block%20group:*&in=state:{state_fips}"

        elif geography == 'place':
            if state_fips:
                return f"for=place:*&in=state:{state_fips}"
            return "for=place:*"

        elif geography == 'zcta':
            return "for=zip%20code%20tabulation%20area:*"

        raise ValueError(f"Unsupported geography: {geography}")

    @staticmethod
    def normalize_state(state_input: str) -> str:
        """
        Normalize a state name, abbreviation, or FIPS code to its FIPS code.

        Raises:
            ValueError: If the state cannot be resolved.
        """
        from siege_utilities.config import normalize_state_identifier
        return normalize_state_identifier(state_input)

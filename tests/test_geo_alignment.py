"""
Cross-structure alignment tests for the geo module.

Verifies that all 10 interconnected geographic data structures stay in sync
with CANONICAL_GEOGRAPHIC_LEVELS as the single source of truth.

These tests catch drift between structures — e.g., if someone adds a canonical
level but forgets to update the enum, GEOGRAPHIC_LEVELS, or TIGER_FILE_PATTERNS.
"""

import pandas as pd

from siege_utilities.config.census_constants import (
    CANONICAL_GEOGRAPHIC_LEVELS,
    resolve_geographic_level,
    GEOGRAPHIC_LEVELS,
    GEOGRAPHIC_HIERARCHY,
    TIGER_FILE_PATTERNS,
)
from siege_utilities.geo.census_dataset_mapper import GeographyLevel
from siege_utilities.geo.geoid_utils import (
    GEOID_LENGTHS,
    GEOID_COMPONENT_LENGTHS,
    validate_geoid,
)
from siege_utilities.geo.spatial_data import BOUNDARY_TYPE_CATALOG
from siege_utilities.geo.census_files.pl_downloader import SUMMARY_LEVELS


# =============================================================================
# CANONICAL ↔ GEOID_LENGTHS ALIGNMENT
# =============================================================================

class TestCanonicalToGEOIDLengths:
    """Verify GEOID_LENGTHS stays perfectly in sync with CANONICAL."""

    def test_keys_match_exactly(self):
        """GEOID_LENGTHS must have exactly the same keys as CANONICAL."""
        assert set(GEOID_LENGTHS.keys()) == set(CANONICAL_GEOGRAPHIC_LEVELS.keys())

    def test_values_match_canonical_geoid_length(self):
        """Every GEOID_LENGTHS value must match the canonical geoid_length."""
        for level, length in GEOID_LENGTHS.items():
            expected = CANONICAL_GEOGRAPHIC_LEVELS[level]['geoid_length']
            assert length == expected, (
                f"GEOID_LENGTHS['{level}'] = {length}, "
                f"but CANONICAL says geoid_length = {expected}"
            )

    def test_entry_counts_equal(self):
        """Both structures must have the same number of entries."""
        assert len(GEOID_LENGTHS) == len(CANONICAL_GEOGRAPHIC_LEVELS)


# =============================================================================
# GEOGRAPHIC_LEVELS ↔ CANONICAL ALIGNMENT
# =============================================================================

class TestGeographicLevelsAlignment:
    """Verify GEOGRAPHIC_LEVELS backward-compat dict stays aligned."""

    def test_all_values_are_valid_canonical_names(self):
        """Every value in GEOGRAPHIC_LEVELS must be a canonical level name."""
        for key, value in GEOGRAPHIC_LEVELS.items():
            assert value in CANONICAL_GEOGRAPHIC_LEVELS, (
                f"GEOGRAPHIC_LEVELS['{key}'] = '{value}' is not a canonical name. "
                f"Valid: {sorted(CANONICAL_GEOGRAPHIC_LEVELS.keys())}"
            )

    def test_all_canonical_names_reachable(self):
        """Every canonical name must be reachable as a value in GEOGRAPHIC_LEVELS."""
        reachable = set(GEOGRAPHIC_LEVELS.values())
        for canonical in CANONICAL_GEOGRAPHIC_LEVELS:
            assert canonical in reachable, (
                f"Canonical level '{canonical}' is not reachable from GEOGRAPHIC_LEVELS. "
                f"Add an entry like \"{canonical.upper()}\": \"{canonical}\""
            )

    def test_all_keys_are_uppercase(self):
        """All keys should be uppercase (convention for backward-compat dict)."""
        for key in GEOGRAPHIC_LEVELS:
            assert key == key.upper(), (
                f"GEOGRAPHIC_LEVELS key '{key}' should be uppercase"
            )


# =============================================================================
# GeographyLevel ENUM ↔ CANONICAL ALIGNMENT
# =============================================================================

class TestGeographyLevelEnumAlignment:
    """Verify GeographyLevel enum covers all canonical levels."""

    def test_all_enum_values_are_canonical(self):
        """Every enum member's .value must be a canonical level name."""
        for member in GeographyLevel:
            assert member.value in CANONICAL_GEOGRAPHIC_LEVELS, (
                f"GeographyLevel.{member.name} has value '{member.value}' "
                f"which is not in CANONICAL_GEOGRAPHIC_LEVELS"
            )

    def test_all_canonical_levels_in_enum(self):
        """Every canonical level must be constructable as a GeographyLevel."""
        enum_values = {m.value for m in GeographyLevel}
        for canonical in CANONICAL_GEOGRAPHIC_LEVELS:
            assert canonical in enum_values, (
                f"Canonical level '{canonical}' has no GeographyLevel enum member. "
                f"Add: {canonical.upper()} = \"{canonical}\""
            )

    def test_missing_resolves_all_canonical_aliases(self):
        """_missing_() should resolve all canonical aliases to enum members."""
        for canonical, info in CANONICAL_GEOGRAPHIC_LEVELS.items():
            for alias in info['aliases']:
                member = GeographyLevel(alias)
                assert member is not None, (
                    f"GeographyLevel('{alias}') should resolve to a member "
                    f"(canonical: '{canonical}')"
                )
                assert member.value == canonical, (
                    f"GeographyLevel('{alias}').value = '{member.value}', "
                    f"expected '{canonical}'"
                )

    def test_backward_compat_aliases_match_canonical(self):
        """Backward-compat enum aliases must resolve to correct canonical."""
        alias_expectations = {
            'COUNTY_SUBDIVISION': 'cousub',
            'CONGRESSIONAL_DISTRICT': 'cd',
            'STATE_LEGISLATIVE_DISTRICT': 'sldu',
            'ZIP_CODE': 'zcta',
            'VOTING_DISTRICT': 'vtd',
        }
        for alias_name, expected_value in alias_expectations.items():
            member = GeographyLevel[alias_name]
            assert member.value == expected_value, (
                f"GeographyLevel.{alias_name}.value = '{member.value}', "
                f"expected '{expected_value}'"
            )


# =============================================================================
# TIGER_FILE_PATTERNS ↔ CANONICAL ALIGNMENT
# =============================================================================

class TestTigerPatternsAlignment:
    """Verify TIGER_FILE_PATTERNS keys and patterns are consistent."""

    # Keys in TIGER_FILE_PATTERNS that are feature layers, not geographic levels.
    # These have valid TIGER download URLs but no GEOID structure.
    _FEATURE_LAYER_KEYS = {
        'uac', 'uac20', 'rails', 'aiannh',
        'roads', 'linear_water', 'area_water', 'edges',
        'address_features', 'pointlm', 'arealm',
        'elsd', 'scsd', 'unsd',
    }

    def test_all_keys_are_canonical_or_feature(self):
        """Every TIGER pattern key must be a canonical level or a known feature layer."""
        for key in TIGER_FILE_PATTERNS:
            assert key in CANONICAL_GEOGRAPHIC_LEVELS or key in self._FEATURE_LAYER_KEYS, (
                f"TIGER_FILE_PATTERNS key '{key}' is not a canonical level or feature layer"
            )

    def test_all_patterns_have_year_placeholder(self):
        """Every TIGER pattern must contain {year}."""
        for key, pattern in TIGER_FILE_PATTERNS.items():
            assert '{year}' in pattern, (
                f"TIGER_FILE_PATTERNS['{key}'] = '{pattern}' missing {{year}}"
            )

    def test_state_level_patterns_have_state_fips(self):
        """State-specific patterns must contain {state_fips}."""
        state_specific = {
            'cousub', 'tract', 'block_group', 'block', 'tabblock20', 'tabblock10',
            'place', 'sldu', 'sldl', 'vtd', 'vtd20', 'puma',
        }
        for key in state_specific:
            if key in TIGER_FILE_PATTERNS:
                assert '{state_fips}' in TIGER_FILE_PATTERNS[key], (
                    f"TIGER_FILE_PATTERNS['{key}'] should contain {{state_fips}} "
                    f"but has: '{TIGER_FILE_PATTERNS[key]}'"
                )

    def test_national_patterns_have_us_marker(self):
        """National-level patterns must contain '_us_'."""
        national = {'nation', 'state', 'county', 'zcta', 'cbsa'}
        for key in national:
            if key in TIGER_FILE_PATTERNS:
                assert '_us_' in TIGER_FILE_PATTERNS[key], (
                    f"TIGER_FILE_PATTERNS['{key}'] should contain '_us_' "
                    f"but has: '{TIGER_FILE_PATTERNS[key]}'"
                )


# =============================================================================
# GEOGRAPHIC_HIERARCHY ↔ CANONICAL ALIGNMENT
# =============================================================================

class TestGeographicHierarchyAlignment:
    """Verify GEOGRAPHIC_HIERARCHY is a valid subset of canonical levels."""

    def test_all_entries_are_canonical(self):
        """Every hierarchy entry must be a canonical level name."""
        for level in GEOGRAPHIC_HIERARCHY:
            assert level in CANONICAL_GEOGRAPHIC_LEVELS, (
                f"GEOGRAPHIC_HIERARCHY entry '{level}' is not a canonical level"
            )

    def test_starts_with_nation_ends_with_block(self):
        """Hierarchy must start with nation and end with block."""
        assert GEOGRAPHIC_HIERARCHY[0] == 'nation'
        assert GEOGRAPHIC_HIERARCHY[-1] == 'block'

    def test_hierarchical_chain_complete(self):
        """The standard hierarchy chain must be complete (no gaps)."""
        expected = ['nation', 'region', 'division', 'state', 'county',
                    'cousub', 'tract', 'block_group', 'block']
        assert GEOGRAPHIC_HIERARCHY == expected


# =============================================================================
# SUMMARY_LEVELS ↔ CANONICAL ALIGNMENT
# =============================================================================

class TestSummaryLevelsAlignment:
    """Verify PL downloader SUMMARY_LEVELS resolve to canonical names."""

    def test_all_keys_resolve_via_resolve_geographic_level(self):
        """Every SUMMARY_LEVELS key must resolve to a canonical name."""
        for key in SUMMARY_LEVELS:
            resolved = resolve_geographic_level(key)
            assert resolved in CANONICAL_GEOGRAPHIC_LEVELS, (
                f"SUMMARY_LEVELS key '{key}' resolves to '{resolved}' "
                f"which is not in CANONICAL"
            )

    def test_county_subdivision_resolves_to_cousub(self):
        """county_subdivision is an alias that must resolve to cousub."""
        assert resolve_geographic_level('county_subdivision') == 'cousub'

    def test_summary_level_codes_are_three_digit_strings(self):
        """All summary level codes must be 3-digit string codes."""
        for key, code in SUMMARY_LEVELS.items():
            assert isinstance(code, str), f"Code for '{key}' should be str"
            assert len(code) == 3, f"Code for '{key}' should be 3 digits, got '{code}'"
            assert code.isdigit(), f"Code for '{key}' should be all digits, got '{code}'"


# =============================================================================
# BOUNDARY_TYPE_CATALOG ↔ CANONICAL ALIGNMENT
# =============================================================================

class TestBoundaryTypeCatalogAlignment:
    """Verify BOUNDARY_TYPE_CATALOG is consistent with canonical levels."""

    # Session-specific congressional district variants (not in CANONICAL, by design)
    CD_SESSION_VARIANTS = {'cd116', 'cd117', 'cd118', 'cd119'}

    # General boundary types not in CANONICAL (features, not geographic levels)
    NON_CANONICAL_GENERAL = {
        'csa', 'metdiv', 'micro', 'necta', 'nectadiv', 'cnecta',
        'aiannh', 'aitsce', 'ttract', 'tbg', 'elsd', 'scsd', 'unsd',
        'address_features', 'linear_water', 'area_water', 'roads', 'rails',
        'edges', 'anrc', 'concity', 'submcd', 'uac', 'uac20',
    }

    def test_redistricting_entries_match_canonical(self):
        """Redistricting entries (minus CD session variants) must be canonical."""
        redistricting = {
            k for k, v in BOUNDARY_TYPE_CATALOG.items()
            if v['category'] == 'redistricting'
        }
        non_session = redistricting - self.CD_SESSION_VARIANTS
        for key in non_session:
            assert key in CANONICAL_GEOGRAPHIC_LEVELS, (
                f"Redistricting entry '{key}' is not a canonical level"
            )

    def test_entry_structure_correct(self):
        """Every catalog entry must have category, abbrev, and name."""
        for key, entry in BOUNDARY_TYPE_CATALOG.items():
            assert 'category' in entry, f"'{key}' missing 'category'"
            assert 'abbrev' in entry, f"'{key}' missing 'abbrev'"
            assert 'name' in entry, f"'{key}' missing 'name'"
            assert entry['category'] in ('redistricting', 'general'), (
                f"'{key}' has invalid category: {entry['category']}"
            )

    def test_cd_session_variants_are_cd_prefixed(self):
        """Congress-specific CD entries must start with 'cd'."""
        for key in self.CD_SESSION_VARIANTS:
            if key in BOUNDARY_TYPE_CATALOG:
                assert key.startswith('cd'), f"Session variant '{key}' should start with 'cd'"

    def test_known_canonical_levels_absent_from_catalog(self):
        """region, division, nation are not boundary types you download."""
        expected_absent = {'region', 'division', 'nation'}
        for level in expected_absent:
            assert level not in BOUNDARY_TYPE_CATALOG, (
                f"'{level}' should NOT be in BOUNDARY_TYPE_CATALOG "
                f"(it's a statistical area, not a downloadable boundary)"
            )


# =============================================================================
# GEOID_COMPONENT_LENGTHS CONSISTENCY
# =============================================================================

class TestGEOIDComponentLengthsConsistency:
    """Verify GEOID component lengths add up to full GEOID lengths."""

    def test_state_component_matches_state_geoid(self):
        """State component (2) must equal GEOID_LENGTHS['state']."""
        assert GEOID_COMPONENT_LENGTHS['state'] == GEOID_LENGTHS['state'] == 2

    def test_county_components_add_to_county_geoid(self):
        """state(2) + county(3) = county GEOID(5)."""
        total = GEOID_COMPONENT_LENGTHS['state'] + GEOID_COMPONENT_LENGTHS['county']
        assert total == GEOID_LENGTHS['county'] == 5

    def test_tract_components_add_to_tract_geoid(self):
        """state(2) + county(3) + tract(6) = tract GEOID(11)."""
        total = (GEOID_COMPONENT_LENGTHS['state'] +
                 GEOID_COMPONENT_LENGTHS['county'] +
                 GEOID_COMPONENT_LENGTHS['tract'])
        assert total == GEOID_LENGTHS['tract'] == 11

    def test_block_group_components_add(self):
        """state(2) + county(3) + tract(6) + bg(1) = block_group GEOID(12)."""
        total = (GEOID_COMPONENT_LENGTHS['state'] +
                 GEOID_COMPONENT_LENGTHS['county'] +
                 GEOID_COMPONENT_LENGTHS['tract'] +
                 GEOID_COMPONENT_LENGTHS['block_group'])
        assert total == GEOID_LENGTHS['block_group'] == 12

    def test_block_components_add_to_block_geoid(self):
        """state(2) + county(3) + tract(6) + block(4) = block GEOID(15)."""
        total = (GEOID_COMPONENT_LENGTHS['state'] +
                 GEOID_COMPONENT_LENGTHS['county'] +
                 GEOID_COMPONENT_LENGTHS['tract'] +
                 GEOID_COMPONENT_LENGTHS['block'])
        assert total == GEOID_LENGTHS['block'] == 15

    def test_place_components_add_to_place_geoid(self):
        """state(2) + place(5) = place GEOID(7)."""
        total = GEOID_COMPONENT_LENGTHS['state'] + GEOID_COMPONENT_LENGTHS['place']
        assert total == GEOID_LENGTHS['place'] == 7

    def test_all_component_keys_are_canonical(self):
        """All GEOID_COMPONENT_LENGTHS keys must be canonical level names."""
        for key in GEOID_COMPONENT_LENGTHS:
            assert key in CANONICAL_GEOGRAPHIC_LEVELS, (
                f"GEOID_COMPONENT_LENGTHS key '{key}' is not a canonical level"
            )


# =============================================================================
# CENSUS API GEOID CONSTRUCTION ALIGNMENT
# =============================================================================

class TestCensusAPIGEOIDAlignment:
    """Verify CensusAPIClient._construct_geoid produces correctly-sized GEOIDs."""

    def _make_api_df(self, geography, **columns):
        """Build a DataFrame mimicking Census API response columns."""
        return pd.DataFrame([columns])

    def test_state_geoid_length(self):
        """State GEOID from API should be 2 characters."""
        from siege_utilities.geo.census_api_client import CensusAPIClient
        client = CensusAPIClient.__new__(CensusAPIClient)
        df = self._make_api_df('state', state='06')
        result = client._construct_geoid(df, 'state')
        geoid = result['GEOID'].iloc[0]
        assert len(str(geoid)) == GEOID_LENGTHS['state'], (
            f"State GEOID '{geoid}' has length {len(str(geoid))}, expected {GEOID_LENGTHS['state']}"
        )

    def test_county_geoid_length(self):
        """County GEOID from API should be 5 characters."""
        from siege_utilities.geo.census_api_client import CensusAPIClient
        client = CensusAPIClient.__new__(CensusAPIClient)
        df = self._make_api_df('county', state='06', county='037')
        result = client._construct_geoid(df, 'county')
        geoid = result['GEOID'].iloc[0]
        assert len(str(geoid)) == GEOID_LENGTHS['county']

    def test_tract_geoid_length(self):
        """Tract GEOID from API should be 11 characters."""
        from siege_utilities.geo.census_api_client import CensusAPIClient
        client = CensusAPIClient.__new__(CensusAPIClient)
        df = self._make_api_df('tract', state='06', county='037', tract='101100')
        result = client._construct_geoid(df, 'tract')
        geoid = result['GEOID'].iloc[0]
        assert len(str(geoid)) == GEOID_LENGTHS['tract']

    def test_block_group_geoid_length(self):
        """Block group GEOID from API should be 12 characters."""
        from siege_utilities.geo.census_api_client import CensusAPIClient
        client = CensusAPIClient.__new__(CensusAPIClient)
        df = pd.DataFrame([{
            'state': '06', 'county': '037', 'tract': '101100', 'block group': '1'
        }])
        result = client._construct_geoid(df, 'block_group')
        geoid = result['GEOID'].iloc[0]
        assert len(str(geoid)) == GEOID_LENGTHS['block_group']

    def test_place_geoid_length(self):
        """Place GEOID from API should be 7 characters."""
        from siege_utilities.geo.census_api_client import CensusAPIClient
        client = CensusAPIClient.__new__(CensusAPIClient)
        df = self._make_api_df('place', state='06', place='44000')
        result = client._construct_geoid(df, 'place')
        geoid = result['GEOID'].iloc[0]
        assert len(str(geoid)) == GEOID_LENGTHS['place']

    def test_constructed_geoids_are_strings(self):
        """All constructed GEOIDs must be strings, not ints."""
        from siege_utilities.geo.census_api_client import CensusAPIClient
        client = CensusAPIClient.__new__(CensusAPIClient)
        test_cases = [
            ('state', {'state': '06'}),
            ('county', {'state': '06', 'county': '037'}),
            ('tract', {'state': '06', 'county': '037', 'tract': '101100'}),
        ]
        for geography, columns in test_cases:
            df = pd.DataFrame([columns])
            result = client._construct_geoid(df, geography)
            geoid = result['GEOID'].iloc[0]
            assert isinstance(geoid, str), (
                f"{geography} GEOID is {type(geoid).__name__}, expected str"
            )

    def test_constructed_geoids_pass_validate(self):
        """Constructed GEOIDs must pass validate_geoid()."""
        from siege_utilities.geo.census_api_client import CensusAPIClient
        client = CensusAPIClient.__new__(CensusAPIClient)
        test_cases = [
            ('state', {'state': '06'}),
            ('county', {'state': '06', 'county': '037'}),
            ('tract', {'state': '06', 'county': '037', 'tract': '101100'}),
        ]
        for geography, columns in test_cases:
            df = pd.DataFrame([columns])
            result = client._construct_geoid(df, geography)
            geoid = result['GEOID'].iloc[0]
            assert validate_geoid(geoid, geography), (
                f"Constructed {geography} GEOID '{geoid}' fails validate_geoid()"
            )


# =============================================================================
# PL DOWNLOADER GEOID CONSTRUCTION ALIGNMENT
# =============================================================================

class TestPLDownloaderGEOIDAlignment:
    """Verify PLFileDownloader._construct_geoid produces correctly-sized GEOIDs."""

    def _make_pl_df(self, **columns):
        """Build a DataFrame mimicking PL file columns (uppercase)."""
        return pd.DataFrame([columns])

    def test_pl_state_geoid_length(self):
        """PL state GEOID should be 2 characters."""
        from siege_utilities.geo.census_files.pl_downloader import PLFileDownloader
        dl = PLFileDownloader.__new__(PLFileDownloader)
        df = self._make_pl_df(STATE='06')
        result = dl._construct_geoid(df, 'state')
        assert len(result['GEOID'].iloc[0]) == GEOID_LENGTHS['state']

    def test_pl_county_geoid_length(self):
        """PL county GEOID should be 5 characters."""
        from siege_utilities.geo.census_files.pl_downloader import PLFileDownloader
        dl = PLFileDownloader.__new__(PLFileDownloader)
        df = self._make_pl_df(STATE='06', COUNTY='037')
        result = dl._construct_geoid(df, 'county')
        assert len(result['GEOID'].iloc[0]) == GEOID_LENGTHS['county']

    def test_pl_tract_geoid_length(self):
        """PL tract GEOID should be 11 characters."""
        from siege_utilities.geo.census_files.pl_downloader import PLFileDownloader
        dl = PLFileDownloader.__new__(PLFileDownloader)
        df = self._make_pl_df(STATE='06', COUNTY='037', TRACT='101100')
        result = dl._construct_geoid(df, 'tract')
        assert len(result['GEOID'].iloc[0]) == GEOID_LENGTHS['tract']

    def test_pl_block_group_geoid_length(self):
        """PL block group GEOID should be 12 characters."""
        from siege_utilities.geo.census_files.pl_downloader import PLFileDownloader
        dl = PLFileDownloader.__new__(PLFileDownloader)
        df = self._make_pl_df(STATE='06', COUNTY='037', TRACT='101100', BLKGRP='1')
        result = dl._construct_geoid(df, 'block_group')
        assert len(result['GEOID'].iloc[0]) == GEOID_LENGTHS['block_group']

    def test_pl_block_geoid_length(self):
        """PL block GEOID should be 15 characters."""
        from siege_utilities.geo.census_files.pl_downloader import PLFileDownloader
        dl = PLFileDownloader.__new__(PLFileDownloader)
        df = self._make_pl_df(STATE='06', COUNTY='037', TRACT='101100', BLOCK='1001')
        result = dl._construct_geoid(df, 'block')
        assert len(result['GEOID'].iloc[0]) == GEOID_LENGTHS['block']

    def test_pl_geoids_are_strings(self):
        """All PL-constructed GEOIDs must be strings."""
        from siege_utilities.geo.census_files.pl_downloader import PLFileDownloader
        dl = PLFileDownloader.__new__(PLFileDownloader)
        df = self._make_pl_df(STATE='06', COUNTY='037', TRACT='101100', BLKGRP='1', BLOCK='1001')
        for geography in ['state', 'county', 'tract', 'block_group', 'block']:
            result = dl._construct_geoid(df.copy(), geography)
            geoid = result['GEOID'].iloc[0]
            assert isinstance(geoid, str), (
                f"PL {geography} GEOID is {type(geoid).__name__}, expected str"
            )


# =============================================================================
# CROSSWALK GEOID FORMAT
# =============================================================================

class TestCrosswalkGEOIDFormat:
    """Verify crosswalk GEOIDs conform to GEOID_LENGTHS for tract level."""

    SAMPLE_TRACT_GEOIDS = [
        '06037101100', '06037101200', '06037101300',
        '36061000100', '36061000200',
    ]

    def test_tract_geoids_pass_validate(self):
        """Standard tract GEOIDs must pass validate_geoid()."""
        for geoid in self.SAMPLE_TRACT_GEOIDS:
            assert validate_geoid(geoid, 'tract'), (
                f"Tract GEOID '{geoid}' fails validate_geoid()"
            )

    def test_tract_geoids_correct_length(self):
        """Tract GEOIDs must be exactly 11 characters."""
        for geoid in self.SAMPLE_TRACT_GEOIDS:
            assert len(geoid) == GEOID_LENGTHS['tract'] == 11

    def test_tract_geoids_are_strings(self):
        """Tract GEOIDs must be strings."""
        for geoid in self.SAMPLE_TRACT_GEOIDS:
            assert isinstance(geoid, str)

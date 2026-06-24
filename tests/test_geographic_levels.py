"""
Unit tests for canonical geographic level resolution.

Tests CANONICAL_GEOGRAPHIC_LEVELS, resolve_geographic_level(), alias mapping,
GeographyLevel enum _missing_, and alias resolution through GEOID functions.
"""

import pytest

from siege_utilities.config.census_constants import (
    CANONICAL_GEOGRAPHIC_LEVELS,
    resolve_geographic_level,
    validate_geographic_level,
    GEOGRAPHIC_LEVELS,
    GEOGRAPHIC_HIERARCHY,
    TIGER_FILE_PATTERNS,
)
from siege_utilities.geo.census_dataset_mapper import GeographyLevel
from siege_utilities.geo.geoid_utils import GEOID_LENGTHS
from siege_utilities.geo.spatial_data import BOUNDARY_TYPE_CATALOG


# =============================================================================
# CANONICAL_GEOGRAPHIC_LEVELS STRUCTURE
# =============================================================================

class TestCanonicalGeographicLevels:
    """Tests for the canonical geographic levels dict structure."""

    def test_has_expected_levels(self):
        """All core Census geographic levels are present."""
        expected = {
            'nation', 'state', 'county', 'cousub', 'tract',
            'block_group', 'block', 'place', 'cd', 'sldu', 'sldl',
            'zcta', 'cbsa', 'puma',
        }
        assert expected.issubset(CANONICAL_GEOGRAPHIC_LEVELS.keys())

    def test_each_entry_has_required_keys(self):
        """Every entry has 'aliases' and 'geoid_length'."""
        for name, info in CANONICAL_GEOGRAPHIC_LEVELS.items():
            assert 'aliases' in info, f"{name} missing 'aliases'"
            assert 'geoid_length' in info, f"{name} missing 'geoid_length'"

    def test_aliases_are_lists(self):
        """Every aliases value is a list."""
        for name, info in CANONICAL_GEOGRAPHIC_LEVELS.items():
            assert isinstance(info['aliases'], list), f"{name} aliases not a list"

    def test_geoid_lengths_are_ints(self):
        """Every geoid_length is a positive integer."""
        for name, info in CANONICAL_GEOGRAPHIC_LEVELS.items():
            assert isinstance(info['geoid_length'], int), f"{name} geoid_length not int"
            assert info['geoid_length'] > 0, f"{name} geoid_length not positive"

    def test_no_alias_collisions(self):
        """No alias maps to multiple canonical names."""
        seen = {}
        for canonical, info in CANONICAL_GEOGRAPHIC_LEVELS.items():
            for alias in info['aliases']:
                assert alias not in seen, (
                    f"Alias '{alias}' claimed by both '{seen[alias]}' and '{canonical}'"
                )
                seen[alias] = canonical

    def test_canonical_names_not_in_other_aliases(self):
        """A canonical name should not appear as an alias of another level."""
        all_aliases = set()
        for canonical, info in CANONICAL_GEOGRAPHIC_LEVELS.items():
            all_aliases.update(info['aliases'])
        for canonical in CANONICAL_GEOGRAPHIC_LEVELS:
            assert canonical not in all_aliases, (
                f"Canonical name '{canonical}' is also an alias of another level"
            )


# =============================================================================
# resolve_geographic_level()
# =============================================================================

class TestResolveGeographicLevel:
    """Tests for the resolve_geographic_level function."""

    # --- Canonical self-resolution ---

    @pytest.mark.parametrize("canonical", list(CANONICAL_GEOGRAPHIC_LEVELS.keys()))
    def test_canonical_resolves_to_self(self, canonical):
        """Every canonical name resolves to itself."""
        assert resolve_geographic_level(canonical) == canonical

    # --- Known aliases ---

    @pytest.mark.parametrize("alias,expected", [
        ('bg', 'block_group'),
        ('blockgroup', 'block_group'),
        ('congressional_district', 'cd'),
        ('county_subdivision', 'cousub'),
        ('state_legislative_upper', 'sldu'),
        ('state_legislative_lower', 'sldl'),
        ('state_legislative_district', 'sldu'),
        ('state_legislative_district_upper', 'sldu'),
        ('state_legislative_district_lower', 'sldl'),
        ('zip_code', 'zcta'),
        ('zcta5', 'zcta'),
        ('zipcode', 'zcta'),
        ('tabblock', 'block'),
        ('us', 'nation'),
        ('national', 'nation'),
        ('voting_district', 'vtd'),
    ])
    def test_alias_resolution(self, alias, expected):
        """Known aliases resolve to correct canonical names."""
        assert resolve_geographic_level(alias) == expected

    # --- Case insensitivity ---

    def test_case_insensitive(self):
        """Resolution is case-insensitive."""
        assert resolve_geographic_level('CD') == 'cd'
        assert resolve_geographic_level('Block_Group') == 'block_group'
        assert resolve_geographic_level('CONGRESSIONAL_DISTRICT') == 'cd'
        assert resolve_geographic_level('Zcta') == 'zcta'

    # --- Whitespace handling ---

    def test_strips_whitespace(self):
        """Leading/trailing whitespace is stripped."""
        assert resolve_geographic_level('  tract  ') == 'tract'
        assert resolve_geographic_level('\tstate\n') == 'state'

    # --- Error cases ---

    def test_invalid_level_raises_valueerror(self):
        """Unrecognized level raises ValueError."""
        with pytest.raises(ValueError, match="Unrecognized geographic level"):
            resolve_geographic_level("invalid_level")

    def test_empty_string_raises_valueerror(self):
        """Empty string raises ValueError."""
        with pytest.raises(ValueError, match="Unrecognized geographic level"):
            resolve_geographic_level("")

    def test_numeric_string_raises_valueerror(self):
        """Numeric string raises ValueError."""
        with pytest.raises(ValueError, match="Unrecognized geographic level"):
            resolve_geographic_level("12345")


# =============================================================================
# validate_geographic_level()
# =============================================================================

class TestValidateGeographicLevel:
    """Tests for the validate_geographic_level function."""

    def test_valid_canonical(self):
        assert validate_geographic_level('tract') is True

    def test_valid_alias(self):
        assert validate_geographic_level('congressional_district') is True

    def test_valid_case_insensitive(self):
        assert validate_geographic_level('CD') is True

    def test_invalid(self):
        assert validate_geographic_level('nonsense') is False


# =============================================================================
# BACKWARD-COMPATIBLE GEOGRAPHIC_LEVELS dict
# =============================================================================

class TestGeographicLevelsBackwardCompat:
    """Tests that the GEOGRAPHIC_LEVELS dict preserves expected keys."""

    def test_original_keys_present(self):
        """All original UPPER_CASE keys still exist."""
        original_keys = [
            'NATION', 'STATE', 'COUNTY', 'PLACE', 'TRACT',
            'BLOCK_GROUP', 'BLOCK', 'CBSA', 'PUMA',
        ]
        for key in original_keys:
            assert key in GEOGRAPHIC_LEVELS, f"Missing key: {key}"

    def test_alias_keys_present(self):
        """Backward-compat alias keys exist."""
        assert 'CONGRESSIONAL_DISTRICT' in GEOGRAPHIC_LEVELS
        assert 'COUNTY_SUBDIVISION' in GEOGRAPHIC_LEVELS
        assert 'ZIP_CODE' in GEOGRAPHIC_LEVELS
        assert 'STATE_LEGISLATIVE_DISTRICT' in GEOGRAPHIC_LEVELS

    def test_alias_values_are_canonical(self):
        """Alias keys map to canonical values."""
        assert GEOGRAPHIC_LEVELS['CONGRESSIONAL_DISTRICT'] == 'cd'
        assert GEOGRAPHIC_LEVELS['COUNTY_SUBDIVISION'] == 'cousub'
        assert GEOGRAPHIC_LEVELS['ZIP_CODE'] == 'zcta'
        assert GEOGRAPHIC_LEVELS['STATE_LEGISLATIVE_DISTRICT'] == 'sldu'


# =============================================================================
# GEOGRAPHIC_HIERARCHY
# =============================================================================

class TestGeographicHierarchy:
    """Tests for the geographic hierarchy list."""

    def test_uses_canonical_names(self):
        """Hierarchy uses canonical names (cousub, not county_subdivision)."""
        assert 'cousub' in GEOGRAPHIC_HIERARCHY
        assert 'county_subdivision' not in GEOGRAPHIC_HIERARCHY

    def test_order(self):
        """Hierarchy goes from largest to smallest."""
        expected_order = ['nation', 'region', 'division', 'state', 'county',
                          'cousub', 'tract', 'block_group', 'block']
        assert GEOGRAPHIC_HIERARCHY == expected_order


# =============================================================================
# GEOID_LENGTHS derivation
# =============================================================================

class TestGEOIDLengthsDerivation:
    """Tests that GEOID_LENGTHS is correctly derived from canonical."""

    def test_derived_from_canonical(self):
        """Every GEOID_LENGTHS entry matches CANONICAL_GEOGRAPHIC_LEVELS."""
        for name, length in GEOID_LENGTHS.items():
            assert name in CANONICAL_GEOGRAPHIC_LEVELS, f"{name} not in canonical"
            assert CANONICAL_GEOGRAPHIC_LEVELS[name]['geoid_length'] == length

    def test_canonical_keys_present(self):
        """Key canonical levels are present."""
        assert 'cd' in GEOID_LENGTHS
        assert 'cousub' in GEOID_LENGTHS
        assert 'sldu' in GEOID_LENGTHS
        assert 'sldl' in GEOID_LENGTHS

    def test_old_keys_absent(self):
        """Legacy long-form keys are NOT in GEOID_LENGTHS."""
        assert 'congressional_district' not in GEOID_LENGTHS
        assert 'county_subdivision' not in GEOID_LENGTHS
        assert 'state_legislative_upper' not in GEOID_LENGTHS
        assert 'state_legislative_lower' not in GEOID_LENGTHS


# =============================================================================
# GeographyLevel enum
# =============================================================================

class TestGeographyLevelEnum:
    """Tests for the GeographyLevel enum with canonical values."""

    def test_canonical_members(self):
        """Canonical enum members have correct values."""
        assert GeographyLevel.CD.value == 'cd'
        assert GeographyLevel.COUSUB.value == 'cousub'
        assert GeographyLevel.SLDU.value == 'sldu'
        assert GeographyLevel.SLDL.value == 'sldl'
        assert GeographyLevel.ZCTA.value == 'zcta'
        assert GeographyLevel.BLOCK_GROUP.value == 'block_group'

    def test_backward_compat_aliases(self):
        """Backward-compat aliases are the same member as canonical."""
        assert GeographyLevel.CONGRESSIONAL_DISTRICT is GeographyLevel.CD
        assert GeographyLevel.COUNTY_SUBDIVISION is GeographyLevel.COUSUB
        assert GeographyLevel.ZIP_CODE is GeographyLevel.ZCTA
        assert GeographyLevel.STATE_LEGISLATIVE_DISTRICT is GeographyLevel.SLDU

    def test_missing_resolves_long_forms(self):
        """_missing_ resolves legacy long-form strings to enum members."""
        assert GeographyLevel('congressional_district') is GeographyLevel.CD
        assert GeographyLevel('county_subdivision') is GeographyLevel.COUSUB
        assert GeographyLevel('zip_code') is GeographyLevel.ZCTA
        assert GeographyLevel('state_legislative_upper') is GeographyLevel.SLDU
        assert GeographyLevel('state_legislative_lower') is GeographyLevel.SLDL

    def test_missing_resolves_abbreviations(self):
        """_missing_ resolves Census abbreviations."""
        assert GeographyLevel('bg') is GeographyLevel.BLOCK_GROUP
        assert GeographyLevel('tabblock') is GeographyLevel.BLOCK

    def test_missing_invalid_raises(self):
        """_missing_ raises ValueError for truly invalid values."""
        with pytest.raises(ValueError):
            GeographyLevel('nonsense')


# =============================================================================
# GEOID functions accept aliases
# =============================================================================

class TestGEOIDFunctionsAcceptAliases:
    """Tests that GEOID functions accept any geographic level alias."""

    def test_normalize_with_alias_bg(self):
        """normalize_geoid accepts 'bg' alias."""
        from siege_utilities.geo.geoid_utils import normalize_geoid
        result = normalize_geoid('060371011001', 'bg')
        assert result == '060371011001'

    def test_normalize_with_alias_congressional_district(self):
        """normalize_geoid accepts 'congressional_district' alias."""
        from siege_utilities.geo.geoid_utils import normalize_geoid
        result = normalize_geoid('0604', 'congressional_district')
        assert result == '0604'

    def test_validate_with_alias_cd(self):
        """validate_geoid accepts 'cd' canonical name."""
        from siege_utilities.geo.geoid_utils import validate_geoid
        assert validate_geoid('0604', 'cd') is True

    def test_validate_with_alias_zip_code(self):
        """validate_geoid accepts 'zip_code' alias."""
        from siege_utilities.geo.geoid_utils import validate_geoid
        assert validate_geoid('90210', 'zip_code') is True

    def test_can_normalize_with_alias(self):
        """can_normalize_geoid accepts aliases."""
        from siege_utilities.geo.geoid_utils import can_normalize_geoid
        assert can_normalize_geoid('604', 'congressional_district') is True

    def test_construct_with_alias_blockgroup(self):
        """construct_geoid accepts 'bg' alias."""
        from siege_utilities.geo.geoid_utils import construct_geoid
        result = construct_geoid('bg', state='06', county='037',
                                 tract='101100', block_group='1')
        assert result == '060371011001'


# =============================================================================
# BOUNDARY_TYPE_CATALOG consistency
# =============================================================================

class TestBoundaryTypeCatalogConsistency:
    """Tests that BOUNDARY_TYPE_CATALOG keys are valid canonical names or known types."""

    def test_redistricting_base_types_resolvable(self):
        """Base redistricting catalog keys (without session numbers) resolve to a canonical level."""
        import re
        redistricting = {k for k, v in BOUNDARY_TYPE_CATALOG.items()
                         if v['category'] == 'redistricting'}
        # Session-specific keys like cd116, cd117, sldl22, vtd20 have a numeric suffix
        # on a canonical base type — strip the suffix and check the base resolves.
        session_pattern = re.compile(r'^([a-z_]+?)(\d+)$')
        for key in redistricting:
            if validate_geographic_level(key):
                continue  # directly resolvable — good
            m = session_pattern.match(key)
            assert m is not None, (
                f"Redistricting type '{key}' is neither a canonical level "
                f"nor a session-specific variant (base+digits)"
            )
            base = m.group(1)
            assert validate_geographic_level(base), (
                f"Redistricting type '{key}' has base '{base}' "
                f"which is not a valid geographic level"
            )

    def test_each_entry_has_required_keys(self):
        """Every catalog entry has category, abbrev, name."""
        for key, info in BOUNDARY_TYPE_CATALOG.items():
            assert 'category' in info, f"{key} missing 'category'"
            assert 'abbrev' in info, f"{key} missing 'abbrev'"
            assert 'name' in info, f"{key} missing 'name'"

    def test_categories_are_valid(self):
        """All categories are either 'redistricting' or 'general'."""
        for key, info in BOUNDARY_TYPE_CATALOG.items():
            assert info['category'] in ('redistricting', 'general'), (
                f"{key} has invalid category '{info['category']}'"
            )


# =============================================================================
# TIGER_FILE_PATTERNS consistency
# =============================================================================

class TestTigerFilePatternsConsistency:
    """Tests that TIGER_FILE_PATTERNS keys are valid canonical names."""

    # Keys in TIGER_FILE_PATTERNS that are feature layers, not geographic levels.
    # These have valid TIGER download URLs but no GEOID structure.
    _FEATURE_LAYER_KEYS = {
        'uac', 'uac20', 'rails', 'aiannh',
        'roads', 'linear_water', 'area_water', 'edges',
        'address_features', 'pointlm', 'arealm',
        'elsd', 'scsd', 'unsd',
    }

    def test_all_keys_are_canonical(self):
        """Every key in TIGER_FILE_PATTERNS is a canonical level or feature layer."""
        for key in TIGER_FILE_PATTERNS:
            assert key in CANONICAL_GEOGRAPHIC_LEVELS or key in self._FEATURE_LAYER_KEYS, (
                f"TIGER pattern key '{key}' is not a canonical geographic level or feature layer"
            )

    def test_core_levels_have_patterns(self):
        """Core levels have download patterns."""
        for level in ['state', 'county', 'tract', 'block_group', 'place']:
            assert level in TIGER_FILE_PATTERNS, f"Missing TIGER pattern for '{level}'"

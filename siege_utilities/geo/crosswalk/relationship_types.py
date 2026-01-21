"""
Relationship types and data classes for Census boundary crosswalks.

This module defines enumerations and data classes that describe how Census
geographic boundaries change between decennial census years (e.g., 2010 to 2020).

Census tracts can:
- Remain unchanged (ONE_TO_ONE)
- Be split into multiple tracts (ONE_TO_MANY)
- Be merged with other tracts (MANY_TO_ONE)

The crosswalk files from Census Bureau provide relationship weights based on:
- Land area proportions
- Population distribution

Example usage:
    from siege_utilities.geo.crosswalk import RelationshipType, WeightMethod

    # Check relationship type
    if relationship == RelationshipType.SPLIT:
        # Handle tract that was split
        ...

    # Specify weighting method
    method = WeightMethod.POPULATION
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class RelationshipType(Enum):
    """
    Types of relationships between source and target geographies in crosswalks.

    These describe how a geographic unit changed between Census years.
    """

    ONE_TO_ONE = "one_to_one"
    """Geographic unit unchanged - maps directly to one target unit."""

    SPLIT = "split"
    """One source unit split into multiple target units (one-to-many)."""

    MERGED = "merged"
    """Multiple source units merged into one target unit (many-to-one)."""

    PARTIAL_OVERLAP = "partial_overlap"
    """Complex relationship - parts of units overlap (many-to-many)."""


class WeightMethod(Enum):
    """
    Methods for weighting data when applying crosswalks.

    Different methods are appropriate for different types of data:
    - AREA: Best for land-use data, environmental measures
    - POPULATION: Best for demographic data, social measures
    - HOUSING: Best for housing-related variables
    - EQUAL: Simple equal weighting (use when weights unavailable)
    """

    AREA = "area"
    """Weight by land area proportion."""

    POPULATION = "population"
    """Weight by population proportion (requires population data)."""

    HOUSING = "housing"
    """Weight by housing unit proportion."""

    EQUAL = "equal"
    """Equal weighting across all relationships."""


@dataclass
class CrosswalkRelationship:
    """
    Represents a single relationship between source and target geographies.

    This is one row in a crosswalk file, describing how data should flow
    from a source geography (e.g., 2010 tract) to a target geography
    (e.g., 2020 tract).

    Attributes:
        source_geoid: GEOID of the source geography
        target_geoid: GEOID of the target geography
        relationship_type: Type of relationship (split, merge, etc.)
        area_weight: Proportion of source area in target (0.0 to 1.0)
        population_weight: Proportion of source population in target
        housing_weight: Proportion of source housing units in target
        source_area: Land area of source geography (sq meters)
        target_area: Land area of target geography (sq meters)
        overlap_area: Area of intersection (sq meters)
    """

    source_geoid: str
    target_geoid: str
    relationship_type: RelationshipType = RelationshipType.ONE_TO_ONE
    area_weight: float = 1.0
    population_weight: Optional[float] = None
    housing_weight: Optional[float] = None
    source_area: Optional[float] = None
    target_area: Optional[float] = None
    overlap_area: Optional[float] = None

    def get_weight(self, method: WeightMethod) -> float:
        """
        Get the appropriate weight for the specified method.

        Args:
            method: Weighting method to use

        Returns:
            Weight value (0.0 to 1.0)

        Raises:
            ValueError: If requested weight type is not available
        """
        if method == WeightMethod.AREA:
            return self.area_weight
        elif method == WeightMethod.POPULATION:
            if self.population_weight is None:
                raise ValueError(
                    "Population weight not available for this crosswalk. "
                    "Use AREA or EQUAL weighting instead."
                )
            return self.population_weight
        elif method == WeightMethod.HOUSING:
            if self.housing_weight is None:
                raise ValueError(
                    "Housing weight not available for this crosswalk. "
                    "Use AREA or EQUAL weighting instead."
                )
            return self.housing_weight
        elif method == WeightMethod.EQUAL:
            return 1.0
        else:
            raise ValueError(f"Unknown weight method: {method}")


@dataclass
class CrosswalkMetadata:
    """
    Metadata about a crosswalk dataset.

    Attributes:
        source_year: Year of source geographies (e.g., 2010)
        target_year: Year of target geographies (e.g., 2020)
        geography_level: Geographic level (e.g., 'tract', 'block_group')
        state_fips: State FIPS code if state-specific, None for national
        total_source_units: Number of unique source geographies
        total_target_units: Number of unique target geographies
        one_to_one_count: Number of unchanged geographies
        split_count: Number of geographies that were split
        merged_count: Number of geographies that were merged
        source_url: URL where crosswalk was downloaded from
        download_date: Date crosswalk was downloaded
    """

    source_year: int
    target_year: int
    geography_level: str
    state_fips: Optional[str] = None
    total_source_units: int = 0
    total_target_units: int = 0
    one_to_one_count: int = 0
    split_count: int = 0
    merged_count: int = 0
    source_url: Optional[str] = None
    download_date: Optional[str] = None

    @property
    def change_rate(self) -> float:
        """
        Calculate the rate of geographic change.

        Returns:
            Proportion of geographies that changed (0.0 to 1.0)
        """
        if self.total_source_units == 0:
            return 0.0
        changed = self.split_count + self.merged_count
        return changed / self.total_source_units

    def summary(self) -> Dict:
        """
        Get a summary dictionary of crosswalk statistics.

        Returns:
            Dictionary with crosswalk statistics
        """
        return {
            'source_year': self.source_year,
            'target_year': self.target_year,
            'geography_level': self.geography_level,
            'state_fips': self.state_fips,
            'total_source_units': self.total_source_units,
            'total_target_units': self.total_target_units,
            'unchanged': self.one_to_one_count,
            'splits': self.split_count,
            'merges': self.merged_count,
            'change_rate': f"{self.change_rate:.1%}"
        }


@dataclass
class GeographyChange:
    """
    Summary of changes for a single geography between Census years.

    This provides a higher-level view than individual relationships,
    summarizing all the changes for a single source geography.

    Attributes:
        source_geoid: GEOID of the source geography
        relationship_type: Overall relationship type
        target_geoids: List of target GEOIDs this geography maps to
        weights: Dictionary mapping target GEOIDs to their weights
        population_2010: Source geography population in 2010
        population_2020: Total population of target geographies in 2020
    """

    source_geoid: str
    relationship_type: RelationshipType
    target_geoids: List[str] = field(default_factory=list)
    weights: Dict[str, float] = field(default_factory=dict)
    population_2010: Optional[int] = None
    population_2020: Optional[int] = None

    @property
    def is_unchanged(self) -> bool:
        """Check if geography is unchanged."""
        return self.relationship_type == RelationshipType.ONE_TO_ONE

    @property
    def was_split(self) -> bool:
        """Check if geography was split."""
        return self.relationship_type == RelationshipType.SPLIT

    @property
    def was_merged(self) -> bool:
        """Check if geography was merged."""
        return self.relationship_type == RelationshipType.MERGED

    @property
    def num_targets(self) -> int:
        """Number of target geographies."""
        return len(self.target_geoids)


# Supported crosswalk years
SUPPORTED_CROSSWALK_YEARS = {
    (2010, 2020): {
        'tract': True,
        'block_group': True,
        'block': True,
        'county': True,
    },
    (2000, 2010): {
        'tract': True,
        'block_group': True,
        'block': True,
        'county': True,
    },
}

# Census Bureau crosswalk file URLs
CROSSWALK_BASE_URL = "https://www2.census.gov/geo/docs/maps-data/data/rel2020"

CROSSWALK_FILE_PATTERNS = {
    'tract': {
        (2010, 2020): "tract/tab20_tract20_tract10_natl.txt",
        (2000, 2010): None,  # Different structure
    },
    'block_group': {
        (2010, 2020): "blkgrp/tab20_blkgrp20_blkgrp10_natl.txt",
    },
    'county': {
        (2010, 2020): "county/tab20_county20_county10_natl.txt",
    },
}

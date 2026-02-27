"""
Tests for CensusDataSelector primary dataset bonus fix (su#164).

Verifies that the primary_dataset bonus (+1.5) is correctly applied
when a dataset's ID matches the pattern's primary_datasets list.
"""

import pytest
from siege_utilities.geo.census_data_selector import CensusDataSelector
from siege_utilities.geo.census_dataset_mapper import (
    CensusDataset, CensusDatasetMapper, SurveyType, GeographyLevel, DataReliability,
)


class TestPrimaryDatasetBonus:
    """Tests that the primary_dataset bonus is applied correctly."""

    def setup_method(self):
        self.selector = CensusDataSelector()

    def test_primary_bonus_applied_for_matching_dataset(self):
        """Primary dataset bonus (+1.5) must be awarded when dataset_id
        appears in the pattern's primary_datasets list."""
        pattern = self.selector.analysis_patterns["demographics"]
        # "acs_5yr_2020" is in demographics.primary_datasets
        dataset = self.selector.mapper.datasets["acs_5yr_2020"]
        assert dataset.dataset_id == "acs_5yr_2020"
        assert dataset.dataset_id in pattern["primary_datasets"]

        # Score via the ranking method
        ranked = self.selector._rank_datasets_by_suitability(
            [dataset], pattern, GeographyLevel.TRACT, None
        )
        _, breakdown = ranked[0]
        assert breakdown["primary_dataset"] == 1.5, (
            "Primary dataset bonus not applied — dataset_id vs name mismatch?"
        )

    def test_primary_bonus_not_applied_for_non_matching_dataset(self):
        """Datasets NOT in primary_datasets must receive 0.0 bonus."""
        pattern = self.selector.analysis_patterns["demographics"]
        # population_estimates_2023 is NOT in demographics.primary_datasets
        dataset = self.selector.mapper.datasets["population_estimates_2023"]
        assert dataset.dataset_id not in pattern["primary_datasets"]

        ranked = self.selector._rank_datasets_by_suitability(
            [dataset], pattern, GeographyLevel.COUNTY, None
        )
        _, breakdown = ranked[0]
        assert breakdown["primary_dataset"] == 0.0

    def test_decennial_gets_bonus_for_demographics(self):
        """decennial_2020 is listed in demographics primary_datasets."""
        pattern = self.selector.analysis_patterns["demographics"]
        dataset = self.selector.mapper.datasets["decennial_2020"]
        assert dataset.dataset_id in pattern["primary_datasets"]

        ranked = self.selector._rank_datasets_by_suitability(
            [dataset], pattern, GeographyLevel.TRACT, None
        )
        _, breakdown = ranked[0]
        assert breakdown["primary_dataset"] == 1.5

    def test_economic_census_gets_bonus_for_business(self):
        """economic_census_2017 is in business.primary_datasets."""
        pattern = self.selector.analysis_patterns["business"]
        dataset = self.selector.mapper.datasets["economic_census_2017"]
        assert dataset.dataset_id in pattern["primary_datasets"]

        ranked = self.selector._rank_datasets_by_suitability(
            [dataset], pattern, GeographyLevel.COUNTY, None
        )
        _, breakdown = ranked[0]
        assert breakdown["primary_dataset"] == 1.5


class TestDatasetIdField:
    """Verify that every dataset in the mapper has a dataset_id matching its key."""

    def test_all_datasets_have_matching_id(self):
        mapper = CensusDatasetMapper()
        for key, dataset in mapper.datasets.items():
            assert dataset.dataset_id == key, (
                f"Dataset key '{key}' doesn't match dataset_id '{dataset.dataset_id}'"
            )


class TestCompatibilityScoreBonus:
    """Verify _calculate_compatibility_score also uses dataset_id."""

    def setup_method(self):
        self.selector = CensusDataSelector()

    def test_compatibility_score_includes_primary_bonus(self):
        pattern = self.selector.analysis_patterns["demographics"]
        dataset = self.selector.mapper.datasets["acs_5yr_2020"]
        score = self.selector._calculate_compatibility_score(dataset, pattern)
        # The +2.0 primary bonus in compatibility score should apply
        assert score >= 2.0

    def test_compatibility_score_excludes_primary_bonus_for_non_primary(self):
        pattern = self.selector.analysis_patterns["demographics"]
        dataset = self.selector.mapper.datasets["economic_census_2017"]
        assert dataset.dataset_id not in pattern["primary_datasets"]
        score = self.selector._calculate_compatibility_score(dataset, pattern)
        # Without primary bonus, base score should be lower
        # (may still get geography/reliability points)
        assert score < 4.0


class TestRationaleUsesDatasetId:
    """Verify _generate_rationale checks dataset_id, not name."""

    def setup_method(self):
        self.selector = CensusDataSelector()

    def test_rationale_includes_primary_match(self):
        pattern = self.selector.analysis_patterns["demographics"]
        dataset = self.selector.mapper.datasets["acs_5yr_2020"]
        rationale = self.selector._generate_rationale(dataset, pattern)
        assert "primary dataset pattern" in rationale.lower()

    def test_rationale_excludes_primary_match_for_non_primary(self):
        pattern = self.selector.analysis_patterns["demographics"]
        dataset = self.selector.mapper.datasets["population_estimates_2023"]
        rationale = self.selector._generate_rationale(dataset, pattern)
        assert "primary dataset pattern" not in rationale.lower()

"""Tests for CensusDatasetMapper — dataset catalog, relationships, and selection.

Pure-logic module, no I/O needed.
"""

import pytest

from siege_utilities.geo.census_dataset_mapper import (
    CensusDataset,
    CensusDatasetMapper,
    DatasetRelationship,
    compare_datasets,
    get_best_dataset_for_analysis,
    get_best_dataset_for_use_case,
    get_census_dataset_mapper,
    get_data_selection_guide,
    get_dataset_info,
    get_dataset_relationships,
    list_datasets_by_geography,
    list_datasets_by_type,
)
from siege_utilities.config.census_registry import (
    GeographyLevel,
    SurveyType,
)


# ---------------------------------------------------------------------------
# CensusDatasetMapper initialization
# ---------------------------------------------------------------------------

class TestMapperInit:

    def test_singleton_factory(self):
        m1 = get_census_dataset_mapper()
        m2 = get_census_dataset_mapper()
        assert isinstance(m1, CensusDatasetMapper)
        assert isinstance(m2, CensusDatasetMapper)

    def test_has_datasets(self):
        mapper = CensusDatasetMapper()
        assert len(mapper.datasets) > 0

    def test_has_relationships(self):
        mapper = CensusDatasetMapper()
        assert len(mapper.relationships) > 0

    def test_decennial_present(self):
        mapper = CensusDatasetMapper()
        assert "decennial_2020" in mapper.datasets


# ---------------------------------------------------------------------------
# get_dataset_info
# ---------------------------------------------------------------------------

class TestGetDatasetInfo:

    def test_known_dataset(self):
        info = get_dataset_info("decennial_2020")
        assert info is not None
        assert isinstance(info, CensusDataset)
        assert info.dataset_id == "decennial_2020"
        assert info.survey_type == SurveyType.DECENNIAL

    def test_unknown_dataset(self):
        info = get_dataset_info("nonexistent_dataset")
        assert info is None


# ---------------------------------------------------------------------------
# list_datasets_by_type
# ---------------------------------------------------------------------------

class TestListByType:

    def test_decennial(self):
        datasets = list_datasets_by_type("decennial")
        assert isinstance(datasets, list)
        assert len(datasets) >= 1
        for ds in datasets:
            assert ds.survey_type == SurveyType.DECENNIAL

    def test_acs(self):
        datasets = list_datasets_by_type("acs_5yr")
        assert isinstance(datasets, list)


# ---------------------------------------------------------------------------
# list_datasets_by_geography
# ---------------------------------------------------------------------------

class TestListByGeography:

    def test_county(self):
        datasets = list_datasets_by_geography("county")
        assert isinstance(datasets, list)
        assert len(datasets) >= 1

    def test_tract(self):
        datasets = list_datasets_by_geography("tract")
        assert isinstance(datasets, list)


# ---------------------------------------------------------------------------
# get_dataset_relationships
# ---------------------------------------------------------------------------

class TestRelationships:

    def test_known_dataset(self):
        rels = get_dataset_relationships("decennial_2020")
        assert isinstance(rels, list)
        for r in rels:
            assert isinstance(r, DatasetRelationship)

    def test_unknown_dataset(self):
        rels = get_dataset_relationships("nonexistent")
        assert isinstance(rels, list)
        assert len(rels) == 0


# ---------------------------------------------------------------------------
# compare_datasets
# ---------------------------------------------------------------------------

class TestCompareDatasets:

    def test_compare_two_known(self):
        mapper = CensusDatasetMapper()
        names = list(mapper.datasets.keys())
        if len(names) >= 2:
            result = compare_datasets(names[0], names[1])
            assert isinstance(result, dict)
            assert "dataset1" in result
            assert "dataset2" in result

    def test_compare_unknown(self):
        result = compare_datasets("nonexistent_1", "nonexistent_2")
        assert isinstance(result, dict)
        # Should handle gracefully


# ---------------------------------------------------------------------------
# get_best_dataset_for_use_case
# ---------------------------------------------------------------------------

class TestBestDataset:

    def test_population_county(self):
        result = get_best_dataset_for_use_case(
            "population", geography_level="county"
        )
        assert isinstance(result, (dict, list))

    def test_income_tract(self):
        result = get_best_dataset_for_use_case(
            "income", geography_level="tract"
        )
        assert isinstance(result, (dict, list))


# ---------------------------------------------------------------------------
# get_data_selection_guide
# ---------------------------------------------------------------------------

class TestSelectionGuide:

    def test_demographic_county(self):
        guide = get_data_selection_guide("demographic", "county")
        assert isinstance(guide, dict)

    def test_economic_tract(self):
        guide = get_data_selection_guide("economic", "tract", time_sensitivity="high")
        assert isinstance(guide, dict)


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

class TestConvenienceFunctions:

    def test_get_best_dataset_for_analysis(self):
        result = get_best_dataset_for_analysis("demographic", "county")
        assert isinstance(result, dict)

"""
Census Dataset Relationship Mapper

This module provides comprehensive mapping and relationship information for Census datasets,
making it easier to understand which datasets to use for different analysis needs.
"""

import json
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import warnings

class SurveyType(Enum):
    """Enumeration of Census survey types."""
    DECENNIAL = "decennial"           # Every 10 years (2020, 2010, etc.)
    ACS_1YR = "acs_1yr"              # American Community Survey 1-year estimates
    ACS_3YR = "acs_3yr"              # American Community Survey 3-year estimates
    ACS_5YR = "acs_5yr"              # American Community Survey 5-year estimates
    CENSUS_BUSINESS = "census_business"  # Economic Census
    POPULATION_ESTIMATES = "population_estimates"  # Annual population estimates
    HOUSING_ESTIMATES = "housing_estimates"  # Annual housing estimates

class GeographyLevel(Enum):
    """Enumeration of Census geography levels."""
    NATION = "nation"
    REGION = "region"
    DIVISION = "division"
    STATE = "state"
    COUNTY = "county"
    COUNTY_SUBDIVISION = "county_subdivision"
    PLACE = "place"
    CONGRESSIONAL_DISTRICT = "congressional_district"
    STATE_LEGISLATIVE_DISTRICT = "state_legislative_district"
    TRACT = "tract"
    BLOCK_GROUP = "block_group"
    BLOCK = "block"
    ZIP_CODE = "zip_code"
    CBSA = "cbsa"  # Metropolitan/Micropolitan Statistical Areas
    PUMA = "puma"  # Public Use Microdata Areas

class DataReliability(Enum):
    """Enumeration of data reliability levels."""
    HIGH = "high"           # Most reliable (decennial, large geographies)
    MEDIUM = "medium"       # Moderately reliable (ACS 5-year, medium geographies)
    LOW = "low"             # Less reliable (ACS 1-year, small geographies)
    ESTIMATED = "estimated" # Modeled estimates

@dataclass
class CensusDataset:
    """Represents a Census dataset with metadata."""
    
    name: str
    survey_type: SurveyType
    geography_levels: List[GeographyLevel]
    time_period: str
    reliability: DataReliability
    description: str
    variables: List[str]
    limitations: List[str]
    best_for: List[str]
    alternatives: List[str]
    data_quality_notes: str
    last_updated: str
    next_update: str
    api_endpoint: Optional[str] = None
    download_url: Optional[str] = None

@dataclass
class DatasetRelationship:
    """Represents a relationship between Census datasets."""
    
    primary_dataset: str
    related_dataset: str
    relationship_type: str  # "complements", "replaces", "supplements", "conflicts"
    description: str
    when_to_use_primary: str
    when_to_use_related: str
    overlap_period: Optional[str] = None
    compatibility_score: float = 1.0  # 0-1 scale

class CensusDatasetMapper:
    """
    Maps relationships between Census datasets and provides intelligent data selection.
    
    This class helps users understand:
    - Which datasets are available for different geography levels
    - How different survey types relate to each other
    - When to use different datasets based on analysis needs
    - Data quality and reliability considerations
    """
    
    def __init__(self):
        self.datasets: Dict[str, CensusDataset] = {}
        self.relationships: List[DatasetRelationship] = []
        self._initialize_datasets()
        self._initialize_relationships()
    
    def _initialize_datasets(self):
        """Initialize the comprehensive Census dataset catalog."""
        
        # Decennial Census (2020)
        self.datasets["decennial_2020"] = CensusDataset(
            name="2020 Decennial Census",
            survey_type=SurveyType.DECENNIAL,
            geography_levels=[
                GeographyLevel.NATION, GeographyLevel.STATE, GeographyLevel.COUNTY,
                GeographyLevel.PLACE, GeographyLevel.TRACT, GeographyLevel.BLOCK_GROUP,
                GeographyLevel.BLOCK
            ],
            time_period="2020-04-01",
            reliability=DataReliability.HIGH,
            description="Complete count of population and housing units every 10 years",
            variables=[
                "total_population", "race", "ethnicity", "age", "sex",
                "household_type", "housing_tenure", "vacancy_status"
            ],
            limitations=[
                "Only basic demographic questions",
                "Limited socioeconomic data",
                "10-year intervals mean data can become outdated"
            ],
            best_for=[
                "Official population counts",
                "Redistricting",
                "Constitutional requirements",
                "High-precision geography analysis"
            ],
            alternatives=[
                "acs_5yr_2020", "population_estimates_2023"
            ],
            data_quality_notes="100% count of population and housing units",
            last_updated="2021-08-12",
            next_update="2030-04-01",
            api_endpoint="https://api.census.gov/data/2020/dec/pl94",
            download_url="https://www2.census.gov/census_2020/"
        )
        
        # ACS 5-Year Estimates (2020)
        self.datasets["acs_5yr_2020"] = CensusDataset(
            name="ACS 5-Year Estimates (2020)",
            survey_type=SurveyType.ACS_5YR,
            geography_levels=[
                GeographyLevel.NATION, GeographyLevel.STATE, GeographyLevel.COUNTY,
                GeographyLevel.PLACE, GeographyLevel.TRACT, GeographyLevel.BLOCK_GROUP
            ],
            time_period="2016-2020",
            reliability=DataReliability.MEDIUM,
            description="5-year rolling average providing detailed socioeconomic data",
            variables=[
                "income", "education", "employment", "housing_value", "rent",
                "commute_time", "health_insurance", "poverty_status"
            ],
            limitations=[
                "5-year period may mask recent changes",
                "Smaller geographies have higher margins of error",
                "Not suitable for very recent analysis"
            ],
            best_for=[
                "Detailed socioeconomic analysis",
                "Small geography analysis",
                "Trend analysis over 5-year periods",
                "Policy planning and research"
            ],
            alternatives=[
                "acs_3yr_2020", "acs_1yr_2020", "decennial_2020"
            ],
            data_quality_notes="Sample-based estimates with margins of error",
            last_updated="2021-12-09",
            next_update="2022-12-09",
            api_endpoint="https://api.census.gov/data/2020/acs/acs5",
            download_url="https://www2.census.gov/programs-surveys/acs/data/pums/2020/"
        )
        
        # ACS 1-Year Estimates (2020)
        self.datasets["acs_1yr_2020"] = CensusDataset(
            name="ACS 1-Year Estimates (2020)",
            survey_type=SurveyType.ACS_1YR,
            geography_levels=[
                GeographyLevel.NATION, GeographyLevel.STATE, GeographyLevel.COUNTY,
                GeographyLevel.PLACE, GeographyLevel.CBSA
            ],
            time_period="2020",
            reliability=DataReliability.LOW,
            description="1-year estimates for larger geographies",
            variables=[
                "income", "education", "employment", "housing_value", "rent",
                "commute_time", "health_insurance", "poverty_status"
            ],
            limitations=[
                "Only available for geographies with 65,000+ people",
                "Higher margins of error than 5-year estimates",
                "More sensitive to sampling fluctuations"
            ],
            best_for=[
                "Recent trend analysis",
                "Large geography analysis",
                "Annual comparisons",
                "Quick assessments"
            ],
            alternatives=[
                "acs_5yr_2020", "population_estimates_2020"
            ],
            data_quality_notes="Sample-based estimates with higher margins of error",
            last_updated="2021-09-16",
            next_update="2022-09-16",
            api_endpoint="https://api.census.gov/data/2020/acs/acs1",
            download_url="https://www2.census.gov/programs-surveys/acs/data/pums/2020/"
        )
        
        # Population Estimates (2023)
        self.datasets["population_estimates_2023"] = CensusDataset(
            name="Population Estimates (2023)",
            survey_type=SurveyType.POPULATION_ESTIMATES,
            geography_levels=[
                GeographyLevel.NATION, GeographyLevel.STATE, GeographyLevel.COUNTY,
                GeographyLevel.PLACE, GeographyLevel.CBSA
            ],
            time_period="2023-07-01",
            reliability=DataReliability.ESTIMATED,
            description="Annual population estimates based on administrative records",
            variables=[
                "total_population", "age_sex_race", "components_of_change",
                "housing_units"
            ],
            limitations=[
                "Modeled estimates, not direct counts",
                "Limited demographic detail",
                "Subject to modeling assumptions"
            ],
            best_for=[
                "Current population estimates",
                "Annual population trends",
                "Intercensal estimates",
                "Quick population assessments"
            ],
            alternatives=[
                "decennial_2020", "acs_5yr_2020"
            ],
            data_quality_notes="Modeled estimates based on administrative records",
            last_updated="2023-12-19",
            next_update="2024-12-19",
            api_endpoint="https://api.census.gov/data/2023/pep/population",
            download_url="https://www2.census.gov/programs-surveys/popest/datasets/"
        )
        
        # Economic Census (2017)
        self.datasets["economic_census_2017"] = CensusDataset(
            name="Economic Census (2017)",
            survey_type=SurveyType.CENSUS_BUSINESS,
            geography_levels=[
                GeographyLevel.NATION, GeographyLevel.STATE, GeographyLevel.COUNTY,
                GeographyLevel.PLACE, GeographyLevel.ZIP_CODE
            ],
            time_period="2017",
            reliability=DataReliability.HIGH,
            description="Complete count of business establishments every 5 years",
            variables=[
                "business_count", "employment", "payroll", "sales_receipts",
                "industry_classification", "business_size"
            ],
            limitations=[
                "5-year intervals",
                "Limited to business establishments",
                "Not all industries covered"
            ],
            best_for=[
                "Business analysis",
                "Economic development",
                "Industry analysis",
                "Employment studies"
            ],
            alternatives=[
                "acs_5yr_2020", "business_patterns_2022"
            ],
            data_quality_notes="Complete count of business establishments",
            last_updated="2019-12-19",
            next_update="2024-12-19",
            api_endpoint="https://api.census.gov/data/2017/ecnbasic",
            download_url="https://www2.census.gov/programs-surveys/economic-census/data/2017/"
        )
    
    def _initialize_relationships(self):
        """Initialize relationships between Census datasets."""
        
        # Decennial vs ACS relationships
        self.relationships.append(DatasetRelationship(
            primary_dataset="decennial_2020",
            related_dataset="acs_5yr_2020",
            relationship_type="complements",
            description="Decennial provides official counts, ACS provides detailed characteristics",
            when_to_use_primary="Need official population counts or basic demographics",
            when_to_use_related="Need detailed socioeconomic data or recent trends",
            overlap_period="2020",
            compatibility_score=0.9
        ))
        
        # ACS 1-year vs 5-year relationships
        self.relationships.append(DatasetRelationship(
            primary_dataset="acs_5yr_2020",
            related_dataset="acs_1yr_2020",
            relationship_type="supplements",
            description="5-year provides stability, 1-year provides recency",
            when_to_use_primary="Need stable estimates for small geographies",
            when_to_use_related="Need recent data for large geographies",
            overlap_period="2020",
            compatibility_score=0.8
        ))
        
        # Population estimates vs Decennial
        self.relationships.append(DatasetRelationship(
            primary_dataset="decennial_2020",
            related_dataset="population_estimates_2023",
            relationship_type="replaces",
            description="Population estimates update decennial counts annually",
            when_to_use_primary="Need official 2020 counts",
            when_to_use_related="Need current population estimates",
            overlap_period=None,
            compatibility_score=0.7
        ))
        
        # Economic Census vs ACS
        self.relationships.append(DatasetRelationship(
            primary_dataset="economic_census_2017",
            related_dataset="acs_5yr_2020",
            relationship_type="complements",
            description="Economic Census provides business data, ACS provides demographic context",
            when_to_use_primary="Need business establishment data",
            when_to_use_related="Need demographic context for business analysis",
            overlap_period="2017-2020",
            compatibility_score=0.6
        ))
    
    def get_dataset_info(self, dataset_name: str) -> Optional[CensusDataset]:
        """Get information about a specific dataset."""
        return self.datasets.get(dataset_name)
    
    def list_datasets_by_type(self, survey_type: SurveyType) -> List[CensusDataset]:
        """List all datasets of a specific survey type."""
        return [dataset for dataset in self.datasets.values() 
                if dataset.survey_type == survey_type]
    
    def list_datasets_by_geography(self, geography_level: GeographyLevel) -> List[CensusDataset]:
        """List all datasets available for a specific geography level."""
        return [dataset for dataset in self.datasets.values() 
                if geography_level in dataset.geography_levels]
    
    def get_best_dataset_for_use_case(self, use_case: str, 
                                    geography_level: GeographyLevel,
                                    time_period: Optional[str] = None) -> List[CensusDataset]:
        """
        Get the best dataset(s) for a specific use case.
        
        Args:
            use_case: Description of what you're trying to analyze
            geography_level: Required geography level
            time_period: Specific time period (optional)
        
        Returns:
            List of recommended datasets, ranked by suitability
        """
        
        suitable_datasets = []
        
        for dataset in self.datasets.values():
            if geography_level not in dataset.geography_levels:
                continue
            
            # Score dataset based on use case
            score = self._score_dataset_for_use_case(dataset, use_case, time_period)
            
            if score > 0:
                suitable_datasets.append((dataset, score))
        
        # Sort by score (highest first)
        suitable_datasets.sort(key=lambda x: x[1], reverse=True)
        
        return [dataset for dataset, score in suitable_datasets]
    
    def _score_dataset_for_use_case(self, dataset: CensusDataset, 
                                  use_case: str, 
                                  time_period: Optional[str]) -> float:
        """Score a dataset for a specific use case."""
        
        score = 0.0
        
        # Check if use case matches dataset's best_for categories
        use_case_lower = use_case.lower()
        for category in dataset.best_for:
            if category.lower() in use_case_lower:
                score += 2.0
        
        # Reliability scoring
        if dataset.reliability == DataReliability.HIGH:
            score += 1.5
        elif dataset.reliability == DataReliability.MEDIUM:
            score += 1.0
        elif dataset.reliability == DataReliability.LOW:
            score += 0.5
        
        # Time period scoring
        if time_period:
            # Prefer more recent data
            try:
                dataset_date = datetime.strptime(dataset.time_period, "%Y-%m-%d")
                target_date = datetime.strptime(time_period, "%Y-%m-%d")
                years_diff = abs((dataset_date - target_date).days / 365.25)
                
                if years_diff <= 1:
                    score += 1.0
                elif years_diff <= 3:
                    score += 0.5
                elif years_diff <= 5:
                    score += 0.2
            except ValueError:
                # Handle different date formats
                pass
        
        return score
    
    def get_dataset_relationships(self, dataset_name: str) -> List[DatasetRelationship]:
        """Get all relationships for a specific dataset."""
        return [rel for rel in self.relationships 
                if rel.primary_dataset == dataset_name or rel.related_dataset == dataset_name]
    
    def compare_datasets(self, dataset1_name: str, dataset2_name: str) -> Dict[str, Any]:
        """Compare two datasets side by side."""
        
        dataset1 = self.datasets.get(dataset1_name)
        dataset2 = self.datasets.get(dataset2_name)
        
        if not dataset1 or not dataset2:
            return {"error": "One or both datasets not found"}
        
        comparison = {
            "dataset1": {
                "name": dataset1.name,
                "survey_type": dataset1.survey_type.value,
                "time_period": dataset1.time_period,
                "reliability": dataset1.reliability.value,
                "geography_levels": [level.value for level in dataset1.geography_levels],
                "variables": dataset1.variables,
                "limitations": dataset1.limitations,
                "best_for": dataset1.best_for
            },
            "dataset2": {
                "name": dataset2.name,
                "survey_type": dataset2.survey_type.value,
                "time_period": dataset2.time_period,
                "reliability": dataset2.reliability.value,
                "geography_levels": [level.value for level in dataset2.geography_levels],
                "variables": dataset2.variables,
                "limitations": dataset2.limitations,
                "best_for": dataset2.best_for
            },
            "comparison": {
                "reliability_difference": self._compare_reliability(dataset1.reliability, dataset2.reliability),
                "geography_overlap": self._get_geography_overlap(dataset1.geography_levels, dataset2.geography_levels),
                "variable_overlap": self._get_variable_overlap(dataset1.variables, dataset2.variables),
                "when_to_use_dataset1": dataset1.best_for,
                "when_to_use_dataset2": dataset2.best_for
            }
        }
        
        return comparison
    
    def _compare_reliability(self, reliability1: DataReliability, 
                           reliability2: DataReliability) -> str:
        """Compare reliability levels between two datasets."""
        
        reliability_order = [DataReliability.HIGH, DataReliability.MEDIUM, 
                           DataReliability.LOW, DataReliability.ESTIMATED]
        
        idx1 = reliability_order.index(reliability1)
        idx2 = reliability_order.index(reliability2)
        
        if idx1 < idx2:
            return f"{reliability1.value} is more reliable than {reliability2.value}"
        elif idx1 > idx2:
            return f"{reliability2.value} is more reliable than {reliability1.value}"
        else:
            return f"Both datasets have {reliability1.value} reliability"
    
    def _get_geography_overlap(self, levels1: List[GeographyLevel], 
                              levels2: List[GeographyLevel]) -> List[str]:
        """Get overlapping geography levels between two datasets."""
        overlap = set(levels1) & set(levels2)
        return [level.value for level in overlap]
    
    def _get_variable_overlap(self, variables1: List[str], 
                             variables2: List[str]) -> List[str]:
        """Get overlapping variables between two datasets."""
        return list(set(variables1) & set(variables2))
    
    def get_data_selection_guide(self, analysis_type: str, 
                                geography_level: GeographyLevel,
                                time_sensitivity: str = "medium") -> Dict[str, Any]:
        """
        Get a comprehensive guide for selecting Census data.
        
        Args:
            analysis_type: Type of analysis (e.g., "demographics", "business", "housing")
            geography_level: Required geography level
            time_sensitivity: How time-sensitive the analysis is ("low", "medium", "high")
        
        Returns:
            Dictionary with data selection recommendations
        """
        
        # Get suitable datasets
        suitable_datasets = self.get_best_dataset_for_use_case(
            analysis_type, geography_level
        )
        
        if not suitable_datasets:
            return {"error": "No suitable datasets found for the specified criteria"}
        
        # Rank by time sensitivity
        if time_sensitivity == "high":
            # Prefer more recent data
            suitable_datasets.sort(key=lambda x: x.time_period, reverse=True)
        elif time_sensitivity == "low":
            # Prefer more reliable data
            suitable_datasets.sort(key=lambda x: x.reliability.value)
        
        primary_recommendation = suitable_datasets[0]
        alternatives = suitable_datasets[1:3] if len(suitable_datasets) > 1 else []
        
        guide = {
            "analysis_type": analysis_type,
            "geography_level": geography_level.value,
            "time_sensitivity": time_sensitivity,
            "primary_recommendation": {
                "dataset": primary_recommendation.name,
                "reason": f"Best balance of reliability, recency, and suitability for {analysis_type}",
                "survey_type": primary_recommendation.survey_type.value,
                "time_period": primary_recommendation.time_period,
                "reliability": primary_recommendation.reliability.value
            },
            "alternatives": [
                {
                    "dataset": alt.name,
                    "reason": f"Alternative option for {analysis_type}",
                    "survey_type": alt.survey_type.value,
                    "time_period": alt.time_period,
                    "reliability": alt.reliability.value
                }
                for alt in alternatives
            ],
            "considerations": [
                "Check margins of error for small geographies",
                "Consider combining multiple datasets for comprehensive analysis",
                "Verify data availability for your specific geography",
                "Account for different survey methodologies"
            ],
            "api_endpoints": {
                primary_recommendation.name: primary_recommendation.api_endpoint
            }
        }
        
        return guide
    
    def export_dataset_catalog(self, filepath: str):
        """Export the complete dataset catalog to JSON."""
        
        catalog = {
            "datasets": {
                name: {
                    "name": dataset.name,
                    "survey_type": dataset.survey_type.value,
                    "geography_levels": [level.value for level in dataset.geography_levels],
                    "time_period": dataset.time_period,
                    "reliability": dataset.reliability.value,
                    "description": dataset.description,
                    "variables": dataset.variables,
                    "limitations": dataset.limitations,
                    "best_for": dataset.best_for,
                    "alternatives": dataset.alternatives,
                    "data_quality_notes": dataset.data_quality_notes,
                    "last_updated": dataset.last_updated,
                    "next_update": dataset.next_update,
                    "api_endpoint": dataset.api_endpoint,
                    "download_url": dataset.download_url
                }
                for name, dataset in self.datasets.items()
            },
            "relationships": [
                {
                    "primary_dataset": rel.primary_dataset,
                    "related_dataset": rel.related_dataset,
                    "relationship_type": rel.relationship_type,
                    "description": rel.description,
                    "when_to_use_primary": rel.when_to_use_primary,
                    "when_to_use_related": rel.when_to_use_related,
                    "overlap_period": rel.overlap_period,
                    "compatibility_score": rel.compatibility_score
                }
                for rel in self.relationships
            ],
            "metadata": {
                "last_updated": datetime.now().isoformat(),
                "total_datasets": len(self.datasets),
                "total_relationships": len(self.relationships)
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(catalog, f, indent=2)
        
        print(f"Dataset catalog exported to {filepath}")

# Convenience functions
def get_census_dataset_mapper() -> CensusDatasetMapper:
    """Get a configured Census dataset mapper instance."""
    return CensusDatasetMapper()

def get_best_dataset_for_analysis(analysis_type: str,
                                geography_level: str,
                                time_sensitivity: str = "medium") -> Dict[str, Any]:
    """
    Convenience function to get the best dataset for analysis.
    
    Args:
        analysis_type: Type of analysis needed
        geography_level: Required geography level
        time_sensitivity: Time sensitivity level
    
    Returns:
        Data selection guide
    """
    mapper = get_census_dataset_mapper()
    geo_level = GeographyLevel(geography_level)
    return mapper.get_data_selection_guide(analysis_type, geo_level, time_sensitivity)

def compare_census_datasets(dataset1_name: str, dataset2_name: str) -> Dict[str, Any]:
    """Convenience function to compare two Census datasets."""
    mapper = get_census_dataset_mapper()
    return mapper.compare_datasets(dataset1_name, dataset2_name)

# Example usage and documentation
if __name__ == "__main__":
    # Example: Get the best dataset for demographic analysis at tract level
    guide = get_best_dataset_for_analysis(
        analysis_type="demographics",
        geography_level="tract",
        time_sensitivity="medium"
    )
    print("Data Selection Guide:")
    print(json.dumps(guide, indent=2))
    
    # Example: Compare decennial census with ACS
    comparison = compare_census_datasets("decennial_2020", "acs_5yr_2020")
    print("\nDataset Comparison:")
    print(json.dumps(comparison, indent=2))

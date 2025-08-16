"""
Intelligent Census Data Selector

This module provides intelligent functions for automatically selecting the best Census datasets
based on analysis requirements, geography needs, and time sensitivity.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
import warnings
from .census_dataset_mapper import (
    CensusDatasetMapper, SurveyType, GeographyLevel, DataReliability,
    get_census_dataset_mapper
)

class CensusDataSelector:
    """
    Intelligent selector for Census data based on analysis requirements.
    
    This class automatically determines the best Census datasets to use for different
    types of analysis, considering factors like:
    - Geography level requirements
    - Time sensitivity
    - Data reliability needs
    - Variable requirements
    - Analysis purpose
    """
    
    def __init__(self):
        self.mapper = get_census_dataset_mapper()
        self.analysis_patterns = self._initialize_analysis_patterns()
    
    def _initialize_analysis_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize patterns for different types of analysis."""
        
        return {
            "demographics": {
                "primary_datasets": ["acs_5yr_2020", "decennial_2020"],
                "variables": ["population", "age", "race", "ethnicity", "income", "education"],
                "geography_preferences": ["tract", "block_group", "county"],
                "time_sensitivity": "medium",
                "reliability_requirement": "medium"
            },
            "housing": {
                "primary_datasets": ["acs_5yr_2020", "decennial_2020"],
                "variables": ["housing_units", "housing_value", "rent", "tenure", "vacancy"],
                "geography_preferences": ["tract", "block_group", "county"],
                "time_sensitivity": "medium",
                "reliability_requirement": "medium"
            },
            "business": {
                "primary_datasets": ["economic_census_2017", "acs_5yr_2020"],
                "variables": ["business_count", "employment", "income", "industry"],
                "geography_preferences": ["county", "place", "zip_code"],
                "time_sensitivity": "low",
                "reliability_requirement": "high"
            },
            "transportation": {
                "primary_datasets": ["acs_5yr_2020"],
                "variables": ["commute_time", "transportation_mode", "vehicle_availability"],
                "geography_preferences": ["tract", "county"],
                "time_sensitivity": "medium",
                "reliability_requirement": "medium"
            },
            "education": {
                "primary_datasets": ["acs_5yr_2020"],
                "variables": ["education_level", "school_enrollment", "field_of_study"],
                "geography_preferences": ["tract", "county"],
                "time_sensitivity": "medium",
                "reliability_requirement": "medium"
            },
            "health": {
                "primary_datasets": ["acs_5yr_2020"],
                "variables": ["health_insurance", "disability_status", "veteran_status"],
                "geography_preferences": ["tract", "county"],
                "time_sensitivity": "medium",
                "reliability_requirement": "medium"
            },
            "poverty": {
                "primary_datasets": ["acs_5yr_2020"],
                "variables": ["poverty_status", "income", "public_assistance"],
                "geography_preferences": ["tract", "county"],
                "time_sensitivity": "medium",
                "reliability_requirement": "medium"
            }
        }
    
    def select_datasets_for_analysis(self, 
                                   analysis_type: str,
                                   geography_level: Union[str, GeographyLevel],
                                   time_period: Optional[str] = None,
                                   variables: Optional[List[str]] = None,
                                   reliability_requirement: Optional[str] = None) -> Dict[str, Any]:
        """
        Select the best Census datasets for a specific analysis.
        
        Args:
            analysis_type: Type of analysis (e.g., "demographics", "housing", "business")
            geography_level: Required geography level
            time_period: Specific time period (optional)
            variables: Required variables (optional)
            reliability_requirement: Reliability requirement ("low", "medium", "high")
        
        Returns:
            Dictionary with dataset recommendations and rationale
        """
        
        # Convert geography level to enum if string
        if isinstance(geography_level, str):
            try:
                geography_level = GeographyLevel(geography_level)
            except ValueError:
                return {"error": f"Invalid geography level: {geography_level}"}
        
        # Get analysis pattern
        pattern = self.analysis_patterns.get(analysis_type.lower())
        if not pattern:
            return {"error": f"Unknown analysis type: {analysis_type}"}
        
        # Override pattern with user requirements
        if reliability_requirement:
            pattern["reliability_requirement"] = reliability_requirement
        
        # Get suitable datasets
        suitable_datasets = self.mapper.get_best_dataset_for_use_case(
            analysis_type, geography_level, time_period
        )
        
        if not suitable_datasets:
            return {"error": f"No suitable datasets found for {analysis_type} at {geography_level.value} level"}
        
        # Filter by reliability requirement
        filtered_datasets = self._filter_by_reliability(
            suitable_datasets, pattern["reliability_requirement"]
        )
        
        # Filter by variable availability
        if variables:
            filtered_datasets = self._filter_by_variables(
                filtered_datasets, variables
            )
        
        # Rank datasets by suitability
        ranked_datasets = self._rank_datasets_by_suitability(
            filtered_datasets, pattern, geography_level, time_period
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            ranked_datasets, analysis_type, geography_level, pattern
        )
        
        return recommendations
    
    def _filter_by_reliability(self, datasets: List, 
                              required_reliability: str) -> List:
        """Filter datasets by reliability requirement."""
        
        reliability_order = ["low", "medium", "high", "estimated"]
        required_idx = reliability_order.index(required_reliability)
        
        filtered = []
        for dataset in datasets:
            dataset_idx = reliability_order.index(dataset.reliability.value)
            if dataset_idx <= required_idx:
                filtered.append(dataset)
        
        return filtered
    
    def _filter_by_variables(self, datasets: List, 
                           required_variables: List[str]) -> List:
        """Filter datasets by variable availability."""
        
        filtered = []
        for dataset in datasets:
            # Check if dataset has most required variables
            available_vars = [var.lower() for var in dataset.variables]
            required_vars = [var.lower() for var in required_variables]
            
            # Calculate variable coverage
            coverage = sum(1 for var in required_vars 
                         if any(req_var in var for req_var in available_vars))
            coverage_ratio = coverage / len(required_vars)
            
            if coverage_ratio >= 0.5:  # At least 50% coverage
                filtered.append((dataset, coverage_ratio))
        
        # Sort by coverage and return datasets only
        filtered.sort(key=lambda x: x[1], reverse=True)
        return [dataset for dataset, coverage in filtered]
    
    def _rank_datasets_by_suitability(self, datasets: List,
                                    pattern: Dict,
                                    geography_level: GeographyLevel,
                                    time_period: Optional[str]) -> List[Tuple]:
        """Rank datasets by suitability for the analysis."""
        
        ranked = []
        
        for dataset in datasets:
            score = 0.0
            
            # Geography preference scoring
            if geography_level.value in pattern.get("geography_preferences", []):
                score += 2.0
            
            # Pattern dataset preference
            if dataset.name in pattern.get("primary_datasets", []):
                score += 1.5
            
            # Reliability scoring
            reliability_order = ["low", "medium", "high", "estimated"]
            dataset_idx = reliability_order.index(dataset.reliability.value)
            pattern_idx = reliability_order.index(pattern["reliability_requirement"])
            
            if dataset_idx <= pattern_idx:
                score += 1.0
            
            # Time period scoring
            if time_period:
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
                    pass
            
            ranked.append((dataset, score))
        
        # Sort by score (highest first)
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked
    
    def _generate_recommendations(self, ranked_datasets: List[Tuple],
                                analysis_type: str,
                                geography_level: GeographyLevel,
                                pattern: Dict) -> Dict[str, Any]:
        """Generate comprehensive dataset recommendations."""
        
        if not ranked_datasets:
            return {"error": "No suitable datasets found after filtering"}
        
        primary_dataset, primary_score = ranked_datasets[0]
        alternatives = ranked_datasets[1:3] if len(ranked_datasets) > 1 else []
        
        recommendations = {
            "analysis_type": analysis_type,
            "geography_level": geography_level.value,
            "primary_recommendation": {
                "dataset": primary_dataset.name,
                "survey_type": primary_dataset.survey_type.value,
                "time_period": primary_dataset.time_period,
                "reliability": primary_dataset.reliability.value,
                "score": primary_score,
                "rationale": self._generate_rationale(primary_dataset, pattern),
                "variables": primary_dataset.variables,
                "limitations": primary_dataset.limitations,
                "api_endpoint": primary_dataset.api_endpoint
            },
            "alternatives": [
                {
                    "dataset": alt_dataset.name,
                    "survey_type": alt_dataset.survey_type.value,
                    "time_period": alt_dataset.time_period,
                    "reliability": alt_dataset.reliability.value,
                    "score": alt_score,
                    "rationale": f"Alternative option with {alt_score:.1f} suitability score"
                }
                for alt_dataset, alt_score in alternatives
            ],
            "data_quality_notes": primary_dataset.data_quality_notes,
            "considerations": [
                "Check margins of error for small geographies",
                "Verify data availability for your specific area",
                "Consider combining multiple datasets for comprehensive analysis",
                "Account for different survey methodologies and time periods"
            ],
            "next_steps": [
                f"Download {primary_dataset.name} data using the provided API endpoint",
                "Review data quality notes and limitations",
                "Consider supplementing with alternative datasets if needed",
                "Validate data against known benchmarks for your area"
            ]
        }
        
        return recommendations
    
    def _generate_rationale(self, dataset, pattern: Dict) -> str:
        """Generate rationale for dataset selection."""
        
        rationales = []
        
        if dataset.name in pattern.get("primary_datasets", []):
            rationales.append("Matches primary dataset pattern for this analysis type")
        
        if dataset.reliability.value == pattern.get("reliability_requirement", "medium"):
            rationales.append("Meets reliability requirements")
        elif dataset.reliability.value == "high":
            rationales.append("Exceeds reliability requirements")
        
        if "tract" in [level.value for level in dataset.geography_levels]:
            rationales.append("Provides detailed geographic coverage")
        
        if dataset.survey_type == SurveyType.ACS_5YR:
            rationales.append("5-year estimates provide stable data for small areas")
        elif dataset.survey_type == SurveyType.DECENNIAL:
            rationales.append("Official count data with highest reliability")
        
        return "; ".join(rationales) if rationales else "Best available option for requirements"
    
    def get_dataset_compatibility_matrix(self, analysis_types: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Generate a compatibility matrix showing which datasets work best for different analysis types.
        
        Args:
            analysis_types: List of analysis types to include (default: all)
        
        Returns:
            DataFrame with compatibility scores
        """
        
        if analysis_types is None:
            analysis_types = list(self.analysis_patterns.keys())
        
        # Get all available datasets
        all_datasets = list(self.mapper.datasets.keys())
        
        # Create compatibility matrix
        matrix_data = []
        
        for analysis_type in analysis_types:
            pattern = self.analysis_patterns[analysis_type]
            row = {"analysis_type": analysis_type}
            
            for dataset_name in all_datasets:
                dataset = self.mapper.datasets[dataset_name]
                
                # Calculate compatibility score
                score = self._calculate_compatibility_score(dataset, pattern)
                row[dataset_name] = score
            
            matrix_data.append(row)
        
        df = pd.DataFrame(matrix_data)
        df.set_index("analysis_type", inplace=True)
        
        return df
    
    def _calculate_compatibility_score(self, dataset, pattern: Dict) -> float:
        """Calculate compatibility score between dataset and analysis pattern."""
        
        score = 0.0
        
        # Dataset preference
        if dataset.name in pattern.get("primary_datasets", []):
            score += 2.0
        
        # Variable coverage
        pattern_vars = pattern.get("variables", [])
        if pattern_vars:
            coverage = sum(1 for var in pattern_vars 
                         if any(pat_var.lower() in var.lower() 
                               for pat_var in dataset.variables))
            score += (coverage / len(pattern_vars)) * 1.0
        
        # Geography preference
        if any(level.value in pattern.get("geography_preferences", []) 
               for level in dataset.geography_levels):
            score += 1.0
        
        # Reliability match
        reliability_order = ["low", "medium", "high", "estimated"]
        dataset_idx = reliability_order.index(dataset.reliability.value)
        pattern_idx = reliability_order.index(pattern.get("reliability_requirement", "medium"))
        
        if dataset_idx <= pattern_idx:
            score += 1.0
        
        return min(score, 5.0)  # Cap at 5.0
    
    def suggest_analysis_approach(self, 
                                analysis_type: str,
                                geography_level: Union[str, GeographyLevel],
                                time_constraints: Optional[str] = None) -> Dict[str, Any]:
        """
        Suggest the best approach for conducting a specific analysis.
        
        Args:
            analysis_type: Type of analysis needed
            geography_level: Required geography level
            time_constraints: Time constraints ("quick", "standard", "comprehensive")
        
        Returns:
            Dictionary with analysis approach recommendations
        """
        
        # Get dataset recommendations
        recommendations = self.select_datasets_for_analysis(
            analysis_type, geography_level
        )
        
        if "error" in recommendations:
            return recommendations
        
        # Generate analysis approach
        approach = {
            "analysis_type": analysis_type,
            "geography_level": geography_level.value if isinstance(geography_level, GeographyLevel) else geography_level,
            "recommended_approach": self._generate_analysis_approach(
                recommendations, time_constraints
            ),
            "data_sources": recommendations["primary_recommendation"],
            "methodology_notes": self._generate_methodology_notes(recommendations),
            "quality_checks": self._generate_quality_checks(recommendations),
            "reporting_considerations": self._generate_reporting_considerations(recommendations)
        }
        
        return approach
    
    def _generate_analysis_approach(self, recommendations: Dict, 
                                  time_constraints: Optional[str]) -> str:
        """Generate recommended analysis approach."""
        
        primary = recommendations["primary_recommendation"]
        
        if primary["survey_type"] == "acs_5yr":
            approach = "Use 5-year ACS estimates for stable, detailed analysis"
        elif primary["survey_type"] == "decennial":
            approach = "Use decennial census for official counts and basic demographics"
        elif primary["survey_type"] == "economic_census":
            approach = "Use economic census for business and employment data"
        else:
            approach = f"Use {primary['dataset']} for primary analysis"
        
        if time_constraints == "quick":
            approach += ". Supplement with population estimates for current data if needed."
        elif time_constraints == "comprehensive":
            approach += ". Consider combining multiple datasets for comprehensive coverage."
        
        return approach
    
    def _generate_methodology_notes(self, recommendations: Dict) -> List[str]:
        """Generate methodology notes for the analysis."""
        
        notes = []
        primary = recommendations["primary_recommendation"]
        
        if primary["survey_type"] == "acs_5yr":
            notes.extend([
                "5-year estimates represent average conditions over 2016-2020",
                "Check margins of error for small geographies",
                "Consider statistical significance when comparing areas"
            ])
        elif primary["survey_type"] == "decennial":
            notes.extend([
                "Data represents conditions as of April 1, 2020",
                "100% count data with no sampling error",
                "Limited to basic demographic questions"
            ])
        
        notes.append(f"Data reliability: {primary['reliability']}")
        notes.append(f"Last updated: {primary.get('last_updated', 'Unknown')}")
        
        return notes
    
    def _generate_quality_checks(self, recommendations: Dict) -> List[str]:
        """Generate data quality check recommendations."""
        
        checks = [
            "Verify geography boundaries match your analysis area",
            "Check for missing or suppressed data",
            "Review margins of error for small geographies",
            "Compare with known benchmarks or previous data",
            "Validate against other data sources if available"
        ]
        
        primary = recommendations["primary_recommendation"]
        if primary["survey_type"] == "acs_5yr":
            checks.append("Review ACS data quality flags and notes")
        
        return checks
    
    def _generate_reporting_considerations(self, recommendations: Dict) -> List[str]:
        """Generate reporting considerations."""
        
        considerations = [
            "Clearly state the data source and time period",
            "Include reliability information in your report",
            "Note any limitations or caveats",
            "Provide context for the data (e.g., '5-year average')",
            "Consider margins of error in your conclusions"
        ]
        
        primary = recommendations["primary_recommendation"]
        if primary["reliability"] == "low":
            considerations.append("Emphasize that results are estimates with uncertainty")
        
        return considerations

# Convenience functions
def get_census_data_selector() -> CensusDataSelector:
    """Get a configured Census data selector instance."""
    return CensusDataSelector()

def select_census_datasets(analysis_type: str,
                          geography_level: str,
                          time_period: Optional[str] = None,
                          variables: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Convenience function to select Census datasets for analysis.
    
    Args:
        analysis_type: Type of analysis needed
        geography_level: Required geography level
        time_period: Specific time period (optional)
        variables: Required variables (optional)
    
    Returns:
        Dataset recommendations
    """
    selector = get_census_data_selector()
    return selector.select_datasets_for_analysis(
        analysis_type, geography_level, time_period, variables
    )

def get_analysis_approach(analysis_type: str,
                         geography_level: str,
                         time_constraints: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to get analysis approach recommendations.
    
    Args:
        analysis_type: Type of analysis needed
        geography_level: Required geography level
        time_constraints: Time constraints (optional)
    
    Returns:
        Analysis approach recommendations
    """
    selector = get_census_data_selector()
    return selector.suggest_analysis_approach(
        analysis_type, geography_level, time_constraints
    )

# Example usage
if __name__ == "__main__":
    # Example: Select datasets for demographic analysis
    recommendations = select_census_datasets(
        analysis_type="demographics",
        geography_level="tract",
        variables=["population", "income", "education"]
    )
    print("Dataset Recommendations:")
    print(recommendations)
    
    # Example: Get analysis approach
    approach = get_analysis_approach(
        analysis_type="housing",
        geography_level="county",
        time_constraints="comprehensive"
    )
    print("\nAnalysis Approach:")
    print(approach)

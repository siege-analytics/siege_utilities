# Census Dataset Suitability Scoring System

## Overview

The Census data selection system uses a sophisticated scoring algorithm to rank datasets based on how well they match your analysis requirements. Understanding these scores helps you make informed decisions about which datasets to use.

## Scoring Scale: 0-5 Points

### Score Interpretation
- **0-2.0**: Poor match - Dataset has significant limitations for your analysis
- **2.1-3.0**: Moderate match - Dataset is usable but may have some limitations
- **3.1-4.0**: Good match - Dataset is well-suited for your analysis
- **4.1-5.0**: Excellent match - Dataset is ideal for your specific requirements

## Scoring Criteria

### 1. Geography Match (+2.0 points)
- **Full points**: Dataset supports the exact geography level you need (tract, county, state, etc.)
- **Zero points**: Dataset doesn't support your required geography level

### 2. Primary Dataset Preference (+1.5 points)
- **Full points**: Dataset is in the recommended list for your analysis type (demographics, housing, business)
- **Zero points**: Dataset is not specifically recommended for this analysis type

### 3. Reliability Match (+1.0 points)
- **Full points**: Dataset reliability meets or exceeds your requirements
- **Zero points**: Dataset reliability is below your requirements

### 4. Time Period Alignment (+1.0 points maximum)
- **+1.0 points**: Dataset is within 1 year of your target date
- **+0.5 points**: Dataset is within 3 years of your target date  
- **+0.2 points**: Dataset is within 5 years of your target date
- **Zero points**: Dataset is more than 5 years from your target date

### 5. Variable Coverage (+1.0 points maximum)
- **Proportional scoring**: Based on how many of your required variables are available
- **Example**: If you need 10 variables and dataset has 8, you get +0.8 points

### 6. Geography Preference (+1.0 points)
- **Full points**: Dataset supports your preferred geography level
- **Zero points**: Dataset doesn't support your preferred geography level

## Real-World Example Scores

### Current System Output: ACS 5-Year Estimates (2020) for Demographic Analysis
- **Geography match**: +2.0 (supports county level analysis)
- **Primary dataset**: +0.0 (not in primary_datasets list for demographics pattern)
- **Reliability match**: +1.0 (meets medium reliability requirement)
- **Time period**: +0.0 (no specific time_period provided in request)
- **Variable coverage**: +0.0 (no specific variables requested)
- **Geography preference**: +0.0 (no geography preference specified)
- **Total: 3.0 points → Good match**

### Why Some Scores Are Zero

The scoring system is conservative and only awards points when specific criteria are met:

1. **Primary Dataset (0.0)**: Only awards points if the dataset is explicitly listed in the analysis pattern's `primary_datasets` list
2. **Time Period (0.0)**: Only awards points when you specify a target year in your request
3. **Variable Coverage (0.0)**: Only awards points when you specify required variables
4. **Geography Preference (0.0)**: Only awards points when you specify geography preferences

### How to Get Higher Scores

To maximize your dataset scores, provide more specific requirements:

```python
# Basic request (gets ~3.0 score)
recommendations = su.select_census_datasets(
    analysis_type='demographics',
    geography_level='county'
)

# Detailed request (can get 4.0+ score)
recommendations = su.select_census_datasets(
    analysis_type='demographics',
    geography_level='county',
    time_period='2020',           # Specify target year
    required_variables=['population', 'income'],  # Specify variables
    geography_preferences=['county', 'tract']     # Specify preferences
)
```

## Using Scores in Your Analysis

1. **Primary Recommendation**: Highest scoring dataset (usually 4.0+)
2. **Alternatives**: Lower scoring but viable options (usually 3.0+)
3. **Avoid**: Scores below 3.0 unless no other options exist

## Best Practices

- Always check the rationale provided with each score
- Consider combining multiple datasets for comprehensive analysis
- Review data quality notes and limitations
- Validate scores against your specific requirements

## Technical Notes

- Scores are capped at 5.0 maximum
- The system automatically ranks datasets by score (highest first)
- Ties are broken by reliability and recency
- All scoring is transparent and reproducible

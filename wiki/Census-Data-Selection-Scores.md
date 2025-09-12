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

## Example Scores

### ACS 5-Year Estimates (2020) for Demographic Analysis
- Geography match: +2.0 (supports county level)
- Primary dataset: +1.5 (recommended for demographics)
- Reliability match: +1.0 (meets medium reliability requirement)
- Time period: +1.0 (2020 data is current)
- Variable coverage: +1.0 (covers all demographic variables)
- Geography preference: +1.0 (county is preferred level)
- **Total: 7.5 points (capped at 5.0) → Excellent match**

### ACS 1-Year Estimates (2020) for Demographic Analysis  
- Geography match: +2.0 (supports county level)
- Primary dataset: +1.5 (recommended for demographics)
- Reliability match: +0.0 (below medium reliability requirement)
- Time period: +1.0 (2020 data is current)
- Variable coverage: +0.5 (limited variable coverage)
- Geography preference: +1.0 (county is preferred level)
- **Total: 6.0 points (capped at 5.0) → Excellent match**

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

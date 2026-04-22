#!/usr/bin/env python3
"""
Polling Analysis Module for Siege Utilities
Provides comprehensive cross-tabulation and longitudinal analysis capabilities
"""

import pandas as pd
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from ..chart_generator import ChartGenerator
from siege_utilities.core.logging import log_error

class PollingAnalyzer:
    """
    Comprehensive polling analysis for cross-dimensional analytics
    """

    def __init__(self):
        self.chart_generator = ChartGenerator()
        self.analysis_results = {}

    def create_cross_tabulation_matrix(self,
                                     data: pd.DataFrame,
                                     dimensions: List[str],
                                     metric: str = 'value',
                                     top_n: int = 10) -> Dict[str, pd.DataFrame]:
        """
        Create comprehensive cross-tabulation matrix for all dimension combinations

        Args:
            data: DataFrame with analytics data
            dimensions: List of dimension column names
            metric: Metric column name to aggregate
            top_n: Number of top items to include per dimension

        Returns:
            Dictionary of cross-tabulation DataFrames
        """
        try:
            cross_tabs = {}

            # Create all possible 2-way combinations
            for i, dim1 in enumerate(dimensions):
                for j, dim2 in enumerate(dimensions[i+1:], i+1):
                    combo_name = f"{dim1}_x_{dim2}"

                    # Create cross-tabulation
                    crosstab = pd.crosstab(
                        data[dim1],
                        data[dim2],
                        values=data[metric],
                        aggfunc='sum',
                        fill_value=0
                    )

                    # Get top N items for each dimension
                    top_dim1 = data.groupby(dim1)[metric].sum().nlargest(top_n).index
                    top_dim2 = data.groupby(dim2)[metric].sum().nlargest(top_n).index

                    # Filter to top items
                    filtered_crosstab = crosstab.loc[top_dim1, top_dim2]

                    cross_tabs[combo_name] = filtered_crosstab

            return cross_tabs

        except Exception as e:
            log_error(f"Error creating cross-tabulation matrix: {e}")
            return {}

    def create_longitudinal_analysis(self,
                                   data: pd.DataFrame,
                                   time_column: str,
                                   dimensions: List[str],
                                   metric: str = 'value',
                                   periods: List[str] = ['daily', 'weekly', 'monthly', 'quarterly']) -> Dict[str, pd.DataFrame]:
        """
        Create longitudinal analysis across multiple time periods and dimensions

        Args:
            data: DataFrame with time series data
            time_column: Column containing time information
            dimensions: List of dimension columns to analyze
            metric: Metric column to analyze
            periods: List of time periods to aggregate

        Returns:
            Dictionary of longitudinal analysis DataFrames
        """
        try:
            longitudinal_results = {}

            # Ensure time column is datetime
            data[time_column] = pd.to_datetime(data[time_column])

            for period in periods:
                period_results = {}

                # Create time-based aggregation
                if period == 'daily':
                    data['period'] = data[time_column].dt.date
                elif period == 'weekly':
                    data['period'] = data[time_column].dt.to_period('W')
                elif period == 'monthly':
                    data['period'] = data[time_column].dt.to_period('M')
                elif period == 'quarterly':
                    data['period'] = data[time_column].dt.to_period('Q')

                # Aggregate by period and each dimension
                for dimension in dimensions:
                    period_dim_data = data.groupby(['period', dimension])[metric].sum().reset_index()
                    period_results[dimension] = period_dim_data

                longitudinal_results[period] = period_results

            return longitudinal_results

        except Exception as e:
            log_error(f"Error creating longitudinal analysis: {e}")
            return {}

    def create_performance_rankings(self,
                                  data: pd.DataFrame,
                                  dimensions: List[str],
                                  metric: str = 'value',
                                  top_n: int = 10) -> Dict[str, List[Tuple]]:
        """
        Create performance rankings across all dimensions

        Args:
            data: DataFrame with analytics data
            dimensions: List of dimension columns to rank
            metric: Metric column to rank by
            top_n: Number of top performers to return

        Returns:
            Dictionary of rankings for each dimension
        """
        try:
            rankings = {}

            for dimension in dimensions:
                # Calculate rankings
                dimension_rankings = data.groupby(dimension)[metric].agg(['sum', 'count']).reset_index()
                dimension_rankings['percentage'] = (dimension_rankings['sum'] / dimension_rankings['sum'].sum()) * 100

                # Sort by performance
                dimension_rankings = dimension_rankings.sort_values('sum', ascending=False).head(top_n)

                # Convert to list of tuples
                rankings[dimension] = [
                    (row[dimension], row['sum'], row['percentage'])
                    for _, row in dimension_rankings.iterrows()
                ]

            return rankings

        except Exception as e:
            log_error(f"Error creating performance rankings: {e}")
            return {}

    def create_change_detection_data(self,
                                   current_data: pd.DataFrame,
                                   historical_data: pd.DataFrame,
                                   geographic_column: str = 'geography',
                                   metric: str = 'value') -> pd.DataFrame:
        """
        Create change detection data showing growth/decline patterns

        Args:
            current_data: Current period data
            historical_data: Historical period data
            geographic_column: Column containing geographic information
            metric: Metric to compare

        Returns:
            DataFrame with change detection results
        """
        try:
            # Aggregate current and historical data
            current_agg = current_data.groupby(geographic_column)[metric].sum().reset_index()
            historical_agg = historical_data.groupby(geographic_column)[metric].sum().reset_index()

            # Merge data
            merged = current_agg.merge(
                historical_agg,
                on=geographic_column,
                suffixes=('_current', '_historical'),
                how='outer'
            ).fillna(0)

            # Calculate change percentage
            merged['change_pct'] = (
                (merged[f'{metric}_current'] - merged[f'{metric}_historical']) /
                merged[f'{metric}_historical'] * 100
            ).fillna(0)

            # Add change direction
            merged['change_direction'] = merged['change_pct'].apply(
                lambda x: 'growth' if x > 0 else 'decline' if x < 0 else 'stable'
            )

            return merged

        except Exception as e:
            log_error(f"Error creating change detection data: {e}")
            return pd.DataFrame()

    def create_polling_summary(self,
                             data: Dict[str, pd.DataFrame],
                             metric: str = 'value') -> str:
        """
        Create executive summary for polling analysis

        Args:
            data: Dictionary of DataFrames with different data types
            metric: Metric column name

        Returns:
            Executive summary string
        """
        try:
            # Extract key metrics
            total_value = 0
            dimensions_info = {}

            for data_type, df in data.items():
                if metric in df.columns:
                    total_value += df[metric].sum()
                    dimensions_info[data_type] = len(df)

            # Find top performers
            top_performers = {}
            for data_type, df in data.items():
                if metric in df.columns and not df.empty:
                    top_item = df.nlargest(1, metric).iloc[0]
                    top_performers[data_type] = {
                        'name': top_item.iloc[0],  # First column (usually the dimension)
                        'value': top_item[metric],
                        'percentage': (top_item[metric] / total_value * 100) if total_value > 0 else 0
                    }

            # Create summary
            summary_parts = [
                f"This comprehensive polling analysis examines {total_value:,} {metric} across multiple dimensions."
            ]

            for data_type, info in dimensions_info.items():
                summary_parts.append(f"{data_type.title()}: {info} items")

            summary_parts.append("Key findings include:")

            for data_type, performer in top_performers.items():
                summary_parts.append(
                    f"{performer['name']} leads {data_type} with {performer['value']:,} {metric} "
                    f"({performer['percentage']:.1f}%)"
                )

            summary_parts.append("Cross-dimensional analysis reveals patterns in distribution and performance.")

            return " ".join(summary_parts)

        except Exception as e:
            return f"Polling analysis summary generation failed: {str(e)}"

    def create_heatmap_visualization(self,
                                   crosstab_data: pd.DataFrame,
                                   title: str = "Cross-Tabulation Heatmap",
                                   metric: str = 'value',
                                   figsize: Tuple[int, int] = (10, 8)) -> plt.Figure:
        """
        Create heatmap visualization for cross-tabulation data

        Args:
            crosstab_data: DataFrame with cross-tabulation data
            title: Chart title
            metric: Metric name for colorbar label
            figsize: Figure size tuple

        Returns:
            Matplotlib figure
        """
        try:
            fig, ax = plt.subplots(figsize=figsize)

            # Create heatmap
            sns.heatmap(crosstab_data,
                       annot=True,
                       fmt='d',
                       cmap='YlOrRd',
                       ax=ax,
                       cbar_kws={'label': metric.title()})

            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_xlabel('')
            ax.set_ylabel('')

            plt.tight_layout()
            return fig

        except Exception as e:
            log_error(f"Error creating heatmap visualization: {e}")
            return None

    def create_trend_analysis_chart(self,
                                  longitudinal_data: Dict[str, pd.DataFrame],
                                  dimension: str,
                                  metric: str = 'value',
                                  figsize: Tuple[int, int] = (12, 6)) -> plt.Figure:
        """
        Create trend analysis chart for longitudinal data

        Args:
            longitudinal_data: Dictionary of longitudinal data by period
            dimension: Dimension to analyze
            metric: Metric to plot
            figsize: Figure size tuple

        Returns:
            Matplotlib figure
        """
        try:
            fig, ax = plt.subplots(figsize=figsize)

            # Plot trends for each period
            for period, data in longitudinal_data.items():
                if dimension in data.columns and metric in data.columns:
                    period_data = data.groupby('period')[metric].sum()
                    ax.plot(period_data.index.astype(str), period_data.values,
                           marker='o', label=period, linewidth=2)

            ax.set_title(f'Trend Analysis: {dimension.title()}', fontsize=14, fontweight='bold')
            ax.set_xlabel('Time Period')
            ax.set_ylabel(metric.title())
            ax.legend()
            ax.grid(True, alpha=0.3)

            plt.xticks(rotation=45)
            plt.tight_layout()
            return fig

        except Exception as e:
            log_error(f"Error creating trend analysis chart: {e}")
            return None

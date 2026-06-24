"""
CRM DataFrame adapters for reporting primitives.

Pure functions that reshape CRM DataFrames into the column conventions
expected by ``reporting/`` chart generators and report builders.
Each adapter is DataFrame-in, DataFrame-out — no side effects.
"""

from __future__ import annotations


import pandas as pd

__all__ = [
    "pipeline_adapter",
    "timeseries_adapter",
    "geographic_adapter",
    "tabular_adapter",
]


def pipeline_adapter(
    df: pd.DataFrame,
    *,
    stage_column: str = "stage",
    value_column: str = "amount",
    stage_order: list[str] | None = None,
) -> pd.DataFrame:
    """Reshape opportunity data into pipeline/funnel chart input.

    Groups by *stage_column*, sums *value_column*, and orders stages
    by *stage_order* (or by descending value if not specified).

    Returns:
        DataFrame with columns: ``stage``, ``count``, ``total_value``,
        ``avg_value``.
    """
    if df.empty:
        return pd.DataFrame(columns=["stage", "count", "total_value", "avg_value"])

    grouped = df.groupby(stage_column).agg(
        count=(stage_column, "size"),
        total_value=(value_column, "sum"),
        avg_value=(value_column, "mean"),
    ).reset_index()
    grouped.columns = ["stage", "count", "total_value", "avg_value"]

    if stage_order:
        cat_type = pd.CategoricalDtype(categories=stage_order, ordered=True)
        grouped["stage"] = grouped["stage"].astype(cat_type)
        grouped = grouped.sort_values("stage").reset_index(drop=True)
    else:
        grouped = grouped.sort_values("total_value", ascending=False).reset_index(drop=True)

    return grouped


def timeseries_adapter(
    df: pd.DataFrame,
    *,
    timestamp_column: str = "timestamp",
    value_column: str | None = None,
    freq: str = "D",
    agg: str = "count",
) -> pd.DataFrame:
    """Reshape activity data into time-series chart input.

    Groups records by *freq* (daily, weekly, monthly) and aggregates.
    If *value_column* is None and *agg* is "count", counts records per
    period.

    Returns:
        DataFrame with columns: ``date``, ``value``.
    """
    if df.empty:
        return pd.DataFrame(columns=["date", "value"])

    work = df.copy()
    work[timestamp_column] = pd.to_datetime(work[timestamp_column], errors="coerce")
    work = work.dropna(subset=[timestamp_column])

    if work.empty:
        return pd.DataFrame(columns=["date", "value"])

    work = work.set_index(timestamp_column)

    if value_column and agg != "count":
        resampled = work[value_column].resample(freq).agg(agg)
    else:
        resampled = work.resample(freq).size()

    result = resampled.reset_index()
    result.columns = ["date", "value"]
    return result


def geographic_adapter(
    df: pd.DataFrame,
    *,
    street_column: str = "address_street",
    city_column: str = "address_city",
    state_column: str = "address_state",
    postal_code_column: str = "address_postal_code",
    country_column: str = "address_country",
) -> pd.DataFrame:
    """Extract address components for geocoding and choropleth input.

    Returns a DataFrame with standardized address columns ready for
    ``geo/`` geocoding and boundary lookup.

    Returns:
        DataFrame with columns: ``street``, ``city``, ``state``,
        ``postal_code``, ``country``, plus the original index.
    """
    if df.empty:
        return pd.DataFrame(columns=["street", "city", "state", "postal_code", "country"])

    result = pd.DataFrame({
        "street": df.get(street_column),
        "city": df.get(city_column),
        "state": df.get(state_column),
        "postal_code": df.get(postal_code_column),
        "country": df.get(country_column),
    }, index=df.index)

    result = result.dropna(how="all")
    return result


def tabular_adapter(
    df: pd.DataFrame,
    *,
    columns: list[str] | None = None,
    rename: dict[str, str] | None = None,
    sort_by: str | None = None,
    ascending: bool = True,
    limit: int | None = None,
) -> pd.DataFrame:
    """Prepare any CRM DataFrame for table rendering in PDF/PPTX reports.

    Selects, renames, sorts, and limits columns to produce a
    presentation-ready table.

    Returns:
        DataFrame ready for ``ReportGenerator`` table rendering.
    """
    if df.empty:
        return df

    result = df.copy()

    if columns:
        available = [c for c in columns if c in result.columns]
        result = result[available]

    if rename:
        result = result.rename(columns=rename)

    if sort_by and sort_by in result.columns:
        result = result.sort_values(sort_by, ascending=ascending)

    if limit:
        result = result.head(limit)

    return result.reset_index(drop=True)

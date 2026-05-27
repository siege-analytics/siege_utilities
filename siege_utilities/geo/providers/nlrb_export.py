"""DataFrame export for NLRB records.

Converts NLRBFetchResult or lists of dataclass records into pandas
DataFrames for analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def cases_to_dataframe(cases):
    """Convert a list of NLRBCaseRecord to a DataFrame.

    Args:
        cases: List of NLRBCaseRecord instances, or an NLRBFetchResult.

    Returns:
        pandas DataFrame with one row per case.
    """
    import pandas as pd

    from siege_utilities.geo.providers.nlrb_clients import NLRBFetchResult

    if isinstance(cases, NLRBFetchResult):
        cases = cases.cases
    if not cases:
        return pd.DataFrame()
    return pd.DataFrame([c.to_dict() for c in cases])


def elections_to_dataframe(elections):
    """Convert a list of ElectionRecord to a DataFrame."""
    import pandas as pd

    from siege_utilities.geo.providers.nlrb_clients import NLRBFetchResult

    if isinstance(elections, NLRBFetchResult):
        elections = elections.elections
    if not elections:
        return pd.DataFrame()
    return pd.DataFrame([e.to_dict() for e in elections])


def ulp_charges_to_dataframe(charges):
    """Convert a list of ULPRecord to a DataFrame."""
    import pandas as pd

    from siege_utilities.geo.providers.nlrb_clients import NLRBFetchResult

    if isinstance(charges, NLRBFetchResult):
        charges = charges.ulp_charges
    if not charges:
        return pd.DataFrame()
    return pd.DataFrame([c.to_dict() for c in charges])


def fetch_result_to_dataframes(result):
    """Convert an NLRBFetchResult to a dict of DataFrames.

    Returns:
        Dict with keys 'cases', 'elections', 'ulp_charges', each a DataFrame.
    """
    return {
        "cases": cases_to_dataframe(result),
        "elections": elections_to_dataframe(result),
        "ulp_charges": ulp_charges_to_dataframe(result),
    }

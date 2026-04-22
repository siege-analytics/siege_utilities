"""
Survey hierarchy dataclasses: View → Chain → Cluster → Stack.

Stack   = complete report (all sections + shared WeightScheme)
Cluster = one named section (→ one deck section)
Chain   = one cross-tab slide (question × break variables)
View    = one cell statistic (count, pct, sig flag)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import pandas as pd

if TYPE_CHECKING:
    from ..reporting.pages.page_models import Argument, TableType


# ---------------------------------------------------------------------------
# View — one cell statistic
# ---------------------------------------------------------------------------

@dataclass
class View:
    """A single statistic in one cell of a cross-tabulation."""
    metric: str                  # column name / statistic label
    base: float                  # effective respondent count (weighted sum or raw count)
    count: float                 # weighted or raw count
    pct: Optional[float] = None  # proportion (0–1); None for non-percent views
    sig_flag: Optional[str] = None  # column letter if significantly different
    ci: Optional[float] = None   # 95% confidence interval (MEAN_SCALE only)


# ---------------------------------------------------------------------------
# Chain — one cross-tabulation
# ---------------------------------------------------------------------------

@dataclass
class Chain:
    """One cross-tabulation: row_var × break_vars.

    ``table_type`` drives chart selection, significance testing approach, and
    whether percent bases are respondents (MULTIPLE_RESPONSE) or column totals.

    Fields populated by later pipeline stages (significance testing,
    weighting) are declared here with ``None`` defaults so
    :func:`dataclasses.fields` / :func:`dataclasses.asdict` see them — the
    previous pattern of attaching them dynamically via ``setattr`` broke
    introspection.
    """

    row_var: str
    break_vars: List[str]
    views: Dict[str, List[View]]       # key = break variable value
    table_type: TableType
    base_note: str = ""
    geo_column: Optional[str] = None  # presence triggers map generation
    delta_column: Optional[str] = None  # for LONGITUDINAL: computed change column

    # Populated by siege_utilities.survey.significance.chi_square_flag.
    # None = not yet tested; True/False = tested.
    chi_square_significant: Optional[bool] = None
    chi_square_p: Optional[float] = None

    def to_dataframe(self) -> pd.DataFrame:
        """Render the chain as a display-ready wide DataFrame.

        Columns = break variable values; rows = row variable categories.
        For MULTIPLE_RESPONSE, cells are percents (may exceed 100% column-sum).
        """
        if not self.views:
            return pd.DataFrame()

        records: Dict[str, Dict[str, Any]] = {}
        for break_val, view_list in self.views.items():
            for v in view_list:
                if v.metric not in records:
                    records[v.metric] = {}
                records[v.metric][break_val] = (
                    v.pct * 100 if v.pct is not None else v.count
                )

        df = pd.DataFrame.from_dict(records, orient="index")
        df.index.name = self.row_var
        return df

    def to_argument(self, headline: str, narrative: str) -> Argument:
        """Wrap this Chain in an Argument (calls chart + map builders)."""
        from .render import chain_to_argument
        return chain_to_argument(self, headline=headline, narrative=narrative)


# ---------------------------------------------------------------------------
# Cluster — one named section
# ---------------------------------------------------------------------------

@dataclass
class Cluster:
    """A named group of Chains forming one report section."""
    name: str
    chains: List[Chain] = field(default_factory=list)

    def add_chain(self, chain: Chain) -> "Cluster":
        self.chains.append(chain)
        return self


# ---------------------------------------------------------------------------
# WeightScheme — RIM target marginals
# ---------------------------------------------------------------------------

@dataclass
class WeightScheme:
    """Target marginals for RIM (raking) weighting.

    Example::

        WeightScheme(targets={
            "age_group": {"18-34": 0.25, "35-54": 0.40, "55+": 0.35},
            "gender":    {"M": 0.48, "F": 0.52},
        })
    """

    targets: Dict[str, Dict[Any, float]]
    weight_col: str = "weight"
    max_iterations: int = 1000
    convergence: float = 1e-6

    def validate(self) -> None:
        for var, marginals in self.targets.items():
            total = sum(marginals.values())
            if abs(total - 1.0) > 1e-4:
                raise ValueError(
                    f"WeightScheme targets for '{var}' sum to {total:.4f}, expected 1.0"
                )


# ---------------------------------------------------------------------------
# Stack — complete report
# ---------------------------------------------------------------------------

@dataclass
class Stack:
    """A complete survey report: all Clusters + shared WeightScheme."""
    name: str
    clusters: List[Cluster] = field(default_factory=list)
    weight_scheme: Optional[WeightScheme] = None

    def add_cluster(self, cluster: Cluster) -> "Stack":
        self.clusters.append(cluster)
        return self

    @property
    def all_chains(self) -> List[Chain]:
        return [chain for cluster in self.clusters for chain in cluster.chains]

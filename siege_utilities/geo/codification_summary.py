"""Summary portrait for codification.

Assembles headline metrics from block assignment, demographics,
urbanicity, and recency into a structured area portrait.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from .codification import CodificationResult
from .codification_blocks import BlockGroup, SpreadMetrics
from .codification_demographics import DemographicSignature
from .codification_urbanicity import UrbanicityDistribution
from .codification_recency import RecencyAnalysis

log = logging.getLogger(__name__)


@dataclass
class AreaPortrait:
    """Structured summary portrait of a codified area.

    Combines headline metrics from all codification enrichment layers.
    """

    geocoding_summary: dict[str, Any] = field(default_factory=dict)
    spread: Optional[SpreadMetrics] = None
    demographics: Optional[DemographicSignature] = None
    urbanicity: Optional[UrbanicityDistribution] = None
    recency: Optional[RecencyAnalysis] = None
    top_blocks: list[BlockGroup] = field(default_factory=list)

    def headline_metrics(self) -> dict[str, Any]:
        metrics: dict[str, Any] = {}

        metrics.update(self.geocoding_summary)

        if self.spread:
            metrics["block_count"] = self.spread.block_count
            metrics["tract_count"] = self.spread.tract_count
            metrics["county_count"] = self.spread.county_count
            metrics["concentration"] = round(self.spread.concentration, 3)

        if self.demographics:
            metrics["pct_white"] = round(self.demographics.pct_white, 3)
            metrics["pct_black"] = round(self.demographics.pct_black, 3)
            metrics["pct_hispanic"] = round(self.demographics.pct_hispanic, 3)
            metrics["pct_voting_age"] = round(self.demographics.pct_voting_age, 3)

        if self.urbanicity:
            metrics["dominant_category"] = self.urbanicity.dominant_category
            metrics["dominant_locale"] = self.urbanicity.dominant_locale

        if self.recency:
            metrics["median_vintage"] = self.recency.median_vintage
            metrics["new_construction_pct"] = round(self.recency.new_construction_pct, 3)

        return metrics

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "geocoding": self.geocoding_summary,
        }
        if self.spread:
            d["spread"] = {
                "block_count": self.spread.block_count,
                "tract_count": self.spread.tract_count,
                "county_count": self.spread.county_count,
                "state_count": self.spread.state_count,
                "concentration": self.spread.concentration,
                "max_block_pct": self.spread.max_block_pct,
            }
        if self.demographics:
            d["demographics"] = {
                "total_block_population": self.demographics.total_block_population,
                "pct_white": self.demographics.pct_white,
                "pct_black": self.demographics.pct_black,
                "pct_hispanic": self.demographics.pct_hispanic,
                "pct_asian": self.demographics.pct_asian,
                "pct_voting_age": self.demographics.pct_voting_age,
                "pct_housing_occupied": self.demographics.pct_housing_occupied,
            }
        if self.urbanicity:
            d["urbanicity"] = {
                "dominant_category": self.urbanicity.dominant_category,
                "dominant_locale": self.urbanicity.dominant_locale,
                "distribution": self.urbanicity.category_distribution,
            }
        if self.recency:
            d["recency"] = {
                "total_analyzed": self.recency.total_analyzed,
                "median_vintage": self.recency.median_vintage,
                "new_construction_pct": self.recency.new_construction_pct,
                "vintage_distribution": self.recency.vintage_distribution,
            }
        if self.top_blocks:
            d["top_blocks"] = [
                {
                    "block_geoid": b.block_geoid,
                    "address_count": b.address_count,
                    "tract_geoid": b.tract_geoid,
                }
                for b in self.top_blocks
            ]
        return d


def build_portrait(
    codification: CodificationResult,
    spread: Optional[SpreadMetrics] = None,
    demographics: Optional[DemographicSignature] = None,
    urbanicity: Optional[UrbanicityDistribution] = None,
    recency: Optional[RecencyAnalysis] = None,
    top_n: int = 10,
) -> AreaPortrait:
    """Build a structured area portrait from codification results.

    Args:
        codification: CodificationResult from codify_area().
        spread: Pre-computed spread metrics.
        demographics: Pre-computed demographic signature.
        urbanicity: Pre-computed urbanicity distribution.
        recency: Pre-computed recency analysis.
        top_n: Number of top blocks to include.
    """
    top_blocks = []
    if codification.blocks:
        sorted_blocks = sorted(
            codification.blocks,
            key=lambda b: b.address_count,
            reverse=True,
        )[:top_n]
        top_blocks = [
            BlockGroup(
                block_geoid=b.block_geoid,
                tract_geoid=b.tract_geoid,
                county_geoid=b.county_geoid,
                state_geoid=b.state_geoid,
                address_count=b.address_count,
            )
            for b in sorted_blocks
        ]

    return AreaPortrait(
        geocoding_summary=codification.summarize(),
        spread=spread,
        demographics=demographics,
        urbanicity=urbanicity,
        recency=recency,
        top_blocks=top_blocks,
    )

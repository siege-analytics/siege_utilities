"""
Census API subpackage — split components of CensusAPIClient.

Each module handles one concern:

- **variable_registry** — variable groups, descriptions, lookup, metadata
- **dataset_selector** — pure-logic dataset/geography validation and URL building
- **api** — HTTP transport, caching, rate limiting, response processing
- **catalog** — hierarchical table metadata (Dataset → Subject → Family → Table → Variable)
- **catalog_populator** — fetches metadata from Census API to populate the catalog
"""

from .variable_registry import VariableRegistry
from .dataset_selector import DatasetSelector
from .api import CensusAPI
from .catalog_populator import CensusCatalogPopulator
from .catalog import (
    CensusCatalog,
    CensusCatalogDataset,
    CensusFamily,
    CensusSubject,
    CensusTable,
    CensusVariable,
    FamilyType,
)
from . import tiger_state

__all__ = [
    "CensusAPI",
    "CensusCatalog",
    "CensusCatalogPopulator",
    "CensusCatalogDataset",
    "CensusFamily",
    "CensusSubject",
    "CensusTable",
    "CensusVariable",
    "DatasetSelector",
    "FamilyType",
    "VariableRegistry",
    "tiger_state",
]

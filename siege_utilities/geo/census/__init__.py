"""
Census API subpackage — split components of CensusAPIClient.

Each module handles one concern:

- **variable_registry** — variable groups, descriptions, lookup, metadata
- **dataset_selector** — pure-logic dataset/geography validation and URL building
- **api** — HTTP transport, caching, rate limiting, response processing
"""

from .variable_registry import VariableRegistry
from .dataset_selector import DatasetSelector
from .api import CensusAPI

__all__ = [
    "VariableRegistry",
    "DatasetSelector",
    "CensusAPI",
]

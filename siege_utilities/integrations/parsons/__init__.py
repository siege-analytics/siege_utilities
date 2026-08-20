"""TMC Parsons wrappers for siege_utilities.

Wraps `TMC Parsons <https://move-coop.github.io/parsons/>`_ connectors
behind siege's :class:`~siege_utilities.connectors._protocol.ConnectorProtocol`
and :class:`~siege_utilities.connectors._protocol.ConnectorError` hierarchy.
Callers see ``pd.DataFrame`` in / out and typed errors; no direct
``parsons`` import needed on the consumer side.

Install::

    pip install siege_utilities[parsons-core]        # base + adapter
    pip install siege_utilities[parsons-van]         # + VAN / EveryAction
    pip install siege_utilities[parsons-advocacy]    # ElectInfo-persona meta

See :doc:`docs/PARSONS_LICENSE_ANALYSIS`, :doc:`docs/PARSONS_DEP_MATRIX`,
:doc:`docs/PARSONS_AUTH_MATRIX`, and :doc:`docs/parsons_overlap_decision`
for the integration boundaries, extras layout, credential-bridge design,
and reconciliation with existing siege connectors.

Public API — this ``__all__`` is authoritative. New symbols require a
matching entry (see `[rule:writing-code]` writing-code:4 —
"verify before asserting a symbol exists").
"""

from __future__ import annotations

from ._adapter import dataframe_to_parsons_table, parsons_table_to_dataframe
from ._auth import CONNECTOR_KWARG_MAPS, ConnectorKwargSpec, bridge_credentials
from ._errors import map_parsons_exception, translate_errors
from .van import SUPPORTED_OBJECT_TYPES as VAN_SUPPORTED_OBJECT_TYPES
from .van import SiegeEveryAction, SiegeVAN

__all__ = [
    # Adapter
    "parsons_table_to_dataframe",
    "dataframe_to_parsons_table",
    # Error mapping
    "map_parsons_exception",
    "translate_errors",
    # Auth bridge
    "bridge_credentials",
    "CONNECTOR_KWARG_MAPS",
    "ConnectorKwargSpec",
    # Connectors
    "SiegeVAN",
    "SiegeEveryAction",
    "VAN_SUPPORTED_OBJECT_TYPES",
]

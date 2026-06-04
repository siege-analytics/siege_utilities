"""
CRM connector primitives.

Pull/push records from commercial CRMs (Salesforce, HubSpot, Zoho,
Microsoft Dynamics 365) through a unified :class:`ConnectorProtocol`.
CRM data flows into the analytics pipeline — normalize via
``identifiers/``, enrich via ``geo/``, visualize via ``reporting/``.

See ``docs/epics/CRM_INTEGRATIONS_EPIC.md`` for the full epic.
"""

from siege_utilities.connectors._protocol import (
    ConnectorAuthError,
    ConnectorError,
    ConnectorNotFoundError,
    ConnectorProtocol,
    ConnectorRateLimitError,
    UpsertError,
    UpsertResult,
)

__all__ = [
    "ConnectorProtocol",
    "UpsertResult",
    "UpsertError",
    "ConnectorError",
    "ConnectorAuthError",
    "ConnectorRateLimitError",
    "ConnectorNotFoundError",
]

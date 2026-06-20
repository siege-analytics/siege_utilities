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
    "CRMAddress",
    "CRMContact",
    "CRMAccount",
    "CRMOpportunity",
    "CRMActivity",
]

_MODEL_NAMES = {"CRMAddress", "CRMContact", "CRMAccount", "CRMOpportunity", "CRMActivity"}


def __getattr__(name: str):
    if name in _MODEL_NAMES:
        from siege_utilities.connectors._models import (
            CRMAccount,
            CRMActivity,
            CRMAddress,
            CRMContact,
            CRMOpportunity,
        )

        _lazy = {
            "CRMAddress": CRMAddress,
            "CRMContact": CRMContact,
            "CRMAccount": CRMAccount,
            "CRMOpportunity": CRMOpportunity,
            "CRMActivity": CRMActivity,
        }
        globals().update(_lazy)
        return _lazy[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

"""
CRM connector primitives — lazy-loaded.

Pull/push records from commercial CRMs (Salesforce, HubSpot, Zoho,
Microsoft Dynamics 365) through a unified :class:`ConnectorProtocol`.
CRM data flows into the analytics pipeline — normalize via
``identifiers/``, enrich via ``geo/``, visualize via ``reporting/``.

See ``docs/epics/CRM_INTEGRATIONS_EPIC.md`` for the full epic.
"""

import importlib
import sys

_LAZY_IMPORTS = {}


def _register(names, module):
    for name in names:
        _LAZY_IMPORTS[name] = module


# Protocol, error hierarchy, bulk-operation types
_register([
    "ConnectorProtocol",
    "UpsertResult",
    "UpsertError",
    "ConnectorError",
    "ConnectorAuthError",
    "ConnectorRateLimitError",
    "ConnectorNotFoundError",
], "._protocol")

# Canonical CRM data models
_register([
    "CRMAddress",
    "CRMContact",
    "CRMAccount",
    "CRMOpportunity",
    "CRMActivity",
], "._models")

# --- Connector modules (added as workstreams land) ---
_register(["SalesforceConnector", "SOQLQuery"], ".salesforce")
_register(["HubSpotConnector"], ".hubspot")
# _register(["ZohoConnector"], ".zoho")
# _register(["DynamicsConnector"], ".dynamics")

__all__ = list(_LAZY_IMPORTS.keys())


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        mod = importlib.import_module(_LAZY_IMPORTS[name], __package__)
        val = getattr(mod, name)
        setattr(sys.modules[__name__], name, val)
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(list(globals().keys()) + list(_LAZY_IMPORTS.keys())))

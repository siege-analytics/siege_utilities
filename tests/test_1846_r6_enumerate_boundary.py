"""R-1846-6 breadth guarantee for the public-edge redaction boundary (#1846).

Enumerate every public callable actually defined on each connector class --
rather than a hand-maintained method list -- and assert each one carries the
boundary marker set by ``_SecretRedactionMixin._wrap_callable``. A newly added
public method therefore cannot silently escape the boundary, which is what makes
the hand-listed ``pytest.skip`` in test_1846_r5_boundary_allmethods.py a
representative functional spot-check rather than the breadth proof.
"""
import inspect

import pytest

from siege_utilities.connectors.dynamics import DynamicsConnector
from siege_utilities.connectors.hubspot import HubSpotConnector
from siege_utilities.connectors.salesforce import SalesforceConnector
from siege_utilities.connectors.zoho import ZohoConnector

CONNECTORS = [SalesforceConnector, HubSpotConnector, ZohoConnector, DynamicsConnector]


def _boundary_callables(cls):
    """Yield (name, resolved function) for every callable the boundary wraps in
    the class's own namespace: public methods, ``__init__``, and the accessors of
    every property / staticmethod / classmethod descriptor."""
    for name, attr in vars(cls).items():
        public = name == "__init__" or not name.startswith("_")
        if isinstance(attr, (staticmethod, classmethod)):
            func = attr.__func__
            if inspect.isfunction(func) and public:
                yield name, func
        elif isinstance(attr, property):
            for part in (attr.fget, attr.fset, attr.fdel):
                if part is not None:
                    yield name, part
        elif inspect.isfunction(attr) and public:
            yield name, attr


@pytest.mark.parametrize("cls", CONNECTORS, ids=lambda c: c.__name__)
def test_every_public_callable_is_boundary_wrapped(cls):
    unwrapped = [
        name for name, func in _boundary_callables(cls)
        if not getattr(func, "_secret_boundary", False)
    ]
    assert not unwrapped, (
        f"{cls.__name__} public callables escape the redaction boundary: {unwrapped}"
    )


@pytest.mark.parametrize("cls", CONNECTORS, ids=lambda c: c.__name__)
def test_enumeration_is_not_vacuous(cls):
    # A future refactor that relocated every public method onto a shared base
    # would make the wrap check pass by enumerating nothing; require a real
    # surface so the breadth guarantee cannot silently become a no-op.
    assert sum(1 for _ in _boundary_callables(cls)) >= 5

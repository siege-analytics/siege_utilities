"""R-1846-5 breadth check for the public-edge redaction boundary (#1846).

Drives core public connector methods through an upstream transport failure
whose error text equals the configured credential, with a short and a long
value, and asserts the value never appears in the exception's str/repr/args,
its formatted traceback (including any chain), or any captured log record. This
complements the 62-case runtime-sink oracle by covering the create/read/request
surface generically rather than sink by sink.
"""
import logging
import traceback
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from tests.test_1417_crm_retry_idempotency import connector

PROVIDERS = ["salesforce", "hubspot", "zoho", "dynamics"]
LONG = "DUMMYCONFIGUREDSECRET7a4c"
SHORT = "Z7q9xA"

# Core public methods that route an upstream failure to a raise. Each exists on
# all four connectors; absent ones are skipped.
CALLS = [
    ("request", ("POST", "/ordinary")),
    ("create_record", ("Contact", {"name": "Synthetic"})),
    ("update_record", ("Contact", "ordinary-id", {"name": "Synthetic"})),
    ("get_objects", ("Contact",)),
    ("list_object_types", ()),
    ("upsert_records", ("Contact", pd.DataFrame({"external_id": ["ordinary"], "name": ["Synthetic"]}), "external_id")),
]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(requests.Session, "send", Mock(side_effect=AssertionError("NO NETWORK")))
    monkeypatch.setattr("time.sleep", Mock())


def configured(provider, secret):
    c = connector(provider)
    c._client_secret = c._access_token = secret
    c._refresh_token = None
    c._retry_attempts = 1
    c._session.headers["Authorization"] = "Bearer " + secret
    return c


def _surfaces(exc):
    return [
        str(exc),
        repr(exc),
        repr(exc.args),
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    ]


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("secret", [LONG, SHORT])
@pytest.mark.parametrize("name,args", CALLS)
def test_public_method_failure_never_leaks(provider, secret, name, args, caplog):
    c = configured(provider, secret)
    method = getattr(c, name, None)
    # Hard drift guard (#1846 R-1846-7): every CALLS entry must exist on every
    # provider. A skip here would silently stop exercising a method that was
    # renamed or removed, so assert presence instead. Breadth of wrapping is
    # proven separately by test_1846_r6_enumerate_boundary.
    assert method is not None, (
        f"{provider} is missing public CALLS method {name!r}; remove it from CALLS "
        f"or restore it on the connector"
    )
    # Upstream transport failure whose text equals the configured credential.
    c._session.request = Mock(side_effect=ValueError(secret))
    c._session.post = Mock(side_effect=ValueError(secret))
    c._session.put = Mock(side_effect=ValueError(secret))
    caplog.set_level(logging.DEBUG)
    caplog.clear()
    try:
        result = method(*args)
    except BaseException as exc:  # noqa: BLE001 - boundary must scrub every class
        for surface in _surfaces(exc):
            assert secret not in surface, (name, surface)
    else:
        assert secret not in repr(result), (name, repr(result))
    assert secret not in caplog.text, (name, caplog.text)

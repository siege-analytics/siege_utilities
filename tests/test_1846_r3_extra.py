"""R-1846-3 extra coverage: fail-closed logger on a non-sequence collector, and
every declared secret attribute collected for every connector. No real transport.
"""
import logging
from unittest.mock import Mock

import pytest
import requests

from siege_utilities.connectors._protocol import _SECRET_COLLECTION_FAILED
from tests.test_1417_crm_retry_idempotency import connector

LEAK = "REVIEW_ONLY_LEAK_SENTINEL_LONG_9d4f"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(requests.Session, "send", Mock(side_effect=AssertionError("NO NETWORK")))


def test_fail_closed_logger_on_non_sequence_collector(caplog):
    # F2: a collector returning something other than a list/tuple must not leave
    # the adapter redacting against nothing. The arg is dropped and the trusted
    # template plus a suppressed marker is emitted instead.
    c = connector("salesforce")
    c._secret_values = lambda: {"not": "a list or tuple"}
    caplog.set_level(logging.INFO)
    caplog.clear()
    c._log.info("Synthetic upstream result: %s", LEAK)
    assert LEAK not in caplog.text
    assert caplog.records
    assert "suppressed" in caplog.text


def test_fail_closed_logger_when_collector_raises(caplog):
    # F2: a collector that raises is already mapped to the fail-closed sentinel;
    # the adapter must still drop the arg rather than redact against nothing.
    def boom():
        raise RuntimeError("synthetic collector failure")

    c = connector("salesforce")
    c._secret_values = boom
    caplog.set_level(logging.INFO)
    caplog.clear()
    c._log.info("Synthetic upstream result: %s", LEAK)
    assert LEAK not in caplog.text
    assert caplog.records


@pytest.mark.parametrize("provider", ["salesforce", "hubspot", "zoho", "dynamics"])
def test_every_declared_secret_attr_is_collected(provider):
    # F4: every attribute in _SECRET_ATTRS is read by _secret_values for every
    # connector, so a credential stored under any of them is redactable.
    c = connector(provider)
    expected = []
    for index, attr in enumerate(c._SECRET_ATTRS):
        value = f"REVIEW_SECRET_ATTR_{index}_LONGENOUGH_{attr}"
        setattr(c, attr, value)
        expected.append(value)
    collected = c._secret_values()
    assert collected is not _SECRET_COLLECTION_FAILED
    for value in expected:
        assert value in collected

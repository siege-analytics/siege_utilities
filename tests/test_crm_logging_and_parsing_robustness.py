"""CRM connector logging, redaction and parsing stay correct on awkward input.

* The redacting log adapter attributes records to the real caller and never
  turns a mismatched log template into a caller-visible exception.
* Quoted-secret redaction runs in linear time on long backslash runs.
* HubSpot deal probability scales to a percentage without float error.
* HubSpot and Zoho token errors with non-object JSON bodies still raise the
  typed auth error.

Synthetic values only; every send is intercepted.
"""
from __future__ import annotations

import logging
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

import siege_utilities
from siege_utilities.connectors._http import RedactingLogger
from siege_utilities.connectors._protocol import ConnectorAuthError
from siege_utilities.connectors.hubspot import HubSpotConnector
from siege_utilities.core._http import redact_secrets
from tests.crm_connector_factories import connector, response


class _Records(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def adapter() -> Iterator[tuple[RedactingLogger, _Records]]:
    base = logging.getLogger("tests.crm_logging_robustness")
    base.setLevel(logging.DEBUG)
    base.propagate = False
    handler = _Records()
    base.addHandler(handler)
    yield RedactingLogger(base, {}), handler
    base.removeHandler(handler)


def test_log_record_is_attributed_to_the_calling_function(
    adapter: tuple[RedactingLogger, _Records],
) -> None:
    log, handler = adapter
    log.warning("upstream returned %s", 503)
    record, = handler.records
    assert record.funcName == "test_log_record_is_attributed_to_the_calling_function"
    assert record.pathname == __file__


def test_explicit_stacklevel_is_still_honoured(adapter: tuple[RedactingLogger, _Records]) -> None:
    log, handler = adapter

    def helper() -> None:
        log.warning("from helper", stacklevel=2)

    helper()
    record, = handler.records
    assert record.funcName == "test_explicit_stacklevel_is_still_honoured"


@pytest.mark.parametrize("template,args", [
    ("two placeholders %s %s", (1,)),
    ("one placeholder %s", (1, 2)),
    ("numeric %d", ("not-a-number",)),
    ("named %(missing)s", ({"present": 1},)),
])
def test_mismatched_template_logs_instead_of_raising(
    adapter: tuple[RedactingLogger, _Records], template: str, args: tuple,
) -> None:
    log, handler = adapter
    log.warning(template, *args)  # must not raise
    record, = handler.records
    assert record.getMessage().startswith(template)
    assert "could not be formatted" in record.getMessage()


def test_single_mapping_argument_renders_like_stdlib_logging(
    adapter: tuple[RedactingLogger, _Records],
) -> None:
    log, handler = adapter
    log.warning("status %(code)s", {"code": 429})
    record, = handler.records
    assert record.getMessage() == "status 429"


def test_quoted_secret_redaction_is_linear_on_backslash_runs() -> None:
    # 60 backslashes in an unterminated value: a pattern that can split each
    # escape two ways explores ~Fibonacci(60) paths and never returns.
    # The child imports the same source tree as this test, not whatever
    # siege_utilities happens to be installed in the interpreter.
    source_root = str(Path(siege_utilities.__file__).resolve().parents[1])
    code = (
        f"import sys\nsys.path.insert(0, {source_root!r})\n"
        "from siege_utilities.core._http import redact_secrets\n"
        "redact_secrets('{\"token\": \"' + '\\\\' * 60)\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True, timeout=20)


@pytest.mark.parametrize("text", [
    '{"token": "abc\\"def"}',
    "{'token': 'abc\\\\'}",
])
def test_quoted_secret_with_escapes_is_fully_redacted(text: str) -> None:
    redacted = redact_secrets(text)
    assert "abc" not in redacted and "def" not in redacted
    assert "[REDACTED]" in redacted


@pytest.mark.parametrize("fraction,expected", [
    ("0.29", 29.0), (0.29, 29.0), ("0.57", 57.0), (0.07, 7.0), ("1", 100.0),
])
def test_hubspot_probability_scales_without_float_error(fraction: object, expected: float) -> None:
    hubspot = HubSpotConnector.__new__(HubSpotConnector)
    frame = pd.DataFrame([{"id": "deal-1", "properties": {
        "dealname": "Renewal", "hs_deal_stage_probability": fraction,
    }}])
    record, = hubspot.to_crm_opportunities(frame)
    assert record.probability == expected


def test_hubspot_non_numeric_probability_still_raises_value_error() -> None:
    hubspot = HubSpotConnector.__new__(HubSpotConnector)
    frame = pd.DataFrame([{"id": "deal-1", "properties": {
        "dealname": "Renewal", "hs_deal_stage_probability": "high",
    }}])
    with pytest.raises(ValueError):
        hubspot.to_crm_opportunities(frame)


@pytest.mark.parametrize("provider", ["hubspot", "zoho"])
@pytest.mark.parametrize("body", [["invalid_grant"], "invalid_grant", 7])
def test_token_error_with_non_object_json_raises_auth_error(provider: str, body: object) -> None:
    c = connector(provider)
    c._session.post = Mock(return_value=response(400, body))
    with pytest.raises(ConnectorAuthError) as caught:
        c._exchange_token("https://auth.example.test/token", {"grant_type": "refresh_token"})
    assert "auth failed (400)" in str(caught.value)

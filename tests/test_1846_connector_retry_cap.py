"""R2 B1: cap CRM rate-limit waits before calling the platform clock."""

import math
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import Mock
from types import SimpleNamespace

import pytest
import requests

from siege_utilities.connectors._protocol import ConnectorRateLimitError
from tests.test_1417_crm_retry_idempotency import connector, response


PROVIDERS = ["salesforce", "hubspot", "zoho", "dynamics"]


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("hint", ["901", "1e300", "1e999", "inf", "nan", "date"])
def test_connector_over_cap_raises_without_sleep(provider, hint, monkeypatch):
    c = connector(provider)
    if hint == "date":
        hint = format_datetime(datetime.now(timezone.utc) + timedelta(hours=1), usegmt=True)
    sleep = Mock()
    monkeypatch.setattr("time.sleep", sleep)
    c._session.request = Mock(side_effect=[response(429, headers={"Retry-After": hint}), response()])
    with pytest.raises(ConnectorRateLimitError) as caught:
        c.request("GET", "/records")
    delay = caught.value.retry_after
    assert delay is not None
    assert not math.isfinite(delay) or delay > 900
    sleep.assert_not_called()
    c._session.request.assert_called_once()


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("delay", [30, 900])
def test_connector_finite_wait_then_retry(provider, delay, monkeypatch):
    c = connector(provider)
    sleep = Mock()
    monkeypatch.setattr("time.sleep", sleep)
    c._session.request = Mock(side_effect=[response(429, headers={"Retry-After": str(delay)}), response()])
    assert c.request("GET", "/records") == {}
    sleep.assert_called_once_with(delay)
    assert c._session.request.call_count == 2


@pytest.mark.parametrize("provider", PROVIDERS)
def test_connector_custom_wait_cap(provider, monkeypatch):
    c = connector(provider)
    c._max_retry_wait = 10
    sleep = Mock()
    monkeypatch.setattr("time.sleep", sleep)
    c._session.request = Mock(return_value=response(429, headers={"Retry-After": "30"}))
    with pytest.raises(ConnectorRateLimitError) as caught:
        c.request("GET", "/records")
    assert caught.value.retry_after == 30
    sleep.assert_not_called()


def test_connector_retry_helper_caps_fallback(monkeypatch):
    from siege_utilities.connectors._retry import rate_limit_error

    sleep = Mock()
    monkeypatch.setattr("time.sleep", sleep)
    with pytest.raises(ConnectorRateLimitError) as caught:
        rate_limit_error({}, "throttled", 1000)
    assert caught.value.retry_after is None
    sleep.assert_not_called()


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("failure", ["transport", "server"])
def test_connector_exponential_backoff_cannot_overflow(provider, failure, monkeypatch):
    c = connector(provider)
    c._retry_backoff = 1e300
    c._max_retry_wait = 10
    sleep = Mock()
    monkeypatch.setattr("time.sleep", sleep)
    failed = requests.Timeout() if failure == "transport" else response(503)
    c._session.request = Mock(side_effect=[failed, failed, response()])
    assert c.request("GET", "/records") == {}
    assert [call.args for call in sleep.call_args_list] == [(10,), (10,)]


@pytest.mark.parametrize("provider", PROVIDERS)
@pytest.mark.parametrize("cap", [10, -1, float("inf"), float("nan")])
def test_connector_constructor_wait_setting(provider, cap, monkeypatch):
    from siege_utilities.connectors import dynamics

    cls = type(connector(provider))
    kwargs = {"client_id": "id", "client_secret": "secret", "max_retry_wait": cap}
    if provider == "dynamics":
        monkeypatch.setattr(dynamics, "MSAL_AVAILABLE", True)
        monkeypatch.setattr(dynamics, "msal", SimpleNamespace(ConfidentialClientApplication=Mock()), raising=False)
        kwargs.update(environment_url="https://dynamics.example.test", tenant_id="tenant")
    if cap == 10:
        c = cls(**kwargs)
        assert c._max_retry_wait == cap
        c.close()
    else:
        with pytest.raises(ValueError, match="max_retry_wait"):
            cls(**kwargs)

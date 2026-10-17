"""Error-path coverage (SU-4b) for siege_utilities.geo.census.variable_registry.

Forces:
- get_variable_metadata's ``except (RequestException, OSError, ValueError)``
  propagation path
- list_available_variables's re-raise of the same exception family
"""

import pytest
import requests

from siege_utilities.geo.census.variable_registry import VariableRegistry


def test_get_variable_metadata_raises_on_request_failure(monkeypatch):
    reg = VariableRegistry()

    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("network down")

    monkeypatch.setattr(requests, "get", boom)
    # A code that is not in local descriptions forces the API path.
    with pytest.raises(requests.exceptions.ConnectionError):
        reg.get_variable_metadata("ZZ_FAKE_999E", year=2020)


def test_list_available_variables_reraises_on_request_failure(monkeypatch):
    reg = VariableRegistry()

    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("network down")

    monkeypatch.setattr(requests, "get", boom)
    with pytest.raises(requests.exceptions.RequestException):
        reg.list_available_variables(year=2020)

"""Offline contracts for the dual-source Census framework (#1375)."""

from dataclasses import FrozenInstanceError, dataclass
from unittest.mock import AsyncMock, Mock, call

import httpx
import pandas as pd
import pytest
from requests.exceptions import Timeout

from siege_utilities.geo.census.api import CensusAPI
from siege_utilities.geo.census.dual_source import (
    AlternationPolicy,
    ApiSource,
    BulkFileSource,
    CensusDataSource,
    DualSourceCensusClient,
    Provenance,
)
from siege_utilities.geo.census_api_client import (
    CensusAPIError,
    CensusRateLimitError,
)


@dataclass
class FakeSource:
    """Structural source implementation with an observable fetch boundary."""

    name: str
    fetch: Mock


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(
        "requests.sessions.Session.request",
        Mock(side_effect=AssertionError("Live network is forbidden")),
    )


@pytest.fixture
def request_kwargs():
    return {
        "variables": ["B01001_001E"],
        "year": 2022,
        "dataset": "acs5",
        "geography": "county",
        "state_fips": "06",
        "county_fips": "037",
        "include_moe": False,
    }


@pytest.fixture
def frame():
    return pd.DataFrame(
        {"GEOID": ["06037", "06073"], "B01001_001E": [100, 200]},
        index=pd.Index([7, 9], name="row"),
    )


@pytest.fixture
def primary(frame):
    return FakeSource(
        "api", Mock(return_value=(
            frame, Provenance("api", None, 1, False),
        )),
    )


@pytest.fixture
def secondary():
    return FakeSource(
        "bulk", Mock(return_value=(
            pd.DataFrame({"GEOID": ["01001", "01003"], "B01001_001E": [300, 400]}),
            Provenance("bulk", "summary-file.csv", 1, False),
        )),
    )


def test_api_healthy(primary, secondary, request_kwargs):
    source: CensusDataSource = primary
    client = DualSourceCensusClient(source, secondary)

    result, provenance = client.fetch(**request_kwargs)

    assert result is primary.fetch.return_value[0]
    assert provenance == Provenance("api", None, 1, False)
    primary.fetch.assert_called_once_with(**request_kwargs)
    secondary.fetch.assert_not_called()


@pytest.mark.parametrize("budget", [1, 3])
@pytest.mark.parametrize("error_type", [CensusRateLimitError, Timeout])
def test_forced_api_degradation(
    primary, secondary, request_kwargs, budget, error_type,
):
    primary.fetch.side_effect = error_type("API under pressure")
    original_provenance = secondary.fetch.return_value[1]
    client = DualSourceCensusClient(
        primary, secondary, AlternationPolicy(max_api_attempts=budget),
    )

    result, provenance = client.fetch(**request_kwargs)

    assert result is secondary.fetch.return_value[0]
    assert provenance == Provenance(
        "bulk", "summary-file.csv", budget + 1, True,
    )
    assert original_provenance == Provenance(
        "bulk", "summary-file.csv", 1, False,
    )
    assert primary.fetch.call_args_list == [call(**request_kwargs)] * budget
    secondary.fetch.assert_called_once_with(**request_kwargs)


@pytest.mark.parametrize("error_type", [CensusAPIError, OSError])
def test_both_fail_reraises_last_error(
    primary, secondary, request_kwargs, error_type,
):
    primary_error = CensusRateLimitError("API exhausted")
    last_error = error_type("Bulk retrieval failed")
    primary.fetch.side_effect = primary_error
    secondary.fetch.side_effect = last_error
    client = DualSourceCensusClient(primary, secondary)

    with pytest.raises(error_type, match="Bulk retrieval failed") as raised:
        client.fetch(**request_kwargs)

    assert raised.value is last_error
    assert raised.value.__context__ is primary_error
    assert primary.fetch.call_count == 3
    secondary.fetch.assert_called_once_with(**request_kwargs)


@pytest.mark.parametrize("use_secondary", [False, True])
def test_preserves_source_frame_and_provenance_on_every_return(
    primary, secondary, request_kwargs, use_secondary,
):
    if use_secondary:
        primary.fetch.side_effect = CensusRateLimitError("API exhausted")
    source = secondary if use_secondary else primary
    source_frame = source.fetch.return_value[0]
    before = source_frame.copy(deep=True)

    result, provenance = DualSourceCensusClient(primary, secondary).fetch(
        **request_kwargs,
    )

    assert result is source_frame
    assert result.shape == (2, 2)
    pd.testing.assert_frame_equal(result, before)
    assert isinstance(provenance, Provenance)
    assert provenance == (
        Provenance("bulk", "summary-file.csv", 4, True)
        if use_secondary else Provenance("api", None, 1, False)
    )


def test_primary_recovers_within_budget(primary, secondary, request_kwargs):
    primary.fetch.side_effect = [
        CensusRateLimitError("First attempt"),
        Timeout("Second attempt"),
        primary.fetch.return_value,
    ]

    result, provenance = DualSourceCensusClient(primary, secondary).fetch(
        **request_kwargs,
    )

    assert result is primary.fetch.return_value[0]
    assert provenance == Provenance("api", None, 3, False)
    assert primary.fetch.call_args_list == [call(**request_kwargs)] * 3
    secondary.fetch.assert_not_called()


@pytest.mark.parametrize("error_type", [CensusAPIError, ValueError])
def test_unconfigured_primary_error_propagates_immediately(
    primary, secondary, request_kwargs, error_type,
):
    error = error_type("Invalid request")
    primary.fetch.side_effect = error

    with pytest.raises(error_type, match="Invalid request") as raised:
        DualSourceCensusClient(primary, secondary).fetch(**request_kwargs)

    assert raised.value is error
    primary.fetch.assert_called_once_with(**request_kwargs)
    secondary.fetch.assert_not_called()


def test_custom_fallback_errors(primary, secondary, request_kwargs):
    primary.fetch.side_effect = CensusAPIError("Custom fallback")
    policy = AlternationPolicy(
        max_api_attempts=2, fallback_on=(CensusAPIError,),
    )

    result, provenance = DualSourceCensusClient(
        primary, secondary, policy,
    ).fetch(**request_kwargs)

    assert result is secondary.fetch.return_value[0]
    assert provenance == Provenance("bulk", "summary-file.csv", 3, True)
    assert primary.fetch.call_count == 2
    secondary.fetch.assert_called_once_with(**request_kwargs)


def test_empty_fallback_tuple_disables_fallback(
    primary, secondary, request_kwargs,
):
    primary.fetch.side_effect = CensusRateLimitError("No fallback configured")
    policy = AlternationPolicy(fallback_on=())

    with pytest.raises(CensusRateLimitError, match="No fallback configured"):
        DualSourceCensusClient(primary, secondary, policy).fetch(
            **request_kwargs,
        )

    primary.fetch.assert_called_once_with(**request_kwargs)
    secondary.fetch.assert_not_called()


def test_attempts_and_degraded_status_reset_per_request(
    primary, secondary, request_kwargs,
):
    primary.fetch.side_effect = [
        CensusRateLimitError("First request degraded"),
        primary.fetch.return_value,
    ]
    client = DualSourceCensusClient(
        primary, secondary, AlternationPolicy(max_api_attempts=1),
    )

    _, first = client.fetch(**request_kwargs)
    _, second = client.fetch(**request_kwargs)

    assert first == Provenance("bulk", "summary-file.csv", 2, True)
    assert second == Provenance("api", None, 1, False)
    assert primary.fetch.call_count == 2
    secondary.fetch.assert_called_once_with(**request_kwargs)


def test_api_source_forwards_request(frame, request_kwargs):
    api = Mock(spec=CensusAPI)
    api.fetch_data.return_value = frame
    source: CensusDataSource = ApiSource(api)

    result, provenance = source.fetch(**request_kwargs)

    assert source.name == "api"
    assert result is frame
    assert provenance == Provenance("api", None, 1, False)
    api.fetch_data.assert_called_once_with(**request_kwargs)


@pytest.mark.parametrize(
    "error_type", [CensusAPIError, CensusRateLimitError, Timeout],
)
def test_api_source_propagates_errors(request_kwargs, error_type):
    api = Mock(spec=CensusAPI)
    error = error_type("API failure")
    api.fetch_data.side_effect = error

    with pytest.raises(error_type, match="API failure") as raised:
        ApiSource(api).fetch(**request_kwargs)

    assert raised.value is error
    api.fetch_data.assert_called_once_with(**request_kwargs)


def test_wrapped_transport_timeout_triggers_default_fallback(
    secondary, request_kwargs,
):
    api = Mock(spec=CensusAPI)
    error = CensusAPIError("Census API request timed out after 3 attempts")
    error.__cause__ = Timeout("Transport timeout")
    api.fetch_data.side_effect = error

    result, provenance = DualSourceCensusClient(
        ApiSource(api), secondary,
    ).fetch(**request_kwargs)

    assert result is secondary.fetch.return_value[0]
    assert provenance == Provenance("bulk", "summary-file.csv", 4, True)
    assert api.fetch_data.call_args_list == [call(**request_kwargs)] * 3
    secondary.fetch.assert_called_once_with(**request_kwargs)


def test_bulk_source_propagates_transport_error(request_kwargs, monkeypatch):
    source: CensusDataSource = BulkFileSource()
    error = httpx.ReadTimeout("Summary File timeout")
    monkeypatch.setattr(httpx.AsyncClient, "send", AsyncMock(side_effect=error))

    assert source.name == "bulk"
    with pytest.raises(Timeout, match="Summary File timeout") as raised:
        source.fetch(**request_kwargs)
    assert str(raised.value) == str(error)


def test_bulk_transport_error_propagates(primary, request_kwargs, monkeypatch):
    primary.fetch.side_effect = CensusRateLimitError("API exhausted")
    monkeypatch.setattr(
        httpx.AsyncClient, "send", AsyncMock(side_effect=httpx.ReadTimeout("Summary File timeout")),
    )

    with pytest.raises(Timeout, match="Summary File timeout"):
        DualSourceCensusClient(primary, BulkFileSource()).fetch(
            **request_kwargs,
        )

    assert primary.fetch.call_count == 3


def test_provenance_is_frozen():
    provenance = Provenance("api", None, 1, False)

    with pytest.raises(FrozenInstanceError):
        provenance.degraded = True


def test_policy_defaults():
    policy = AlternationPolicy()

    assert policy.max_api_attempts == 3
    assert policy.fallback_on == (CensusRateLimitError, Timeout)
    assert policy.alternate_under_sustained_pressure is False


@pytest.mark.parametrize("budget", [0, -1, 1.5, True, "3"])
def test_policy_rejects_invalid_attempt_budget(budget):
    with pytest.raises(
        ValueError, match="max_api_attempts must be a positive integer",
    ):
        AlternationPolicy(max_api_attempts=budget)

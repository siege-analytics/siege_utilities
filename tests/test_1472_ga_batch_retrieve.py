"""Offline regressions for #1472, using Google SDK doubles at import time."""

import importlib.util
import inspect
import json
import logging
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest


@pytest.fixture
def ga(monkeypatch):
    """Load an isolated module so SDK doubles do not leak to other tests."""
    # Keep output assertions independent of optional parquet engines. The
    # batch still writes files through save_as_pandas and atomic_write_path.
    monkeypatch.setattr(pd.DataFrame, "to_parquet", pd.DataFrame.to_csv)

    class GoogleAuthError(Exception):
        pass

    class RefreshError(GoogleAuthError):
        pass

    class GoogleAPICallError(Exception):
        pass

    credentials = MagicMock(expired=False, refresh_token="test-refresh-token")
    credentials.to_json.return_value = json.dumps({
        "client_id": "test-client", "client_secret": "test-secret",
        "refresh_token": "test-refresh-token",
    })
    oauth = MagicMock()
    oauth.from_authorized_user_file.return_value = credentials
    service = MagicMock()

    def load_service_key(filename, scopes):
        data = json.loads(Path(filename).read_text())
        if not {"client_email", "token_uri"} <= data.keys():
            raise ValueError("Service account info missing fields client_email, token_uri")
        return credentials

    service.from_service_account_file.side_effect = load_service_key
    response = SimpleNamespace(
        dimension_headers=[], metric_headers=[SimpleNamespace(name="sessions")],
        rows=[SimpleNamespace(
            dimension_values=[], metric_values=[SimpleNamespace(value="7")],
        )],
    )
    data_client = MagicMock()
    data_client.return_value.run_report.return_value = response
    flow = MagicMock()
    flow.from_client_config.return_value.run_local_server.return_value = credentials
    build = MagicMock()
    modules = {}

    def sdk_module(name, **attributes):
        if name not in modules:
            module = ModuleType(name)
            module.__path__ = []
            modules[name] = module
            if "." in name:
                parent, child = name.rsplit(".", 1)
                setattr(sdk_module(parent), child, module)
        modules[name].__dict__.update(attributes)
        return modules[name]

    sdk_module("google.oauth2.credentials", Credentials=oauth)
    sdk_module("google.oauth2.service_account", Credentials=service)
    sdk_module("google_auth_oauthlib.flow", InstalledAppFlow=flow)
    sdk_module("google.auth.transport.requests", Request=MagicMock())
    sdk_module("google.auth.exceptions", GoogleAuthError=GoogleAuthError, RefreshError=RefreshError)
    sdk_module("google.api_core.exceptions", GoogleAPICallError=GoogleAPICallError)
    sdk_module("googleapiclient.discovery", build=build)
    sdk_module("google.analytics.data_v1beta", BetaAnalyticsDataClient=data_client)
    sdk_module("google.analytics.data_v1beta.types", **{
        name: SimpleNamespace for name in ("RunReportRequest", "DateRange", "Metric", "Dimension")
    })
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    source = Path(__file__).resolve().parents[1] / "siege_utilities/analytics/google_analytics.py"
    spec = importlib.util.spec_from_file_location("siege_utilities.analytics._ga_1472", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return SimpleNamespace(
        module=module, oauth=oauth, service=service, credentials=credentials,
        flow=flow, build=build, data_client=data_client, response=response,
        GoogleAuthError=GoogleAuthError, RefreshError=RefreshError,
    )


def _profile(ga, tmp_path, property_id="123", kind="service-account", account_type="ga4"):
    if kind == "service-account":
        data = {
            "type": "service_account", "client_email": f"{property_id}@example.test",
            "token_uri": "https://oauth2.googleapis.com/token", "private_key": "test-key",
        }
    else:
        # The token serialized by authenticate() need not include a type or token_uri.
        data = {"client_id": "test-client", "client_secret": "test-secret", "refresh_token": "test-token"}
    path = tmp_path / f"{property_id}.json"
    path.write_text(json.dumps(data))
    profile = ga.module.create_ga_account_profile(
        "client", property_id, account_type=account_type, credentials_file=str(path),
    )
    profile["credential_kind"] = kind
    return profile


def _batch(ga, tmp_path, **kwargs):
    return ga.module.batch_retrieve_ga_data(
        "client", "2026-01-01", "2026-01-31", ["sessions"],
        output_directory=str(tmp_path / "output"), **kwargs,
    )


def test_oauth_token_profile_uses_authorized_user_credentials(ga, tmp_path, monkeypatch):
    """Done-when 1: the documented token-file workflow must return data."""
    token = tmp_path / "ga_token.json"
    token.write_text(ga.credentials.to_json())
    profile = ga.module.create_ga_account_profile("client", "123", credentials_file=str(token))
    monkeypatch.setattr(ga.module, "list_ga_accounts_for_client", lambda *a, **kw: [profile])

    result = _batch(ga, tmp_path)

    assert result["success"], result["errors"]
    assert profile["credential_kind"] == "oauth-token"
    assert result["accounts_processed"] == 1
    ga.oauth.from_authorized_user_file.assert_called_once_with(
        str(token), ["https://www.googleapis.com/auth/analytics.readonly"],
    )
    ga.service.from_service_account_file.assert_not_called()
    ga.build.assert_not_called()
    assert pd.read_csv(result["output_files"][0])["sessions"].tolist() == [7]


def test_both_retrieves_ga4_only_with_sunset_note(ga, tmp_path, monkeypatch, caplog):
    """Done-when 2: both is a GA4-only alias with a visible warning."""
    profile = _profile(ga, tmp_path, account_type="both")
    monkeypatch.setattr(ga.module, "list_ga_accounts_for_client", lambda *a, **kw: [profile])
    with caplog.at_level(logging.WARNING):
        result = _batch(ga, tmp_path)

    assert result["success"], result["errors"]
    assert "GA4-only" in caplog.text
    assert "Universal Analytics" in caplog.text and "sunset" in caplog.text
    ga.data_client.return_value.run_report.assert_called_once()
    ga.build.assert_not_called()


def test_ua_is_rejected_with_sunset_error(ga):
    """Done-when 3: reject UA before credentials or API requests are needed."""
    with pytest.raises(NotImplementedError, match="Universal Analytics.*sunset"):
        ga.module.create_ga_account_profile("client", "123", account_type="ua")
    connector = ga.module.GoogleAnalyticsConnector()
    with pytest.raises(NotImplementedError, match="Universal Analytics.*sunset"):
        connector.get_ua_data("123", "2026-01-01", "2026-01-31", ["ga:sessions"])
    assert "Retrieve data from GA4 and Universal Analytics" not in ga.module.__doc__
    ga.build.assert_not_called()


@pytest.mark.parametrize("error_type", ["GoogleAuthError", "RefreshError"])
@pytest.mark.parametrize("failure_stage", ["authentication", "report"])
def test_auth_error_keeps_results_before_and_after_bad_account(
    ga, tmp_path, monkeypatch, error_type, failure_stage,
):
    """Done-when 4: return the summary and both good accounts' data."""
    profiles = [_profile(ga, tmp_path, str(i)) for i in range(3)]
    monkeypatch.setattr(ga.module, "list_ga_accounts_for_client", lambda *a, **kw: profiles)
    error = getattr(ga, error_type)("test credential rejected")
    if failure_stage == "authentication":
        ga.service.from_service_account_file.side_effect = [ga.credentials, error, ga.credentials]
    else:
        ga.data_client.return_value.run_report.side_effect = [ga.response, error, ga.response]

    result = _batch(ga, tmp_path)

    assert result["success"] is False
    assert result["accounts_processed"] == 2
    assert result["total_rows"] == 2
    assert len(result["errors"]) == 1
    assert "ga_1" in result["errors"][0]
    assert "test credential rejected" in result["errors"][0]
    assert [Path(p).name for p in result["output_files"]] == [
        f"ga_{i}_2026-01-01_2026-01-31.parquet" for i in (0, 2)
    ]
    for path in result["output_files"]:
        assert pd.read_csv(path)["sessions"].tolist() == [7]


def test_batch_finds_profiles_in_custom_config_directory(ga, tmp_path):
    """Done-when 5: exercise actual profile persistence and discovery."""
    profile = _profile(ga, tmp_path)
    config = str(tmp_path / "client-config")
    ga.module.save_ga_account_profile(profile, config_directory=config)

    result = _batch(ga, tmp_path, config_directory=config)

    assert result["success"], result
    assert result["accounts_processed"] == 1
    assert result["total_rows"] == 1


def test_oauth_uses_loopback_and_rejects_retired_oob_uri(ga, tmp_path):
    """Done-when 6: both entry points use loopback and reject OOB."""
    for factory in (ga.module.GoogleAnalyticsConnector, ga.module.create_ga_connector_with_oauth2):
        assert inspect.signature(factory).parameters["redirect_uri"].default is None
        with pytest.raises(ValueError, match="OOB.*retired"):
            factory("client", "secret", redirect_uri="urn:ietf:wg:oauth:2.0:oob")

    connector = ga.module.create_ga_connector_with_oauth2("client", "secret")
    connector.authenticate(str(tmp_path / "new-token.json"))

    config = ga.flow.from_client_config.call_args.args[0]
    assert config["installed"]["redirect_uris"] == ["http://localhost"]
    ga.flow.from_client_config.return_value.run_local_server.assert_called_once_with(port=0)
    assert json.loads((tmp_path / "new-token.json").read_text())["refresh_token"] == "test-refresh-token"
    ga.build.assert_not_called()


def test_service_account_kind_round_trips_and_authenticates(ga, tmp_path):
    key = _profile(ga, tmp_path)["credentials_file"]
    profile = ga.module.create_ga_account_profile(
        "client", "123", credentials_file=key, credential_kind="service-account",
    )
    config = str(tmp_path / "config")
    ga.module.save_ga_account_profile(profile, config_directory=config)
    assert ga.module.load_ga_account_profile("ga_123", config)["credential_kind"] == "service-account"
    assert _batch(ga, tmp_path, config_directory=config)["success"]
    ga.service.from_service_account_file.assert_called_once()
    ga.oauth.from_authorized_user_file.assert_not_called()
    ga.build.assert_not_called()


@pytest.mark.parametrize("kind", ["oauth-token", "service-account"])
def test_existing_profiles_without_credential_kind(ga, tmp_path, monkeypatch, kind):
    profile = _profile(ga, tmp_path, kind=kind)
    del profile["credential_kind"]
    monkeypatch.setattr(ga.module, "list_ga_accounts_for_client", lambda *a, **kw: [profile])
    assert _batch(ga, tmp_path)["success"]


def test_saved_ua_profile_is_reported_without_authenticating(ga, tmp_path, monkeypatch):
    profile = _profile(ga, tmp_path)
    profile["account_type"] = "ua"
    monkeypatch.setattr(ga.module, "list_ga_accounts_for_client", lambda *a, **kw: [profile])
    result = _batch(ga, tmp_path)
    assert result["success"] is False
    assert "Universal Analytics" in result["errors"][0]
    assert "sunset" in result["errors"][0]
    ga.service.from_service_account_file.assert_not_called()
    ga.build.assert_not_called()

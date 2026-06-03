"""Integration test: Narrative 3 — Analytics → Consolidated Data (#780 WS3-T3).

Story: A consultant pulls GA4 web traffic data, transforms it (aggregate
by date, compute derived metrics), and exports a consolidated report.
All API calls are mocked — the test verifies the auth-fetch-transform-export
pipeline, not the API itself.

SU-1 enforcement: expired/invalid auth raises, not returns empty DataFrame.
"""

import importlib
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from siege_utilities.files.operations import safe_json_write, safe_json_read


def _make_ga4_response(dimension_names, metric_names, rows):
    return SimpleNamespace(
        dimension_headers=[SimpleNamespace(name=n) for n in dimension_names],
        metric_headers=[SimpleNamespace(name=n) for n in metric_names],
        rows=[
            SimpleNamespace(
                dimension_values=[SimpleNamespace(value=v) for v in dims],
                metric_values=[SimpleNamespace(value=v) for v in mets],
            )
            for dims, mets in rows
        ],
    )


@pytest.fixture
def ga_connector():
    mock_types = MagicMock()
    mock_types.RunReportRequest = MagicMock()
    mock_types.DateRange = MagicMock()
    mock_types.Metric = MagicMock()
    mock_types.Dimension = MagicMock()
    mock_ga_data = MagicMock()
    mock_ga_data.types = mock_types
    mock_auth_exc = MagicMock()
    mock_auth_exc.GoogleAuthError = type("GoogleAuthError", (Exception,), {})
    mock_api_exc = MagicMock()
    mock_api_exc.GoogleAPICallError = type("GoogleAPICallError", (Exception,), {})

    mock_modules = {
        "google": MagicMock(),
        "google.oauth2": MagicMock(),
        "google.oauth2.credentials": MagicMock(),
        "google_auth_oauthlib": MagicMock(),
        "google_auth_oauthlib.flow": MagicMock(),
        "google.auth": MagicMock(),
        "google.auth.transport": MagicMock(),
        "google.auth.transport.requests": MagicMock(),
        "google.auth.exceptions": mock_auth_exc,
        "googleapiclient": MagicMock(),
        "googleapiclient.discovery": MagicMock(),
        "google.analytics": MagicMock(),
        "google.analytics.data_v1beta": mock_ga_data,
        "google.analytics.data_v1beta.types": mock_types,
        "google.analytics.admin_v1beta": MagicMock(),
        "google.api_core": MagicMock(),
        "google.api_core.exceptions": mock_api_exc,
    }
    with patch.dict("sys.modules", mock_modules):
        import siege_utilities.analytics.google_analytics as ga_mod
        importlib.reload(ga_mod)
        with patch.object(
            ga_mod.GoogleAnalyticsConnector, "__init__", lambda self, **kw: None
        ):
            conn = ga_mod.GoogleAnalyticsConnector()
            conn.ga4_client = MagicMock()
            conn.credentials = MagicMock()
            conn.auth_method = "service_account"
            yield conn, ga_mod


SAMPLE_ROWS = [
    (["2024-01-01"], ["1000", "450", "120.5"]),
    (["2024-01-02"], ["1200", "520", "98.3"]),
    (["2024-01-03"], ["800", "300", "150.0"]),
    (["2024-01-04"], ["1500", "700", "200.75"]),
    (["2024-01-05"], ["950", "410", "110.0"]),
]


@pytest.mark.integration
class TestAnalyticsPipelineNarrative:
    """End-to-end: fetch GA4 → transform → export consolidated data."""

    def test_fetch_transform_export(self, ga_connector, tmp_path):
        conn, ga_mod = ga_connector

        response = _make_ga4_response(
            ["date"],
            ["sessions", "activeUsers", "totalRevenue"],
            SAMPLE_ROWS,
        )
        conn.ga4_client.run_report.return_value = response

        df = conn.get_ga4_data(
            property_id="properties/123456",
            start_date="2024-01-01",
            end_date="2024-01-05",
            metrics=["sessions", "activeUsers", "totalRevenue"],
            dimensions=["date"],
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5
        assert "sessions" in df.columns
        assert "date" in df.columns

        df["sessions"] = pd.to_numeric(df["sessions"], errors="coerce")
        df["activeUsers"] = pd.to_numeric(df["activeUsers"], errors="coerce")
        df["totalRevenue"] = pd.to_numeric(df["totalRevenue"], errors="coerce")
        df["conversion_rate"] = df["activeUsers"] / df["sessions"]

        assert df["conversion_rate"].iloc[0] == pytest.approx(0.45, abs=0.01)

        output_path = str(tmp_path / "consolidated_report.json")
        report = {
            "period": "2024-01-01 to 2024-01-05",
            "total_sessions": int(df["sessions"].sum()),
            "total_users": int(df["activeUsers"].sum()),
            "total_revenue": float(df["totalRevenue"].sum()),
            "avg_conversion_rate": float(df["conversion_rate"].mean()),
        }
        safe_json_write(output_path, report)
        loaded = safe_json_read(output_path)
        assert loaded["total_sessions"] == 5450
        assert loaded["avg_conversion_rate"] > 0

    def test_multi_dimension_aggregation(self, ga_connector):
        conn, ga_mod = ga_connector

        response = _make_ga4_response(
            ["date", "country"],
            ["sessions"],
            [
                (["2024-01-01", "US"], ["500"]),
                (["2024-01-01", "UK"], ["300"]),
                (["2024-01-02", "US"], ["600"]),
                (["2024-01-02", "UK"], ["250"]),
            ],
        )
        conn.ga4_client.run_report.return_value = response

        df = conn.get_ga4_data(
            property_id="properties/123456",
            start_date="2024-01-01",
            end_date="2024-01-02",
            metrics=["sessions"],
            dimensions=["date", "country"],
        )
        assert len(df) == 4

        df["sessions"] = pd.to_numeric(df["sessions"], errors="coerce")
        by_country = df.groupby("country")["sessions"].sum()
        assert by_country["US"] == 1100
        assert by_country["UK"] == 550


@pytest.mark.integration
class TestAnalyticsSU1:
    """SU-1: auth failure must raise, not return empty DataFrame."""

    def test_expired_token_raises(self, ga_connector):
        conn, ga_mod = ga_connector
        conn.ga4_client.run_report.side_effect = Exception(
            "Request had invalid authentication credentials"
        )
        with pytest.raises(Exception, match="invalid authentication"):
            conn.get_ga4_data(
                property_id="properties/123456",
                start_date="2024-01-01",
                end_date="2024-01-05",
                metrics=["sessions"],
            )

    def test_empty_response_returns_empty_dataframe(self, ga_connector):
        conn, ga_mod = ga_connector
        response = _make_ga4_response(["date"], ["sessions"], [])
        conn.ga4_client.run_report.return_value = response

        df = conn.get_ga4_data(
            property_id="properties/123456",
            start_date="2024-01-01",
            end_date="2024-01-05",
            metrics=["sessions"],
            dimensions=["date"],
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

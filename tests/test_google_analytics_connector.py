"""
Tests for GoogleAnalyticsConnector GA4 response parsing.

Covers the two bugs fixed in PR #299:
1. dimension_headers/metric_headers must be read from the Response, not Row objects
2. GA4 API returns metric values as strings — need pd.to_numeric coercion
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, PropertyMock
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Helpers to build mock GA4 API responses
# ---------------------------------------------------------------------------

def _make_header(name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name)


def _make_dimension_value(value: str) -> SimpleNamespace:
    return SimpleNamespace(value=value)


def _make_metric_value(value: str) -> SimpleNamespace:
    """GA4 returns ALL values (including numeric metrics) as strings."""
    return SimpleNamespace(value=value)


def _make_row(dim_values: list[str], metric_values: list[str]) -> SimpleNamespace:
    """Build a mock GA4 Row — contains only values, NOT headers."""
    return SimpleNamespace(
        dimension_values=[_make_dimension_value(v) for v in dim_values],
        metric_values=[_make_metric_value(v) for v in metric_values],
    )


def _make_response(
    dimension_names: list[str],
    metric_names: list[str],
    rows: list[tuple[list[str], list[str]]],
) -> SimpleNamespace:
    """Build a mock RunReportResponse with headers at the response level."""
    return SimpleNamespace(
        dimension_headers=[_make_header(n) for n in dimension_names],
        metric_headers=[_make_header(n) for n in metric_names],
        rows=[_make_row(dims, mets) for dims, mets in rows],
    )


# ---------------------------------------------------------------------------
# Fixture: a connector with a mocked ga4_client
# ---------------------------------------------------------------------------

@pytest.fixture
def connector():
    """Create a GoogleAnalyticsConnector with a mocked GA4 client."""
    with patch.dict("sys.modules", {
        "google.oauth2.credentials": MagicMock(),
        "google_auth_oauthlib.flow": MagicMock(),
        "google.auth.transport.requests": MagicMock(),
        "googleapiclient.discovery": MagicMock(),
        "google.analytics.data_v1beta": MagicMock(),
        "google.analytics.data_v1beta.types": MagicMock(),
    }):
        # Patch the availability flag and imports at module level
        import importlib
        import siege_utilities.analytics.google_analytics as ga_mod
        original_available = ga_mod.GOOGLE_ANALYTICS_AVAILABLE
        ga_mod.GOOGLE_ANALYTICS_AVAILABLE = True

        # Build connector without triggering real auth
        with patch.object(ga_mod.GoogleAnalyticsConnector, "__init__", lambda self, **kw: None):
            conn = ga_mod.GoogleAnalyticsConnector()
            conn.ga4_client = MagicMock()
            conn.credentials = MagicMock()
            conn.auth_method = "service_account"
            conn.analytics_service = None
            conn.service_account_data = None
            conn.client_id = None
            conn.client_secret = None
            conn.redirect_uri = None

        yield conn, ga_mod

        ga_mod.GOOGLE_ANALYTICS_AVAILABLE = original_available


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGA4ResponseParsing:
    """Test that get_ga4_data correctly parses GA4 RunReportResponse."""

    def test_headers_read_from_response_not_rows(self, connector):
        """PR #299 bug 1: headers are at the response level, not per-row."""
        conn, ga_mod = connector
        response = _make_response(
            dimension_names=["date", "country"],
            metric_names=["sessions", "users"],
            rows=[
                (["2025-06-01", "United States"], ["1234", "987"]),
                (["2025-06-01", "Canada"], ["56", "42"]),
            ],
        )
        conn.ga4_client.run_report.return_value = response

        df = conn.get_ga4_data(
            property_id="123456",
            start_date="2025-06-01",
            end_date="2025-06-30",
            metrics=["sessions", "users"],
            dimensions=["date", "country"],
        )

        assert list(df.columns) == ["date", "country", "sessions", "users"]
        assert len(df) == 2
        assert df.iloc[0]["country"] == "United States"
        assert df.iloc[1]["country"] == "Canada"

    def test_metric_columns_are_numeric(self, connector):
        """PR #299 bug 2: GA4 returns metrics as strings; must be coerced to numeric."""
        conn, ga_mod = connector
        response = _make_response(
            dimension_names=["date"],
            metric_names=["sessions", "bounceRate"],
            rows=[
                (["2025-06-01"], ["1500", "0.42"]),
                (["2025-06-02"], ["2000", "0.38"]),
            ],
        )
        conn.ga4_client.run_report.return_value = response

        df = conn.get_ga4_data(
            property_id="123456",
            start_date="2025-06-01",
            end_date="2025-06-02",
            metrics=["sessions", "bounceRate"],
            dimensions=["date"],
        )

        # Metrics should be numeric, not object/string
        assert pd.api.types.is_numeric_dtype(df["sessions"])
        assert pd.api.types.is_numeric_dtype(df["bounceRate"])
        assert df["sessions"].sum() == 3500
        assert df["bounceRate"].iloc[0] == pytest.approx(0.42)

    def test_nlargest_works_on_metric_columns(self, connector):
        """The original crash: nlargest on string columns raises TypeError."""
        conn, ga_mod = connector
        response = _make_response(
            dimension_names=["source"],
            metric_names=["sessions"],
            rows=[
                (["google"], ["500"]),
                (["direct"], ["300"]),
                (["facebook"], ["100"]),
            ],
        )
        conn.ga4_client.run_report.return_value = response

        df = conn.get_ga4_data(
            property_id="123456",
            start_date="2025-06-01",
            end_date="2025-06-30",
            metrics=["sessions"],
            dimensions=["source"],
        )

        # This was the exact operation that failed before the fix
        top = df.nlargest(2, "sessions")
        assert list(top["source"]) == ["google", "direct"]

    def test_empty_response(self, connector):
        """Handle a response with no rows."""
        conn, ga_mod = connector
        response = _make_response(
            dimension_names=["date"],
            metric_names=["sessions"],
            rows=[],
        )
        conn.ga4_client.run_report.return_value = response

        df = conn.get_ga4_data(
            property_id="123456",
            start_date="2025-06-01",
            end_date="2025-06-30",
            metrics=["sessions"],
            dimensions=["date"],
        )

        assert len(df) == 0

    def test_dimensions_only(self, connector):
        """Response with dimensions but no metrics."""
        conn, ga_mod = connector
        response = _make_response(
            dimension_names=["country", "city"],
            metric_names=[],
            rows=[
                (["US", "New York"], []),
                (["CA", "Toronto"], []),
            ],
        )
        conn.ga4_client.run_report.return_value = response

        df = conn.get_ga4_data(
            property_id="123456",
            start_date="2025-06-01",
            end_date="2025-06-30",
            metrics=[],
            dimensions=["country", "city"],
        )

        assert list(df.columns) == ["country", "city"]
        assert len(df) == 2

    def test_no_dimensions(self, connector):
        """Response with metrics only (aggregate totals, no dimensions)."""
        conn, ga_mod = connector
        response = _make_response(
            dimension_names=[],
            metric_names=["sessions", "users"],
            rows=[
                ([], ["16843", "14950"]),
            ],
        )
        conn.ga4_client.run_report.return_value = response

        df = conn.get_ga4_data(
            property_id="123456",
            start_date="2025-06-01",
            end_date="2025-12-31",
            metrics=["sessions", "users"],
        )

        assert len(df) == 1
        assert df.iloc[0]["sessions"] == 16843
        assert df.iloc[0]["users"] == 14950

    def test_not_authenticated_raises(self, connector):
        """get_ga4_data should fail gracefully when not authenticated."""
        conn, ga_mod = connector
        conn.ga4_client = None

        df = conn.get_ga4_data(
            property_id="123456",
            start_date="2025-06-01",
            end_date="2025-06-30",
            metrics=["sessions"],
        )

        # Should return empty DataFrame, not raise
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

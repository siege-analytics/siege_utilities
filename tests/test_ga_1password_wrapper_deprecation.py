"""Test that the 1Password GA wrapper emits DeprecationWarning (ELE-2442)."""
from __future__ import annotations

import warnings
from unittest.mock import patch

import pytest

from siege_utilities.analytics.google_analytics import (
    create_ga_connector_from_1password,
)


class TestCreateGAConnectorFrom1PasswordDeprecation:
    def test_emits_deprecation_warning(self):
        with patch(
            "siege_utilities.analytics.google_analytics.create_ga_connector_with_service_account"
        ) as fake_factory, patch(
            "siege_utilities.config.get_google_service_account_from_1password"
        ) as fake_fetch:
            fake_factory.return_value = "sentinel"
            fake_fetch.return_value = {"client_email": "x"}

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                result = create_ga_connector_from_1password("any-title")

        assert result == "sentinel"
        deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        assert len(deprecations) == 1
        msg = str(deprecations[0].message)
        assert "deprecated" in msg
        assert "get_google_service_account_from_1password" in msg
        assert "create_ga_connector_with_service_account" in msg


class TestDatabricksInitDocstring:
    def test_docstring_mentions_azure_sedona_motivation(self):
        import siege_utilities.databricks as db_pkg

        assert db_pkg.__doc__ is not None
        doc = db_pkg.__doc__
        assert "Azure Databricks" in doc
        assert "Sedona" in doc
        assert "dataframe_bridge" in doc
        assert "load-bearing" in doc.lower()

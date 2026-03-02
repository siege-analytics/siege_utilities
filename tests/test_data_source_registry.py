"""Tests for DataSource registry models and manager."""

import pytest
import tempfile
from pathlib import Path

from siege_utilities.config.models.data_sources import (
    DataSource,
    DataSourceStatus,
    DataSourceType,
    Jurisdiction,
    JurisdictionLevel,
    SourceCredential,
)
from siege_utilities.config.data_source_registry import DataSourceRegistry


# --- Jurisdiction model tests ---


class TestJurisdiction:
    def test_federal_jurisdiction(self):
        j = Jurisdiction(level=JurisdictionLevel.FEDERAL, name="Federal")
        assert j.level == JurisdictionLevel.FEDERAL
        assert j.state_fips is None

    def test_state_jurisdiction(self):
        j = Jurisdiction(
            level=JurisdictionLevel.STATE,
            state_fips="48",
            state_abbreviation="TX",
            name="Texas",
        )
        assert j.state_fips == "48"
        assert j.state_abbreviation == "TX"

    def test_county_jurisdiction(self):
        j = Jurisdiction(
            level=JurisdictionLevel.COUNTY,
            state_fips="48",
            state_abbreviation="TX",
            county_fips="48453",
            name="Travis County",
        )
        assert j.county_fips == "48453"

    def test_federal_rejects_state_fips(self):
        with pytest.raises(ValueError, match="must not have state_fips"):
            Jurisdiction(level=JurisdictionLevel.FEDERAL, state_fips="48", name="Bad")

    def test_state_requires_state_fips(self):
        with pytest.raises(ValueError, match="require state_fips"):
            Jurisdiction(level=JurisdictionLevel.STATE, name="Texas")

    def test_county_requires_county_fips(self):
        with pytest.raises(ValueError, match="require county_fips"):
            Jurisdiction(
                level=JurisdictionLevel.COUNTY,
                state_fips="48",
                name="Travis County",
            )

    def test_non_numeric_fips_rejected(self):
        with pytest.raises(ValueError, match="must be numeric"):
            Jurisdiction(
                level=JurisdictionLevel.STATE, state_fips="XX", name="Bad"
            )


# --- DataSource model tests ---


class TestDataSource:
    def test_basic_creation(self):
        ds = DataSource(
            source_id="test",
            name="Test Source",
            source_type=DataSourceType.CAMPAIGN_FINANCE,
            jurisdiction=Jurisdiction(level=JurisdictionLevel.FEDERAL, name="Federal"),
        )
        assert ds.source_id == "test"
        assert ds.status == DataSourceStatus.PLANNED

    def test_active_source(self):
        ds = DataSource(
            source_id="fec",
            name="FEC",
            source_type=DataSourceType.CAMPAIGN_FINANCE,
            jurisdiction=Jurisdiction(level=JurisdictionLevel.FEDERAL, name="Federal"),
            status=DataSourceStatus.ACTIVE,
            auth_required=True,
            auth_type="api_key",
            file_formats=["csv", "fec"],
        )
        assert ds.status == DataSourceStatus.ACTIVE
        assert ds.auth_type == "api_key"
        assert "csv" in ds.file_formats

    def test_invalid_auth_type(self):
        with pytest.raises(ValueError, match="auth_type must be one of"):
            DataSource(
                source_id="bad",
                name="Bad",
                source_type=DataSourceType.CAMPAIGN_FINANCE,
                jurisdiction=Jurisdiction(level=JurisdictionLevel.FEDERAL, name="Federal"),
                auth_type="invalid",
            )


# --- SourceCredential tests ---


class TestSourceCredential:
    def test_basic_credential(self):
        cred = SourceCredential(
            source_id="fec",
            credential_type="api_key",
            credential_ref="FEC_API_KEY",
        )
        assert cred.environment == "production"

    def test_staging_credential(self):
        cred = SourceCredential(
            source_id="census",
            credential_type="api_key",
            credential_ref="CENSUS_API_KEY_STAGING",
            environment="staging",
        )
        assert cred.environment == "staging"


# --- DataSourceRegistry tests ---


class TestDataSourceRegistry:
    def test_builtin_sources_loaded(self):
        reg = DataSourceRegistry()
        assert len(reg) >= 6
        assert "fec" in reg
        assert "census" in reg
        assert "nlrb" in reg
        assert "nces" in reg
        assert "tx_ethics" in reg
        assert "fl_elections" in reg

    def test_get_source(self):
        reg = DataSourceRegistry()
        fec = reg.get_source("fec")
        assert fec is not None
        assert fec.name == "Federal Election Commission"
        assert fec.status == DataSourceStatus.ACTIVE

    def test_get_nonexistent_source(self):
        reg = DataSourceRegistry()
        assert reg.get_source("nonexistent") is None

    def test_list_active(self):
        reg = DataSourceRegistry()
        active = reg.list_active()
        ids = [s.source_id for s in active]
        assert "fec" in ids
        assert "census" in ids
        assert "tx_ethics" not in ids  # planned, not active

    def test_list_sources_exclude_planned(self):
        reg = DataSourceRegistry()
        active_only = reg.list_sources(include_planned=False)
        ids = [s.source_id for s in active_only]
        assert "tx_ethics" not in ids
        assert "fl_elections" not in ids

    def test_list_by_type(self):
        reg = DataSourceRegistry()
        cf_sources = reg.list_by_type(DataSourceType.CAMPAIGN_FINANCE)
        ids = [s.source_id for s in cf_sources]
        assert "fec" in ids
        assert "tx_ethics" in ids
        assert "census" not in ids

    def test_list_by_jurisdiction_level(self):
        reg = DataSourceRegistry()
        federal = reg.list_by_jurisdiction(level=JurisdictionLevel.FEDERAL)
        ids = [s.source_id for s in federal]
        assert "fec" in ids
        assert "tx_ethics" not in ids

    def test_list_by_jurisdiction_state(self):
        reg = DataSourceRegistry()
        texas = reg.list_by_jurisdiction(state_abbreviation="TX")
        assert len(texas) == 1
        assert texas[0].source_id == "tx_ethics"

    def test_register_custom_source(self):
        reg = DataSourceRegistry()
        custom = DataSource(
            source_id="ca_sos",
            name="California Secretary of State",
            source_type=DataSourceType.CAMPAIGN_FINANCE,
            jurisdiction=Jurisdiction(
                level=JurisdictionLevel.STATE,
                state_fips="06",
                state_abbreviation="CA",
                name="California",
            ),
        )
        reg.register_source(custom)
        assert "ca_sos" in reg
        assert reg.get_source("ca_sos").name == "California Secretary of State"

    def test_register_credential(self):
        reg = DataSourceRegistry()
        cred = SourceCredential(
            source_id="fec",
            credential_type="api_key",
            credential_ref="FEC_API_KEY",
        )
        reg.register_credential(cred)
        fetched = reg.get_credential("fec")
        assert fetched is not None
        assert fetched.credential_ref == "FEC_API_KEY"

    def test_credential_environment_override(self):
        reg = DataSourceRegistry()
        prod = SourceCredential(
            source_id="fec",
            credential_type="api_key",
            credential_ref="FEC_PROD_KEY",
            environment="production",
        )
        staging = SourceCredential(
            source_id="fec",
            credential_type="api_key",
            credential_ref="FEC_STAGING_KEY",
            environment="staging",
        )
        reg.register_credential(prod)
        reg.register_credential(staging)
        assert reg.get_credential("fec", "production").credential_ref == "FEC_PROD_KEY"
        assert reg.get_credential("fec", "staging").credential_ref == "FEC_STAGING_KEY"

    def test_get_nonexistent_credential(self):
        reg = DataSourceRegistry()
        assert reg.get_credential("nonexistent") is None

    def test_yaml_round_trip(self, tmp_path):
        reg = DataSourceRegistry()
        reg.register_credential(SourceCredential(
            source_id="fec",
            credential_type="api_key",
            credential_ref="MY_KEY",
        ))

        yaml_path = tmp_path / "registry.yaml"
        reg.save_to_yaml(yaml_path)
        assert yaml_path.exists()

        # Load into fresh registry (starts with builtins, overlays YAML)
        reg2 = DataSourceRegistry(config_path=yaml_path)
        assert "fec" in reg2
        assert reg2.get_credential("fec") is not None
        assert reg2.get_credential("fec").credential_ref == "MY_KEY"

    def test_load_nonexistent_yaml(self):
        reg = DataSourceRegistry(config_path=Path("/nonexistent/path.yaml"))
        # Should not raise, just skip
        assert "fec" in reg

    def test_contains(self):
        reg = DataSourceRegistry()
        assert "fec" in reg
        assert "nonexistent" not in reg

    def test_tx_ethics_is_planned(self):
        reg = DataSourceRegistry()
        tx = reg.get_source("tx_ethics")
        assert tx.status == DataSourceStatus.PLANNED
        assert tx.jurisdiction.state_abbreviation == "TX"
        assert tx.jurisdiction.state_fips == "48"

    def test_fl_elections_is_planned(self):
        reg = DataSourceRegistry()
        fl = reg.get_source("fl_elections")
        assert fl.status == DataSourceStatus.PLANNED
        assert fl.jurisdiction.state_abbreviation == "FL"

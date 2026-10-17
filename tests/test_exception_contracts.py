"""Offline regressions for the consequential failure contracts in #1532."""

import importlib

import pandas as pd
import pytest
import yaml


@pytest.mark.parametrize("module", ["enhanced_config", "migration"])
def test_corrupt_profile_not_migrated(tmp_path, module):
    mod = importlib.import_module(f"siege_utilities.config.{module}")
    (tmp_path / "user_config.yaml").write_text(
        "username: [unclosed\n", encoding="utf-8"
    )
    migrator = mod.ConfigurationMigrator(tmp_path, tmp_path / "new")
    result = migrator.migrate_all_configurations()
    assert result["user_profile"]["migrated"] is False
    assert result.get("error") or result["user_profile"]["error"]
    with pytest.raises((OSError, ValueError, yaml.YAMLError)):
        migrator.migrate_user_profile()


@pytest.mark.parametrize("helper", ["_get_place_population", "_get_ua_population"])
@pytest.mark.parametrize("columns", [{"POP": ["n/a"]}, {"NAME": ["unknown"]}])
def test_unknown_population_raises(helper, columns):
    from siege_utilities.geo.locale import NCESLocaleClassifier

    classifier = NCESLocaleClassifier.__new__(NCESLocaleClassifier)
    classifier._place_populations = {}
    classifier._ua_populations = {}
    with pytest.raises(ValueError, match="population"):
        getattr(classifier, helper)(pd.DataFrame(columns))


def test_state_request_never_returns_national_frame(monkeypatch):
    from siege_utilities.geo import spatial_data

    national = pd.DataFrame({"GEOID": ["48001", "06001", "36001"]})

    class Source:
        def get_geographic_boundaries(self, *args, **kwargs):
            return national.copy()

    monkeypatch.setattr(spatial_data, "CensusDataSource", Source)
    with (
        pytest.warns(DeprecationWarning),
        pytest.raises(ValueError, match="state FIPS"),
    ):
        spatial_data.get_census_boundaries(2020, "county", state_identifier="TX")


@pytest.mark.parametrize("missing", [2018, 2020])
def test_missing_snapshot_year_flags_interval(missing):
    from siege_utilities.geo.temporal.services import TemporalTimeseriesBuilder

    class Store:
        def load_demographics(self, geography_type, year, dataset):
            if year == missing:
                raise FileNotFoundError(f"no snapshot for {year}")
            return pd.DataFrame(
                [
                    {
                        "boundary_id": "48001",
                        "year": year,
                        "values": {"B01001_001E": 1000 + year},
                        "moe_values": {},
                    }
                ]
            )

    (result,) = TemporalTimeseriesBuilder(store=Store()).build(
        ["B01001_001E"],
        [2016, 2017, 2018, 2019, 2020],
        "tract",
    )
    assert not result.success
    assert any(str(missing) in error for error in result.errors)
    assert result.records_created == 0
    assert not getattr(result, "series", [])

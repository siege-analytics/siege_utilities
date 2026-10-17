"""Offline reviewer probes for #1532 CR-2 through CR-4."""

import importlib
import os
import sqlite3
from unittest.mock import Mock

import pytest
import yaml


@pytest.mark.parametrize("module", ["enhanced_config", "migration"])
@pytest.mark.parametrize("profile", [None, "username: [unclosed\n"], ids=["missing", "corrupt"])
def test_profile_failure_does_not_abort_clients(tmp_path, module, profile):
    cls = importlib.import_module(f"siege_utilities.config.{module}").ConfigurationMigrator
    if profile is not None:
        (tmp_path / "user_config.yaml").write_text(profile, encoding="utf-8")
    clients = tmp_path / "clients"
    clients.mkdir()
    (clients / "acme.yaml").write_text("client_name: Acme\nindustry: Research\n", encoding="utf-8")

    result = cls(tmp_path, tmp_path / "new").migrate_all_configurations()

    assert result["client_profiles"] == {"migrated": ["acme"], "errors": []}
    assert result["total_migrated"] == 1
    assert result["user_profile"]["migrated"] is False
    assert result["user_profile"]["error"]


@pytest.fixture
def swmaps_without_attributes(tmp_path):
    path = tmp_path / "optional.sqlite"
    with sqlite3.connect(path, timeout=5.0) as conn:
        conn.executescript("""
            CREATE TABLE features (uuid TEXT, name TEXT, layer_id TEXT);
            CREATE TABLE points (fid TEXT, seq INTEGER, lat REAL, lon REAL, elv REAL);
            CREATE TABLE feature_layers (uuid TEXT, name TEXT, group_name TEXT, geom_type TEXT);
            INSERT INTO features VALUES ('one', 'Hydrant', 'layer');
            INSERT INTO points VALUES ('one', 0, 30, -97, NULL);
            INSERT INTO feature_layers VALUES ('layer', 'Hydrant', 'Water', 'point');
        """)
    return str(path)


@pytest.mark.parametrize("remaining", [None, "attribute_values", "attribute_fields"])
def test_absent_attribute_tables_yield_empty_attributes(swmaps_without_attributes, remaining):
    pytest.importorskip("shapely")
    from siege_utilities.geo.data_reception import detect_format
    from siege_utilities.geo.swmaps_reader import open_swmaps, read_features

    if remaining:
        with sqlite3.connect(swmaps_without_attributes, timeout=5.0) as conn:
            conn.execute(f"CREATE TABLE {remaining} (unused TEXT)")
    assert detect_format(swmaps_without_attributes) == "swmaps"
    with open_swmaps(swmaps_without_attributes) as archive:
        records = list(read_features(archive))
    assert len(records) == 1
    assert records[0]["feature_id"] == "one"
    assert records[0]["attributes"] == {}


@pytest.mark.parametrize("missing", ["none", "warn", "raise"])
def test_absent_attribute_tables_honor_missing_policy(swmaps_without_attributes, missing, monkeypatch):
    data_reception = importlib.import_module("siege_utilities.geo.data_reception")

    warning = Mock()
    monkeypatch.setattr(data_reception.log, "warning", warning)

    def extract():
        return data_reception.extract_attributes_swmaps(swmaps_without_attributes, "one", ["name"], missing=missing)

    if missing == "raise":
        with pytest.raises(KeyError, match="name"):
            extract()
    elif missing == "warn":
        assert extract() is None
        warning.assert_called_once_with("attribute field %r not present on feature", "name")
    else:
        assert extract() is None


@pytest.mark.parametrize("reader", ["features", "attribute"])
def test_present_broken_attribute_tables_raise(swmaps_without_attributes, reader):
    from siege_utilities.geo.data_reception import extract_attributes_swmaps
    from siege_utilities.geo.swmaps_reader import open_swmaps, read_features

    with sqlite3.connect(swmaps_without_attributes, timeout=5.0) as conn:
        conn.executescript("""
            CREATE TABLE attribute_values (wrong_column TEXT);
            CREATE TABLE attribute_fields (wrong_column TEXT);
        """)
    with pytest.raises(sqlite3.DatabaseError, match="SWMaps attribute") as error:
        if reader == "features":
            pytest.importorskip("shapely")
            with open_swmaps(swmaps_without_attributes) as archive:
                list(read_features(archive))
        else:
            extract_attributes_swmaps(swmaps_without_attributes, "one", ["name"])
    assert isinstance(error.value.__cause__, sqlite3.DatabaseError)


@pytest.mark.parametrize("operation", ["export", "import"])
@pytest.mark.parametrize("failure", ["unwritable", "yaml"])
def test_config_write_failures_propagate(tmp_path, monkeypatch, operation, failure):
    from siege_utilities.config.user_config import UserConfigManager

    manager = UserConfigManager(config_dir=tmp_path / "config")
    source = tmp_path / "source.yaml"
    source.write_text("username: imported\n", encoding="utf-8")
    target = tmp_path / "export.yaml"
    target.write_text("original export\n", encoding="utf-8")
    saved = manager.user_config_file.read_bytes()
    error = PermissionError("target unwritable") if failure == "unwritable" else yaml.YAMLError("dump failed")
    if failure == "unwritable":
        monkeypatch.setattr(os, "replace", Mock(side_effect=error))
    else:
        monkeypatch.setattr(yaml, "dump", Mock(side_effect=error))

    with pytest.raises(type(error), match=str(error)):
        if operation == "export":
            manager.export_config(str(target))
        else:
            manager.import_config(str(source))
    assert target.read_text(encoding="utf-8") == "original export\n"
    assert manager.user_config_file.read_bytes() == saved
    assert not list(tmp_path.rglob(".user_config.*.tmp"))


@pytest.mark.parametrize("contents", [None, "username: [unclosed\n"], ids=["missing", "yaml"])
def test_import_read_failures_propagate(tmp_path, contents):
    from siege_utilities.config.user_config import UserConfigManager

    manager = UserConfigManager(config_dir=tmp_path / "config")
    source = tmp_path / "source.yaml"
    if contents is not None:
        source.write_text(contents, encoding="utf-8")
    with pytest.raises((OSError, yaml.YAMLError)):
        manager.import_config(str(source))


def test_nxgen_parse_failure_does_not_return_partial_success(monkeypatch):
    from siege_utilities.geo.providers import nlrb_clients

    session = Mock()
    session.get.return_value.text = """<table>
        <tr><td class="case-number">05-RC-111111</td></tr>
        <tr><td class="case-number">05-RC-222222</td></tr>
    </table>"""
    record = nlrb_clients.NLRBCaseRecord(case_number="05-RC-111111", case_type="RC")
    error = ValueError("second record is malformed")
    constructor = Mock(side_effect=[record, error])
    monkeypatch.setattr(nlrb_clients, "NLRBCaseRecord", constructor)

    with pytest.raises(RuntimeError, match="NxGen.*parse") as caught:
        nlrb_clients.NLRBNxGenClient(session=session).fetch_case("05-RC-111111")
    assert caught.value.__cause__ is error
    assert constructor.call_count == 2
    assert session.get.call_args.kwargs["timeout"] > 0

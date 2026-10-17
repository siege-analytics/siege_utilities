"""Credential persistence regressions for #1541; all secrets are sentinels."""

import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts/check_secure_writes.py"
SENTINEL = "SENTINEL"
SOCIAL = [
    ("instagram", "instagram", "ig_account_id", "access_token"),
    ("facebook_business", "facebook", "fb_account_id", "access_token"),
    ("x_twitter", "x", "x_account_id", "bearer_token"),
]


@pytest.fixture
def umask_022():
    old = os.umask(0o022)
    try:
        yield
    finally:
        os.umask(old)


def _social(case):
    module, prefix, id_key, token_key = case
    mod = importlib.import_module(f"siege_utilities.analytics.{module}")
    profile = getattr(mod, f"create_{prefix}_account_profile")(
        "client", "123", **{token_key: SENTINEL},
    )
    return mod, profile, getattr(mod, f"save_{prefix}_account_profile")


@pytest.mark.parametrize("case", SOCIAL, ids=[s[0] for s in SOCIAL])
@pytest.mark.parametrize("existing", [False, True], ids=["new", "existing"])
def test_social_profile_permissions(tmp_path, umask_022, case, existing):
    mod, profile, save = _social(case)
    service, prefix, id_key, token_key = case
    expected = tmp_path / service / f"{id_key.split('_')[0]}_account_{profile[id_key]}.json"
    if existing:
        expected.parent.mkdir()
        expected.write_text("old public contents")
        expected.chmod(0o644)
    path = Path(save(profile, config_directory=str(tmp_path)))
    assert path == expected
    mode = path.stat().st_mode & 0o777
    assert mode & 0o077 == 0, f"credential file mode is {mode:04o}, expected 0600"
    assert mode == 0o600
    assert json.loads(path.read_text())[token_key] == SENTINEL
    if not existing:
        assert path.parent.stat().st_mode & 0o777 == 0o700


@pytest.mark.parametrize("case", SOCIAL, ids=[s[0] for s in SOCIAL])
def test_social_default_directory_round_trip(tmp_path, monkeypatch, case):
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.chdir(tmp_path)
    mod, profile, save = _social(case)
    service, prefix, id_key, token_key = case
    path = Path(save(profile))
    assert path.parent == tmp_path / "home/.siege_utilities" / service
    assert getattr(mod, f"load_{prefix}_account_profile")(profile[id_key]) == profile
    assert not (tmp_path / "config").exists()


@pytest.mark.parametrize("existing", [False, True])
def test_helper_restricts_fd_before_payload(tmp_path, monkeypatch, umask_022, existing):
    from siege_utilities.files import secure_write as mod

    path = tmp_path / "new" / "nested" / "credentials.json"
    if existing:
        path.parent.mkdir(parents=True)
        path.write_text("old data")
        path.chmod(0o644)
    original_fdopen = os.fdopen

    def inspect_fd(fd, *args, **kwargs):
        assert os.fstat(fd).st_mode & 0o777 == 0o600
        return original_fdopen(fd, *args, **kwargs)

    monkeypatch.setattr(mod.os, "fdopen", inspect_fd)
    mod.secure_write_text(path, SENTINEL + " é")
    assert path.read_text(encoding="utf-8") == SENTINEL + " é"
    if not existing:
        assert path.parent.stat().st_mode & 0o777 == 0o700
        assert path.parent.parent.stat().st_mode & 0o777 == 0o700


def test_helper_closes_fd_and_never_writes_after_permission_failure(tmp_path, monkeypatch):
    from siege_utilities.files import secure_write as mod

    opened = []

    def fail_chmod(fd, mode):
        opened.append(fd)
        raise OSError("permission failure")

    monkeypatch.setattr(mod.os, "fchmod", fail_chmod)
    path = tmp_path / "key"
    with pytest.raises(OSError, match="permission failure"):
        mod.secure_write_text(path, SENTINEL)
    assert path.read_bytes() == b""
    with pytest.raises(OSError):
        os.fstat(opened[0])


@pytest.mark.skipif(not hasattr(os, "O_NOFOLLOW"), reason="requires O_NOFOLLOW")
def test_helper_refuses_symlink(tmp_path):
    from siege_utilities.files.secure_write import secure_write_text

    target = tmp_path / "target"
    target.write_text("unchanged")
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(OSError):
        secure_write_text(link, SENTINEL)
    assert target.read_text() == "unchanged"


@pytest.mark.parametrize("fail", [False, True])
def test_temporary_service_account_cleanup(umask_022, fail):
    from siege_utilities.config.credential_manager import create_temporary_service_account_file

    path = None
    try:
        with create_temporary_service_account_file({"private_key": SENTINEL}) as filename:
            path = Path(filename)
            assert path.stat().st_mode & 0o777 == 0o600
            assert json.loads(path.read_text()) == {"private_key": SENTINEL}
            if fail:
                raise RuntimeError("consumer failed")
    except RuntimeError as exc:
        assert fail and str(exc) == "consumer failed"
    assert path is not None and not path.exists()
    assert not path.parent.exists()


def test_temporary_service_account_serialization_failure_cleans_directory(tmp_path, monkeypatch):
    from siege_utilities.config import credential_manager as mod

    monkeypatch.setattr(mod.tempfile, "tempdir", str(tmp_path))
    with pytest.raises(TypeError):
        with mod.create_temporary_service_account_file({"private_key": object()}):
            pytest.fail("serialization should fail")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("fail", [False, True])
def test_ga_service_account_caller_cleans_key(monkeypatch, fail):
    from siege_utilities.analytics import google_analytics as mod

    paths = []
    credentials = object()

    def load_file(filename, scopes):
        path = Path(filename)
        paths.append(path)
        assert json.loads(path.read_text())["private_key"] == SENTINEL
        if fail:
            raise ValueError("SDK rejected key")
        return credentials

    service_account = SimpleNamespace(Credentials=SimpleNamespace(from_service_account_file=load_file))
    monkeypatch.setitem(sys.modules, "google.oauth2", SimpleNamespace(service_account=service_account))
    monkeypatch.setattr(mod, "build", MagicMock(), raising=False)
    monkeypatch.setattr(mod, "BetaAnalyticsDataClient", MagicMock(), raising=False)
    connector = object.__new__(mod.GoogleAnalyticsConnector)
    connector.service_account_data = {"private_key": SENTINEL, "client_email": "test@example.com"}
    if fail:
        with pytest.raises(ValueError, match="SDK rejected key"):
            connector.authenticate_service_account()
    else:
        connector.authenticate_service_account()
        assert connector.credentials is credentials
    assert len(paths) == 1 and not paths[0].exists()


def test_other_credential_writers(tmp_path, umask_022, monkeypatch):
    from siege_utilities.analytics import google_analytics as ga, google_workspace as workspace
    from siege_utilities.config import connections, enhanced_config
    from siege_utilities.config.models.person import Person
    from siege_utilities.config.models.export import export_entities
    from siege_utilities.config.models.actor_types import User, Organization, Collaboration
    from siege_utilities.config.models.user_profile import UserProfile
    from siege_utilities.config.models.client_profile import ClientProfile
    from siege_utilities.config.databases import save_database_config

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    token_json = json.dumps({"token": SENTINEL})
    credentials = SimpleNamespace(to_json=lambda: token_json)
    connector = object.__new__(ga.GoogleAnalyticsConnector)
    connector.credentials = credentials
    ga_token = tmp_path / "ga_token.json"
    connector._save_credentials(ga_token)
    paths = [ga_token]
    flow = MagicMock()
    flow.from_client_config.return_value.run_local_server.return_value = credentials
    monkeypatch.setattr(workspace, "_GOOGLE_AVAILABLE", True)
    monkeypatch.setattr(workspace, "InstalledAppFlow", flow, raising=False)
    workspace_token = tmp_path / "workspace_token.json"
    workspace.GoogleWorkspaceClient.from_oauth("client", SENTINEL, token_file=workspace_token)
    paths.append(workspace_token)
    profile = ga.create_ga_account_profile("client", "123")
    profile["access_token"] = SENTINEL
    ga_path = Path(ga.save_ga_account_profile(profile))
    assert ga_path.parent == tmp_path / ".siege_utilities/google_analytics"
    assert ga.load_ga_account_profile(profile["ga_account_id"]) == profile
    paths.append(ga_path)
    profile = connections.create_connection_profile("test", "api", {"token": SENTINEL})
    connection_path = Path(connections.save_connection_profile(profile))
    assert connection_path.parent == tmp_path / ".siege_utilities/connections"
    assert connections.load_connection_profile(profile["connection_id"]) == profile
    paths.append(connection_path)

    person_data = dict(person_id="test", name="Test", email="test@example.com",
                       credentials=[dict(name="test", service="test", credential_type="oauth_token", token=SENTINEL)])
    person_path = tmp_path / "person.yaml"
    Person(**person_data).to_yaml(person_path, exclude_sensitive=False)
    paths.append(person_path)
    user = User(**person_data, username="test")
    entity_path = tmp_path / "entities.yaml"
    export_entities(users=[user], path=entity_path, exclude_sensitive=False)
    paths.append(entity_path)
    org = Organization(org_id="org", name="Test", org_type="internal", primary_email="test@example.com",
                       notes=SENTINEL)
    collab = Collaboration(collab_id="collab", name="Test",
                           description=SENTINEL)
    for entity, filename in [(org, "org.yaml"), (collab, "collab.yaml")]:
        path = tmp_path / filename
        entity.to_yaml(path, exclude_sensitive=False)
        paths.append(path)
    with pytest.warns(DeprecationWarning):
        enhanced_config.save_user_profile(UserProfile(census_api_key=SENTINEL + "-key"), "test", tmp_path / "users")
    paths.append(tmp_path / "users/test.yaml")
    client_profile = ClientProfile(
        client_id="test", client_code="ACME", client_name="Test", contact_info={},
        industry="Tech", project_count=0, status="active", report_preferences={},
        branding_config=dict(primary_color="#000000", secondary_color="#111111",
                             accent_color="#222222", text_color="#333333",
                             background_color="#FFFFFF", primary_font="Arial",
                             secondary_font="Arial"),
        database_connections=[dict(name="test", connection_type="postgresql", host="localhost",
                                   port=5432, database="test", username="test", password=SENTINEL + "-password1!")],
    )
    with pytest.warns(DeprecationWarning):
        enhanced_config.save_client_profile(client_profile, tmp_path / "clients")
    paths.append(tmp_path / "clients/ACME.yaml")
    export_path = tmp_path / "config.yaml"
    enhanced_config.export_config_yaml({"api_key": SENTINEL}, export_path)
    paths.append(export_path)
    paths.append(Path(save_database_config({"name": "test", "connection_params": {"api_key": SENTINEL}}, str(tmp_path))))
    for path in paths:
        assert path.stat().st_mode & 0o777 == 0o600, path
        assert SENTINEL in path.read_text(), path


@pytest.mark.parametrize("spark", [False, True])
def test_boundary_staging_returns_actual_path(tmp_path, monkeypatch, caplog, spark):
    import pandas as pd
    from siege_utilities.geo import boundary_sources as mod

    geometry = SimpleNamespace(apply=lambda fn: [fn(SimpleNamespace(wkt="POINT (0 0)"))])
    gdf = MagicMock()
    gdf.__len__.return_value = 1
    gdf.drop.return_value = pd.DataFrame({"name": ["test"]})
    gdf.geometry = geometry
    provider = SimpleNamespace(CensusTIGERProvider=lambda: SimpleNamespace(get_boundary=lambda *a, **kw: gdf))
    monkeypatch.setitem(sys.modules, "siege_utilities.geo.providers.boundary_providers", provider)
    monkeypatch.setattr(mod.tempfile, "tempdir", str(tmp_path))
    written = []

    def write_parquet(frame, path):
        written.append((path, frame.copy()))
        Path(path).write_bytes(b"PAR1")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", write_parquet)
    engine = MagicMock() if spark else object()
    caplog.set_level("INFO", logger=mod.__name__)
    result = mod.stage_census_boundaries(engine, "county")
    if spark:
        assert result == "s3a://boundaries/tiger/county/2020/data.parquet"
        engine._session.createDataFrame.return_value.write.mode.return_value.parquet.assert_called_once_with(result)
    else:
        path = Path(result)
        assert path.is_file() and path.parent.parent == tmp_path
        assert path.parent.name.startswith("siege_boundaries_")
        assert path.parent.stat().st_mode & 0o777 == 0o700
        assert written[0][0] == path
        assert written[0][1]["geometry"].tolist() == ["POINT (0 0)"]
        assert "s3a://" not in caplog.text
    assert result in caplog.text


@pytest.mark.parametrize("empty", [None, []])
def test_boundary_staging_empty_result_raises(monkeypatch, empty):
    from siege_utilities.geo.boundary_sources import stage_census_boundaries

    provider = SimpleNamespace(CensusTIGERProvider=lambda: SimpleNamespace(get_boundary=lambda *a, **kw: empty))
    monkeypatch.setitem(sys.modules, "siege_utilities.geo.providers.boundary_providers", provider)
    with pytest.raises(ValueError, match="No boundaries returned"):
        stage_census_boundaries(object(), "county")


def test_boundary_staging_write_failure_cleans_directory(tmp_path, monkeypatch):
    import pandas as pd
    from siege_utilities.geo import boundary_sources as mod

    gdf = MagicMock()
    gdf.__len__.return_value = 1
    gdf.drop.return_value = pd.DataFrame({"name": ["test"]})
    gdf.geometry.apply.return_value = [None]
    provider = SimpleNamespace(CensusTIGERProvider=lambda: SimpleNamespace(get_boundary=lambda *a, **kw: gdf))
    monkeypatch.setitem(sys.modules, "siege_utilities.geo.providers.boundary_providers", provider)
    monkeypatch.setattr(mod.tempfile, "tempdir", str(tmp_path))

    def fail_write(frame, path):
        Path(path).write_bytes(b"partial")
        raise OSError("disk full")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", fail_write)
    with pytest.raises(OSError, match="disk full"):
        mod.stage_census_boundaries(object(), "county")
    assert list(tmp_path.iterdir()) == []


def _guard(root, *args):
    return subprocess.run([sys.executable, str(GUARD), str(root), *args],
                          capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize("sink", [
    'open(path, "w").write(str(payload))',
    'open(file=path, mode="wb").write(b"x")',
    'path.open("w").write(str(payload))',
    'path.write_text(str(payload))',
    'path.write_bytes(b"x")',
    'json.dump(payload, stream)',
    'yaml.dump(payload, stream=stream)',
    'yaml.safe_dump(payload, stream)',
    'secure_write_text(path, "safe"); path.write_text(str(payload))',
])
def test_guard_planted_credential_write(tmp_path, sink):
    planted = tmp_path / "planted.py"
    planted.write_text(f'def save(path, stream):\n    payload = {{"access_token": "SENTINEL"}}\n    {sink}\n')
    result = _guard(tmp_path)
    assert result.returncode != 0
    assert "planted.py:3:" in result.stdout and "credential-write" in result.stdout


@pytest.mark.parametrize("source,rule", [
    ('import os\ndef save(path):\n    path.write_text("data")\n    os.chmod(path, 0o600)\n', "write-then-chmod"),
    ('import os\nfrom pathlib import Path\ndef save(path):\n    with open(path, "w") as f:\n        f.write("data")\n    os.chmod(Path(path), 0o600)\n', "write-then-chmod"),
    ('from os import chmod as restrict\ndef save(path):\n    path.write_bytes(b"x")\n    restrict(path, 0o600)\n', "write-then-chmod"),
    ('PATH = "/tmp/predictable"\n', "fixed-tmp-path"),
    ('PATH = f"/tmp/{name}"\n', "fixed-tmp-path"),
    ('from json import dump as emit\ndef save(stream):\n    payload = dict(refresh_token="x")\n    emit(payload, stream)\n', "credential-write"),
    ('def save(path):\n    payload = {}\n    payload["password"] = "x"\n    path.write_text(str(payload))\n', "credential-write"),
])
def test_guard_other_patterns(tmp_path, source, rule):
    (tmp_path / "planted.py").write_text(source)
    result = _guard(tmp_path)
    assert result.returncode != 0 and rule in result.stdout
    assert "planted.py:" in result.stdout


def test_guard_secure_and_noncredential_writes_pass(tmp_path):
    (tmp_path / "clean.py").write_text(
        'import json\nfrom siege_utilities.files.secure_write import secure_write_text\n'
        'def save(path):\n    payload = {"token": "SENTINEL"}\n'
        '    secure_write_text(path, json.dumps(payload))\n'
        'def cache(path):\n    path.write_text("public data")\n'
    )
    result = _guard(tmp_path)
    assert result.returncode == 0, result.stdout


def test_guard_clean_tree():
    result = _guard(ROOT / "siege_utilities")
    assert result.returncode == 0, result.stdout
    assert "PASS: 0" in result.stdout


def test_guard_invalid_and_empty_tree_fail(tmp_path):
    assert _guard(tmp_path).returncode != 0
    (tmp_path / "bad.py").write_text("def broken(:")
    result = _guard(tmp_path)
    assert result.returncode != 0 and "bad.py:1:" in result.stdout


def test_guard_allowlist_is_exact_and_stale_entries_fail(tmp_path):
    spec = importlib.util.spec_from_file_location("secure_guard", GUARD)
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    path = tmp_path / "planted.py"
    path.write_text('PATH = "/tmp/reviewed"\n')
    line, scope, rule, digest = guard.scan_file(path)[0]
    allow = tmp_path / "allow.json"
    allow.write_text(json.dumps([dict(file="planted.py", scope=scope, rule=rule, sha256=digest,
                                     reason="Synthetic allow-list fixture")]))
    assert _guard(tmp_path, "--allowlist", str(allow)).returncode == 0
    path.write_text('PATH = "/tmp/changed"\n')
    result = _guard(tmp_path, "--allowlist", str(allow))
    assert result.returncode != 0 and "fixed-tmp-path" in result.stdout
    assert "stale allow-list entry" in result.stdout

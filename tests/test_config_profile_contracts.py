"""Canonical contract tests for config profile helpers tracked by #1201."""

import json
from datetime import datetime
from datetime import timedelta

from siege_utilities import associate_client_with_project
from siege_utilities import cleanup_old_connections
from siege_utilities import create_client_profile
from siege_utilities import create_connection_profile
from siege_utilities import find_connection_by_name
from siege_utilities import get_client_project_associations
from siege_utilities import get_connection_status
from siege_utilities import list_client_profiles
from siege_utilities import list_connection_profiles
from siege_utilities import load_client_profile
from siege_utilities import load_connection_profile
from siege_utilities import save_client_profile
from siege_utilities import save_connection_profile
from siege_utilities import search_client_profiles
from siege_utilities import update_client_profile
from siege_utilities import update_connection_profile
from siege_utilities import validate_client_profile
from siege_utilities.config.projects import create_project_config
from siege_utilities.config.projects import save_project_config


def _contact():
    return {
        "primary_contact": "Ada Lovelace",
        "email": "ada@example.test",
    }


def test_client_profile_roundtrip_search_update_and_association(tmp_path):
    config_dir = tmp_path / "config"
    profile = create_client_profile(
        "Example Client",
        "EXAMPLE",
        _contact(),
        industry="Analytics",
        project_count=0,
        logo_path="brand/logo.svg",
    )

    validation = validate_client_profile(profile)
    assert validation["is_valid"] is True
    assert "No projects associated with client" in validation["warnings"]

    saved_path = save_client_profile(profile, str(config_dir))
    assert saved_path.endswith("client_EXAMPLE.json")

    loaded = load_client_profile("EXAMPLE", str(config_dir))
    assert loaded["client_name"] == "Example Client"
    assert loaded["contact_info"] == _contact()

    listed = list_client_profiles(str(config_dir))
    assert [client["code"] for client in listed] == ["EXAMPLE"]
    assert listed[0]["industry"] == "Analytics"

    search_results = search_client_profiles(
        "analytics",
        ["metadata.industry", "client_name"],
        str(config_dir),
    )
    assert [client["client_code"] for client in search_results] == ["EXAMPLE"]

    update_client_profile(
        "EXAMPLE",
        {
            "contact_info": {"phone": "+1-555-0100"},
            "metadata": {"project_count": 3},
        },
        str(config_dir),
    )
    updated = load_client_profile("EXAMPLE", str(config_dir))
    assert updated["contact_info"]["phone"] == "+1-555-0100"
    assert updated["metadata"]["project_count"] == 3

    project = create_project_config("Example Project", "PROJ", str(tmp_path))
    save_project_config(project, str(config_dir))

    associate_client_with_project("EXAMPLE", "PROJ", str(config_dir))
    assert get_client_project_associations("EXAMPLE", str(config_dir)) == [
        "PROJ"
    ]
    associated = load_client_profile("EXAMPLE", str(config_dir))
    assert associated["metadata"]["project_count"] == 1


def test_connection_roundtrip_filter_status_update_and_cleanup(tmp_path):
    config_dir = tmp_path / "config"
    profile = create_connection_profile(
        "Warehouse",
        "database",
        {"connection_string": "sqlite:///:memory:"},
        status="active",
        auto_connect=True,
        tags=["prod"],
    )

    saved_path = save_connection_profile(profile, str(config_dir))
    assert saved_path.endswith(f"connection_{profile['connection_id']}.json")

    loaded = load_connection_profile(profile["connection_id"], str(config_dir))
    assert loaded["name"] == "Warehouse"
    assert loaded["database_specific"]["ssl_mode"] == "prefer"

    assert find_connection_by_name("Warehouse", str(config_dir))["name"] == (
        "Warehouse"
    )
    assert find_connection_by_name("missing", str(config_dir)) is None

    listed = list_connection_profiles("database", str(config_dir))
    assert [connection["connection_id"] for connection in listed] == [
        profile["connection_id"]
    ]
    assert list_connection_profiles("notebook", str(config_dir)) == []

    status = get_connection_status(profile["connection_id"], str(config_dir))
    assert status["status"] == "active"
    assert status["health"] == "unknown"
    assert status["auto_connect"] is True

    update_connection_profile(
        profile["connection_id"],
        {"metadata": {"status": "inactive", "connection_count": 2}},
        str(config_dir),
    )
    updated = get_connection_status(profile["connection_id"], str(config_dir))
    assert updated["status"] == "inactive"
    assert updated["connection_count"] == 2

    stale = create_connection_profile("Stale", "api", {"url": "old"})
    stale_path = save_connection_profile(stale, str(config_dir))
    stale_file = config_dir / "connections" / stale_path.split("/")[-1]
    saved_stale = json.loads(stale_file.read_text())
    saved_stale["metadata"]["created_date"] = (
        datetime.now() - timedelta(days=120)
    ).isoformat()
    saved_stale["metadata"]["last_used"] = (
        datetime.now() - timedelta(days=120)
    ).isoformat()
    saved_stale["metadata"]["connection_count"] = 0
    stale_file.write_text(json.dumps(saved_stale))

    assert cleanup_old_connections(90, str(config_dir)) == 1
    assert not stale_file.exists()

    remaining_files = list(
        (config_dir / "connections").glob("connection_*.json")
    )
    remaining_profiles = [
        json.loads(path.read_text()) for path in remaining_files
    ]
    assert [item["name"] for item in remaining_profiles] == ["Warehouse"]

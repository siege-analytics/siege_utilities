from __future__ import annotations

import pytest

import siege_utilities as su


def test_dependency_wrapper_carries_machine_readable_metadata():
    wrapper = su._create_dependency_wrapper("needs_extra", ["demo-extra>=1.0"])

    assert wrapper.__siege_optional_dependency_wrapper__ is True
    assert wrapper.__siege_required_dependencies__ == ("demo-extra>=1.0",)
    assert wrapper.__siege_missing_dependencies__ == ("demo-extra>=1.0",)
    assert wrapper.__siege_available__ is False
    with pytest.raises(ImportError, match="demo-extra>=1.0"):
        wrapper()


def test_get_package_info_separates_missing_optional_dependency_symbols(monkeypatch):
    target = "UserConfigManager"
    monkeypatch.setattr(
        su,
        "_missing_dependencies",
        lambda deps: list(deps) if target in ["UserConfigManager"] and deps else [],
    )

    info = su.get_package_info()

    assert target in info["unavailable_functions"]
    assert target not in info["available_functions"]
    metadata = info["optional_dependency_symbols"][target]
    assert metadata["available"] is False
    assert metadata["required_dependencies"] == ["pydantic>=2.0"]
    assert metadata["missing_dependencies"] == ["pydantic>=2.0"]
    assert metadata["category"] == "config"
    assert target not in info["categories"]["config"]


def test_get_available_functions_uses_registry_derived_categories():
    categories = su.get_available_functions()

    assert "files" in categories
    assert "copy_file" in categories["files"]
    assert "reporting" in categories
    assert "create_bar_chart" in categories["reporting"]
    assert "configure_shared_logging" in categories["core"]


def test_dependency_distribution_import_name_mismatches_are_supported(monkeypatch):
    calls = []

    def fake_import(name):
        calls.append(name)
        if name in {"google.analytics.data_v1beta", "snowflake.connector"}:
            return object()
        raise ImportError(name)

    monkeypatch.setattr(su.importlib, "import_module", fake_import)

    assert su._missing_dependencies(["google-analytics-data", "snowflake-connector-python"]) == []
    assert "google.analytics.data_v1beta" in calls
    assert "snowflake.connector" in calls


def test_lazy_checker_package_level_missing_dep_is_reported_not_crashed(tmp_path, monkeypatch):
    import scripts.check_lazy_imports as checker

    package_root = tmp_path / "fake_optional_pkg"
    package_root.mkdir()
    (package_root / "__init__.py").write_text(
        "import definitely_missing_optional_dep_for_siege_probe\n", encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    failures, optional_skips = checker._check_package("fake_optional_pkg", quiet=True)

    assert failures == []
    assert optional_skips
    assert "definitely_missing_optional_dep_for_siege_probe" in optional_skips[0]


def test_lazy_checker_package_level_missing_local_module_fails(tmp_path, monkeypatch):
    import scripts.check_lazy_imports as checker

    package_root = tmp_path / "fakepkg"
    package_root.mkdir()
    (package_root / "__init__.py").write_text(
        "from .missing_local import thing\n", encoding="utf-8"
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    failures, optional_skips = checker._check_package("fakepkg", quiet=True)

    assert optional_skips == []
    assert failures
    assert "missing local module: fakepkg.missing_local" in failures[0]

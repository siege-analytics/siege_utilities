import scripts.check_notebook_capability_coverage as checker


def test_top_level_packages_ignore_cache_only_directories(tmp_path, monkeypatch):
    package_root = tmp_path / "siege_utilities"
    package_root.mkdir()
    real_package = package_root / "real_package"
    real_package.mkdir()
    (real_package / "__init__.py").write_text("", encoding="utf-8")
    static_surface = package_root / "configs"
    static_surface.mkdir()
    (static_surface / "defaults.yaml").write_text("enabled: true\n", encoding="utf-8")
    cache_only = package_root / "integrations"
    (cache_only / "__pycache__").mkdir(parents=True)
    (cache_only / "__pycache__" / "__init__.cpython-311.pyc").write_bytes(b"cache")

    monkeypatch.setattr(checker, "PACKAGE_ROOT", package_root)

    assert checker._top_level_packages() == {"configs", "real_package"}

"""Canonical root-import contracts for distributed HDFS helpers."""

from siege_utilities.distributed import HDFSConfig
from siege_utilities.distributed import create_hdfs_operations
from siege_utilities.distributed import setup_distributed_environment
from siege_utilities.distributed.hdfs_operations import AbstractHDFSOperations


def test_create_hdfs_operations_root_import_returns_configured_ops(
    tmp_path,
):
    config = HDFSConfig(cache_directory=str(tmp_path))

    ops = create_hdfs_operations(config)

    assert isinstance(ops, AbstractHDFSOperations)
    assert ops.config is config
    assert ops.data_sync_cache == tmp_path / "data_sync_info.json"
    assert ops.dependencies_cache == tmp_path / "dependencies_info.json"


def test_setup_distributed_environment_root_import_delegates(
    monkeypatch,
    tmp_path,
):
    from siege_utilities.distributed import hdfs_operations

    calls = []
    sentinel = object()

    class StubOperations:
        def __init__(self, config):
            calls.append(("init", config))

        def setup_distributed_environment(self, data_path, dependency_paths):
            calls.append(("setup", data_path, dependency_paths))
            return sentinel

    monkeypatch.setattr(
        hdfs_operations,
        "AbstractHDFSOperations",
        StubOperations,
    )
    config = HDFSConfig(cache_directory=str(tmp_path))

    result = setup_distributed_environment(
        config,
        data_path="/data/input",
        dependency_paths=["/deps/pkg"],
    )

    assert result is sentinel
    assert calls == [
        ("init", config),
        ("setup", "/data/input", ["/deps/pkg"]),
    ]

"""Tests for Databricks auth/session/secrets helpers."""

import sys
import types

import pytest

from siege_utilities.databricks.auth import get_workspace_client
from siege_utilities.databricks.secrets import (
    ensure_secret_scope,
    get_runtime_secret,
    put_secret,
    runtime_secret_exists,
)
from siege_utilities.databricks.session import get_active_spark_session, get_dbutils


def test_get_workspace_client_with_pat(monkeypatch):
    """Workspace client should receive PAT/profile args."""
    databricks_module = types.ModuleType("databricks")
    sdk_module = types.ModuleType("databricks.sdk")

    class FakeWorkspaceClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    sdk_module.WorkspaceClient = FakeWorkspaceClient
    monkeypatch.setitem(sys.modules, "databricks", databricks_module)
    monkeypatch.setitem(sys.modules, "databricks.sdk", sdk_module)

    client = get_workspace_client(
        profile="SUZY_USER",
        host="https://adb.example.net",
        token="abc123",
    )
    assert client.kwargs["profile"] == "SUZY_USER"
    assert client.kwargs["host"] == "https://adb.example.net"
    assert client.kwargs["token"] == "abc123"


def test_get_workspace_client_requires_full_azure_sp(monkeypatch):
    """Azure SP auth should require all three SP fields."""
    databricks_module = types.ModuleType("databricks")
    sdk_module = types.ModuleType("databricks.sdk")
    sdk_module.WorkspaceClient = object
    monkeypatch.setitem(sys.modules, "databricks", databricks_module)
    monkeypatch.setitem(sys.modules, "databricks.sdk", sdk_module)

    with pytest.raises(ValueError):
        get_workspace_client(
            azure_client_id="client-id-only",
            azure_client_secret=None,
            azure_tenant_id=None,
        )


def test_get_active_spark_session_existing(monkeypatch):
    """Existing active Spark session should be returned."""
    pyspark_module = types.ModuleType("pyspark")
    sql_module = types.ModuleType("pyspark.sql")

    class FakeSparkSession:
        @staticmethod
        def getActiveSession():
            return "ACTIVE_SPARK"

    sql_module.SparkSession = FakeSparkSession
    monkeypatch.setitem(sys.modules, "pyspark", pyspark_module)
    monkeypatch.setitem(sys.modules, "pyspark.sql", sql_module)

    assert get_active_spark_session() == "ACTIVE_SPARK"


def test_get_dbutils_from_pyspark_dbutils(monkeypatch):
    """DBUtils should resolve from pyspark.dbutils when available."""
    pyspark_module = types.ModuleType("pyspark")
    sql_module = types.ModuleType("pyspark.sql")
    dbutils_module = types.ModuleType("pyspark.dbutils")

    class FakeBuilder:
        def appName(self, _name):
            return self

        def getOrCreate(self):
            return "SPARK_FROM_BUILDER"

    class FakeSparkSession:
        builder = FakeBuilder()

        @staticmethod
        def getActiveSession():
            return None

    class FakeDBUtils:
        def __init__(self, spark):
            self.spark = spark

    sql_module.SparkSession = FakeSparkSession
    dbutils_module.DBUtils = FakeDBUtils

    monkeypatch.setitem(sys.modules, "pyspark", pyspark_module)
    monkeypatch.setitem(sys.modules, "pyspark.sql", sql_module)
    monkeypatch.setitem(sys.modules, "pyspark.dbutils", dbutils_module)

    dbutils = get_dbutils()
    assert dbutils.spark == "SPARK_FROM_BUILDER"


def test_runtime_secret_helpers_with_dbutils_stub():
    """Runtime secret wrappers should use dbutils secrets API."""
    class SecretItem:
        def __init__(self, key):
            self.key = key

    class SecretApi:
        def get(self, scope, key):
            return f"{scope}:{key}:value"

        def list(self, scope):
            assert scope == "my-scope"
            return [SecretItem("alpha"), SecretItem("beta")]

    class DBUtilsStub:
        secrets = SecretApi()

    dbutils = DBUtilsStub()
    assert get_runtime_secret("my-scope", "alpha", dbutils=dbutils) == "my-scope:alpha:value"
    assert runtime_secret_exists("my-scope", "beta", dbutils=dbutils) is True
    assert runtime_secret_exists("my-scope", "gamma", dbutils=dbutils) is False


def test_workspace_secret_scope_and_put():
    """Workspace scope helpers should call list/create/put APIs."""
    class ScopeItem:
        def __init__(self, name):
            self.name = name

    class SecretsApi:
        def __init__(self):
            self.created = []
            self.puts = []

        def list_scopes(self):
            return [ScopeItem("existing-scope")]

        def create_scope(self, scope):
            self.created.append(scope)

        def put_secret(self, scope, key, string_value):
            self.puts.append((scope, key, string_value))

    class WorkspaceClientStub:
        def __init__(self):
            self.secrets = SecretsApi()

    client = WorkspaceClientStub()
    assert ensure_secret_scope("existing-scope", workspace_client=client) is True
    assert ensure_secret_scope("new-scope", workspace_client=client) is True
    assert client.secrets.created == ["new-scope"]

    assert put_secret("new-scope", "token", "abc", workspace_client=client) is True
    assert client.secrets.puts == [("new-scope", "token", "abc")]

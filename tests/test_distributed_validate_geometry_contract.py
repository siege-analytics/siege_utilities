"""Canonical root-import contracts for validate_geometry."""

from unittest.mock import Mock

from siege_utilities.distributed import validate_geometry


class Expr:
    def __init__(self, text):
        self.text = text

    def alias(self, name):
        return (self.text, name)


def test_validate_geometry_uses_expr_without_functions_alias(monkeypatch):
    from siege_utilities.distributed import spark_utils

    selected = Mock()
    df = Mock()
    df.columns = ["geom"]
    df.select.return_value = selected
    expr_calls = []

    def fake_expr(text):
        expr_calls.append(text)
        return Expr(text)

    monkeypatch.delattr(spark_utils, "F", raising=False)
    monkeypatch.setattr(spark_utils, "expr", fake_expr, raising=False)

    result = validate_geometry(df, "geom", "stage-one")

    assert result is df
    assert expr_calls == ["typeof(geom)", "ST_SRID(geom)"]
    df.select.assert_called_once_with(
        "geom",
        ("typeof(geom)", "geometry_type"),
        ("ST_SRID(geom)", "srid"),
    )
    selected.show.assert_called_once_with(10, truncate=False)


def test_validate_geometry_preserves_postal_code_when_present(monkeypatch):
    from siege_utilities.distributed import spark_utils

    selected = Mock()
    df = Mock()
    df.columns = ["postal_code", "geom"]
    df.select.return_value = selected

    monkeypatch.setattr(
        spark_utils,
        "expr",
        lambda text: Expr(text),
        raising=False,
    )

    validate_geometry(df, "geom", "stage-two")

    df.select.assert_called_once_with(
        "postal_code",
        "geom",
        ("typeof(geom)", "geometry_type"),
        ("ST_SRID(geom)", "srid"),
    )

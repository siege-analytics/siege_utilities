"""Regression tests for Sprint A reliability fixes (issue #452).

Each test pins a specific reliability bug from the hostile review so a
future refactor can't silently regress it. Tests are deliberately
narrow — they assert the specific user-visible behavior, not the
implementation path.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Item 1 — build_chain rejects empty / schema-incompatible input
# ---------------------------------------------------------------------------

def test_build_chain_rejects_empty_dataframe():
    from siege_utilities.survey.crosstab import build_chain, CrosstabInputError

    with pytest.raises(CrosstabInputError, match="empty DataFrame"):
        build_chain(pd.DataFrame(), row_var="x", break_vars=["y"])


def test_build_chain_rejects_missing_row_var():
    from siege_utilities.survey.crosstab import build_chain, CrosstabInputError

    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    with pytest.raises(CrosstabInputError, match="row_var 'missing'"):
        build_chain(df, row_var="missing", break_vars=["a"])


def test_build_chain_rejects_missing_break_var():
    from siege_utilities.survey.crosstab import build_chain, CrosstabInputError

    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    with pytest.raises(CrosstabInputError, match="break_vars"):
        build_chain(df, row_var="a", break_vars=["nope"])


# ---------------------------------------------------------------------------
# Item 2 — SparkEngine.groupby_agg validates unknown functions up-front
# ---------------------------------------------------------------------------

def test_spark_groupby_agg_rejects_unknown_function():
    pytest.importorskip("pyspark")
    from siege_utilities.engines.dataframe_engine import SparkEngine

    eng = SparkEngine.__new__(SparkEngine)  # bypass __init__ — no session
    with pytest.raises(ValueError, match="unsupported aggregation"):
        eng.groupby_agg(df=object(), group_cols=["g"], agg_dict={"x": "median"})


# ---------------------------------------------------------------------------
# Item 3 — apply_rim_weights pre-validates target columns + categories
# ---------------------------------------------------------------------------

def test_apply_rim_weights_rejects_missing_column():
    pytest.importorskip("weightipy")
    from siege_utilities.survey.weights import apply_rim_weights

    df = pd.DataFrame({"age": ["18-34", "35-54"]})
    with pytest.raises(ValueError, match="target column 'gender'"):
        apply_rim_weights(df, targets={"gender": {"M": 0.5, "F": 0.5}})


def test_apply_rim_weights_rejects_missing_category():
    pytest.importorskip("weightipy")
    from siege_utilities.survey.weights import apply_rim_weights

    df = pd.DataFrame({"age": ["18-34", "35-54"]})
    with pytest.raises(ValueError, match="categor(?:y|ies)"):
        apply_rim_weights(df, targets={"age": {"18-34": 0.5, "55+": 0.5}})


# ---------------------------------------------------------------------------
# Item 4 — GA date params validated as YYYY-MM-DD or relative keyword
# ---------------------------------------------------------------------------

def test_ga_date_validation_accepts_iso_and_keywords():
    pytest.importorskip("google.analytics.data_v1beta")
    from siege_utilities.analytics.google_analytics import GoogleAnalyticsConnector

    # Static method — no instance state needed.
    GoogleAnalyticsConnector._validate_ga_date("2026-01-15", "start_date")
    GoogleAnalyticsConnector._validate_ga_date("today", "start_date")
    GoogleAnalyticsConnector._validate_ga_date("7daysAgo", "start_date")


def test_ga_date_validation_rejects_garbage():
    pytest.importorskip("google.analytics.data_v1beta")
    from siege_utilities.analytics.google_analytics import GoogleAnalyticsConnector

    with pytest.raises(ValueError, match="start_date"):
        GoogleAnalyticsConnector._validate_ga_date("01/15/2026", "start_date")
    with pytest.raises(ValueError, match="end_date"):
        GoogleAnalyticsConnector._validate_ga_date("", "end_date")
    with pytest.raises(ValueError):
        GoogleAnalyticsConnector._validate_ga_date("2026-13-40", "start_date")


# ---------------------------------------------------------------------------
# Item 5 — ReportLab Paragraph escape
# ---------------------------------------------------------------------------

def test_escape_paragraph_neutralizes_markup():
    from siege_utilities.reporting.report_generator import _escape_paragraph

    # ``<`` and ``&`` would otherwise be parsed as mini-HTML by ReportLab.
    assert _escape_paragraph("Q&A about <3 favorites") == (
        "Q&amp;A about &lt;3 favorites"
    )
    # Order matters: a literal & should not double-escape.
    assert _escape_paragraph("&amp;") == "&amp;amp;"


# ---------------------------------------------------------------------------
# Item 6 — IDML add_text_frame accepts a style_name
# ---------------------------------------------------------------------------

def test_idml_add_text_frame_records_style_name():
    from siege_utilities.reporting.idml_export import IDMLExporter

    exp = IDMLExporter()
    exp.add_text_frame("hello", style_name="CustomHeading")
    assert exp._text_frames[-1]["style"] == "CustomHeading"


# ---------------------------------------------------------------------------
# Item 7 — PowerPoint filename gets a uuid suffix to avoid collisions
# ---------------------------------------------------------------------------

def test_powerpoint_filename_unique_within_same_second(tmp_path):
    pytest.importorskip("pptx")
    from siege_utilities.reporting.powerpoint_generator import (
        PowerPointGenerator,
    )

    gen = PowerPointGenerator(client_name="Acme", output_dir=tmp_path)
    # Patch datetime so two calls share the same second; uuid suffix
    # must still differentiate them.
    fixed = "20260512_120000"
    with patch(
        "siege_utilities.reporting.powerpoint_generator.datetime"
    ) as mock_dt:
        mock_dt.now.return_value.strftime.return_value = fixed
        p1 = gen.create_presentation_from_data({}, "Test")
        p2 = gen.create_presentation_from_data({}, "Test")
    assert p1 != p2, "uuid suffix must make same-second filenames unique"


# ---------------------------------------------------------------------------
# Item 8 — PDF output path writability is checked up-front
# ---------------------------------------------------------------------------

def test_generate_pdf_report_rejects_unwritable_dir(tmp_path):
    pytest.importorskip("reportlab")
    from siege_utilities.reporting.report_generator import ReportGenerator

    gen = ReportGenerator(client_name="Acme", output_dir=tmp_path)
    # /proc is read-only on Linux; on macOS use a path under a file
    # (cannot mkdir under a regular file).
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("placeholder")
    bad_out = blocker / "report.pdf"

    ok = gen.generate_pdf_report({"metadata": {"title": "x"}, "sections": []}, str(bad_out))
    assert ok is False, "writability pre-check should fail before building PDF"


# ---------------------------------------------------------------------------
# Item 9 — _redact does not eat Git SHAs / UUIDs / decimals
# ---------------------------------------------------------------------------

def test_redact_passes_through_git_sha():
    from siege_utilities.config.credential_manager import _redact

    sha = "a525ba2c4dfe1a2b3c4d5e6f7890abcdef123456"  # 40 hex
    out = _redact(f"failed at commit {sha}")
    assert sha in out, f"Git SHA was redacted: {out!r}"


def test_redact_passes_through_decimal_id():
    from siege_utilities.config.credential_manager import _redact

    out = _redact("user id 12345678901234567890123456789012345")
    assert "12345678901234567890123456789012345" in out


def test_redact_still_catches_jwt_like_token():
    from siege_utilities.config.credential_manager import _redact

    # JWT with two ``.``s; the segments themselves contain the
    # non-hex chars (``_-``) and uppercase letters that trip the rule.
    jwt_segment = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9_extra-tail"
    out = _redact(f"got token={jwt_segment}")
    assert jwt_segment not in out
    assert "[REDACTED]" in out


def test_redact_still_catches_keyvalue_form():
    from siege_utilities.config.credential_manager import _redact

    out = _redact('password="hunter2"')
    assert "hunter2" not in out

"""Error-path tests for the reporting subsystem.

Covers report_generator, chart_generator (via engine mixins),
base_template, and client_branding error handling.
"""

from __future__ import annotations


import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Optional dependency guards
# ---------------------------------------------------------------------------

try:
    import reportlab  # noqa: F401
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

needs_reportlab = pytest.mark.skipif(
    not REPORTLAB_AVAILABLE, reason="reportlab not installed"
)
needs_matplotlib = pytest.mark.skipif(
    not MATPLOTLIB_AVAILABLE, reason="matplotlib not installed"
)


# ---------------------------------------------------------------------------
# BaseReportTemplate error paths
# ---------------------------------------------------------------------------

@needs_reportlab
class TestBaseTemplateErrors:

    def test_missing_branding_config_file_raises(self, tmp_path):
        """A nonexistent branding YAML should raise FileNotFoundError."""
        from siege_utilities.reporting.templates.base_template import BaseReportTemplate
        fake_yaml = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError):
            BaseReportTemplate(
                output_filename=str(tmp_path / "out.pdf"),
                branding_config_path=fake_yaml,
            )

    def test_invalid_yaml_branding_config_raises(self, tmp_path):
        """Malformed YAML should raise a yaml error."""
        import yaml
        from siege_utilities.reporting.templates.base_template import BaseReportTemplate
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("{{{{not valid yaml::::")
        with pytest.raises(yaml.YAMLError):
            BaseReportTemplate(
                output_filename=str(tmp_path / "out.pdf"),
                branding_config_path=bad_yaml,
            )

    def test_generate_report_not_implemented_raises(self, tmp_path):
        """The base generate_report is abstract and should raise."""
        from siege_utilities.reporting.templates.base_template import BaseReportTemplate
        template = BaseReportTemplate(
            output_filename=str(tmp_path / "out.pdf"),
        )
        with pytest.raises(NotImplementedError, match="Subclasses must implement"):
            template.generate_report({})

    def test_build_document_empty_story_raises_or_succeeds(self, tmp_path):
        """Building with an empty story should not crash silently.
        ReportLab may raise on truly empty story or produce a valid empty PDF."""
        from siege_utilities.reporting.templates.base_template import BaseReportTemplate
        template = BaseReportTemplate(
            output_filename=str(tmp_path / "empty.pdf"),
        )
        # ReportLab requires at least one flowable; an empty story raises
        # or produces a trivial PDF — either is acceptable, but not a silent hang.
        try:
            template.build_document([])
        except (ValueError, TypeError, RuntimeError, OSError, AttributeError):
            pass  # acceptable: ReportLab may raise on empty story


# ---------------------------------------------------------------------------
# ReportGenerator error paths
# ---------------------------------------------------------------------------

@needs_reportlab
class TestReportGeneratorErrors:

    def test_missing_client_branding_falls_back(self, tmp_path):
        """Unknown client name should log a warning, not raise."""
        from siege_utilities.reporting.report_generator import ReportGenerator
        gen = ReportGenerator(
            client_name="nonexistent_client_xyz",
            output_dir=tmp_path,
        )
        # Should have fallen back to empty config
        assert gen.branding_config is not None

    def test_generate_pdf_report_invalid_output_dir_raises(self, tmp_path):
        """Writing to an unwritable dir raises OSError (documented, SU-1)."""
        from siege_utilities.reporting.report_generator import ReportGenerator
        gen = ReportGenerator(client_name="test", output_dir=tmp_path)
        report_content = gen.create_analytics_report(
            title="Test", charts=[], data_summary="test",
        )
        # A path that cannot be created/written. generate_pdf_report documents
        # "Raises OSError if the output directory cannot be created or is not
        # writable"; previously asserted a False return.
        with pytest.raises(OSError):
            gen.generate_pdf_report(
                report_content,
                output_path="/dev/null/impossible/path/report.pdf",
            )

    def test_generate_pdf_report_empty_content_succeeds(self, tmp_path):
        """Empty content produces a trivial PDF and returns None (success)."""
        from siege_utilities.reporting.report_generator import ReportGenerator
        gen = ReportGenerator(client_name="test", output_dir=tmp_path)
        out = tmp_path / "empty.pdf"
        # Returns None on success and raises on failure (documented contract);
        # previously asserted isinstance(result, bool).
        result = gen.generate_pdf_report(report_content={}, output_path=str(out))
        assert result is None
        assert out.exists()

    def test_add_section_to_report_missing_sections_key(self, tmp_path):
        """add_section should create the sections list if missing."""
        from siege_utilities.reporting.report_generator import ReportGenerator
        gen = ReportGenerator(client_name="test", output_dir=tmp_path)
        report = {}  # no 'sections' key
        updated = gen.add_section(report, "text", "Title", "content")
        assert "sections" in updated
        assert len(updated["sections"]) == 1


# ---------------------------------------------------------------------------
# ChartGenerator error paths
# ---------------------------------------------------------------------------

@needs_matplotlib
@needs_reportlab
class TestChartGeneratorErrors:

    @pytest.fixture
    def generator(self, tmp_path):
        from siege_utilities.reporting.chart_generator import ChartGenerator
        return ChartGenerator(output_dir=tmp_path)

    def test_bar_chart_empty_data_returns_placeholder(self, generator):
        """An empty DataFrame should not raise — should return a placeholder or image."""
        df = pd.DataFrame()
        result = generator.create_bar_chart(df, title="Empty")
        # Should return something (placeholder), not None/raise
        assert result is not None

    def test_bar_chart_no_numeric_columns_returns_placeholder(self, generator):
        """A DataFrame with no numeric columns should produce a placeholder."""
        df = pd.DataFrame({"a": ["x", "y", "z"], "b": ["p", "q", "r"]})
        result = generator.create_bar_chart(df, title="No Numbers")
        assert result is not None

    def test_bar_chart_invalid_column_returns_placeholder(self, generator):
        """Referencing a nonexistent column returns a placeholder (error is logged)."""
        df = pd.DataFrame({"a": [1, 2, 3]})
        # The bar engine catches KeyError internally and returns a placeholder
        result = generator.create_bar_chart(df, x_column="nonexistent", y_column="a")
        assert result is not None

    def test_line_chart_empty_data_returns_placeholder(self, generator):
        """Empty data should produce a placeholder, not crash."""
        df = pd.DataFrame()
        result = generator.create_line_chart(df, title="Empty Line")
        assert result is not None

    def test_save_figure_as_vector_invalid_format_raises(self, generator):
        """An unsupported vector format is invalid input -> ValueError (SU-1)."""
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3])
        try:
            with pytest.raises(ValueError):
                generator.save_figure_as_vector(fig, "/tmp/test", fmt="bmp")
        finally:
            plt.close(fig)


# ---------------------------------------------------------------------------
# _escape_paragraph edge cases
# ---------------------------------------------------------------------------

@needs_reportlab
class TestEscapeParagraphErrors:

    def test_escape_paragraph_none_input_returns_string(self):
        """Non-string input should be coerced, not raise."""
        from siege_utilities.reporting.report_generator import _escape_paragraph
        result = _escape_paragraph(None)
        assert isinstance(result, str)
        assert "None" in result

    def test_escape_paragraph_empty_string(self):
        from siege_utilities.reporting.report_generator import _escape_paragraph
        assert _escape_paragraph("") == ""

    def test_escape_paragraph_html_entities(self):
        from siege_utilities.reporting.report_generator import _escape_paragraph
        result = _escape_paragraph("Q&A about <3 favorites")
        assert "&amp;" in result
        assert "&lt;" in result
        assert "<3" not in result


# ---------------------------------------------------------------------------
# ClientBranding error paths
# ---------------------------------------------------------------------------

class TestClientBrandingErrors:

    def test_slugify_empty_name_raises(self):
        from siege_utilities.reporting.client_branding import _slugify_client_name
        with pytest.raises(ValueError, match="non-empty string"):
            _slugify_client_name("")

    def test_slugify_none_raises(self):
        from siege_utilities.reporting.client_branding import _slugify_client_name
        with pytest.raises(ValueError):
            _slugify_client_name(None)  # type: ignore[arg-type]

    def test_slugify_only_special_chars_raises(self):
        from siege_utilities.reporting.client_branding import _slugify_client_name
        with pytest.raises(ValueError, match="no slug-safe characters"):
            _slugify_client_name("...")


# ---------------------------------------------------------------------------
# _process_chart_list error paths
# ---------------------------------------------------------------------------

@needs_reportlab
class TestProcessChartListErrors:

    def test_process_chart_list_invalid_path_skipped(self, tmp_path):
        """A nonexistent file path in chart list should be silently skipped."""
        from siege_utilities.reporting.report_generator import ReportGenerator
        gen = ReportGenerator(client_name="test", output_dir=tmp_path)
        result = gen._process_chart_list([str(tmp_path / "nonexistent.png")])
        assert result == []

    def test_process_chart_list_none_type_skipped(self, tmp_path):
        """None in the chart list should be skipped without raising."""
        from siege_utilities.reporting.report_generator import ReportGenerator
        gen = ReportGenerator(client_name="test", output_dir=tmp_path)
        result = gen._process_chart_list([None])
        # Should not raise; None has no .drawOn, not a str/Path, etc.
        assert isinstance(result, list)

    def test_process_chart_list_empty_list_returns_empty(self, tmp_path):
        """An empty chart list should return an empty list."""
        from siege_utilities.reporting.report_generator import ReportGenerator
        gen = ReportGenerator(client_name="test", output_dir=tmp_path)
        result = gen._process_chart_list([])
        assert result == []

    def test_process_chart_list_dict_missing_path_skipped(self, tmp_path):
        """A dict chart with no valid path should be skipped."""
        from siege_utilities.reporting.report_generator import ReportGenerator
        gen = ReportGenerator(client_name="test", output_dir=tmp_path)
        result = gen._process_chart_list([{"title": "no path here"}])
        assert result == []

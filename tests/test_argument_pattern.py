"""
Tests for Argument + TableType additions (SAL-64).
"""
import pandas as pd
import pytest

try:
    import reportlab  # noqa: F401
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

requires_reportlab = pytest.mark.skipif(
    not REPORTLAB_AVAILABLE, reason="reportlab not installed"
)


# ---------------------------------------------------------------------------
# TableType
# ---------------------------------------------------------------------------

class TestTableTypeEnum:
    def test_all_seven_variants_importable(self):
        from siege_utilities.reporting.pages.page_models import TableType
        expected = {
            "SINGLE_RESPONSE", "MULTIPLE_RESPONSE", "CROSS_TAB",
            "LONGITUDINAL", "RANKING", "MEAN_SCALE", "BANNER",
        }
        actual = {m.name for m in TableType}
        assert actual == expected

    def test_values_are_snake_case_strings(self):
        from siege_utilities.reporting.pages.page_models import TableType
        for member in TableType:
            assert member.value == member.name.lower()

    def test_importable_from_reporting_top_level(self):
        from siege_utilities.reporting import TableType
        assert TableType is not None
        assert hasattr(TableType, "MULTIPLE_RESPONSE")


# ---------------------------------------------------------------------------
# Argument
# ---------------------------------------------------------------------------

class TestArgumentDefaults:
    def test_layout_auto_side_by_side_without_map(self):
        from siege_utilities.reporting.pages.page_models import Argument, TableType
        df = pd.DataFrame({"q": ["yes", "no"], "n": [60, 40]})
        arg = Argument(
            headline="Party ID",
            narrative="Most respondents lean left.",
            table=df,
            table_type=TableType.SINGLE_RESPONSE,
        )
        assert arg.layout == "side_by_side"

    def test_layout_auto_full_width_with_map(self):
        from siege_utilities.reporting.pages.page_models import Argument, TableType
        df = pd.DataFrame({"q": ["yes"], "n": [100]})
        arg = Argument(
            headline="Geographic spread",
            narrative="Heavy concentration in metro areas.",
            table=df,
            table_type=TableType.CROSS_TAB,
            map_figure=object(),  # any truthy value
        )
        assert arg.layout == "full_width"

    def test_explicit_layout_overrides_auto(self):
        from siege_utilities.reporting.pages.page_models import Argument, TableType
        df = pd.DataFrame()
        arg = Argument(
            headline="X", narrative="Y", table=df,
            table_type=TableType.RANKING,
            layout="full_width",
        )
        assert arg.layout == "full_width"

    def test_tags_default_to_empty_list(self):
        from siege_utilities.reporting.pages.page_models import Argument, TableType
        arg = Argument(
            headline="H", narrative="N", table=None,
            table_type=TableType.BANNER,
        )
        assert arg.tags == []

    def test_importable_from_reporting_top_level(self):
        from siege_utilities.reporting import Argument
        assert Argument is not None

    def test_base_note_and_source_note_default_none(self):
        from siege_utilities.reporting.pages.page_models import Argument, TableType
        arg = Argument(headline="H", narrative="N", table=None,
                       table_type=TableType.MEAN_SCALE)
        assert arg.base_note is None
        assert arg.source_note is None


# ---------------------------------------------------------------------------
# TitlePage — parameterized
# ---------------------------------------------------------------------------

@requires_reportlab
class TestTitlePageParameterized:
    PRIMARY = "#1a3a5c"
    SECONDARY = "#2d6a9f"
    ACCENT = "#e8a020"

    def _make_page(self, **kwargs):
        from siege_utilities.reporting.pages.page_models import TitlePage
        defaults = dict(
            primary_color=self.PRIMARY,
            secondary_color=self.SECONDARY,
            accent_color=self.ACCENT,
            client_name="Acme Corp",
            client_url="https://acme.example.com",
            prepared_by="Siege Analytics",
        )
        defaults.update(kwargs)
        return TitlePage(**defaults)

    def test_default_report_type_has_no_google_analytics(self):
        page = self._make_page()
        # build() returns a story list; inspect the first paragraph's text
        story = page.build("2025-01-01", "2025-12-31")
        first_para = story[0]
        assert "GOOGLE ANALYTICS" not in first_para.text
        assert "ANALYTICS REPORT" in first_para.text

    def test_custom_report_type_appears_in_header(self):
        page = self._make_page(report_type="DONOR INTELLIGENCE REPORT")
        story = page.build("2025-01-01", "2025-12-31")
        assert "DONOR INTELLIGENCE REPORT" in story[0].text

    def test_tagline_omitted_when_empty(self):
        page = self._make_page(tagline="")
        story = page.build("2025-01-01", "2025-12-31")
        texts = [getattr(el, "text", "") for el in story]
        assert not any("200 years" in t for t in texts)

    def test_tagline_rendered_when_provided(self):
        page = self._make_page(tagline="Serving democracy since 1960")
        story = page.build("2025-01-01", "2025-12-31")
        texts = [getattr(el, "text", "") for el in story]
        assert any("Serving democracy" in t for t in texts)

    def test_no_masai_or_siege_hardcoded(self):
        page = self._make_page(prepared_by="Custom Firm LLC")
        story = page.build("2025-01-01", "2025-12-31")
        combined = " ".join(getattr(el, "text", "") for el in story)
        assert "Masai Interactive" not in combined

    def test_phone_omitted_when_none(self):
        page = self._make_page(phone=None)
        story = page.build("2025-01-01", "2025-12-31")
        texts = [getattr(el, "text", "") for el in story]
        assert not any("Phone" in t for t in texts)

    def test_phone_present_when_provided(self):
        page = self._make_page(phone="+12025550100")
        story = page.build("2025-01-01", "2025-12-31")
        texts = [getattr(el, "text", "") for el in story]
        assert any("+12025550100" in t for t in texts)


# ---------------------------------------------------------------------------
# TableOfContentsPage.build()
# ---------------------------------------------------------------------------

@requires_reportlab
class TestTocBuild:
    PRIMARY = "#1a3a5c"
    SECONDARY = "#2d6a9f"
    ACCENT = "#e8a020"

    def _make_page(self):
        from siege_utilities.reporting.pages.page_models import TableOfContentsPage
        return TableOfContentsPage(self.PRIMARY, self.SECONDARY, self.ACCENT)

    def test_build_returns_non_empty_story(self):
        page = self._make_page()
        toc_data = [
            {"section": "Overview", "title": "Executive Summary", "page_num": 2},
            {"section": "Overview", "title": "Methodology", "page_num": 3},
            {"section": "Results", "title": "Party ID", "page_num": 5},
        ]
        story = page.build(toc_data)
        assert len(story) > 0

    def test_build_with_empty_list(self):
        page = self._make_page()
        story = page.build([])
        assert isinstance(story, list)

    def test_build_includes_title_text(self):
        page = self._make_page()
        story = page.build([{"section": "S1", "title": "Item A"}])
        texts = [getattr(el, "text", "") for el in story]
        assert any("Table of Contents" in t for t in texts)

    def test_build_includes_section_and_item(self):
        page = self._make_page()
        story = page.build([{"section": "Demographics", "title": "Age Breakdown"}])
        texts = [getattr(el, "text", "") for el in story]
        assert any("Demographics" in t for t in texts)
        assert any("Age Breakdown" in t for t in texts)

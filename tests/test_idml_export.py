"""
Tests for siege_utilities.reporting.idml_export

Covers:
- IDMLExporter class methods (text frames, image frames, tables, placeholders)
- Manual ZIP-based IDML creation (no simpleidml dependency)
- export_report_idml() convenience function with ga_data dict
- Template loading with mocked simpleidml
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any, Dict
from unittest import mock

import pytest

from siege_utilities.reporting.idml_export import (
    IDMLExporter,
    export_report_idml,
    _uid,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def exporter():
    """Return a fresh IDMLExporter (no template)."""
    return IDMLExporter()


@pytest.fixture
def tmp_dir(tmp_path):
    """Return a temporary directory as a Path."""
    return tmp_path


def _sample_ga_data() -> Dict[str, Any]:
    """Minimal ga_data dict matching the structure from the GA report example."""
    return {
        "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
        "totals": {
            "users": 15000,
            "sessions": 22000,
            "pageviews": 65000,
            "avg_bounce_rate": 42.5,
            "avg_session_duration": 145.3,
            "pages_per_session": 2.95,
        },
        "changes": {
            "users": 10.5,
            "sessions": 8.2,
            "bounce_rate": -3.1,
            "duration": 12.4,
        },
        "traffic_sources": [
            {"source": "organic", "medium": "search", "sessions": 9900,
             "users": 6300, "bounce_rate": 42.3, "avg_duration": 145.2},
            {"source": "direct", "medium": "(none)", "sessions": 5500,
             "users": 4200, "bounce_rate": 38.7, "avg_duration": 168.5},
        ],
        "top_pages": [
            {"page": "/", "pageviews": 16250, "unique_views": 14300,
             "avg_time": 45.3, "bounce_rate": 35.2, "exit_rate": 28.4},
            {"page": "/products", "pageviews": 11700, "unique_views": 9750,
             "avg_time": 92.1, "bounce_rate": 42.1, "exit_rate": 35.7},
        ],
        "devices": [
            {"device": "desktop", "sessions": 11440, "bounce_rate": 38.2},
            {"device": "mobile", "sessions": 9240, "bounce_rate": 52.4},
        ],
        "geo_data": [
            {"country": "United States", "region": "California",
             "city": "Los Angeles", "sessions": 3300, "users": 2100},
        ],
    }


# ---------------------------------------------------------------------------
# Tests: _uid helper
# ---------------------------------------------------------------------------

class TestUid:
    def test_uid_returns_string(self):
        assert isinstance(_uid(), str)

    def test_uid_is_8_chars(self):
        assert len(_uid()) == 8

    def test_uid_is_unique(self):
        ids = {_uid() for _ in range(100)}
        assert len(ids) == 100


# ---------------------------------------------------------------------------
# Tests: IDMLExporter — basic construction
# ---------------------------------------------------------------------------

class TestIDMLExporterInit:
    def test_default_construction(self, exporter):
        assert exporter.template_path is None
        assert exporter.page_width == 612.0
        assert exporter.page_height == 792.0
        assert exporter._text_frames == []
        assert exporter._image_frames == []
        assert exporter._tables == []
        assert exporter._replacements == {}
        assert exporter._idml_package is None

    def test_custom_page_dimensions(self):
        ex = IDMLExporter(page_width=842, page_height=595)  # A4 landscape
        assert ex.page_width == 842
        assert ex.page_height == 595

    def test_template_path_stored(self, tmp_dir):
        p = tmp_dir / "template.idml"
        ex = IDMLExporter(template_path=str(p))
        assert ex.template_path == p


# ---------------------------------------------------------------------------
# Tests: add_text_frame
# ---------------------------------------------------------------------------

class TestAddTextFrame:
    def test_add_text_frame_basic(self, exporter):
        exporter.add_text_frame("Hello World")
        assert len(exporter._text_frames) == 1
        frame = exporter._text_frames[0]
        assert frame["text"] == "Hello World"
        assert frame["style"] == "NormalParagraphStyle"
        assert "uid" in frame

    def test_add_text_frame_custom_style(self, exporter):
        exporter.add_text_frame("Title", style_name="Heading1", x=10, y=20,
                                width=400, height=50)
        frame = exporter._text_frames[0]
        assert frame["style"] == "Heading1"
        assert frame["x"] == 10
        assert frame["y"] == 20
        assert frame["width"] == 400
        assert frame["height"] == 50

    def test_add_multiple_frames(self, exporter):
        exporter.add_text_frame("One")
        exporter.add_text_frame("Two")
        exporter.add_text_frame("Three")
        assert len(exporter._text_frames) == 3
        texts = [f["text"] for f in exporter._text_frames]
        assert texts == ["One", "Two", "Three"]


# ---------------------------------------------------------------------------
# Tests: add_image_frame
# ---------------------------------------------------------------------------

class TestAddImageFrame:
    def test_add_image_frame(self, exporter):
        exporter.add_image_frame("/path/to/chart.png", x=50, y=100,
                                 width=300, height=200)
        assert len(exporter._image_frames) == 1
        img = exporter._image_frames[0]
        assert img["image_path"] == "/path/to/chart.png"
        assert img["x"] == 50
        assert img["width"] == 300


# ---------------------------------------------------------------------------
# Tests: add_table
# ---------------------------------------------------------------------------

class TestAddTable:
    def test_add_table(self, exporter):
        headers = ["Name", "Value"]
        rows = [["Alice", "100"], ["Bob", "200"]]
        exporter.add_table(headers, rows, x=72, y=200, width=468, height=100)
        assert len(exporter._tables) == 1
        tbl = exporter._tables[0]
        assert tbl["headers"] == ["Name", "Value"]
        assert len(tbl["rows"]) == 2


# ---------------------------------------------------------------------------
# Tests: replace_placeholder
# ---------------------------------------------------------------------------

class TestReplacePlaceholder:
    def test_register_replacement(self, exporter):
        exporter.replace_placeholder("{{NAME}}", "Siege Analytics")
        assert exporter._replacements["{{NAME}}"] == "Siege Analytics"

    def test_replacement_applied_in_text(self, exporter, tmp_dir):
        exporter.add_text_frame("Hello {{NAME}}, welcome!")
        exporter.replace_placeholder("{{NAME}}", "Dheeraj")
        out = tmp_dir / "test_replace.idml"
        exporter.save(str(out))

        with zipfile.ZipFile(out) as zf:
            story_files = [n for n in zf.namelist() if n.startswith("Stories/")]
            assert len(story_files) >= 1
            content = zf.read(story_files[0]).decode("utf-8")
            assert "Dheeraj" in content
            assert "{{NAME}}" not in content

    def test_multiple_replacements(self, exporter, tmp_dir):
        exporter.add_text_frame("{{A}} and {{B}}")
        exporter.replace_placeholder("{{A}}", "Alpha")
        exporter.replace_placeholder("{{B}}", "Beta")
        out = tmp_dir / "multi_replace.idml"
        exporter.save(str(out))

        with zipfile.ZipFile(out) as zf:
            story_files = [n for n in zf.namelist() if n.startswith("Stories/")]
            content = zf.read(story_files[0]).decode("utf-8")
            assert "Alpha" in content
            assert "Beta" in content


# ---------------------------------------------------------------------------
# Tests: save — manual ZIP structure
# ---------------------------------------------------------------------------

class TestSaveManualZip:
    def test_save_creates_file(self, exporter, tmp_dir):
        out = tmp_dir / "output.idml"
        result = exporter.save(str(out))
        assert Path(result).exists()

    def test_save_appends_extension(self, exporter, tmp_dir):
        out = tmp_dir / "output"
        result = exporter.save(str(out))
        assert result.endswith(".idml")
        assert Path(result).exists()

    def test_save_creates_parent_dirs(self, exporter, tmp_dir):
        out = tmp_dir / "sub" / "dir" / "report.idml"
        result = exporter.save(str(out))
        assert Path(result).exists()

    def test_output_is_valid_zip(self, exporter, tmp_dir):
        exporter.add_text_frame("Test content")
        out = tmp_dir / "valid.idml"
        exporter.save(str(out))
        assert zipfile.is_zipfile(out)

    def test_zip_contains_required_files(self, exporter, tmp_dir):
        exporter.add_text_frame("Content")
        out = tmp_dir / "structure.idml"
        exporter.save(str(out))

        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
            assert "mimetype" in names
            assert "META-INF/container.xml" in names
            assert "designmap.xml" in names
            assert "Resources/Preferences.xml" in names
            assert "Resources/Styles.xml" in names
            assert "Resources/Graphic.xml" in names
            assert "Resources/Fonts.xml" in names
            # At least one spread and one story
            assert any(n.startswith("Spreads/") for n in names)
            assert any(n.startswith("Stories/") for n in names)

    def test_mimetype_content(self, exporter, tmp_dir):
        exporter.add_text_frame("X")
        out = tmp_dir / "mime.idml"
        exporter.save(str(out))
        with zipfile.ZipFile(out) as zf:
            assert zf.read("mimetype") == b"application/vnd.adobe.indesign-idml-package"

    def test_designmap_references_stories(self, exporter, tmp_dir):
        exporter.add_text_frame("A")
        exporter.add_text_frame("B")
        out = tmp_dir / "dm.idml"
        exporter.save(str(out))
        with zipfile.ZipFile(out) as zf:
            dm = zf.read("designmap.xml").decode("utf-8")
            assert "idPkg:Story" in dm
            assert "idPkg:Spread" in dm

    def test_page_dimensions_in_preferences(self, tmp_dir):
        ex = IDMLExporter(page_width=800, page_height=600)
        ex.add_text_frame("Custom page")
        out = tmp_dir / "custom_page.idml"
        ex.save(str(out))
        with zipfile.ZipFile(out) as zf:
            prefs = zf.read("Resources/Preferences.xml").decode("utf-8")
            assert 'PageWidth="800"' in prefs
            assert 'PageHeight="600"' in prefs

    def test_text_content_in_story(self, exporter, tmp_dir):
        exporter.add_text_frame("Important Analysis")
        out = tmp_dir / "text.idml"
        exporter.save(str(out))
        with zipfile.ZipFile(out) as zf:
            story_files = [n for n in zf.namelist() if n.startswith("Stories/")]
            all_content = " ".join(zf.read(s).decode("utf-8") for s in story_files)
            assert "Important Analysis" in all_content

    def test_image_frame_link(self, exporter, tmp_dir):
        exporter.add_image_frame("/charts/chart1.png", x=10, y=10,
                                 width=200, height=150)
        out = tmp_dir / "img.idml"
        exporter.save(str(out))
        with zipfile.ZipFile(out) as zf:
            spread_files = [n for n in zf.namelist() if n.startswith("Spreads/")]
            spread_xml = zf.read(spread_files[0]).decode("utf-8")
            assert "/charts/chart1.png" in spread_xml
            assert "Rectangle" in spread_xml

    def test_table_content(self, exporter, tmp_dir):
        exporter.add_table(
            ["Col1", "Col2"],
            [["a", "b"], ["c", "d"]],
        )
        out = tmp_dir / "tbl.idml"
        exporter.save(str(out))
        with zipfile.ZipFile(out) as zf:
            story_files = [n for n in zf.namelist() if n.startswith("Stories/")]
            all_content = " ".join(zf.read(s).decode("utf-8") for s in story_files)
            assert "Col1" in all_content
            assert "Col2" in all_content

    def test_xml_special_chars_escaped(self, exporter, tmp_dir):
        exporter.add_text_frame('Value < 100 & value > 50 "quoted"')
        out = tmp_dir / "escape.idml"
        exporter.save(str(out))
        with zipfile.ZipFile(out) as zf:
            story_files = [n for n in zf.namelist() if n.startswith("Stories/")]
            content = zf.read(story_files[0]).decode("utf-8")
            assert "&lt;" in content
            assert "&gt;" in content
            assert "&amp;" in content
            assert "&quot;" in content

    def test_empty_exporter_produces_valid_idml(self, exporter, tmp_dir):
        """Even with no content, save should produce a valid IDML ZIP."""
        out = tmp_dir / "empty.idml"
        exporter.save(str(out))
        assert zipfile.is_zipfile(out)
        with zipfile.ZipFile(out) as zf:
            assert "designmap.xml" in zf.namelist()

    def test_custom_style_in_styles_xml(self, exporter, tmp_dir):
        exporter.add_text_frame("Styled", style_name="MyCustomStyle")
        out = tmp_dir / "styles.idml"
        exporter.save(str(out))
        with zipfile.ZipFile(out) as zf:
            styles = zf.read("Resources/Styles.xml").decode("utf-8")
            assert "MyCustomStyle" in styles

    def test_geometric_bounds_format(self, exporter, tmp_dir):
        exporter.add_text_frame("Pos", x=100, y=200, width=300, height=50)
        out = tmp_dir / "bounds.idml"
        exporter.save(str(out))
        with zipfile.ZipFile(out) as zf:
            spread_files = [n for n in zf.namelist() if n.startswith("Spreads/")]
            spread_xml = zf.read(spread_files[0]).decode("utf-8")
            # Bounds should be "top left bottom right" = "y x y+h x+w"
            assert "200 100 250 400" in spread_xml


# ---------------------------------------------------------------------------
# Tests: export_report_idml convenience function
# ---------------------------------------------------------------------------

class TestExportReportIdml:
    def test_basic_export(self, tmp_dir):
        ga_data = _sample_ga_data()
        out = tmp_dir / "ga_report.idml"
        result = export_report_idml(ga_data, str(out))
        assert Path(result).exists()
        assert zipfile.is_zipfile(result)

    def test_title_in_output(self, tmp_dir):
        ga_data = _sample_ga_data()
        out = tmp_dir / "titled.idml"
        export_report_idml(ga_data, str(out), title="Q1 Report")
        with zipfile.ZipFile(out) as zf:
            stories = [n for n in zf.namelist() if n.startswith("Stories/")]
            all_content = " ".join(zf.read(s).decode("utf-8") for s in stories)
            assert "Q1 Report" in all_content

    def test_date_range_in_output(self, tmp_dir):
        ga_data = _sample_ga_data()
        out = tmp_dir / "dated.idml"
        export_report_idml(ga_data, str(out))
        with zipfile.ZipFile(out) as zf:
            stories = [n for n in zf.namelist() if n.startswith("Stories/")]
            all_content = " ".join(zf.read(s).decode("utf-8") for s in stories)
            assert "2026-01-01" in all_content
            assert "2026-01-31" in all_content

    def test_kpi_data_in_output(self, tmp_dir):
        ga_data = _sample_ga_data()
        out = tmp_dir / "kpi.idml"
        export_report_idml(ga_data, str(out))
        with zipfile.ZipFile(out) as zf:
            stories = [n for n in zf.namelist() if n.startswith("Stories/")]
            all_content = " ".join(zf.read(s).decode("utf-8") for s in stories)
            assert "15,000" in all_content  # formatted users
            assert "22,000" in all_content  # formatted sessions

    def test_traffic_sources_table(self, tmp_dir):
        ga_data = _sample_ga_data()
        out = tmp_dir / "sources.idml"
        export_report_idml(ga_data, str(out))
        with zipfile.ZipFile(out) as zf:
            stories = [n for n in zf.namelist() if n.startswith("Stories/")]
            all_content = " ".join(zf.read(s).decode("utf-8") for s in stories)
            assert "organic" in all_content
            assert "direct" in all_content

    def test_top_pages_table(self, tmp_dir):
        ga_data = _sample_ga_data()
        out = tmp_dir / "pages.idml"
        export_report_idml(ga_data, str(out))
        with zipfile.ZipFile(out) as zf:
            stories = [n for n in zf.namelist() if n.startswith("Stories/")]
            all_content = " ".join(zf.read(s).decode("utf-8") for s in stories)
            assert "/products" in all_content

    def test_devices_table(self, tmp_dir):
        ga_data = _sample_ga_data()
        out = tmp_dir / "devs.idml"
        export_report_idml(ga_data, str(out))
        with zipfile.ZipFile(out) as zf:
            stories = [n for n in zf.namelist() if n.startswith("Stories/")]
            all_content = " ".join(zf.read(s).decode("utf-8") for s in stories)
            assert "desktop" in all_content
            assert "mobile" in all_content

    def test_empty_ga_data(self, tmp_dir):
        """Should not crash with minimal/empty ga_data."""
        out = tmp_dir / "empty_ga.idml"
        result = export_report_idml({}, str(out))
        assert Path(result).exists()

    def test_placeholder_substitution_applied(self, tmp_dir):
        ga_data = _sample_ga_data()
        out = tmp_dir / "placeholders.idml"
        export_report_idml(ga_data, str(out))
        with zipfile.ZipFile(out) as zf:
            stories = [n for n in zf.namelist() if n.startswith("Stories/")]
            all_content = " ".join(zf.read(s).decode("utf-8") for s in stories)
            # Placeholders should have been replaced, not left raw
            assert "{{TITLE}}" not in all_content
            assert "{{DATE_RANGE}}" not in all_content

    def test_zip_structure_complete(self, tmp_dir):
        ga_data = _sample_ga_data()
        out = tmp_dir / "complete.idml"
        export_report_idml(ga_data, str(out))
        with zipfile.ZipFile(out) as zf:
            names = zf.namelist()
            assert "mimetype" in names
            assert "designmap.xml" in names
            assert any(n.startswith("Spreads/") for n in names)
            assert any(n.startswith("Stories/") for n in names)


# ---------------------------------------------------------------------------
# Tests: simpleidml mock path
# ---------------------------------------------------------------------------

class TestSimpleIDMLPath:
    def test_template_loading_with_mock_simpleidml(self, tmp_dir):
        """When simpleidml is available, loading a template should use it."""
        # Create a fake IDML file (just a ZIP)
        template = tmp_dir / "template.idml"
        with zipfile.ZipFile(template, "w") as zf:
            zf.writestr("mimetype", "application/vnd.adobe.indesign-idml-package")
            zf.writestr("designmap.xml", "<Document/>")

        mock_package = mock.MagicMock()
        mock_package.stories = []

        with mock.patch("siege_utilities.reporting.idml_export.SIMPLEIDML_AVAILABLE", True):
            with mock.patch("siege_utilities.reporting.idml_export.simpleidml") as mock_sidml:
                mock_sidml.IDMLPackage.return_value = mock_package
                ex = IDMLExporter(template_path=str(template))
                assert ex._idml_package is mock_package
                mock_sidml.IDMLPackage.assert_called_once_with(str(template))

    def test_save_with_simpleidml_calls_export(self, tmp_dir):
        """When simpleidml package is loaded, save delegates to it."""
        mock_package = mock.MagicMock()
        mock_package.stories = []

        ex = IDMLExporter()
        ex._idml_package = mock_package
        ex.replace_placeholder("{{X}}", "Y")

        out = tmp_dir / "via_sidml.idml"
        ex.save(str(out))

        mock_package.export_to_file.assert_called_once()

    def test_save_with_simpleidml_applies_replacements(self, tmp_dir):
        mock_package = mock.MagicMock()
        mock_package.stories = []
        mock_package.set_tag.side_effect = Exception("not supported")
        mock_package.read.return_value = b"<Content>{{NAME}}</Content>"

        ex = IDMLExporter()
        ex._idml_package = mock_package
        ex.replace_placeholder("{{NAME}}", "Test")

        out = tmp_dir / "replace_sidml.idml"
        ex.save(str(out))

        # Should have tried set_tag, then fallen back to raw replacement
        mock_package.set_tag.assert_called_once_with("{{NAME}}", "Test")

    def test_fallback_when_simpleidml_load_fails(self, tmp_dir):
        """If simpleidml raises on load, fall back to manual builder."""
        template = tmp_dir / "bad.idml"
        template.write_bytes(b"not a zip")

        with mock.patch("siege_utilities.reporting.idml_export.SIMPLEIDML_AVAILABLE", True):
            with mock.patch("siege_utilities.reporting.idml_export.simpleidml") as mock_sidml:
                mock_sidml.IDMLPackage.side_effect = Exception("corrupt")
                ex = IDMLExporter(template_path=str(template))
                assert ex._idml_package is None  # fell back

        # Should still be able to save via manual path
        ex.add_text_frame("Fallback content")
        out = tmp_dir / "fallback.idml"
        ex.save(str(out))
        assert zipfile.is_zipfile(out)


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_unicode_content(self, exporter, tmp_dir):
        exporter.add_text_frame("Analyse des donnees en francais")
        out = tmp_dir / "unicode.idml"
        exporter.save(str(out))
        with zipfile.ZipFile(out) as zf:
            stories = [n for n in zf.namelist() if n.startswith("Stories/")]
            content = zf.read(stories[0]).decode("utf-8")
            assert "francais" in content

    def test_large_table(self, exporter, tmp_dir):
        headers = [f"Col{i}" for i in range(10)]
        rows = [[f"r{r}c{c}" for c in range(10)] for r in range(50)]
        exporter.add_table(headers, rows)
        out = tmp_dir / "large_table.idml"
        exporter.save(str(out))
        assert zipfile.is_zipfile(out)

    def test_mixed_content(self, exporter, tmp_dir):
        exporter.add_text_frame("Title", style_name="Title")
        exporter.add_text_frame("Body text")
        exporter.add_image_frame("/img/chart.png")
        exporter.add_table(["A", "B"], [["1", "2"]])
        out = tmp_dir / "mixed.idml"
        exporter.save(str(out))
        with zipfile.ZipFile(out) as zf:
            stories = [n for n in zf.namelist() if n.startswith("Stories/")]
            # 2 text frames + 1 table + 1 image = 4 stories
            assert len(stories) == 4

    def test_spread_contains_all_frames(self, exporter, tmp_dir):
        exporter.add_text_frame("TF1")
        exporter.add_text_frame("TF2")
        exporter.add_image_frame("/img.png")
        out = tmp_dir / "frames.idml"
        exporter.save(str(out))
        with zipfile.ZipFile(out) as zf:
            spread_files = [n for n in zf.namelist() if n.startswith("Spreads/")]
            spread_xml = zf.read(spread_files[0]).decode("utf-8")
            assert spread_xml.count("TextFrame") == 2
            assert "Rectangle" in spread_xml

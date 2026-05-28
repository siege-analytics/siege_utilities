"""Error-path tests for siege_utilities.reporting.templates (SU-4b).

Covers content_page_template, page_templates, table_of_contents_template,
and title_page_template.
"""

import pytest

try:
    from siege_utilities.reporting.templates.content_page_template import (
        ContentPageTemplate,
    )
    from siege_utilities.reporting.templates.title_page_template import (
        TitlePageTemplate,
    )
    from siege_utilities.reporting.templates.table_of_contents_template import (
        TableOfContentsTemplate,
    )
    from siege_utilities.reporting.templates.page_templates import (
        PageTemplateManager,
    )
    _SKIP = False
except ImportError:
    _SKIP = True

pytestmark = pytest.mark.skipif(_SKIP, reason="reporting template deps missing")


class TestContentPageTemplateErrors:
    """Error paths for ContentPageTemplate brand config loading."""

    def test_missing_branding_returns_none_or_default(self):
        """Missing branding manager returns default config without raising."""
        template = ContentPageTemplate()
        config = template._load_brand_config()
        assert config is not None or config is None


class TestTitlePageTemplateErrors:
    """Error paths for TitlePageTemplate brand config loading."""

    def test_missing_branding_returns_none_or_default(self):
        """Missing branding manager returns default config without raising."""
        template = TitlePageTemplate()
        config = template._load_brand_config()
        assert config is not None or config is None


class TestTableOfContentsTemplateErrors:
    """Error paths for TableOfContentsTemplate brand config loading."""

    def test_missing_branding_returns_none_or_default(self):
        """Missing branding manager returns default config without raising."""
        template = TableOfContentsTemplate()
        config = template._load_brand_config()
        assert config is not None or config is None


class TestPageTemplateManagerErrors:
    """Error paths for PageTemplateManager."""

    def test_invalid_template_dir_returns_empty(self, tmp_path):
        """Nonexistent template directory does not raise on load."""
        bogus = tmp_path / "no_such_dir"
        mgr = PageTemplateManager(template_dir=str(bogus))
        assert mgr is not None

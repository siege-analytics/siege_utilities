"""Error-path coverage (SU-4b) for siege_utilities.reporting.templates.page_templates.

update_template and export_template raise KeyError for an unknown template.
"""
import pytest
from siege_utilities.reporting.templates.page_templates import PageTemplateManager


def test_modify_template_raises_keyerror_for_unknown_template():
    mgr = PageTemplateManager()
    with pytest.raises(KeyError) as exc_info:
        mgr.modify_template("no_such_template_zzz", page_width=100)
    assert "Template not found" in str(exc_info.value)


def test_export_template_raises_keyerror_for_unknown_template(tmp_path):
    mgr = PageTemplateManager()
    with pytest.raises(KeyError):
        mgr.export_template("no_such_template_zzz", str(tmp_path / "out.yaml"))

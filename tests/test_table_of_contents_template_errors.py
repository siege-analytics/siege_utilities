"""Error-path coverage (SU-4b) for reporting.templates.table_of_contents_template.

Forces the except ImportError branch of _load_brand_config by making the
client_branding import fail; the handler must fall back to the default config.
"""
import io
import sys

from reportlab.pdfgen import canvas
from siege_utilities.reporting.templates.table_of_contents_template import TableOfContentsTemplate


def test_load_brand_config_falls_back_when_branding_import_fails(monkeypatch):
    tmpl = TableOfContentsTemplate(canvas.Canvas(io.BytesIO()))
    # Break the optional client_branding import so the except branch runs.
    monkeypatch.setitem(
        sys.modules,
        "siege_utilities.reporting.templates.client_branding",
        None,
    )
    cfg = tmpl._load_brand_config()
    assert isinstance(cfg, dict)

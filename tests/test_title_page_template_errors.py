"""Error-path coverage (SU-4b) for reporting.templates.title_page_template.

Forces the except ImportError branch of _load_brand_config by making the
client_branding import fail; the handler must fall back to the default config.
"""
import io
import sys

# reportlab is an optional reporting dependency; skip the module when it is
# absent (the no-GDAL / no-reporting CI job) so collection does not hard-fail.
try:
    import reportlab  # noqa: F401
except ImportError:
    import pytest
    pytest.skip("reportlab not available", allow_module_level=True)

from reportlab.pdfgen import canvas
from siege_utilities.reporting.templates.title_page_template import TitlePageTemplate


def test_load_brand_config_falls_back_when_branding_import_fails(monkeypatch):
    tmpl = TitlePageTemplate(canvas.Canvas(io.BytesIO()))
    # Break the optional client_branding import so the except branch runs.
    monkeypatch.setitem(
        sys.modules,
        "siege_utilities.reporting.templates.client_branding",
        None,
    )
    cfg = tmpl._load_brand_config()
    assert isinstance(cfg, dict)

"""A missing GDAL library marks GeoDjango unavailable instead of raising (#1889)."""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytest.importorskip("django")

REPO_ROOT = Path(__file__).resolve().parents[1]

# Runs in a fresh interpreter so siege_utilities.geo.django is imported anew
# and this process's module cache is untouched.
GDAL_MISSING_IMPORT = """
    import importlib.abc
    import sys

    from django.core.exceptions import ImproperlyConfigured

    hits = []

    class GdalMissingFinder(importlib.abc.MetaPathFinder):
        # Django raises this when the GDAL C library cannot be loaded.
        def find_spec(self, name, path=None, target=None):
            if name == "django.contrib.gis.db.models":
                hits.append(name)
                raise ImproperlyConfigured(
                    "Could not find the GDAL library. Is GDAL installed?"
                )
            return None

    sys.meta_path.insert(0, GdalMissingFinder())

    import siege_utilities.geo.django as geo_django

    print(geo_django.__file__)
    print(hits)
    print(geo_django._django_available, geo_django._gis_available)
    try:
        geo_django._check_dependencies()
    except ImportError as exc:
        print(type(exc).__name__, exc)
"""


def test_missing_gdal_marks_gis_unavailable_without_raising():
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(GDAL_MISSING_IMPORT)],
        capture_output=True, text=True, cwd=REPO_ROOT, timeout=120,
    )

    assert result.returncode == 0, result.stderr
    module_file, hits, flags, dependency_error = result.stdout.splitlines()
    assert Path(module_file).resolve().is_relative_to(REPO_ROOT)
    assert hits == "['django.contrib.gis.db.models']"
    assert flags == "True False"
    assert dependency_error.startswith("ImportError GeoDjango is not available.")

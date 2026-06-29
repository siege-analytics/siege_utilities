"""
Minimal Django settings for siege_utilities test suite.

Uses PostGIS backend — SpatiaLite is not viable because:
- pyenv Python lacks enable_load_extension
- mod_spatialite.so is not installed
- 11 boundary models use geoid__regex CheckConstraints (PostgreSQL ~ operator)

DB credentials via environment variables with local dev defaults.
"""

import os

from django.core.exceptions import ImproperlyConfigured

SECRET_KEY = "test-secret-key-not-for-production"

DEBUG = False

GDAL_LIBRARY_PATH = os.getenv("GDAL_LIBRARY_PATH", "")
GEOS_LIBRARY_PATH = os.getenv("GEOS_LIBRARY_PATH", "")

# Detect GDAL availability — controls DB engine and installed apps.
# Narrow to the exceptions that genuinely signal GDAL absence, so that an
# UNRELATED Django/GIS misconfiguration surfaces loudly instead of silently
# downgrading the test project to plain PostgreSQL (writing-code:7):
#   - ImproperlyConfigured: django.contrib.gis.gdal.libgdal raises this when
#     no GDAL library is found in its search names ("Could not find the GDAL
#     library") or the OS is unsupported.
#   - OSError: ctypes.CDLL fails to load a GDAL_LIBRARY_PATH that points at a
#     missing/unloadable shared object.
#   - ImportError: django.contrib.gis itself is unavailable.
# Any other exception (a real settings bug) is intentionally NOT caught.
_HAS_GDAL = False
try:
    from django.contrib.gis.gdal import libgdal  # noqa: F401
    _HAS_GDAL = True
except (ImproperlyConfigured, ImportError, OSError):
    pass

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
]

if _HAS_GDAL:
    INSTALLED_APPS += [
        "django.contrib.gis",
        "rest_framework_gis",
        "siege_utilities.geo.django",
    ]

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis" if _HAS_GDAL else "django.db.backends.postgresql",
        "NAME": os.environ.get("SIEGE_TEST_DB_NAME", "siege_geo"),
        "USER": os.environ.get("SIEGE_TEST_DB_USER", "postgres"),
        "PASSWORD": os.environ.get("SIEGE_TEST_DB_PASSWORD", ""),
        "HOST": os.environ.get("SIEGE_TEST_DB_HOST", "localhost"),
        "PORT": os.environ.get("SIEGE_TEST_DB_PORT", "5432"),
        "TEST": {
            "NAME": "test_siege_geo",
        },
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ROOT_URLCONF = "tests.django_project.urls"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "CRITICAL",
    },
}

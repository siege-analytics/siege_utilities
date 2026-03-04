"""
Minimal Django settings for siege_utilities test suite.

Uses PostGIS backend — SpatiaLite is not viable because:
- pyenv Python lacks enable_load_extension
- mod_spatialite.so is not installed
- 11 boundary models use geoid__regex CheckConstraints (PostgreSQL ~ operator)

DB credentials via environment variables with local dev defaults.
"""

import os

SECRET_KEY = "test-secret-key-not-for-production"

DEBUG = False

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.gis",
    "rest_framework",
    "rest_framework_gis",
    "siege_utilities.geo.django",
]

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
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

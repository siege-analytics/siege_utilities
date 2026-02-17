"""
Minimal Django settings for running GeoDjango unit tests.

Uses SQLite in-memory — sufficient for tests that only need
Django's ORM import chain (e.g. `from django.db import transaction`)
without actual database queries or spatial operations.

For tests that need PostGIS, use the @pytest.mark.integration marker.
"""

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SECRET_KEY = 'test-secret-key-not-for-production'

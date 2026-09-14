import ast
from pathlib import Path

from scripts import check_hollow_work


def _findings(source: str, path: str = "siege_utilities/example.py") -> list[str]:
    tree = ast.parse(source)
    return list(check_hollow_work.check_empty_bodies(Path(path), tree))


def test_import_error_fallback_logging_stubs_are_carved_out():
    source = '''
try:
    from siege_utilities.core.logging import log_info, log_warning, log_error, log_debug
except ImportError:
    def log_info(message): pass
    def log_warning(message): pass
    def log_error(message): pass
    def log_debug(message): pass
'''
    assert _findings(source) == []


def test_regular_pass_only_function_still_flags():
    source = '''
def placeholder():
    pass
'''
    findings = _findings(source)
    assert len(findings) == 1
    assert "def placeholder() has pass-only body" in findings[0]


def test_context_manager_dunder_noops_are_carved_out():
    source = '''
class Resource:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass
'''
    assert _findings(source) == []


def test_dummy_named_mapping_update_noop_is_carved_out():
    source = '''
from collections.abc import MutableMapping

class NoopMapping(MutableMapping):
    def __getitem__(self, key):
        raise KeyError(key)
    def __setitem__(self, key, value):
        raise TypeError("read only")
    def __delitem__(self, key):
        raise TypeError("read only")
    def __iter__(self):
        return iter(())
    def __len__(self):
        return 0
    def update(self, other=None, **kwargs):
        pass
'''
    assert _findings(source) == []


def test_regular_mutable_mapping_update_noop_still_flags():
    source = '''
from collections.abc import MutableMapping

class ReadOnlyMapping(MutableMapping):
    def __getitem__(self, key):
        raise KeyError(key)
    def __setitem__(self, key, value):
        raise TypeError("read only")
    def __delitem__(self, key):
        raise TypeError("read only")
    def __iter__(self):
        return iter(())
    def __len__(self):
        return 0
    def update(self, other=None, **kwargs):
        pass
'''
    findings = _findings(source)
    assert len(findings) == 1
    assert "def update() has pass-only body" in findings[0]


def test_regular_dict_init_noop_still_flags():
    source = '''
class ReadOnlyDict(dict):
    def __init__(self, *args, **kwargs):
        pass
'''
    findings = _findings(source)
    assert len(findings) == 1
    assert "def __init__() has pass-only body" in findings[0]


def test_django_appconfig_ready_noop_is_carved_out():
    source = '''
from django.apps import AppConfig

class SiegeGeoConfig(AppConfig):
    def ready(self):
        pass
'''
    assert _findings(source, "siege_utilities/geo/django/apps.py") == []


def test_dummy_progress_bar_noops_are_carved_out():
    source = '\nclass _DummyProgressBar:\n    def __init__(self, *args, **kwargs):\n        pass\n    def __enter__(self):\n        return self\n    def __exit__(self, *args):\n        pass\n    def update(self, n=1):\n        pass\n'
    assert _findings(source) == []

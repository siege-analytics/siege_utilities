"""
Django-style project settings for siege_utilities.

Resolution order (highest priority first):
1. Function parameters (caller always wins)
2. Environment variables (SIEGE_<SETTING_NAME>)
3. Django settings (if Django is installed and configured)
4. Project YAML file (siege_utilities.yaml, discovered by walking up from CWD)
5. Library defaults (conf/defaults.py)

Usage:
    from siege_utilities.conf import settings
    settings.STORAGE_CRS          # -> 4269
    settings.PROJECTION_CRS       # -> 2163

Override in tests:
    with settings.override(STORAGE_CRS=4326):
        assert settings.STORAGE_CRS == 4326
"""

import os
import threading
from contextlib import contextmanager
from pathlib import Path

from .defaults import DEFAULTS

_SENTINEL = object()


class Settings:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._local = threading.local()
                    obj._yaml_cache = None
                    obj._yaml_path = None
                    cls._instance = obj
        return cls._instance

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)

        # 1. Override context (thread-local)
        overrides = getattr(self._local, "overrides", {})
        if name in overrides:
            return overrides[name]

        # 2. Env var: SIEGE_<NAME>
        env_val = os.environ.get(f"SIEGE_{name}")
        if env_val is not None:
            return self._coerce(name, env_val)

        # 3. Django settings
        try:
            from django.conf import settings as django_settings

            if hasattr(django_settings, name):
                return getattr(django_settings, name)
        except (ImportError, Exception):
            pass

        # 4. YAML file
        yaml_conf = self._load_yaml()
        if yaml_conf and name in yaml_conf:
            return yaml_conf[name]

        # 5. Library defaults
        if name in DEFAULTS:
            return DEFAULTS[name]

        raise AttributeError(f"siege_utilities has no setting '{name}'")

    def _coerce(self, name: str, val: str):
        """Coerce env var string to the type of the default."""
        default = DEFAULTS.get(name)
        if isinstance(default, bool):
            return val.lower() in ("true", "1", "yes")
        if isinstance(default, int):
            return int(val)
        if isinstance(default, float):
            return float(val)
        return val

    def _load_yaml(self) -> dict | None:
        # SIEGE_SETTINGS_FILE overrides CWD discovery
        explicit = os.environ.get("SIEGE_SETTINGS_FILE")
        if explicit:
            candidate = Path(explicit)
            if candidate.is_file():
                if self._yaml_path == candidate and self._yaml_cache is not None:
                    return self._yaml_cache
                try:
                    import yaml

                    with open(candidate) as f:
                        self._yaml_cache = yaml.safe_load(f) or {}
                        self._yaml_path = candidate
                except ImportError:
                    pass
                return self._yaml_cache
            # Explicit path set but file missing — don't fall through to CWD walk
            self._yaml_path = None
            self._yaml_cache = None
            return None

        cwd = Path.cwd()
        for directory in [cwd, *cwd.parents]:
            candidate = directory / "siege_utilities.yaml"
            if candidate.is_file():
                # Return cached result if same file
                if self._yaml_path == candidate and self._yaml_cache is not None:
                    return self._yaml_cache
                try:
                    import yaml

                    with open(candidate) as f:
                        self._yaml_cache = yaml.safe_load(f) or {}
                        self._yaml_path = candidate
                except ImportError:
                    pass
                return self._yaml_cache
        self._yaml_path = None
        self._yaml_cache = None
        return None

    def reload(self):
        """Clear cached project settings and force fresh resolution."""
        self._yaml_cache = None
        self._yaml_path = None

    @contextmanager
    def override(self, **kwargs):
        """Temporarily override settings (thread-local, safe for concurrent use)."""
        overrides = getattr(self._local, "overrides", {})
        previous = {k: overrides.get(k, _SENTINEL) for k in kwargs}
        overrides = {**overrides, **kwargs}
        self._local.overrides = overrides
        try:
            yield self
        finally:
            current = getattr(self._local, "overrides", {})
            for k, v in previous.items():
                if v is _SENTINEL:
                    current.pop(k, None)
                else:
                    current[k] = v
            self._local.overrides = current

    @classmethod
    def _reset(cls):
        """Reset singleton — for tests only."""
        cls._instance = None


settings = Settings()

"""
Runtime compatibility guard for siege_utilities.

Provides a canonical, idempotent bootstrap utility that Databricks notebooks
and job clusters can call to verify (and if necessary repair) the Python
environment before importing heavy siege_utilities submodules.

Usage in a Databricks notebook cell::

    from siege_utilities.runtime import ensure_compatible
    ensure_compatible()          # raises RuntimeGuardError on failure
    # now safe to import anything from siege_utilities

The guard is deliberately stdlib-only so it can always be imported, even when
pydantic or other dependencies are in a broken state.

See: https://github.com/siege-analytics/siege_utilities/issues/211
"""

import importlib
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

__all__ = [
    "ensure_compatible",
    "diagnose_environment",
    "purge_stale_modules",
    "is_databricks_runtime",
    "RuntimeGuardError",
]

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class RuntimeGuardError(RuntimeError):
    """Raised when the runtime environment cannot satisfy siege_utilities requirements.

    Attributes:
        diagnostics: dict produced by :func:`diagnose_environment`
        remediation: human-readable remediation steps
    """

    def __init__(self, message: str, diagnostics: Optional[Dict] = None,
                 remediation: Optional[str] = None):
        self.diagnostics = diagnostics or {}
        self.remediation = remediation or ""
        full = message
        if remediation:
            full += f"\n\nRemediation:\n{remediation}"
        super().__init__(full)


# ---------------------------------------------------------------------------
# Environment detection
# ---------------------------------------------------------------------------

def is_databricks_runtime() -> bool:
    """Detect whether we are running inside a Databricks environment.

    Checks ``DATABRICKS_RUNTIME_VERSION`` (set on every DBR cluster) and
    falls back to probing for ``/dbfs``.
    """
    if os.environ.get("DATABRICKS_RUNTIME_VERSION"):
        return True
    if Path("/dbfs").is_dir():
        return True
    return False


def _get_databricks_runtime_version() -> Optional[str]:
    """Return the Databricks Runtime version string, or None."""
    return os.environ.get("DATABRICKS_RUNTIME_VERSION")


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def diagnose_environment() -> Dict:
    """Collect diagnostic information about the current Python environment.

    Returns a dict with:
    - ``python_version``: e.g. "3.11.9"
    - ``platform``: e.g. "linux"
    - ``is_databricks``: bool
    - ``databricks_runtime``: version string or None
    - ``pydantic_version``: installed version or "NOT INSTALLED"
    - ``pydantic_v2``: bool — True if pydantic>=2.0 is importable
    - ``pydantic_module_path``: file path of loaded pydantic module
    - ``typing_extensions_version``: version or "NOT INSTALLED"
    - ``siege_utilities_version``: version or "NOT INSTALLED"
    - ``stale_pydantic_modules``: list of pydantic module names still in sys.modules
    """
    diag: Dict = {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": sys.platform,
        "is_databricks": is_databricks_runtime(),
        "databricks_runtime": _get_databricks_runtime_version(),
    }

    # pydantic
    try:
        import pydantic
        diag["pydantic_version"] = getattr(pydantic, "__version__", "unknown")
        diag["pydantic_module_path"] = getattr(pydantic, "__file__", "unknown")
        # Check for v2 capability
        try:
            from pydantic import field_validator  # noqa: F401
            diag["pydantic_v2"] = True
        except ImportError:
            diag["pydantic_v2"] = False
    except ImportError:
        diag["pydantic_version"] = "NOT INSTALLED"
        diag["pydantic_module_path"] = None
        diag["pydantic_v2"] = False

    # typing_extensions
    try:
        import typing_extensions
        diag["typing_extensions_version"] = getattr(typing_extensions, "__version__", "unknown")
    except ImportError:
        diag["typing_extensions_version"] = "NOT INSTALLED"

    # siege_utilities
    try:
        diag["siege_utilities_version"] = importlib.metadata.version("siege-utilities")
    except Exception:
        try:
            from siege_utilities import __version__
            diag["siege_utilities_version"] = __version__
        except Exception:
            diag["siege_utilities_version"] = "NOT INSTALLED"

    # Stale pydantic modules in sys.modules
    diag["stale_pydantic_modules"] = [
        name for name in sys.modules if name == "pydantic" or name.startswith("pydantic.")
    ]

    return diag


# ---------------------------------------------------------------------------
# Module purge
# ---------------------------------------------------------------------------

def purge_stale_modules(prefixes: Optional[List[str]] = None) -> List[str]:
    """Remove cached modules from ``sys.modules`` matching the given prefixes.

    This is necessary on Databricks when the cluster pre-installs pydantic v1
    but siege_utilities needs v2.  After ``pip install pydantic>=2``, the old
    v1 module objects remain cached and shadow the new installation.

    Args:
        prefixes: Module name prefixes to purge.  Defaults to
            ``["pydantic", "siege_utilities"]``.

    Returns:
        List of module names that were purged.
    """
    if prefixes is None:
        prefixes = ["pydantic", "siege_utilities"]

    purged = []
    for name in list(sys.modules.keys()):
        if any(name == p or name.startswith(p + ".") for p in prefixes):
            del sys.modules[name]
            purged.append(name)

    if purged:
        log.info("Purged %d stale modules from sys.modules: %s",
                 len(purged), ", ".join(sorted(purged)[:10]))

    return purged


# ---------------------------------------------------------------------------
# Main guard
# ---------------------------------------------------------------------------

_REMEDIATION_DATABRICKS = """\
In a Databricks notebook cell, run:

    %pip install 'pydantic>=2,<3' 'typing_extensions>=4.6' 'siege-utilities[geo,data]>=3.4.1,<4'

Then restart the Python process:

    dbutils.library.restartPython()

Or call the full bootstrap:

    from siege_utilities.runtime import ensure_compatible
    ensure_compatible(auto_install=True)
"""

_REMEDIATION_LOCAL = """\
Run:

    pip install 'pydantic>=2,<3' 'typing_extensions>=4.6' 'siege-utilities>=3.4.1'
"""


def ensure_compatible(
    *,
    auto_install: bool = False,
    purge_on_conflict: bool = True,
    required_imports: Optional[List[Tuple[str, str]]] = None,
    quiet: bool = False,
) -> Dict:
    """Verify (and optionally repair) the runtime environment for siege_utilities.

    This is the canonical entry-point that Databricks notebooks should call
    before importing heavy siege_utilities submodules.  It is **idempotent** —
    calling it multiple times is safe and cheap after the first success.

    Args:
        auto_install: If True and pydantic v2 is missing, attempt
            ``pip install`` to fix the environment.  Only recommended for
            interactive notebook use, not production jobs.
        purge_on_conflict: If True (default), purge stale pydantic/siege_utilities
            modules from ``sys.modules`` after detecting a version conflict.
        required_imports: Additional (module, attribute) pairs to verify.
            Defaults to checking ``pydantic.field_validator`` (the v2 sentinel).
        quiet: Suppress info-level log messages.

    Returns:
        The diagnostics dict (same as :func:`diagnose_environment`).

    Raises:
        RuntimeGuardError: If the environment is incompatible and cannot be
            repaired (with diagnostics and remediation in the exception).
    """
    if required_imports is None:
        required_imports = [
            ("pydantic", "field_validator"),
            ("pydantic", "BaseModel"),
        ]

    diag = diagnose_environment()

    if not quiet:
        log.info(
            "siege_utilities runtime guard: Python %s, pydantic=%s, databricks=%s",
            diag["python_version"],
            diag["pydantic_version"],
            diag["is_databricks"],
        )

    # Fast path: everything looks good
    if _check_imports(required_imports):
        if not quiet:
            log.info("Runtime guard: all checks passed")
        return diag

    # pydantic v1 detected or pydantic missing — attempt repair
    if auto_install:
        if not quiet:
            log.warning("Runtime guard: pydantic v2 not available, attempting auto-install")
        _auto_install_deps(quiet=quiet)

        if purge_on_conflict:
            purge_stale_modules()

        # Re-check after install + purge
        diag = diagnose_environment()
        if _check_imports(required_imports):
            if not quiet:
                log.info("Runtime guard: environment repaired successfully")
            return diag
    elif purge_on_conflict and diag.get("stale_pydantic_modules"):
        # Try purging without installing (maybe pydantic v2 is installed but
        # v1 modules are cached from an earlier import)
        purge_stale_modules()
        diag = diagnose_environment()
        if _check_imports(required_imports):
            if not quiet:
                log.info("Runtime guard: resolved after purging stale modules")
            return diag

    # Still broken — raise with diagnostics
    remediation = _REMEDIATION_DATABRICKS if diag["is_databricks"] else _REMEDIATION_LOCAL
    raise RuntimeGuardError(
        f"siege_utilities requires pydantic>=2.0 but found: {diag['pydantic_version']}. "
        f"Module path: {diag.get('pydantic_module_path', 'unknown')}",
        diagnostics=diag,
        remediation=remediation,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_imports(required: List[Tuple[str, str]]) -> bool:
    """Return True if all (module, attr) pairs are importable."""
    for mod_name, attr_name in required:
        try:
            mod = importlib.import_module(mod_name)
            if not hasattr(mod, attr_name):
                return False
        except ImportError:
            return False
    return True


def _auto_install_deps(*, quiet: bool = False) -> None:
    """Attempt pip install of core dependencies."""
    packages = [
        "pydantic>=2,<3",
        "typing_extensions>=4.6",
    ]
    cmd = [sys.executable, "-m", "pip", "install", "--quiet", "--no-warn-script-location"]
    cmd.extend(packages)

    if not quiet:
        log.info("Running: %s", " ".join(cmd))

    try:
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL if quiet else None,
                              stderr=subprocess.STDOUT if quiet else None)
    except subprocess.CalledProcessError as exc:
        log.error("pip install failed (exit code %d)", exc.returncode)
    except FileNotFoundError:
        log.error("pip not found at %s", sys.executable)

"""Release-hygiene contract for the package metadata dunders.

The per-symbol coverage scanner flagged __version__, __author__ and
__description__ as untested root symbols. Comparing the runtime __version__
against importlib.metadata would be tautological -- __version__ is itself
``importlib.metadata.version("siege-utilities")`` -- and comparing it against
pyproject is environment-sensitive (it fails whenever an editable install's
recorded metadata lags pyproject, which is a dev-env artifact, not a library
defect).

The robust, release-critical invariant is static: the two human-edited sources
of the version -- ``pyproject.toml`` ``[project].version`` and the literal
fallback assigned in ``siege_utilities/__init__.py`` (used when install
metadata is absent, e.g. editable/serverless imports) -- must agree. If they
drift, such an import silently reports a stale version. Both are read from
source, so this is independent of installed metadata and stable across
environments (#1346). __author__/__description__ may legitimately differ in
wording from the packaging metadata, so they are only checked for presence.
Ref #1199.
"""

import re
import tomllib
from pathlib import Path

from siege_utilities import __author__
from siege_utilities import __description__
from siege_utilities import __version__

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _pyproject_version() -> str:
    data = tomllib.loads(
        (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    return data["project"]["version"]


def _fallback_literal_version() -> str:
    src = (_REPO_ROOT / "siege_utilities" / "__init__.py").read_text(
        encoding="utf-8"
    )
    match = re.search(r'__version__\s*=\s*"([^"]+)"', src)
    assert match, "no literal __version__ fallback found in __init__.py"
    return match.group(1)


class TestPackageMetadataContract:
    def test_fallback_version_matches_pyproject(self):
        # Two independently hand-edited sources of truth for the version must
        # agree, or an import without install metadata reports a stale version.
        assert _fallback_literal_version() == _pyproject_version()

    def test_version_is_dotted_numeric(self):
        parts = __version__.split(".")
        assert len(parts) >= 2
        assert all(p.isdigit() for p in parts[:2])

    def test_author_is_nonempty_string(self):
        assert isinstance(__author__, str)
        assert __author__.strip()

    def test_description_is_nonempty_string(self):
        assert isinstance(__description__, str)
        assert __description__.strip()

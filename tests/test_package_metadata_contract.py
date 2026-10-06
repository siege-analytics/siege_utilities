"""Release-hygiene contract for the package metadata dunders.

The per-symbol coverage scanner flagged __version__, __author__ and
__description__ as untested root symbols. The release-critical invariant is
that the exported __version__ matches the installed package metadata -- a drift
between the two ships a package whose self-reported version lies about what pip
installed. __author__/__description__ may legitimately differ in wording from
the packaging metadata (module dunder vs project table), so they are only
checked for presence, not cross-source equality. Ref #1199.
"""

from importlib.metadata import version

from siege_utilities import __author__
from siege_utilities import __description__
from siege_utilities import __version__


class TestPackageMetadataContract:
    def test_version_matches_installed_metadata(self):
        # Drift here means the import-time version disagrees with what was
        # actually packaged/installed -- a real release defect.
        assert __version__ == version("siege-utilities")

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

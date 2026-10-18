"""#1702: prefixed private-key file names and id_ed25519 must be sensitive."""
import pytest

from siege_utilities.files.validation import is_sensitive_path


@pytest.mark.parametrize(
    "path, expected",
    [
        ("/srv/keys/id_rsa", True),
        ("/srv/keys/id_dsa", True),
        ("/srv/keys/id_ecdsa", True),
        ("/srv/keys/id_ed25519", True),
        ("/srv/keys/deploy_id_rsa", True),
        ("/srv/keys/github-id_ecdsa", True),
        ("/srv/keys/github-id_ed25519", True),
        ("/srv/keys/ci_id_dsa", True),
        ("/srv/keys/id_rsa.pub", False),
        ("/srv/keys/deploy_id_ed25519.pub", False),
        ("/srv/data/paid_rsa", False),
        ("/srv/data/squid_rsa", False),
        ("/srv/data/valid_ed25519", False),
    ],
)
def test_private_key_names_outside_ssh(path, expected):
    assert is_sensitive_path(path) is expected

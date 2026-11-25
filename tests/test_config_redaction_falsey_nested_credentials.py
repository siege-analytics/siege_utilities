"""Falsey nested-credential plaintext-leak regression for #1460 / PR #1832.

Adopted verbatim (test body) from the fresh-surge hostile review's
test_falsey_regression.py; the REVIEW_ROOT/sys.path bootstrap is replaced with
ordinary repo imports. A falsey sensitive container (a zero-length model that
still holds a SecretStr) must never expose its secret as plaintext through
to_dict / to_yaml / export_entities(exclude_sensitive=True). 12 of these cases
were red at ee882655; all 18 are green after the B1832-1 fix.
"""
import os

os.environ.setdefault('SIEGE_AUTO_INIT_DIRS', 'false')

import pytest
from pydantic import BaseModel, Field, SecretStr

from siege_utilities.config.models.actor_types import User
from siege_utilities.config.models.oauth_integration import OAuthIntegration
from siege_utilities.config.models.export import export_entities

SENTINEL = 'DUMMY-FALSEY-CREDENTIAL'


class CredentialBundle(BaseModel):
    entries: list[str] = Field(default_factory=list)
    client_secret: SecretStr = Field(json_schema_extra={'sensitive': True})

    def __len__(self):
        return len(self.entries)


class AliasEnvelope(BaseModel):
    bundle: CredentialBundle = Field(serialization_alias='client_secret')


@pytest.mark.parametrize(
    'case',
    ['bytes-key', 'undecodable-key', 'tuple-key', 'alias-field', 'list-control', 'public-control'],
)
@pytest.mark.parametrize('surface', ['to_dict', 'to_yaml', 'export_entities'])
def test_falsey_nested_credential_never_becomes_plaintext(case, surface):
    bundle = CredentialBundle(client_secret=SENTINEL)
    assert not bundle
    value = {
        'bytes-key': {b'access_token': bundle},
        'undecodable-key': {b'\xff': bundle},
        'tuple-key': {('record', 1): bundle},
        'alias-field': AliasEnvelope(bundle=bundle),
        'list-control': {b'access_token': [bundle]},
        'public-control': {'record': bundle},
    }[case]
    user = User(
        person_id='hostile', name='Hostile Probe', email='hostile@example.com',
        username='hostile',
        oauth_integrations=[OAuthIntegration(
            name='probe', provider='google', service='analytics',
            client_id='public-client-id', client_secret='DUMMY-ROOT-CREDENTIAL',
            redirect_uri='https://example.com/cb', metadata={'record': value},
        )],
    )
    result = (
        export_entities(users=[user], exclude_sensitive=True)
        if surface == 'export_entities'
        else getattr(user, surface)(exclude_sensitive=True)
    )
    assert SENTINEL not in str(result)

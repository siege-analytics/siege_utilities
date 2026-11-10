"""Synthetic falsey value siblings of the original B1832-1 model case."""
from typing import Any
from pydantic import BaseModel, Field, SecretStr
import pytest
from siege_utilities.config.models.actor_types import User
from siege_utilities.config.models.oauth_integration import OAuthIntegration
from siege_utilities.config.models.export import export_entities

SECRET='DUMMY-REMAINING-FALSEY-CREDENTIAL'
class FalseySecret(SecretStr):
    def __bool__(self): return False
class FalseyObject:
    def __init__(self): self.client_secret=SecretStr(SECRET)
    def __bool__(self): return False
class Envelope(BaseModel):
    payload: Any=Field(serialization_alias='client_secret')

@pytest.mark.parametrize('kind',['secretstr','object'])
@pytest.mark.parametrize('placement',['bytes','alias','public-control'])
@pytest.mark.parametrize('surface',['to_dict','to_yaml','export_entities'])
def test_falsey_sensitive_value_never_unwraps(kind,placement,surface):
    secret=FalseySecret(SECRET) if kind=='secretstr' else FalseyObject()
    assert not secret
    value={b'access_token':secret} if placement=='bytes' else Envelope(payload=secret) if placement=='alias' else {'record':secret}
    user=User(person_id='probe',name='Probe',email='probe@example.com',username='probe',oauth_integrations=[OAuthIntegration(name='probe',provider='google',service='analytics',client_id='public-client-id',client_secret='DUMMY-ROOT-SECRET',redirect_uri='https://example.com/cb',metadata={'record':value})])
    result=export_entities(users=[user],exclude_sensitive=True) if surface=='export_entities' else getattr(user,surface)(exclude_sensitive=True)
    assert SECRET not in str(result)

"""Exact-type/ruling probes. Synthetic metadata only; no credential files."""
import math
from decimal import Decimal
from typing import Any
import pytest,yaml
from pydantic import BaseModel,Field,SecretStr,SecretBytes
from siege_utilities.config.models import person as M
from siege_utilities.config.models.actor_types import User,Client,Collaborator,Organization,Collaboration
from siege_utilities.config.models.oauth_integration import OAuthIntegration
from siege_utilities.config.models.export import export_entities,import_entities

SECRET='DUMMY-METACLASS-ONLY-NOT-REAL-CREDENTIAL'
MARKER='***REDACTED***'
class Envelope(BaseModel):payload:Any=Field(serialization_alias='client_secret')

def make_user(value,placement):
    record={b'access_token':value} if placement=='bytes' else Envelope(payload=value)
    return User(person_id='probe',name='Probe',email='probe@example.com',username='probe',oauth_integrations=[OAuthIntegration(name='probe',provider='google',service='analytics',client_id='public-client-id',client_secret='DUMMY-ROOT-SECRET',redirect_uri='https://example.com/cb',metadata={'record':record})])

def output(user,surface):
    if surface=='to_dict':return user.to_dict(exclude_sensitive=True)
    if surface=='to_yaml':return yaml.safe_load(user.to_yaml(exclude_sensitive=True))
    return yaml.safe_load(export_entities(users=[user],exclude_sensitive=True))['entities']['users'][0]

def leaf(result,placement):
    record=result['oauth_integrations'][0]['metadata']['record']
    return record[b'access_token'] if placement=='bytes' else record['payload']

@pytest.mark.parametrize('target',[str,int],ids=['str-class','int-class'])
@pytest.mark.parametrize('truthy',[False,True],ids=['falsey','truthy'])
@pytest.mark.parametrize('placement',['bytes','alias'])
@pytest.mark.parametrize('surface',['to_dict','to_yaml','export_entities'])
def test_metaclass_equality_must_not_authorize_sensitive_object(target,truthy,placement,surface):
    class Masquerade(type):
        def __hash__(cls):return hash(target)
        def __eq__(cls,other):return other is target
    class Credential(metaclass=Masquerade):
        def __init__(self):self.client_secret=SecretStr(SECRET)
        def __eq__(self,other):return True
        def __bool__(self):return truthy
    value=Credential();result=output(make_user(value,placement),surface)
    assert SECRET not in str(result)
    v=leaf(result,placement);assert type(v) is str and v==MARKER

@pytest.mark.parametrize('placement',['bytes','alias'])
@pytest.mark.parametrize('surface',['to_dict','to_yaml','export_entities'])
def test_metaclass_secret_subclass_must_never_reach_unwrap(placement,surface):
    calls=[]
    class Masquerade(type):
        def __hash__(cls):return hash(str)
        def __eq__(cls,other):return other is str
    class Hostile(SecretStr,metaclass=Masquerade):
        def __eq__(self,other):return True
        def get_secret_value(self):calls.append(True);return ''
    value=Hostile(SECRET);value.actual_secret=SECRET
    result=output(make_user(value,placement),surface)
    assert calls==[]
    v=leaf(result,placement);assert type(v) is str and v==MARKER

@pytest.mark.parametrize('secret_type',[SecretStr,SecretBytes],ids=['SecretStr','SecretBytes'])
@pytest.mark.parametrize('placement',['bytes','alias'])
@pytest.mark.parametrize('surface',['to_dict','to_yaml','export_entities'])
def test_hostile_secret_subclass_is_never_unwrapped(secret_type,placement,surface):
    calls=[]
    class Hostile(secret_type):
        def get_secret_value(self):calls.append(True);return '' if secret_type is SecretStr else b''
    value=Hostile(SECRET if secret_type is SecretStr else SECRET.encode());value.actual_secret=SECRET
    result=output(make_user(value,placement),surface)
    v=leaf(result,placement);assert type(v) is str and v==MARKER
    assert SECRET not in str(result)
    assert calls==[]

@pytest.mark.parametrize('value',['',b'',[],{},(),set(),frozenset(),0,0.0,-0.0,False])
def test_exact_empty_preserves_type_and_negative_zero(value):
    result=M._redact_sensitive_value(value)
    assert type(result) is type(value) and result==value
    if type(value) is float:assert math.copysign(1.0,result)==math.copysign(1.0,value)

@pytest.mark.parametrize('value',[True,1,1.0,float('nan'),float('inf'),float('-inf'),Decimal(0)])
def test_nonempty_or_nonallowlisted_numbers_are_redacted(value):
    result=M._redact_sensitive_value(value)
    assert type(result) is str and result==MARKER

def test_ordinary_equality_liar_is_not_consulted():
    calls=[]
    class Liar:
        def __eq__(self,other):calls.append(other);return True
        def __bool__(self):return False
    result=M._redact_sensitive_value(Liar())
    assert type(result) is str and result==MARKER
    assert calls==[]

@pytest.mark.parametrize('typ',[list,dict,set])
def test_empty_mutables_never_return_the_shared_sentinel(typ):
    value=typ();sentinel=M._EMPTY_SENTINELS[typ]
    result=M._redact_sensitive_value(value)
    assert result is value and result is not sentinel
    if typ is list:result.append('DUMMY')
    elif typ is dict:result['DUMMY']='DUMMY'
    else:result.add('DUMMY')
    assert M._EMPTY_SENTINELS[typ]==typ()
    fresh=typ();assert M._redact_sensitive_value(fresh) is fresh

ACTORS=[
 ('users',User,dict(person_id='user',name='User',email='user@example.com',username='user')),
 ('clients',Client,dict(person_id='client',name='Client',email='client@example.com',client_code='DEMO',industry='consulting',project_count=0,client_status='active')),
 ('collaborators',Collaborator,dict(person_id='collaborator',name='Collaborator',email='collaborator@example.com',external_organization='External')),
 ('organizations',Organization,dict(org_id='org',name='Organization',org_type='internal',primary_email='org@example.com')),
 ('collaborations',Collaboration,dict(collab_id='collab',name='Collaboration')),
]
MODES=[{},dict(exclude_sensitive=False),dict(exclude_sensitive=True)]
@pytest.mark.parametrize('entry',ACTORS,ids=[x[0] for x in ACTORS])
@pytest.mark.parametrize('mode',MODES,ids=['default','unredacted','redacted'])
def test_default_actor_round_trip(entry,mode):
    group,cls,kw=entry;obj=cls(**kw)
    text=export_entities(**{group:[obj]},**mode)
    assert MARKER not in text
    restored=import_entities(text)[group]
    assert len(restored)==1 and type(restored[0]) is cls
    assert restored[0].model_dump()==obj.model_dump()

@pytest.mark.parametrize('mode',MODES,ids=['default','unredacted','redacted'])
def test_combined_all_actor_round_trip(mode):
    objects={group:[cls(**kw)] for group,cls,kw in ACTORS}
    restored=import_entities(export_entities(**objects,**mode))
    for group,items in objects.items():
        assert len(restored[group])==1
        assert restored[group][0].model_dump()==items[0].model_dump()

@pytest.mark.parametrize('placement',['bytes','alias'])
@pytest.mark.parametrize('surface',['to_dict','to_yaml','export_entities'])
def test_exact_wrapper_bytes_public_must_redact_nonempty_lying_payload(placement,surface):
    class LyingBytes(bytes):
        def __eq__(self,other):return True
    raw=LyingBytes(SECRET.encode());raw.hidden_secret=SecretStr(SECRET)
    value=SecretBytes(raw)
    assert type(value) is SecretBytes and len(value.get_secret_value())>0
    result=output(make_user(value,placement),surface)
    assert SECRET not in str(result)
    v=leaf(result,placement);assert type(v) is str and v==MARKER

@pytest.mark.parametrize('wrapper',[SecretStr,SecretBytes],ids=['SecretStr','SecretBytes'])
def test_exact_wrapper_cannot_use_payload_equality_as_emptiness(wrapper):
    class LyingStr(str):
        def __eq__(self,other):return True
    class LyingBytes(bytes):
        def __eq__(self,other):return True
    raw=LyingStr(SECRET) if wrapper is SecretStr else LyingBytes(SECRET.encode())
    value=wrapper(raw)
    assert type(value) is wrapper and len(value.get_secret_value())>0
    result=M._redact_sensitive_value(value)
    assert type(result) is str and result==MARKER

def test_real_redacted_placeholder_is_still_rejected():
    u=User(person_id='r',name='Reject',email='r@example.com',username='reject',google_analytics_key=SecretStr(SECRET))
    text=export_entities(users=[u],exclude_sensitive=True)
    with pytest.raises(ValueError,match='Cannot import redacted'):import_entities(text)

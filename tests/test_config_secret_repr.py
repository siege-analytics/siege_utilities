"""Secret representation, validation and consumer regressions for #1552."""

from dataclasses import asdict
from pathlib import Path
import subprocess
import sys
from urllib.parse import quote_plus
from unittest.mock import patch

import pytest
import yaml
from pydantic import SecretStr, ValidationError

from siege_utilities.config.models.actor_types import User
from siege_utilities.config.models.client_profile import ClientProfile
from siege_utilities.config.models.credential import Credential
from siege_utilities.config.models.database_connection import DatabaseConnection
from siege_utilities.config.models.oauth_integration import OAuthIntegration
from siege_utilities.config.models.person import Person
from siege_utilities.config.models.social_media_account import SocialMediaAccount
from siege_utilities.config.models.user_profile import UserProfile
from siege_utilities.config.user_config import UserConfigManager, UserProfile as LegacyUserProfile

pytestmark = pytest.mark.unit

# Construct synthetic fixtures at runtime; these are never live credentials.
PASSWORD = "".join(("S3cr3t", "Passw0rd!"))
KEY = "sentinel-api-key-1552"
DB = dict(name="prod", connection_type="postgresql", host="db.example.com",
          port=5432, database="warehouse", username="etl", password=PASSWORD)
CREDENTIAL = dict(name="warehouse", credential_type="username_password", service="database")
OAUTH = dict(name="google", provider="google", service="analytics",
             client_id="public-client-id", client_secret="sentinel-client-secret",
             redirect_uri="https://example.com/callback")
SOCIAL = dict(platform="twitter", account_id="etl", account_name="ETL",
              access_token="sentinel-social-access-token")
PERSON = dict(person_id="etl", name="ETL User", email="etl@example.com")
DSN = f"postgresql://etl:{PASSWORD}@host/db"
KEY_FIELDS = ("census_api_key", "google_analytics_key", "facebook_business_key")
SECRET_CASES = [
    (DatabaseConnection, DB, "password", PASSWORD, 100),
    *((Credential, CREDENTIAL, name, KEY, limit) for name, limit in
      (("password", 500), ("api_key", 500), ("token", 1000), ("secret", 500))),
    *((OAuthIntegration, OAUTH, name, KEY, limit) for name, limit in
      (("client_secret", 200), ("access_token", 2000), ("refresh_token", 2000))),
    *((SocialMediaAccount, SOCIAL, name, "sentinel-social-token-1552", 500)
      for name in ("access_token", "refresh_token")),
    *((UserProfile, {}, name, KEY, 100) for name in KEY_FIELDS),
    *((User, dict(PERSON, username="etl"), name, KEY, 100) for name in KEY_FIELDS),
]


@pytest.mark.parametrize("render", [repr, str])
@pytest.mark.parametrize("model,kwargs,field,value,limit", SECRET_CASES)
def test_secret_representations(model, kwargs, field, value, limit, render):
    instance = model(**dict(kwargs, **{field: value}))
    assert value not in render(instance)
    assert getattr(instance, field).get_secret_value() == value


@pytest.mark.parametrize("model,kwargs,field,value,limit", SECRET_CASES)
def test_overlong_secrets_do_not_leak(model, kwargs, field, value, limit):
    rejected = "Sentinel1-" + "x" * limit
    with pytest.raises(ValidationError) as caught:
        model(**dict(kwargs, **{field: rejected}))
    assert "Sentinel1-" not in str(caught.value)
    assert "Sentinel1-" not in repr(caught.value)


@pytest.mark.parametrize("model,kwargs,field,rejected", [
    (DatabaseConnection, DB, "password", "short!1"),
    (DatabaseConnection, DB, "password", "lowercase1"),
    (DatabaseConnection, DB, "password", "UPPERCASE1"),
    (DatabaseConnection, DB, "password", "NoDigitsHere"),
    (Credential, CREDENTIAL, "password", "short!1"),
    (Credential, CREDENTIAL, "api_key", "short-key"),
    (OAuthIntegration, OAUTH, "client_secret", "short-key"),
    (SocialMediaAccount, SOCIAL, "access_token", "short-token"),
    (SocialMediaAccount, SOCIAL, "access_token", "invalid-token-characters!!!"),
    *((UserProfile, {}, field, "invalid-key!") for field in KEY_FIELDS),
])
def test_invalid_secrets_do_not_leak(model, kwargs, field, rejected):
    with pytest.raises(ValidationError) as caught:
        model(**dict(kwargs, **{field: rejected}))
    assert rejected not in str(caught.value)
    assert rejected not in repr(caught.value)


@pytest.mark.parametrize("render", [repr, str])
def test_parent_aggregator_repr(render):
    person = Person(**PERSON, credentials=[Credential(**CREDENTIAL, password=PASSWORD)],
                    oauth_integrations=[OAuthIntegration(**OAUTH)],
                    database_connections=[DatabaseConnection(**DB)])
    assert PASSWORD not in render(person)
    assert OAUTH["client_secret"] not in render(person)


@pytest.mark.parametrize("field,child", [
    ("database_connections", dict(DB, password="Short7!")),
    ("credentials", dict(CREDENTIAL, password="Short7!")),
    ("oauth_integrations", dict(OAUTH, client_secret="Short7!")),
])
def test_aggregator_person_yaml_validation_hides_nested_secrets(field, child):
    document = yaml.safe_dump(dict(PERSON, **{field: [child]}))
    with pytest.raises(ValidationError) as caught:
        Person.from_yaml(document)
    assert field in str(caught.value)
    assert "Short7!" not in str(caught.value)
    assert "Short7!" not in repr(caught.value)


@pytest.mark.parametrize("missing_field", [False, True])
def test_aggregator_client_profile_validation_hides_nested_secrets(missing_field):
    payload = dict(
        client_id="etl", client_name="ETL", client_code="ET", contact_info={},
        industry="Tech", project_count=0, status="active", report_preferences={},
        branding_config=dict(primary_color="#000000", secondary_color="#111111",
                             accent_color="#222222", text_color="#333333",
                             background_color="#FFFFFF", primary_font="Arial",
                             secondary_font="Arial"),
        database_connections=[dict(DB, password="Short7!")],
    )
    if missing_field:
        del payload["client_name"]
        payload["database_connections"][0]["password"] = PASSWORD
    sentinel = PASSWORD if missing_field else "Short7!"
    with pytest.raises(ValidationError) as caught:
        ClientProfile(**payload)
    assert ("client_name" if missing_field else "database_connections.0.password") in str(caught.value)
    assert sentinel not in str(caught.value)
    assert sentinel not in repr(caught.value)


@pytest.mark.parametrize("model,kwargs", [
    (UserProfile, {}), (User, dict(PERSON, username="etl")), (LegacyUserProfile, {}),
])
def test_postgresql_connection_repr_and_consumer(model, kwargs, tmp_path):
    profile = model(**kwargs, postgresql_connection=DSN)
    assert PASSWORD not in repr(profile)
    assert PASSWORD not in str(profile)
    if model is LegacyUserProfile:
        assert asdict(profile)["postgresql_connection"] == DSN
    else:
        assert profile.postgresql_connection.get_secret_value() == DSN
        assert PASSWORD not in profile.model_dump_json()
    manager = UserConfigManager(config_dir=tmp_path)
    manager.user_profile = profile
    assert manager.get_database_connection() == DSN
    assert manager.get_database_connection("postgresql") == DSN


@pytest.mark.parametrize("model,kwargs", [(UserProfile, {}), (User, dict(PERSON, username="etl"))])
def test_postgresql_connection_default_and_length(model, kwargs):
    assert model(**kwargs).postgresql_connection.get_secret_value() == ""
    with pytest.raises(ValidationError) as caught:
        model(**kwargs, postgresql_connection=DSN + "x" * 500)
    assert PASSWORD not in str(caught.value)
    assert PASSWORD not in repr(caught.value)


@pytest.mark.parametrize("model,kwargs", [(UserProfile, {}), (User, dict(PERSON, username="etl"))])
def test_postgresql_connection_yaml_roundtrip(model, kwargs, tmp_path):
    from siege_utilities.config.enhanced_config import load_user_profile, save_user_profile

    profile = model(**kwargs, postgresql_connection=DSN)
    if model is User:
        restored = User.from_yaml(profile.to_yaml())
    else:
        save_user_profile(profile, "etl", config_dir=tmp_path)
        restored = load_user_profile("etl", config_dir=tmp_path)
    assert restored.postgresql_connection.get_secret_value() == DSN


@pytest.mark.parametrize("field", KEY_FIELDS)
def test_dataclass_repr(field):
    profile = LegacyUserProfile(**{field: KEY})
    assert KEY not in repr(profile)
    assert KEY not in str(profile)
    assert getattr(profile, field) == KEY
    assert asdict(profile)[field] == KEY


@pytest.mark.parametrize("connection_type", ["postgresql", "mysql", "sqlite", "duckdb"])
def test_database_connection_consumer(connection_type):
    password = PASSWORD + "@:/?#% +"
    connection = DatabaseConnection(**dict(DB, connection_type=connection_type, password=password))
    assert connection.password.get_secret_value() == password
    expected = {
        "postgresql": f"postgresql://etl:{quote_plus(password)}@db.example.com:5432/warehouse?sslmode=require",
        "mysql": f"mysql://etl:{quote_plus(password)}@db.example.com:5432/warehouse?ssl=true",
        "sqlite": "sqlite:///warehouse",
        "duckdb": "duckdb:///warehouse",
    }
    assert connection.get_connection_string() == expected[connection_type]


@pytest.mark.parametrize("platform", ["facebook", "twitter", "linkedin", "instagram", "youtube", "tiktok"])
def test_social_auth_consumer(platform):
    account = SocialMediaAccount(**dict(SOCIAL, platform=platform, account_id="12345"))
    assert account.get_auth_headers() == {"Authorization": f"Bearer {SOCIAL['access_token']}"}


def test_google_workspace_consumer():
    from siege_utilities.analytics.google_workspace import GoogleWorkspaceClient
    from siege_utilities.config.models.google_account import GoogleAccount

    person = Person(**PERSON, oauth_integrations=[OAuthIntegration(**OAUTH)])
    account = GoogleAccount(google_account_id="google", display_name="ETL", email="etl@example.com",
                            oauth_integration_name="google")
    with patch.object(GoogleWorkspaceClient, "from_oauth") as factory:
        GoogleWorkspaceClient.from_account(account, person=person)
    assert factory.call_args.kwargs["client_secret"] == OAUTH["client_secret"]


def test_explicit_person_yaml_export_preserves_secrets():
    person = Person(**PERSON, credentials=[Credential(**CREDENTIAL, password=PASSWORD)],
                    oauth_integrations=[OAuthIntegration(**OAUTH)],
                    database_connections=[DatabaseConnection(**DB)])
    exported = person.to_yaml()
    restored = Person.from_yaml(exported)
    assert restored.credentials[0].password.get_secret_value() == PASSWORD
    assert restored.oauth_integrations[0].client_secret.get_secret_value() == OAUTH["client_secret"]
    assert restored.database_connections[0].get_connection_string() == person.database_connections[0].get_connection_string()
    assert PASSWORD not in person.model_dump_json()


def test_profile_yaml_consumer(tmp_path):
    from siege_utilities.config.enhanced_config import load_user_profile, save_user_profile

    profile = UserProfile(username="etl", **dict.fromkeys(KEY_FIELDS, KEY))
    save_user_profile(profile, "etl", config_dir=tmp_path)
    restored = load_user_profile("etl", config_dir=tmp_path)
    for field in KEY_FIELDS:
        assert getattr(restored, field).get_secret_value() == KEY


@pytest.mark.parametrize("model,kwargs", [(UserProfile, {}), (User, dict(PERSON, username="etl"))])
def test_empty_default_secrets_are_wrapped(model, kwargs):
    instance = model(**kwargs)
    for field in KEY_FIELDS:
        assert isinstance(getattr(instance, field), SecretStr)
        assert getattr(instance, field).get_secret_value() == ""


def test_assignment_and_token_refresh_keep_secrets_wrapped():
    integration = OAuthIntegration(**OAUTH)
    integration.update_tokens("refreshed-access-token", "refreshed-refresh-token")
    assert integration.access_token.get_secret_value() == "refreshed-access-token"
    assert integration.refresh_token.get_secret_value() == "refreshed-refresh-token"
    assert "refreshed-access-token" not in repr(integration)
    connection = DatabaseConnection(**DB)
    with pytest.raises(ValidationError) as caught:
        connection.password = "short!1"
    assert "short!1" not in str(caught.value)
    assert connection.password.get_secret_value() == PASSWORD


@pytest.mark.parametrize("declaration", [
    "class Leaky(BaseModel):\n    password: str",
    "class Leaky(BaseModel):\n    API_KEY: Optional[str]",
    "class Leaky(BaseModel):\n    refresh_token: str | None",
    "class Leaky(BaseModel):\n    client_secret: 'Optional[str]'",
    "class Leaky(BaseModel):\n    secret: Annotated[str, Field()]",
    "@dataclass\nclass Leaky:\n    private_key: str",
    "class Leaky(NamedTuple):\n    token: str",
    "class Parent(BaseModel):\n    pass\nclass Leaky(Parent):\n    password: str",
])
def test_class_guard_rejects_plain_secrets(tmp_path, declaration):
    from scripts.check_secret_repr import main

    source = ("from pydantic import BaseModel, Field\n"
              "from dataclasses import dataclass\n"
              "from typing import Optional, NamedTuple, Annotated\n" + declaration)
    (tmp_path / "planted.py").write_text(source)
    assert main([str(tmp_path)]) == 1


@pytest.mark.parametrize("declaration", [
    'postgresql_connection: str = Field(json_schema_extra={"sensitive": True}, default="")',
    'postgresql_connection: Optional[str] = Field(sensitive=True, default=None)',
    'dsn: str = Field(default="")',
])
def test_class_guard_rejects_connection_fields(tmp_path, declaration):
    (tmp_path / "planted.py").write_text(
        "from pydantic import BaseModel, Field\nfrom typing import Optional\n"
        "class Leaky(BaseModel):\n    " + declaration + "\n"
    )
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parents[1] / "scripts/check_secret_repr.py"),
         str(tmp_path)], capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert f"planted.py:4:Leaky.{declaration.split(':')[0]}" in result.stdout
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("default", ['""', '"Field(repr=False)"'])
def test_class_guard_string_defaults_are_values(tmp_path, default):
    (tmp_path / "planted.py").write_text(
        "from pydantic import BaseModel, Field\nclass Leaky(BaseModel):\n"
        f"    password: str = {default}\n"
    )
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parents[1] / "scripts/check_secret_repr.py"),
         str(tmp_path)], capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert "planted.py:3:Leaky.password" in result.stdout
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("declaration", [
    'token: SecretStr = SecretStr("")',
    '''password: 'Annotated[str, Field(repr=False)]' = ""''',
    'postgresql_connection: str = Field(default="", repr=False, json_schema_extra={"sensitive": True})',
])
def test_class_guard_safe_string_defaults(tmp_path, declaration):
    from scripts.check_secret_repr import main

    (tmp_path / "safe.py").write_text(
        "from pydantic import BaseModel, Field, SecretStr\nfrom typing import Annotated\n"
        "class Safe(BaseModel):\n    " + declaration + "\n"
    )
    assert main([str(tmp_path)]) == 0


@pytest.mark.parametrize("parent_import", [
    "from .base import Parent as P", "from . import PublicParent as P",
])
def test_class_guard_aliases_and_cross_module_inheritance(tmp_path, capsys, parent_import):
    from scripts.check_secret_repr import main

    (tmp_path / "base.py").write_text("import pydantic as p\nclass Parent(p.BaseModel):\n    pass\n")
    (tmp_path / "__init__.py").write_text("from .base import Parent as PublicParent\n")
    child = tmp_path / "child.py"
    child.write_text(parent_import + "\nfrom typing import Optional as O\n"
                     "class Child(P):\n    password: O[str]\n")
    assert main([str(tmp_path)]) == 1
    assert "child.py:4:Child.password" in capsys.readouterr().out
    child.write_text(parent_import + "\nfrom pydantic import SecretStr\n"
                     "class Child(P):\n    password: SecretStr\n")
    assert main([str(tmp_path)]) == 0


def test_class_guard_accepts_safe_fields(tmp_path):
    from scripts.check_secret_repr import main

    (tmp_path / "safe.py").write_text('''
from pydantic import BaseModel, Field, SecretStr
from dataclasses import dataclass, field
from typing import Annotated, Optional, ClassVar
class Safe(BaseModel):
    password: SecretStr
    api_key: Optional[SecretStr]
    token_type: str = Field(repr=False)
    secret: Annotated[str, Field(repr=False)]
    connection_type: str = "postgresql"
    token_count: int
    password_label: ClassVar[str] = "Password"
@dataclass
class Legacy:
    private_key: str = field(repr=False)
class Ordinary:
    secret: str
''')
    assert main([str(tmp_path)]) == 0


def test_class_guard_fails_on_unparseable_source(tmp_path):
    from scripts.check_secret_repr import main

    (tmp_path / "broken.py").write_text("class Broken(:")
    with pytest.raises(SyntaxError):
        main([str(tmp_path)])


def test_class_guard_checks_library():
    from scripts.check_secret_repr import main

    assert main([]) == 0


def test_person_password_strength_consumer():
    person = Person(**PERSON, credentials=[Credential(**CREDENTIAL, password=PASSWORD[:8])])
    assert "Strengthen 1 weak passwords" in person.get_security_recommendations()
    person.credentials[0].password = PASSWORD
    assert not any("Strengthen" in item for item in person.get_security_recommendations())


@pytest.mark.parametrize("model,kwargs,field,rejected", [
    (DatabaseConnection, DB, "password", b"lowercase1"),
    (SocialMediaAccount, SOCIAL, "access_token", b"invalid-token-characters!!!"),
])
def test_byte_input_preserves_secret_format_constraints(model, kwargs, field, rejected):
    with pytest.raises(ValidationError) as caught:
        model(**dict(kwargs, **{field: rejected}))
    assert rejected.decode() not in str(caught.value)

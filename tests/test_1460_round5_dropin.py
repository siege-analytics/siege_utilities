"""#1460 round-5 drop-in regressions: digit/plural/compound names and query-string secrets."""

import json

from pydantic import create_model
import pytest
import yaml

from siege_utilities.config.models.actor_types import User
from siege_utilities.config.models.export import export_entities, import_entities

ROUND5_SECRET_NAMES = (
    "apiKey2", "password2", "db_password1", "apikeys", "secrets", "passwords",
    "clientsecret", "accesstoken", "refreshtoken", "secretkey",
    "accesskey", "sessionid",
)
# Must stay public (suffix/compound matching must not over-reach).
ROUND5_PUBLIC_NAMES = ("author", "keyboard", "monkey", "turkey", "hockey", "secretary", "tokenizer")


def _export(person, surface):
    if surface == "to_dict":
        data = person.to_dict(exclude_sensitive=True)
        return data, json.dumps(data)
    if surface == "to_yaml":
        text = person.to_yaml(exclude_sensitive=True)
        return yaml.safe_load(text), text
    text = export_entities(users=[person], exclude_sensitive=True)
    return yaml.safe_load(text)["entities"]["users"][0], text


def _user(**fields):
    model = create_model("Round5User", __base__=User, **{k: (str, ...) for k in fields})
    return model(person_id="r5", name="R5", email="r5@example.com", username="r5", **fields)


@pytest.mark.parametrize("surface", ["to_dict", "to_yaml", "export_entities"])
@pytest.mark.parametrize("name", ROUND5_SECRET_NAMES)
def test_round5_secret_names_redacted(surface, name):
    data, text = _export(_user(**{name: "sentinel-r5"}), surface)
    assert data[name] == "***REDACTED***"
    assert "sentinel-r5" not in text


@pytest.mark.parametrize("name", ROUND5_SECRET_NAMES)
def test_round5_secret_names_flagged_by_guard_classifier(name):
    from siege_utilities.config.models._sensitivity import SECRET_FIELD_NAME

    assert SECRET_FIELD_NAME.search(name) is not None


@pytest.mark.parametrize("name", ROUND5_PUBLIC_NAMES)
def test_round5_public_names_not_flagged(name):
    from siege_utilities.config.models._sensitivity import SECRET_FIELD_NAME

    assert SECRET_FIELD_NAME.search(name) is None


@pytest.mark.parametrize("surface", ["to_dict", "to_yaml", "export_entities"])
@pytest.mark.parametrize("url", [
    "https://api.example/x?access_token=sentinel-qs&page=1",
    "https://api.example/x?api_key=sentinel-qs",
    "https://bucket.example/o?X-Amz-Signature=sentinel-qs",
    "jdbc:postgresql://db.example/x?user=svc&password=sentinel-qs",
])
def test_url_query_string_secrets_redacted(surface, url):
    data, text = _export(_user(endpoint=url), surface)
    assert "sentinel-qs" not in text
    assert "***REDACTED***" in data["endpoint"]


def test_url_query_string_redaction_rejected_on_import(monkeypatch):
    from siege_utilities.config.models import export

    person = _user(endpoint="https://api.example/x?access_token=sentinel-qs")
    monkeypatch.setattr(export, "User", type(person))
    text = export_entities(users=[person], exclude_sensitive=True)
    with pytest.raises(ValueError, match="Cannot import redacted values"):
        import_entities(text)

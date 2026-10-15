"""#1460 round-6 drop-in: run-together names that the round-4 head redacted."""

import json

from pydantic import create_model
import pytest
import yaml

from siege_utilities.config.models._sensitivity import SECRET_FIELD_NAME
from siege_utilities.config.models.actor_types import User
from siege_utilities.config.models.export import export_entities

# Redacted by b9ca4e3c (substring floor); leak on 948037c0/7ed59307.
ROUND6_SECRET_NAMES = (
    "secretaccesskey", "awssecretaccesskey", "apikeyid", "xapikey",
    "googleapikey", "censusapikey", "privatekeypem", "privatekeyid",
    "secretkeyid", "clientsecretkey", "secretvalue", "tokenvalue", "passwordhash",
)
# Must stay public.
ROUND6_PUBLIC_NAMES = (
    "secretary", "secretariat", "tokenizer", "tokenized",
    "keyboard", "monkey", "turkey", "hockey", "author",
)


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
    model = create_model("Round6User", __base__=User, **{k: (str, ...) for k in fields})
    return model(person_id="r6", name="R6", email="r6@example.com", username="r6", **fields)


@pytest.mark.parametrize("surface", ["to_dict", "to_yaml", "export_entities"])
@pytest.mark.parametrize("name", ROUND6_SECRET_NAMES)
def test_round6_run_together_names_redacted(surface, name):
    data, text = _export(_user(**{name: "sentinel-r6"}), surface)
    assert data[name] == "***REDACTED***"
    assert "sentinel-r6" not in text


@pytest.mark.parametrize("name", ROUND6_SECRET_NAMES)
def test_round6_run_together_names_flagged_by_guard_classifier(name):
    assert SECRET_FIELD_NAME.search(name) is not None


@pytest.mark.parametrize("name", ROUND6_PUBLIC_NAMES)
def test_round6_public_names_not_flagged(name):
    assert SECRET_FIELD_NAME.search(name) is None

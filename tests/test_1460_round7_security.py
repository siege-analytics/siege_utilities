"""Red-first #1460 regressions: typed object traversal and encoded nested URLs."""

from dataclasses import dataclass
from urllib.parse import quote, unquote

import pytest
import yaml
from pydantic import ConfigDict, Field

from siege_utilities.config.models.actor_types import User
from siege_utilities.config.models.export import export_entities, import_entities


@dataclass
class Nested:
    apiKey2: str = "synthetic-inner"
    public_label: str = "safe-label"


class PlainNested:
    def __init__(self):
        self.password2 = "synthetic-plain"
        self.public_label = "safe-plain"
        self.value = "safe-value"


class UserWithObjects(User):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    nested: Nested = Field(default_factory=Nested)
    plain: PlainNested = Field(default_factory=PlainNested)


def _user(**kwargs):
    return UserWithObjects(
        person_id="r7", name="R7", email="r7@example.com", username="r7", **kwargs,
    )


@pytest.mark.parametrize("surface", ["to_dict", "to_yaml", "export_entities"])
def test_typed_and_plain_nested_objects_scrubbed_with_safe_yaml(surface):
    user = _user()
    if surface == "to_dict":
        data = user.to_dict(exclude_sensitive=True)
        text = repr(data)
    elif surface == "to_yaml":
        text = user.to_yaml(exclude_sensitive=True)
        data = yaml.safe_load(text)
    else:
        text = export_entities(users=[user], exclude_sensitive=True)
        data = yaml.safe_load(text)["entities"]["users"][0]
    assert data["nested"]["apiKey2"] == "***REDACTED***"
    assert data["plain"]["password2"] == "***REDACTED***"
    assert data["nested"]["public_label"] == "safe-label"
    assert data["plain"]["public_label"] == "safe-plain"
    assert data["plain"]["value"] == "safe-value"
    assert "synthetic-inner" not in text
    assert "synthetic-plain" not in text
    assert "!!python/object" not in text


@pytest.mark.parametrize("surface", ["to_yaml", "export_entities"])
def test_unredacted_yaml_uses_safe_mapping_not_python_object_tags(surface):
    user = _user()
    text = (user.to_yaml() if surface == "to_yaml"
            else export_entities(users=[user]))
    assert "!!python/object" not in text
    data = yaml.safe_load(text)
    if surface == "export_entities":
        data = data["entities"]["users"][0]
    assert data["nested"]["apiKey2"] == "synthetic-inner"
    assert data["plain"]["password2"] == "synthetic-plain"
    assert data["plain"]["value"] == "safe-value"


@pytest.mark.parametrize("layers", [1, 2, 3])
@pytest.mark.parametrize("surface", ["to_dict", "to_yaml", "export_entities"])
def test_percent_encoded_nested_redirect_userinfo_scrubbed(layers, surface):
    nested = "https://u:synthetic-pass@i/p"
    for _ in range(layers):
        nested = quote(nested, safe="")
    user = _user(website="https://h/p?redirect=" + nested + "&keep=public")
    if surface == "to_dict":
        data = user.to_dict(exclude_sensitive=True)
    elif surface == "to_yaml":
        data = yaml.safe_load(user.to_yaml(exclude_sensitive=True))
    else:
        data = yaml.safe_load(export_entities(users=[user], exclude_sensitive=True))["entities"]["users"][0]
    url = data["website"]
    assert url.startswith("https://h/p?redirect=")
    assert url.endswith("&keep=public")
    for _ in range(layers):
        url = unquote(url)
    assert "synthetic-pass" not in url
    assert "https://u:***REDACTED***@i/p" in url
    with pytest.raises(ValueError, match="Cannot import redacted values"):
        if surface == "export_entities":
            import_entities(export_entities(users=[user], exclude_sensitive=True))
        else:
            UserWithObjects.from_yaml(user.to_yaml(exclude_sensitive=True))


def test_excessively_encoded_nested_redirect_fails_closed():
    nested = "https://u:synthetic-pass@i/p"
    for _ in range(35):
        nested = quote(nested, safe="")
    website = _user(website="https://h/p?redirect=" + nested).to_dict(exclude_sensitive=True)["website"]
    assert website == "https://h/p?redirect=***REDACTED***"
    assert "synthetic-pass" not in website


@pytest.mark.parametrize("surface", ["to_dict", "to_yaml", "export_entities"])
def test_encoded_benign_redirect_preserved_byte_for_byte(surface):
    website = "https://h/p?redirect=https%3A%2F%2Fu%2Fp&keep=public"
    user = _user(website=website)
    if surface == "to_dict":
        data = user.to_dict(exclude_sensitive=True)
    elif surface == "to_yaml":
        data = yaml.safe_load(user.to_yaml(exclude_sensitive=True))
    else:
        data = yaml.safe_load(export_entities(users=[user], exclude_sensitive=True))["entities"]["users"][0]
    assert data["website"] == website

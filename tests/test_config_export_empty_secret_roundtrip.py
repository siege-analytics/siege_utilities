"""Amended R-1832-2: an exact-type empty Pydantic secret is preserved so a
default model's export -> import round-trip keeps working. That a secret
subclass is redacted without its ``get_secret_value()`` ever being consulted
is covered in ``test_config_redaction_empty_values.py``.
"""
from siege_utilities.config.models.actor_types import User
from siege_utilities.config.models.export import export_entities, import_entities


def _default_user() -> User:
    # Sensitive API-key fields default to SecretStr('') (actor_types.py:107,113,
    # 119,132); no explicit secret is supplied.
    return User(person_id="rt", name="RT User", email="rt@example.com",
                username="rt", oauth_integrations=[])


def test_default_user_export_import_roundtrips_end_to_end():
    user = _default_user()
    exported = export_entities(users=[user], exclude_sensitive=True)
    # The empty default secrets are preserved as '', not redacted, so the
    # placeholder guard in import_entities does not trip.
    assert "***REDACTED***" not in exported
    imported = import_entities(exported)
    assert len(imported["users"]) == 1
    back = imported["users"][0]
    assert back.google_analytics_key.get_secret_value() == ""
    assert back.facebook_business_key.get_secret_value() == ""
    assert back.census_api_key.get_secret_value() == ""
    assert back.postgresql_connection.get_secret_value() == ""

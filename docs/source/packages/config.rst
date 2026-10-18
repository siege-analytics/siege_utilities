Config
======

User and project configuration: credentials, database connections, client
profiles, project management.

Sharing exports without secrets
-------------------------------

``Person.to_dict``, ``Person.to_yaml`` and ``export_entities`` accept
``exclude_sensitive=True``. Redaction walks live models, including subclass
fields, nested dataclasses and plain objects, dictionaries and lists. YAML
exports use safe mappings rather than Python-object constructor tags. A field declared with
``Field(json_schema_extra={"sensitive": True})`` is redacted in full. An
explicit ``sensitive=False`` preserves the field while still walking its
contents.

Unmarked names use the same token-aware classifier as the field-marker guard.
CamelCase boundaries, hyphens, dots and spaces are normalized to underscores,
then whole tokens identify credentials such as ``accessKey``, ``api-key``,
``authorization``, ``session_cookie``, ``credentials``, ``pem`` and bare ``key``.
Adjacent count, policy, min, max, length, type and version qualifiers describe
non-secret metadata. Relational and public key qualifiers preserve names such
as ``primary_key`` and ``public_key``. These exclusions apply per token:
``public_key_secret`` still redacts.
Trailing digits are ignored on each token, so ``apiKey2`` and ``password2``
redact. Secret plurals and compounds such as ``secrets``, ``passwords``,
``clientsecret`` and ``accesstoken`` also redact. Run-together tokens containing
secret, token, password, passwd, apikey, privatekey or accesskey redact too,
including ``secretaccesskey``, ``googleapikey`` and ``passwordhash``.
``secretary``, ``secretariat``, ``tokenizer`` and ``tokenized`` remain public,
but they do not exempt an additional secret indicator in the same joined name:
``secretarypassword`` and ``tokenizersecret`` redact. Other compounds ending in ``key`` or ``keys`` require a known secret prefix
(api, access, secret, private, signing or ssh); ``sessionid`` is also recognized.
Names such as ``monkey``, ``turkey`` and ``hockey`` remain public.

String values containing URL userinfo passwords are scrubbed regardless of
their field name: ``https://user:password@host/path`` becomes
``https://user:***REDACTED***@host/path``. The rest of the URL is preserved.
Secret query and fragment parameters use the same name classifier as model
fields (plus provider signature aliases), including ``refresh_token``,
``id_token``, ``clientSecret``, ``access_token``, ``api_key``,
``X-Amz-Signature`` and ``password``. For
example, ``https://host/path?access_token=value&page=1`` becomes
``https://host/path?access_token=***REDACTED***&page=1``. The same placeholder
is used for these values, including in JDBC URLs and nested metadata.
Percent-encoded nested redirect URL userinfo is decoded in layers for password
scrubbing while non-credential redirect parameters keep their original value.

Secrets inside JSON-encoded strings are **not redacted** by name. Store these
secrets in dictionary fields or fields explicitly marked ``sensitive=True``.
For example, use ``{"client_secret": value}`` as a dictionary, rather than
encoding that dictionary as a string in an unmarked field. Secrets under
innocuous names also require an explicit sensitivity marker.

``from_yaml`` and ``import_entities`` reject values containing
``***REDACTED***``, including scrubbed URLs, so placeholders cannot overwrite
credentials. Use an unredacted export for backups and restoration. Exports
containing only public values can round-trip with ``exclude_sensitive=True``.

.. automodule:: siege_utilities.config
   :members:
   :show-inheritance:

Submodules
----------

.. automodule:: siege_utilities.config.credential_manager
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.connections
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.databases
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.clients
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.projects
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.user_config
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.enhanced_config
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.paths
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.directories
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.constants
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.census_constants
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.census_registry
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.nces_constants
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.data_source_registry
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.google_account_registry
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.hydra_manager
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.migration
   :members:
   :show-inheritance:

Models
------

.. automodule:: siege_utilities.config.models
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.models.actor_types
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.models.branding_config
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.models.client_profile
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.models.credential
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.models.data_sources
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.models.database_connection
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.models.export
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.models.google_account
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.models.oauth_integration
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.models.person
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.models.report_preferences
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.models.social_media_account
   :members:
   :show-inheritance:

.. automodule:: siege_utilities.config.models.user_profile
   :members:
   :show-inheritance:

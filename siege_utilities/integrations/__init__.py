"""Third-party library integrations.

Each subpackage exposes siege-native helpers layered on top of a specific
external library. The long-term shape is ``ConnectorProtocol`` wrappers
returning ``pandas.DataFrame`` and raising ``ConnectorError``; today's
substrate ships the plumbing (adapters, error mapping, credential
bridging) and connector wrapper classes land per-connector.

Current subpackages:

- :mod:`siege_utilities.integrations.parsons` — TMC Parsons plumbing
  (``parsons.Table`` ↔ ``pandas.DataFrame`` adapter, exception mapping to
  the ``ConnectorError`` hierarchy, siege-profile → Parsons-constructor
  credential bridge). See its ``__init__`` for the currently exported
  helper API; connector wrapper classes are being added incrementally.

See ``docs/PARSONS_LICENSE_ANALYSIS.md`` and ``docs/PARSONS_DEP_MATRIX.md``
for the integration boundaries.
"""

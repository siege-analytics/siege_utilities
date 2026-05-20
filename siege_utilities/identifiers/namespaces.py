"""
UUID5 namespace derivation helpers.

Consumers declare their own root seed and per-entity-type sub-namespaces
using these factory functions, then hardcode the resulting UUIDs as
immutable constants in their own code. The consumer's tests should
verify that the hardcoded values match the derivation (same pattern
shown in the docstrings below).
"""

from uuid import NAMESPACE_URL, UUID, uuid5


def derive_root(seed: str) -> UUID:
    """
    Derive a root UUID5 namespace from a string seed.

    Consumers pick a stable seed string representing their domain
    (e.g., "mydomain.example.com"). The derived UUID should be computed
    once, hardcoded in consumer code as a constant, and treated as
    immutable — changing it would invalidate every UUID derived under it.

    Example::

        >>> ROOT = derive_root("example.com")
        >>> ROOT  # this value should be hardcoded in consumer code:
        UUID('cfbff0d1-9375-5685-968a-48ce8b7ebbbb')

    Args:
        seed: A non-empty string. Convention: lowercase DNS-style name.

    Returns:
        The UUID5 derived from ``NAMESPACE_URL`` and ``seed``.

    Raises:
        ValueError: if ``seed`` is empty.
    """
    if not seed or not seed.strip():
        raise ValueError("root seed must be non-empty")
    return uuid5(NAMESPACE_URL, seed)


def derive_sub_namespace(root: UUID, name: str) -> UUID:
    """
    Derive a sub-namespace UUID5 from a root namespace + name.

    Used for per-entity-type namespaces: a consumer with a root and a
    domain concept like "person" derives the PERSON_NS this way.

    Example::

        >>> ROOT = derive_root("example.com")
        >>> PERSON_NS = derive_sub_namespace(ROOT, "person")
        >>> # hardcode PERSON_NS in consumer code; assert-match in tests.

    Args:
        root: The root namespace UUID (typically from ``derive_root``).
        name: Non-empty string identifying the sub-namespace purpose.
            Convention: lowercase snake_case, stable for the lifetime of
            the consumer.

    Returns:
        The UUID5 derived from ``root`` and ``name``.

    Raises:
        ValueError: if ``name`` is empty.
    """
    if not name or not name.strip():
        raise ValueError("sub-namespace name must be non-empty")
    return uuid5(root, name)

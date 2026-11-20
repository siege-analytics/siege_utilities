"""Internal row identity shared by batch geocoding layers."""

from uuid import uuid4


class _BatchId(str):
    """A library-issued ID; plain caller strings never count as internal IDs."""


def _assign_batch_ids(input_ids: list[str]) -> list[str]:
    """Preserve IDs from an upstream layer, assigning fresh IDs at entry.

    The marker survives in-process calls; backends only need to echo its
    string value. Repeated inputs still receive separate IDs. Caller IDs
    stay with the original inputs and are restored after joining results.
    """
    assigned = []
    used = set()
    for input_id in input_ids:
        if isinstance(input_id, _BatchId) and input_id not in used:
            batch_id = input_id
        else:
            batch_id = _BatchId(uuid4().hex)
        used.add(batch_id)
        assigned.append(batch_id)
    return assigned

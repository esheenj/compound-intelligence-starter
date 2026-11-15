"""Pure Python behavior baseline for the Rust interop qualification experiment."""

MAX_ITEMS = 200_000
MAX_TOTAL_BYTES = 8_000_000
_ALLOWED = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_-")


def classify_ids(values):
    """Return (accepted_unique, duplicates, rejected) for bounded ASCII IDs.

    Valid identifiers contain 1–64 ASCII lowercase letters, digits, '_' or '-'.
    The first valid occurrence counts as accepted; repeats count as duplicates.
    Invalid entries are rejected without consuming a unique identifier.
    """
    if not isinstance(values, (list, tuple)):
        raise TypeError("values must be a list or tuple of strings")
    if len(values) > MAX_ITEMS:
        raise ValueError("batch too large")
    total = 0
    seen = set()
    accepted = duplicate = rejected = 0
    for item in values:
        if not isinstance(item, str):
            raise TypeError("all values must be strings")
        data = item.encode("utf-8")
        total += len(data)
        if total > MAX_TOTAL_BYTES:
            raise ValueError("batch bytes too large")
        if not 1 <= len(data) <= 64 or not set(item) <= _ALLOWED:
            rejected += 1
        elif item in seen:
            duplicate += 1
        else:
            accepted += 1
            seen.add(item)
    return accepted, duplicate, rejected

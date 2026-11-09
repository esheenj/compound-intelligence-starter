"""Synthetic record-format validator. No hash verification or execution authority."""
from __future__ import annotations

import sys

STATES = frozenset({"ACCEPTED", "REJECTED", "INCONCLUSIVE"})
HEX = frozenset("0123456789abcdef")


def validate_line(line: str) -> bool:
    """Validate one tab-separated id, state and digest-text record."""
    if not isinstance(line, str) or len(line.encode("utf-8")) > 512:
        return False
    fields = line.split("\t")
    if len(fields) != 3:
        return False
    record_id, state, digest = fields
    if not (1 <= len(record_id) <= 64):
        return False
    if not all(ch in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in record_id):
        return False
    return state in STATES and len(digest) == 64 and all(ch in HEX for ch in digest)


def main() -> None:
    for raw in sys.stdin:
        line = raw.removesuffix("\n").removesuffix("\r")
        sys.stdout.write("VALID\n" if validate_line(line) else "INVALID\n")


if __name__ == "__main__":
    main()

"""Reference parser for fictional bounded event aggregation; no private data."""
from __future__ import annotations

import sys
from collections.abc import Iterable

CATEGORIES = ("atlas", "beacon", "cobalt", "delta")
KINDS = ("PASS", "FAIL", "RETRY")


def parse_record(raw: bytes) -> tuple[str, str, str, int] | None:
    if len(raw) > 256:
        return None
    try:
        line = raw.decode("ascii")
    except UnicodeDecodeError:
        return None
    parts = line.split("\t")
    if len(parts) != 4:
        return None
    event_id, category, kind, amount_text = parts
    if len(event_id) != 9 or not event_id.startswith("E") or not event_id[1:].isascii() or not event_id[1:].isdigit():
        return None
    if category not in CATEGORIES or kind not in KINDS:
        return None
    digits = amount_text[1:] if amount_text.startswith("-") else amount_text
    if not digits or not digits.isascii() or not digits.isdigit():
        return None
    if (len(digits) > 1 and digits[0] == "0") or amount_text == "-0":
        return None
    value = int(amount_text)
    if not -10_000 <= value <= 10_000:
        return None
    return event_id, category, kind, value


def aggregate(records: Iterable[bytes]) -> bytes:
    seen: set[str] = set()
    accepted = duplicates = rejected = 0
    totals: dict[tuple[str, str], list[int]] = {}
    for raw in records:
        record = parse_record(raw)
        if record is None:
            rejected += 1
            continue
        event_id, category, kind, value = record
        if event_id in seen:
            duplicates += 1
            continue
        seen.add(event_id)
        accepted += 1
        group = totals.setdefault((category, kind), [0, 0])
        group[0] += 1
        group[1] += value
    lines = [f"ACCEPTED\t{accepted}", f"DUPLICATES\t{duplicates}", f"REJECTED\t{rejected}"]
    for category in CATEGORIES:
        for kind in KINDS:
            count, total = totals.get((category, kind), [0, 0])
            lines.append(f"GROUP\t{category}\t{kind}\t{count}\t{total}")
    return ("\n".join(lines) + "\n").encode("ascii")


if __name__ == "__main__":
    sys.stdout.buffer.write(aggregate(raw.removesuffix(b"\n") for raw in sys.stdin.buffer))

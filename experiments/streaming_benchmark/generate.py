"""Deterministically generate original synthetic events, never personal records."""
from __future__ import annotations

import argparse
import sys

CATEGORIES = ("atlas", "beacon", "cobalt", "delta")
KINDS = ("PASS", "FAIL", "RETRY")


def generate(rows: int) -> bytes:
    if not 1 <= rows <= 250_000:
        raise ValueError("rows must be in 1..250000")
    output = bytearray()
    for i in range(rows):
        event_id = f"E{i - 1 if i > 0 and i % 149 == 0 else i:08d}"
        category = CATEGORIES[i % len(CATEGORIES)]
        kind = "UNKNOWN" if i % 233 == 0 else KINDS[i % len(KINDS)]
        amount = "+5" if i % 397 == 0 else str((i * 37) % 20001 - 10000)
        if i % 683 == 0:
            event_id = "Ebad"
        line = f"{event_id}\t{category}\t{kind}\t{amount}"
        if i % 521 == 0:
            line += "\textra"
        output.extend(line.encode("ascii") + b"\n")
    return bytes(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=100_000)
    sys.stdout.buffer.write(generate(parser.parse_args().rows))

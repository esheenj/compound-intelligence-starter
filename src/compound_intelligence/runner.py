"""Run a bounded experiment batch, optionally with a local Ollama challenger."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import bounded_run
from .ollama import advisory

EXAMPLES = [
    {"id": "addition-001", "kind": "sum", "values": [2, 2], "expected": 4},
    {"id": "addition-002", "kind": "sum", "values": [3, 5], "expected": 7},
    {"id": "addition-003", "kind": "sum", "values": [8, 13], "expected": 21},
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="JSON file containing a list of experiments")
    parser.add_argument("--workspace", type=Path, default=Path("local-data"))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--ollama-model", help="Optional local Ollama reviewer model")
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8")) if args.input else EXAMPLES
    reviewer = (lambda item: advisory(item, model=args.ollama_model)) if args.ollama_model else None
    result = bounded_run(args.workspace / "experiments.sqlite3", data, args.limit, reviewer)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

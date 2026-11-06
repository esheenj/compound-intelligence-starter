"""Runnable stdlib-only demonstration of validated, durable experiment evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

CANDIDATES = (
    {"id": "candidate-001", "claim": "2 + 2 = 4", "expression": [2, 2], "expected": 4},
    {"id": "candidate-002", "claim": "3 + 5 = 7", "expression": [3, 5], "expected": 7},
    {"id": "candidate-003", "claim": "8 + 13 = 21", "expression": [8, 13], "expected": 21},
)


def evaluate(candidate: dict) -> dict:
    """Challenge expected outcome using a separate deterministic computation."""
    actual = sum(candidate["expression"])
    accepted = actual == candidate["expected"]
    return {
        "id": candidate["id"],
        "claim": candidate["claim"],
        "hypothesis": {"inputs": candidate["expression"], "expected": candidate["expected"]},
        "challenge": {"method": "independent arithmetic", "actual": actual},
        "status": "VERIFIED" if accepted else "REJECTED",
        "reason": "validation passed" if accepted else "counterexample: expectation differs from computation",
    }


def read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run(workspace: Path, iterations: int = 3) -> dict:
    if iterations < 0:
        raise ValueError("iterations must be non-negative")
    workspace.mkdir(parents=True, exist_ok=True)
    ledger = workspace / "evidence.jsonl"
    before = read_records(ledger)
    seen = {r["id"] for r in before}
    appended = []
    for candidate in CANDIDATES[:iterations]:
        if candidate["id"] in seen:
            continue
        evidence = evaluate(candidate)
        evidence["recorded_at"] = datetime.now(timezone.utc).isoformat()
        canonical = json.dumps({k: v for k, v in evidence.items() if k != "recorded_at"}, sort_keys=True)
        evidence["evidence_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
        with ledger.open("a", encoding="utf-8") as file:
            file.write(json.dumps(evidence, sort_keys=True) + "\n")
        appended.append(evidence)
        seen.add(candidate["id"])
    after = read_records(ledger)
    return {
        "new_experiments": len(appended),
        "total_experiments": len(after),
        "verified": sum(r["status"] == "VERIFIED" for r in after),
        "rejected": sum(r["status"] == "REJECTED" for r in after),
        "ledger": str(ledger),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path("local-data"))
    parser.add_argument("--iterations", type=int, default=3)
    options = parser.parse_args()
    print(json.dumps(run(options.workspace, options.iterations), indent=2))


if __name__ == "__main__":
    main()

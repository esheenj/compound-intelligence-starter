"""Bounded experiments with independent validation and transactional evidence."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MAX_CANDIDATES = 100


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def validate(candidate: dict) -> dict:
    """Only deterministic arithmetic is supported by this teaching implementation."""
    if candidate.get("kind") != "sum":
        raise ValueError("unsupported experiment kind")
    values = candidate.get("values")
    expected = candidate.get("expected")
    if not isinstance(values, list) or not (1 <= len(values) <= 32):
        raise ValueError("values must be a list containing 1-32 integers")
    if any(type(x) is not int or abs(x) > 1_000_000 for x in values):
        raise ValueError("values must be bounded integers")
    if type(expected) is not int:
        raise ValueError("expected must be an integer")
    actual = sum(values)
    return {
        "method": "trusted Python sum of bounded integers",
        "actual": actual,
        "accepted": actual == expected,
        "counterexample": None if actual == expected else {"expected": expected, "actual": actual},
    }


class EvidenceStore:
    """SQLite transactions prevent duplicate records after repeated execution."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=10)
        self.db.execute("PRAGMA busy_timeout=10000")
        self.db.execute("CREATE TABLE IF NOT EXISTS evidence (id TEXT PRIMARY KEY, input_sha256 TEXT NOT NULL, record TEXT NOT NULL)")
        self.db.commit()

    def close(self):
        self.db.close()

    def get(self, experiment_id: str) -> dict | None:
        row = self.db.execute("SELECT record FROM evidence WHERE id=?", (experiment_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self) -> list[dict]:
        return [json.loads(row[0]) for row in self.db.execute("SELECT record FROM evidence ORDER BY id")]

    def run(self, experiment: dict, advisory: dict | None = None) -> tuple[dict, bool]:
        experiment_id = experiment.get("id")
        if not isinstance(experiment_id, str) or not (1 <= len(experiment_id) <= 128):
            raise ValueError("experiment id must be 1-128 characters")
        if any(not (c.isalnum() or c in "-_.") for c in experiment_id):
            raise ValueError("experiment id contains invalid characters")
        payload = {"kind": experiment.get("kind"), "values": experiment.get("values"), "expected": experiment.get("expected")}
        digest = hashlib.sha256(canonical(payload).encode()).hexdigest()
        with self.db:
            existing = self.db.execute("SELECT input_sha256,record FROM evidence WHERE id=?", (experiment_id,)).fetchone()
            if existing:
                if existing[0] != digest:
                    raise ValueError("experiment id already used with different inputs")
                return json.loads(existing[1]), False
            result = validate(payload)
            record = {
                "id": experiment_id,
                "input_sha256": digest,
                "experiment": payload,
                "validation": result,
                "status": "VERIFIED" if result["accepted"] else "REJECTED",
                "advisory": advisory,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            }
            self.db.execute("INSERT INTO evidence (id,input_sha256,record) VALUES (?,?,?)", (experiment_id, digest, canonical(record)))
            return record, True


def bounded_run(path: Path, experiments: list[dict], limit: int = 10, advisor=None) -> dict:
    if type(limit) is not int or not 0 <= limit <= MAX_CANDIDATES:
        raise ValueError("limit must be between 0 and 100")
    if not isinstance(experiments, list) or len(experiments) > MAX_CANDIDATES:
        raise ValueError("experiments must be a list of at most 100 items")
    store = EvidenceStore(path)
    try:
        output = []
        for item in experiments[:limit]:
            experiment_id = item.get("id")
            previous = store.get(experiment_id) if isinstance(experiment_id, str) else None
            # Never invoke a model again for an already recorded identity.
            advisory = None if previous else advisor(item) if advisor else None
            record, created = store.run(item, advisory)
            output.append({"id": record["id"], "status": record["status"], "new": created, "advisory": record["advisory"]})
        return {"processed": len(output), "new": sum(x["new"] for x in output), "experiments": output}
    finally:
        store.close()

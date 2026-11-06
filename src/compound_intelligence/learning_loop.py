"""v1.0: verified exemplar retrieval and independently checked next-task proposals.

Local explicit CLI invocation only; no background services or generated-code execution.
The offline fixture is a teaching simulation, NOT evidence of real AI improvement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path

from .challenges import evaluate, public_task, validate_task
from .engine import canonical
from .problem_runner import propose_ollama

SCHEMA = "compound-learning-loop-v1"
MAX_EXEMPLARS = 3
MAX_TASKS = 10


def _digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class KnowledgeStore:
    """Transactional verified-only, locally persisted exemplars and run receipts."""

    def __init__(self, path: Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=10)
        self.db.execute("PRAGMA busy_timeout=10000")
        self.db.execute("""CREATE TABLE IF NOT EXISTS exemplars
            (id TEXT PRIMARY KEY, task TEXT NOT NULL, proposal TEXT NOT NULL,
             digest TEXT NOT NULL, status TEXT NOT NULL CHECK(status='VERIFIED'))""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS loop_receipts
            (id TEXT PRIMARY KEY, spec_digest TEXT NOT NULL, receipt TEXT NOT NULL)""")
        self.db.commit()

    def close(self):
        self.db.close()

    def remember(self, task: dict, proposal: dict) -> bool:
        validate_task(task)
        assessment = evaluate(task, proposal)
        if assessment["status"] != "VERIFIED":
            return False
        value = {"task": public_task(task), "proposal": proposal}
        digest = _digest(value)
        with self.db:
            found = self.db.execute("SELECT digest FROM exemplars WHERE id=?", (task["id"],)).fetchone()
            if found:
                if found[0] != digest:
                    raise ValueError("existing verified exemplar id has different content")
                return False
            self.db.execute("INSERT INTO exemplars VALUES (?,?,?,?,?)",
                            (task["id"], canonical(value["task"]), canonical(proposal),
                             digest, "VERIFIED"))
        return True

    def relevant(self, task: dict, limit: int = MAX_EXEMPLARS) -> list[dict]:
        validate_task(task)
        if type(limit) is not int or not 0 <= limit <= MAX_EXEMPLARS:
            raise ValueError("exemplar limit must be 0-3")
        rows = self.db.execute("SELECT id,task,proposal,digest FROM exemplars ORDER BY id").fetchall()
        found = []
        target = public_task(task)
        target_digest = _digest(target)
        for item_id, raw_task, raw_proposal, digest in rows:
            example = json.loads(raw_task)
            if item_id == task["id"] or _digest(example) == target_digest or example["type"] != task["type"]:
                continue
            if task["type"] == "extract" and set(example["fields"]) != set(task["fields"]):
                continue
            found.append({"source_id": item_id, "source_digest": digest,
                          "task": example, "verified_proposal": json.loads(raw_proposal)})
        return found[:limit]

    def receipt(self, run_id: str, spec: dict) -> dict | None:
        row = self.db.execute("SELECT spec_digest,receipt FROM loop_receipts WHERE id=?", (run_id,)).fetchone()
        if not row:
            return None
        if row[0] != _digest(spec):
            raise ValueError("run id already used with different inputs")
        return json.loads(row[1])

    def commit(self, run_id: str, spec: dict, result: dict) -> dict:
        with self.db:
            prior = self.receipt(run_id, spec)
            if prior is not None:
                return prior
            self.db.execute("INSERT INTO loop_receipts VALUES (?,?,?)",
                            (run_id, _digest(spec), canonical(result)))
        return result


def offline_fixture(model: str, task: dict) -> dict:
    """Deterministic mock uses a retrieved schema; not a real model."""
    if task["type"] != "extract":
        return {"_error": "fixture supports extraction only"}
    examples = task.get("verified_examples", [])
    if not examples:
        return {"_error": "fixture requires a verified format example"}
    if set(task["fields"]) != {"support_email", "returns_days"}:
        return {"_error": "unsupported fixture schema"}
    email = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", task["text"])
    days = re.search(r"\b(\d{1,3})\s+days\b", task["text"], re.IGNORECASE)
    if not email or not days:
        return {"_error": "fixture could not extract required fields"}
    return {"support_email": email.group(0), "returns_days": int(days.group(1))}


def run(seed: list[dict], targets: list[dict], workspace: Path, model: str,
        proposer, *, run_id: str, limit: int = MAX_EXEMPLARS) -> dict:
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", run_id):
        raise ValueError("invalid run id")
    if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", model):
        raise ValueError("invalid model name")
    if (not isinstance(seed, list) or not isinstance(targets, list) or
            not 1 <= len(seed) <= MAX_TASKS or not 1 <= len(targets) <= MAX_TASKS):
        raise ValueError("provide 1-10 seed and 1-10 target tasks")
    if type(limit) is not int or not 0 <= limit <= MAX_EXEMPLARS:
        raise ValueError("limit must be 0-3")
    for item in seed + targets:
        validate_task(item)
    names = [item["id"] for item in seed + targets]
    if len(set(names)) != len(names):
        raise ValueError("seed and target IDs must be distinct")
    # Seed inputs are verified locally, never supplied as a trusted user assertion.
    spec = {"seed": seed, "targets": targets, "model": model, "limit": limit}
    store = KnowledgeStore(Path(workspace) / "knowledge.sqlite3")
    try:
        existing = store.receipt(run_id, spec)
        if existing is not None:
            return {**existing, "reused_receipt": True}
        seeded = 0
        for item in seed:
            proposal = offline_fixture("fixture", {"**public_task(item),
                "verified_examples": [{"format": item["type"]}]}) if proposer is offline_fixture else proposer(model, public_task(item))
            if isinstance(proposal, dict) and store.remember(item, proposal):
                seeded += 1
        results = []
        for task in targets:
            exemplars = store.relevant(task, limit)
            prompt_task = {**public_task(task), "verified_examples": exemplars}
            try:
                proposal = proposer(model, prompt_task)
                if isinstance(proposal, dict) and set(proposal) == {"_error"}:
                    status, reason = "NO_RESULT", str(proposal["_error"])[:100]
                else:
                    assessment = evaluate(task, proposal)
                    status, reason = assessment["status"], assessment["reason"]
            except (ValueError, OSError, RuntimeError, TypeError, TimeoutError) as exc:
                status, reason = "NO_RESULT", type(exc).__name__
            results.append({"task": task["id"], "status": status, "reason": reason,
                            "retrieved_ids": [x["source_id"] for x in exemplars],
                            "retrieved_digests": [x["source_digest"] for x in exemplars]})
        receipt = {"schema": SCHEMA, "run_id": run_id,
                   "origin": "SIMULATED_FIXTURE" if proposer is offline_fixture else "LOCAL_MODEL_PROPOSALS",
                   "model": model, "new_verified_exemplars": seeded,
                   "results": results, "reused_receipt": False,
                   "status": "RECORDED_NOT_PROMOTED",
                   "interpretation": "Verified examples were supplied as context, not learned by model weights. "
                                     "Target claims were independently checked against withheld answers. "
                                     "No uplift or generalized intelligence claim is established."}
        return store.commit(run_id, spec, receipt)
    finally:
        store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, default=Path("examples/challenges.json"))
    parser.add_argument("--targets", type=Path, default=Path("examples/transfer_challenges.json"))
    parser.add_argument("--workspace", type=Path, default=Path("local-data/v10"))
    parser.add_argument("--run-id", default="demo-001")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--fixture", action="store_true")
    group.add_argument("--model", help="local Ollama model already installed")
    args = parser.parse_args()
    seeds = json.loads(args.seed.read_text(encoding="utf-8"))
    targets = json.loads(args.targets.read_text(encoding="utf-8"))
    if args.fixture:
        # Offline fixture supports extraction only; filter the generic v0.4 seeds.
        seeds = [task for task in seeds if task["type"] == "extract"]
    model = "fixture-transfer" if args.fixture else args.model
    provider = offline_fixture if args.fixture else propose_ollama
    print(json.dumps(run(seeds, targets, args.workspace, model, provider, run_id=args.run_id), indent=2))


if __name__ == "__main__":
    main()

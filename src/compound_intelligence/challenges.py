"""Typed, bounded challenge evaluation. Never executes proposed source code."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .engine import canonical

MAX_TASKS = 20
MAX_MODELS = 4
MAX_TEXT = 4096


def validate_task(task: dict) -> None:
    if not isinstance(task, dict) or task.get("type") not in ("extract", "patch"):
        raise ValueError("task type must be extract or patch")
    if not isinstance(task.get("id"), str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", task["id"]):
        raise ValueError("invalid task id")
    if task["type"] == "extract":
        if not isinstance(task.get("text"), str) or not 1 <= len(task["text"]) <= MAX_TEXT:
            raise ValueError("text must be 1-4096 characters")
        fields = task.get("fields")
        expected = task.get("expected")
        if (not isinstance(fields, list) or not 1 <= len(fields) <= 12
                or any(not isinstance(x, str) or not re.fullmatch(r"[a-z_]{1,40}", x) for x in fields)
                or len(fields) != len(set(fields))):
            raise ValueError("invalid extract fields")
        if (not isinstance(expected, dict) or set(expected) != set(fields)
                or any(type(x) not in (str, int, bool) for x in expected.values())):
            raise ValueError("invalid extraction reference")
    else:
        source, expected = task.get("source"), task.get("expected")
        if (not isinstance(source, str) or not isinstance(expected, str)
                or not 1 <= len(source) <= MAX_TEXT or not 1 <= len(expected) <= MAX_TEXT):
            raise ValueError("source and expected must be bounded non-empty strings")
        if not isinstance(task.get("instruction"), str) or not 1 <= len(task["instruction"]) <= 500:
            raise ValueError("patch instruction is required")


def public_task(task: dict) -> dict:
    """Held-out reference is never included in the model prompt."""
    validate_task(task)
    keys = ("id", "type", "text", "fields") if task["type"] == "extract" else (
        "id", "type", "source", "instruction")
    return {key: task[key] for key in keys}


def evaluate(task: dict, proposal: object) -> dict:
    validate_task(task)
    if not isinstance(proposal, dict):
        return {"status": "REJECTED", "reason": "proposal must be a JSON object"}
    if task["type"] == "extract":
        accepted = set(proposal) == set(task["fields"]) and all(
            type(proposal[name]) is type(task["expected"][name])
            and proposal[name] == task["expected"][name] for name in task["fields"]
        )
        return {"status": "VERIFIED" if accepted else "REJECTED",
                "reason": "exact typed field match" if accepted else "fields or values differ"}
    if set(proposal) != {"old", "new"} or any(not isinstance(proposal[k], str) for k in ("old", "new")):
        return {"status": "REJECTED", "reason": "patch needs old and new strings only"}
    old, new, source = proposal["old"], proposal["new"], task["source"]
    if not old or len(old) > 512 or len(new) > 512 or source.count(old) != 1:
        return {"status": "REJECTED", "reason": "patch must replace exactly one bounded match"}
    patched = source.replace(old, new, 1)
    accepted = patched == task["expected"]
    return {"status": "VERIFIED" if accepted else "REJECTED",
            "reason": "static reference match; code not executed" if accepted else "patch differs from reference"}


def fingerprint(task: dict, model: str, version: str = "v0.4") -> str:
    return hashlib.sha256(canonical({"task": task, "model": model, "version": version}).encode()).hexdigest()


class ChallengeLedger:
    """SQLite-backed, atomic, replayable records, including model failures."""

    def __init__(self, path: Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=10)
        self.db.execute("""CREATE TABLE IF NOT EXISTS challenge_records (
            fingerprint TEXT PRIMARY KEY, record TEXT NOT NULL)""")
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def get(self, key: str) -> dict | None:
        row = self.db.execute("SELECT record FROM challenge_records WHERE fingerprint=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, key: str, record: dict) -> tuple[dict, bool]:
        with self.db:
            cursor = self.db.execute("INSERT OR IGNORE INTO challenge_records VALUES (?,?)",
                                     (key, canonical(record)))
            saved = self.get(key)
            return saved, cursor.rowcount == 1

    def records(self) -> list[dict]:
        return [json.loads(x[0]) for x in self.db.execute(
            "SELECT record FROM challenge_records ORDER BY fingerprint")]


def compare(tasks: list[dict], models: list[str], workspace: Path, proposer,
            *, version: str = "v0.4") -> dict:
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= MAX_TASKS:
        raise ValueError("require 1-20 tasks")
    if not isinstance(models, list) or not 1 <= len(models) <= MAX_MODELS:
        raise ValueError("require 1-4 models")
    if len(set(models)) != len(models) or any(
            not isinstance(m, str) or not re.fullmatch(r"[A-Za-z0-9_./:-]{1,128}", m)
            for m in models):
        raise ValueError("invalid or duplicate model identifier")
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", version):
        raise ValueError("invalid model/experiment version")
    if not callable(proposer):
        raise ValueError("proposer must be callable")
    for task in tasks:
        validate_task(task)
    ids = [task["id"] for task in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("task ids must be unique")
    ledger = ChallengeLedger(Path(workspace) / "challenges.sqlite3")
    results = []
    try:
        for task in tasks:
            for model in models:
                key = fingerprint(task, model, version)
                saved = ledger.get(key)
                if saved is not None:
                    results.append({**saved["summary"], "new": False})
                    continue
                safe_task = public_task(task)
                try:
                    proposal = proposer(model, safe_task)
                    if isinstance(proposal, dict) and set(proposal) == {"_error"}:
                        evaluation = {"status": "NO_RESULT", "reason": str(proposal["_error"])[:100]}
                    else:
                        evaluation = evaluate(task, proposal)
                except (ValueError, TypeError, RuntimeError, OSError, TimeoutError) as exc:
                    evaluation = {"status": "NO_RESULT", "reason": type(exc).__name__}
                summary = {"task": task["id"], "model": model, "status": evaluation["status"],
                           "reason": evaluation["reason"]}
                record = {"summary": summary, "task_type": task["type"],
                          "public_task_sha256": hashlib.sha256(canonical(safe_task).encode()).hexdigest(),
                          "reference_sha256": hashlib.sha256(canonical(task["expected"]).encode()).hexdigest(),
                          "version": version, "recorded_at": datetime.now(timezone.utc).isoformat()}
                saved, created = ledger.save(key, record)
                results.append({**saved["summary"], "new": created})
    finally:
        ledger.close()
    return {"results": results, "verified": sum(x["status"] == "VERIFIED" for x in results),
            "rejected": sum(x["status"] == "REJECTED" for x in results),
            "no_result": sum(x["status"] == "NO_RESULT" for x in results),
            "new": sum(x["new"] for x in results),
            "scope": "Exact-match extraction and static patch checks; no generated code execution"}

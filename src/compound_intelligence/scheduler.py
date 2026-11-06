"""v0.6 finite, local-only job queue with durable claims and result receipts.

No subprocesses, user-supplied source execution, network tools or background loop.
External schedulers MAY invoke one bounded tick at a time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import time
import uuid
from pathlib import Path

from .benchmark import generate
from .engine import canonical
from .problem_runner import fixture

CAPABILITY = "fixture_benchmark"
MAX_JOBS_PER_TICK = 5
MAX_ATTEMPTS = 2
LEASE_SECONDS = 60
FIXTURES = Path(__file__).resolve().parents[2] / "examples" / "challenges.json"


def _job_spec(job_id: str, capability: str) -> dict:
    if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", job_id):
        raise ValueError("invalid job identifier")
    if capability != CAPABILITY:
        raise ValueError("capability not permitted: only fixture_benchmark is available")
    return {"id": job_id, "capability": capability}


class JobQueue:
    def __init__(self, path: Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=10)
        self.db.execute("PRAGMA busy_timeout=10000")
        self.db.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, spec_digest TEXT NOT NULL, capability TEXT NOT NULL,
            state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
            lease_token TEXT, lease_until REAL, result TEXT, error TEXT)""")
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def enqueue(self, job_id: str, capability: str = CAPABILITY) -> dict:
        spec = _job_spec(job_id, capability)
        digest = hashlib.sha256(canonical(spec).encode()).hexdigest()
        with self.db:
            row = self.db.execute("SELECT spec_digest FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row and row[0] != digest:
                raise ValueError("existing job id has a conflicting specification")
            if not row:
                self.db.execute("INSERT INTO jobs (id,spec_digest,capability,state) VALUES (?,?,?,?)",
                                (job_id, digest, capability, "PENDING"))
        return self.get(job_id)

    def get(self, job_id: str) -> dict | None:
        row = self.db.execute("""SELECT id,capability,state,attempts,result,error
                                  FROM jobs WHERE id=?""", (job_id,)).fetchone()
        if not row:
            return None
        return {"id": row[0], "capability": row[1], "state": row[2],
                "attempts": row[3], "result": json.loads(row[4]) if row[4] else None,
                "error": row[5]}

    def list(self) -> list[dict]:
        ids = self.db.execute("SELECT id FROM jobs ORDER BY id").fetchall()
        return [self.get(row[0]) for row in ids]

    def claim(self, now: float | None = None) -> tuple[str, str, str] | None:
        now = time.time() if now is None else now
        self.db.execute("BEGIN IMMEDIATE")
        try:
            # Expired claims become eligible again only if retry budget remains.
            self.db.execute("""UPDATE jobs SET state='PENDING',lease_token=NULL,lease_until=NULL
                WHERE state='RUNNING' AND lease_until <= ? AND attempts < ?""",
                (now, MAX_ATTEMPTS))
            self.db.execute("""UPDATE jobs SET state='FAILED',error='lease expired after retry budget',
                lease_token=NULL,lease_until=NULL
                WHERE state='RUNNING' AND lease_until <= ? AND attempts >= ?""",
                (now, MAX_ATTEMPTS))
            row = self.db.execute("""SELECT id,capability FROM jobs
                    WHERE state='PENDING' ORDER BY id LIMIT 1""").fetchone()
            if not row:
                self.db.commit()
                return None
            token = uuid.uuid4().hex
            self.db.execute("""UPDATE jobs SET state='RUNNING',attempts=attempts+1,
                lease_token=?,lease_until=? WHERE id=?""", (token, now + LEASE_SECONDS, row[0]))
            self.db.commit()
            return row[0], row[1], token
        except BaseException:
            self.db.rollback()
            raise

    def finish(self, job_id: str, token: str, result: dict | None = None, error: str | None = None) -> bool:
        if (result is None) == (error is None):
            raise ValueError("provide exactly one of result or error")
        with self.db:
            row = self.db.execute("SELECT attempts FROM jobs WHERE id=? AND state='RUNNING' AND lease_token=?",
                                  (job_id, token)).fetchone()
            if not row:
                return False
            state = ("DONE" if result is not None else
                     "FAILED" if row[0] >= MAX_ATTEMPTS else "PENDING")
            cursor = self.db.execute("""UPDATE jobs SET state=?,result=?,error=?,
                lease_token=NULL,lease_until=NULL WHERE id=? AND lease_token=? AND state='RUNNING'""",
                (state, canonical(result) if result is not None else None,
                 error[:200] if error else None, job_id, token))
            return cursor.rowcount == 1


def execute(capability: str, workspace: Path, job_id: str) -> dict:
    if capability != CAPABILITY:
        raise ValueError("disallowed capability")
    tasks = json.loads(FIXTURES.read_text(encoding="utf-8"))
    # Isolate job evidence so unrelated tasks never overwrite one another.
    return generate(tasks, ["fixture-correct", "fixture-incorrect"],
                    workspace / "evidence" / job_id, fixture, fixture_mode=True,
                    version="v0.6")


def tick(workspace: Path, max_jobs: int = 1, *, executor=execute) -> list[dict]:
    if type(max_jobs) is not int or not 1 <= max_jobs <= MAX_JOBS_PER_TICK:
        raise ValueError("max_jobs must be 1-5")
    workspace = Path(workspace)
    queue = JobQueue(workspace / "queue.sqlite3")
    outcomes = []
    try:
        for _ in range(max_jobs):
            claimed = queue.claim()
            if claimed is None:
                break
            job_id, capability, token = claimed
            try:
                result = executor(capability, workspace, job_id)
                confirmed = queue.finish(job_id, token, result=result)
            except Exception as exc:
                confirmed = queue.finish(job_id, token, error=type(exc).__name__)
            outcomes.append({"id": job_id, "committed": confirmed,
                             "state": queue.get(job_id)["state"]})
    finally:
        queue.close()
    return outcomes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path("local-data/v06"))
    subs = parser.add_subparsers(dest="command", required=True)
    enqueue = subs.add_parser("enqueue")
    enqueue.add_argument("--id", required=True)
    enqueue.add_argument("--capability", default=CAPABILITY)
    step = subs.add_parser("tick")
    step.add_argument("--max-jobs", type=int, default=1)
    subs.add_parser("status")
    args = parser.parse_args()
    if args.command == "tick":
        result = tick(args.workspace, args.max_jobs)
    else:
        queue = JobQueue(args.workspace / "queue.sqlite3")
        try:
            result = queue.enqueue(args.id, args.capability) if args.command == "enqueue" else queue.list()
        finally:
            queue.close()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

"""Agent Flight Recorder: offline metadata-only fictional event replay.

Only validates supplied event ordering and duplicate/retry identity. It does not
run tools, redact arbitrary untrusted payloads, attest external actions or
authorize operations. Deliberately no event body or secret-bearing fields.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .agentproof import parse_manifest

SCHEMA = "agentflight.events.v1"
REPORT = "agentflight.review.v1"
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,99}\Z")
FIELDS = {"event_id", "job_id", "attempt", "phase"}
TERMINAL = {"SUCCESS", "FAILURE", "CANCELLED"}
PHASES = TERMINAL | {"STARTED"}
MAX_BYTES = 256_000


def fictional_trace(open_attempt: bool = False) -> dict:
    events = [
        {"event_id": "t1", "job_id": "synthetic-lookup", "attempt": 1, "phase": "STARTED"},
        {"event_id": "t1", "job_id": "synthetic-lookup", "attempt": 1, "phase": "STARTED"},
        {"event_id": "t2", "job_id": "synthetic-lookup", "attempt": 1, "phase": "FAILURE"},
        {"event_id": "t3", "job_id": "synthetic-lookup", "attempt": 2, "phase": "STARTED"},
    ]
    if not open_attempt:
        events.append({"event_id": "t4", "job_id": "synthetic-lookup", "attempt": 2, "phase": "SUCCESS"})
    return {"schema": SCHEMA, "events": events}


def _invalid(reason: str) -> dict:
    return {
        "schema": REPORT, "valid_input": False, "requires_review": True,
        "events_applied": 0, "duplicates_ignored": 0,
        "jobs": [], "observations": [], "errors": [reason],
        "scope": "Metadata-only fictional replay; no proof of tool execution or author identity.",
    }


def inspect_trace(document: object) -> dict:
    if type(document) is not dict or set(document) != {"schema", "events"} or document.get("schema") != SCHEMA:
        return _invalid("unsupported document schema or fields")
    events = document["events"]
    if type(events) is not list or not (1 <= len(events) <= 500):
        return _invalid("events must have 1 to 500 records")
    seen: dict[str, dict] = {}
    jobs: dict[str, dict] = {}
    observations: list[dict] = []
    duplicates = 0
    for position, event in enumerate(events, start=1):
        if type(event) is not dict or set(event) != FIELDS:
            return _invalid(f"event {position}: invalid metadata-only fields")
        event_id, job_id = event["event_id"], event["job_id"]
        attempt, phase = event["attempt"], event["phase"]
        if any(type(x) is not str or ID.fullmatch(x) is None for x in (event_id, job_id)):
            return _invalid(f"event {position}: invalid identifier")
        if type(attempt) is not int or not 1 <= attempt <= 30:
            return _invalid(f"event {position}: invalid attempt")
        if type(phase) is not str or phase not in PHASES:
            return _invalid(f"event {position}: invalid phase")
        if event_id in seen:
            if seen[event_id] != event:
                return _invalid(f"event {position}: conflicting event ID")
            duplicates += 1
            continue
        seen[event_id] = event.copy()
        current = jobs.get(job_id)
        if current is None:
            if phase != "STARTED" or attempt != 1:
                return _invalid(f"event {position}: first event must start attempt one")
            jobs[job_id] = {"job_id": job_id, "attempts": 1, "last_phase": "STARTED"}
            continue
        if phase == "STARTED":
            if current["last_phase"] == "STARTED":
                return _invalid(f"event {position}: cannot overlap attempts")
            if attempt != current["attempts"] + 1:
                return _invalid(f"event {position}: non-contiguous retry attempt")
            if current["last_phase"] == "SUCCESS":
                observations.append({"job_id": job_id, "code": "RETRY_AFTER_SUCCESS"})
            current["attempts"] = attempt
            current["last_phase"] = "STARTED"
        else:
            if attempt != current["attempts"] or current["last_phase"] != "STARTED":
                return _invalid(f"event {position}: terminal without matching open attempt")
            current["last_phase"] = phase
    for job in jobs.values():
        if job["last_phase"] == "STARTED":
            observations.append({"job_id": job["job_id"], "code": "MISSING_TERMINAL_RECEIPT"})
    return {
        "schema": REPORT, "valid_input": True,
        "requires_review": bool(observations),
        "events_applied": len(seen), "duplicates_ignored": duplicates,
        "jobs": sorted(jobs.values(), key=lambda x: x["job_id"]),
        "observations": sorted(observations, key=lambda x: (x["job_id"], x["code"])),
        "errors": [],
        "scope": "Metadata-only fictional replay; no proof of tool execution or author identity.",
    }


def _input_document(path: Path) -> object:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("oversized local fixture")
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError("oversized local fixture")
    return parse_manifest(raw.decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline fictional agent flight recorder")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--demo", action="store_true")
    mode.add_argument("--gap-demo", action="store_true")
    mode.add_argument("--input", type=Path)
    args = parser.parse_args()
    try:
        document = (fictional_trace(open_attempt=args.gap_demo)
                    if args.demo or args.gap_demo else _input_document(args.input))
    except (OSError, UnicodeError, ValueError):
        print(json.dumps(_invalid("INPUT_REJECTED"), sort_keys=True, indent=2))
        return 2
    result = inspect_trace(document)
    print(json.dumps(result, sort_keys=True, indent=2))
    return (2 if not result["valid_input"] else 1 if result["requires_review"] else 0)


if __name__ == "__main__":
    raise SystemExit(main())

"""Offline approval-gate event replay with fictional actor claims.

A modeled approval or action report is NEVER real execution authorization,
real identity verification, or evidence that a real command was performed.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .agentproof import parse_manifest

SCHEMA = "agent-review.journal.v1"
REPORT = "agent-review.report.v1"
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,99}\Z")
TYPES = {"REQUESTED", "APPROVED", "DENIED", "REVOKED", "ACTION_REPORTED"}
TERMINAL = {"DENIED", "REVOKED", "ACTION_REPORTED"}


def fictional_events(mode: str = "approved") -> dict:
    events = [
        {"event_id": "r1", "request_id": "demo-request", "sequence": 1,
         "actor": "fictional-requester", "kind": "REQUESTED",
         "scope": "LOCAL_DEMO", "tick": 10},
    ]
    if mode == "pending":
        return {"schema": SCHEMA, "events": events}
    kind = "DENIED" if mode == "denied" else "APPROVED"
    reviewed = {"event_id": "r2", "request_id": "demo-request", "sequence": 2,
                "actor": "fictional-reviewer", "kind": kind,
                "scope": "LOCAL_DEMO", "tick": 20}
    if kind == "APPROVED":
        reviewed["expires_tick"] = 60
    events.append(reviewed)
    if kind == "APPROVED":
        events.append({
            "event_id": "r3", "request_id": "demo-request", "sequence": 3,
            "actor": "fictional-reporter", "kind": "ACTION_REPORTED",
            "scope": "LOCAL_DEMO", "tick": 40,
        })
        events.append(dict(reviewed))
    return {"schema": SCHEMA, "events": events}


def _report(valid: bool, states: dict | None = None, applied: int = 0,
            duplicates: int = 0, errors: list[str] | None = None) -> dict:
    states = states or {}
    pending = [key for key in sorted(states) if states[key]["status"] not in TERMINAL]
    return {
        "schema": REPORT, "valid_input": valid,
        "fully_resolved": valid and not pending,
        "events_applied": applied if valid else 0,
        "duplicates_ignored": duplicates if valid else 0,
        "requests": {key: states[key] for key in sorted(states)} if valid else {},
        "unresolved_request_ids": pending if valid else [],
        "errors": errors or [],
        "execution_authority": "NONE",
        "scope": ("Synthetic claims and policy states only: actor identity is not "
                  "authenticated and ACTION_REPORTED is not evidence of execution."),
    }


def replay(document: object) -> dict:
    if (type(document) is not dict or set(document) != {"schema", "events"}
            or document.get("schema") != SCHEMA):
        return _report(False, errors=["invalid approval journal schema or fields"])
    events = document["events"]
    if type(events) is not list or not (1 <= len(events) <= 10000):
        return _report(False, errors=["events must contain 1 to 10000 entries"])
    requests = {}
    seen = {}
    duplicates = 0
    applied = 0
    for index, event in enumerate(events, 1):
        prefix = "event " + str(index) + ": "
        if type(event) is not dict:
            return _report(False, errors=[prefix + "expected object"])
        kind = event.get("kind")
        if type(kind) is not str or kind not in TYPES:
            return _report(False, errors=[prefix + "unknown transition"])
        required = {"event_id", "request_id", "sequence", "actor", "kind", "scope", "tick"}
        if kind == "APPROVED":
            required.add("expires_tick")
        if set(event) != required:
            return _report(False, errors=[prefix + "missing or unexpected fields"])
        for field in ("event_id", "request_id", "actor", "scope"):
            value = event[field]
            if type(value) is not str or ID.fullmatch(value) is None:
                return _report(False, errors=[prefix + "invalid " + field])
        seq, tick = event["sequence"], event["tick"]
        if type(seq) is not int or not 1 <= seq <= 10000:
            return _report(False, errors=[prefix + "invalid sequence"])
        if type(tick) is not int or not 0 <= tick <= 1000000000:
            return _report(False, errors=[prefix + "invalid tick"])
        if kind == "APPROVED":
            expiry = event["expires_tick"]
            if type(expiry) is not int or not tick < expiry <= tick + 100000:
                return _report(False, errors=[prefix + "invalid expiry"])
        event_id, req_id = event["event_id"], event["request_id"]
        if event_id in seen:
            if seen[event_id] != event:
                return _report(False, errors=[prefix + "conflicting duplicate event ID"])
            duplicates += 1
            continue
        state = requests.get(req_id)
        if state is None:
            if kind != "REQUESTED" or seq != 1:
                return _report(False, errors=[prefix + "request must start at REQUESTED sequence 1"])
            state = {"scope": event["scope"], "requester": event["actor"],
                     "reviewer": None, "status": "PENDING",
                     "last_sequence": seq, "last_tick": tick, "expires_tick": None}
            requests[req_id] = state
        else:
            if event["scope"] != state["scope"]:
                return _report(False, errors=[prefix + "scope changed after request"])
            if seq != state["last_sequence"] + 1 or tick < state["last_tick"]:
                return _report(False, errors=[prefix + "sequence or time regression"])
            if state["status"] in TERMINAL:
                return _report(False, errors=[prefix + "event after terminal decision"])
            if state["status"] == "PENDING":
                if kind not in {"APPROVED", "DENIED"}:
                    return _report(False, errors=[prefix + "independent review required"])
                if event["actor"] == state["requester"]:
                    return _report(False, errors=[prefix + "self review is not allowed"])
                state["reviewer"] = event["actor"]
                if kind == "APPROVED":
                    state["status"] = "APPROVED"
                    state["expires_tick"] = event["expires_tick"]
                else:
                    state["status"] = "DENIED"
            elif state["status"] == "APPROVED":
                if kind not in {"REVOKED", "ACTION_REPORTED"}:
                    return _report(False, errors=[prefix + "unexpected transition after approval"])
                if tick > state["expires_tick"]:
                    return _report(False, errors=[prefix + "approval expired before follow-up"])
                state["status"] = kind
            else:
                return _report(False, errors=[prefix + "unsupported approval state"])
            state["last_sequence"] = seq
            state["last_tick"] = tick
        seen[event_id] = dict(event)
        applied += 1
    return _report(True, states=requests, applied=applied, duplicates=duplicates)


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay fictional agent review decisions offline")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--demo", action="store_true")
    g.add_argument("--pending-demo", action="store_true")
    g.add_argument("--denied-demo", action="store_true")
    g.add_argument("--input", type=Path)
    args = parser.parse_args()
    try:
        if args.demo or args.pending_demo or args.denied_demo:
            data = fictional_events("pending" if args.pending_demo else
                                    ("denied" if args.denied_demo else "approved"))
        else:
            data = parse_manifest(args.input.read_text(encoding="utf-8"))
        result = replay(data)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        result = _report(False, errors=["input rejected: " + str(exc)])
    print(json.dumps(result, sort_keys=True, indent=2))
    return 2 if not result["valid_input"] else (0 if result["fully_resolved"] else 1)


if __name__ == "__main__":
    raise SystemExit(main())

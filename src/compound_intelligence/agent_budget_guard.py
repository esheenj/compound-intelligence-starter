"""Offline synthetic per-agent credit cap admission with duplicate suppression.

This is an educational counter; not billing, provider metering or authorization.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .agentproof import parse_manifest

SCHEMA = "agentbudget.events.v1"
REPORT = "agentbudget.report.v1"
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,99}\Z")


def fictional_events(overrun: bool = False) -> dict:
    return {
        "schema": SCHEMA,
        "limits": {"fictional-agent": 50 if overrun else 100},
        "events": [
            {"event_id": "evt-1", "agent_id": "fictional-agent", "credits": 25},
            {"event_id": "evt-2", "agent_id": "fictional-agent", "credits": 35},
            {"event_id": "evt-2", "agent_id": "fictional-agent", "credits": 35},
        ],
    }


def _report(valid_input: bool, admitted: bool, applied: int = 0, repeated: int = 0, spent: dict | None = None, errors: list[str] | None = None) -> dict:
    return {
        "schema": REPORT, "valid_input": valid_input, "admitted": admitted,
        "events_applied": applied if admitted else 0,
        "duplicates_ignored": repeated if admitted else 0,
        "spent_by_agent": spent if admitted and spent is not None else {},
        "errors": errors or [],
        "scope": "Synthetic integer credit caps; no provider token counting, billing or authenticated execution.",
    }


def assess(document: object) -> dict:
    if type(document) is not dict or set(document) != {"schema", "limits", "events"} or document.get("schema") != SCHEMA:
        return _report(False, False, errors=["invalid usage schema or fields"])
    limits, events = document["limits"], document["events"]
    if type(limits) is not dict or not (1 <= len(limits) <= 1000):
        return _report(False, False, errors=["limits must contain 1 to 1000 agents"])
    for key, value in limits.items():
        if type(key) is not str or ID.fullmatch(key) is None or type(value) is not int or value < 0:
            return _report(False, False, errors=["invalid agent limit"])
    if type(events) is not list or not (1 <= len(events) <= 10000):
        return _report(False, False, errors=["events must contain 1 to 10000 entries"])
    seen = {}
    spent = {agent: 0 for agent in limits}
    repeated = 0
    applied = 0
    for index, event in enumerate(events, 1):
        if type(event) is not dict or set(event) != {"event_id", "agent_id", "credits"}:
            return _report(False, False, errors=["event " + str(index) + ": invalid fields"])
        event_id, agent, amount = event["event_id"], event["agent_id"], event["credits"]
        if type(event_id) is not str or ID.fullmatch(event_id) is None:
            return _report(False, False, errors=["event " + str(index) + ": invalid event_id"])
        if type(agent) is not str or agent not in limits:
            return _report(False, False, errors=["event " + str(index) + ": unknown agent"])
        if type(amount) is not int or amount < 0:
            return _report(False, False, errors=["event " + str(index) + ": invalid credits"])
        if event_id in seen:
            if seen[event_id] != event:
                return _report(False, False, errors=["event " + str(index) + ": conflicting duplicate event_id"])
            repeated += 1
            continue
        if spent[agent] + amount > limits[agent]:
            return _report(True, False, errors=["event " + str(index) + ": synthetic cap exceeded for " + agent])
        spent[agent] += amount
        seen[event_id] = dict(event)
        applied += 1
    return _report(True, True, applied=applied, repeated=repeated, spent={k: spent[k] for k in sorted(spent)})


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline per-agent synthetic credit cap guard")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", action="store_true")
    group.add_argument("--overrun-demo", action="store_true")
    group.add_argument("--input", type=Path)
    args = parser.parse_args()
    try:
        data = (fictional_events(args.overrun_demo) if args.demo or args.overrun_demo
                else parse_manifest(args.input.read_text(encoding="utf-8")))
        report = assess(data)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        report = _report(False, False, errors=["input rejected: " + str(exc)])
    print(json.dumps(report, indent=2, sort_keys=True))
    return 2 if not report["valid_input"] else (0 if report["admitted"] else 1)


if __name__ == "__main__":
    raise SystemExit(main())

"""Offline AgentOps usage journal and task-state replay over fictional events.

This is a deterministic audit *simulation*, not proof that an action happened,
provider billing, a durable transaction store, or any execution authority.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

from .agentproof import parse_manifest

SCHEMA = "agentops.event-journal.v1"
REPORT_SCHEMA = "agentops.replay-report.v1"
IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,99}\Z")
KINDS = {"STARTED", "USAGE", "COMPLETED", "FAILED"}
MAX_EVENTS = 10000


def fictional_journal(*, truncated: bool = False) -> dict:
    """Include a deliberate identical retry; incomplete sample has no terminal."""
    events = [
        {"event_id": "evt-start", "run_id": "fictional-task", "sequence": 1,
         "agent_id": "sample-agent", "kind": "STARTED"},
        {"event_id": "evt-cost", "run_id": "fictional-task", "sequence": 2,
         "agent_id": "sample-agent", "kind": "USAGE", "units": 7},
        {"event_id": "evt-cost", "run_id": "fictional-task", "sequence": 2,
         "agent_id": "sample-agent", "kind": "USAGE", "units": 7},
    ]
    if not truncated:
        events.append({"event_id": "evt-done", "run_id": "fictional-task",
                       "sequence": 3, "agent_id": "sample-agent", "kind": "COMPLETED"})
    return {"schema": SCHEMA, "events": events}


def _report(*, valid: bool, errors: list[str] | None = None,
            runs: dict | None = None, agents: dict | None = None,
            applied: int = 0, repeated: int = 0) -> dict:
    runs = runs or {}
    agents = agents or {}
    incomplete = [key for key in sorted(runs) if runs[key]["status"] == "INCOMPLETE"]
    return {
        "schema": REPORT_SCHEMA,
        "valid_input": valid,
        "fully_reconciled": valid and not incomplete,
        "events_applied": applied if valid else 0,
        "duplicates_ignored": repeated if valid else 0,
        "runs": {key: runs[key] for key in sorted(runs)} if valid else {},
        "units_by_agent": {key: agents[key] for key in sorted(agents)} if valid else {},
        "incomplete_run_ids": incomplete if valid else [],
        "errors": errors or [],
        "scope": ("Fictional event integrity and supplied usage units only; no attested "
                  "producer identity, provider costs, authorized execution or persisted state."),
    }


def replay(document: object) -> dict:
    if (type(document) is not dict
            or set(document) != {"schema", "events"}
            or document.get("schema") != SCHEMA):
        return _report(valid=False, errors=["invalid journal schema or fields"])
    events = document["events"]
    if type(events) is not list or not (1 <= len(events) <= MAX_EVENTS):
        return _report(valid=False, errors=["events must contain 1 to 10000 entries"])
    seen: dict[str, dict] = {}
    runs: dict[str, dict] = {}
    agents: dict[str, int] = {}
    duplicates = 0
    applied = 0
    for index, event in enumerate(events, 1):
        prefix = "event " + str(index) + ": "
        if type(event) is not dict:
            return _report(valid=False, errors=[prefix + "expected an object"])
        kind = event.get("kind")
        if type(kind) is not str or kind not in KINDS:
            return _report(valid=False, errors=[prefix + "unknown event kind"])
        required = {"event_id", "run_id", "sequence", "agent_id", "kind"}
        if kind == "USAGE":
            required.add("units")
        if set(event) != required:
            return _report(valid=False, errors=[prefix + "missing or unexpected fields"])
        for field in ("event_id", "run_id", "agent_id"):
            value = event[field]
            if type(value) is not str or IDENT.fullmatch(value) is None:
                return _report(valid=False, errors=[prefix + "invalid " + field])
        sequence = event["sequence"]
        if type(sequence) is not int or sequence < 1:
            return _report(valid=False, errors=[prefix + "sequence must be positive integer"])
        if kind == "USAGE":
            amount = event["units"]
            if type(amount) is not int or not 1 <= amount <= 1000000000:
                return _report(valid=False, errors=[prefix + "units must be a bounded positive integer"])
        event_id, run_id, agent = event["event_id"], event["run_id"], event["agent_id"]
        if event_id in seen:
            if seen[event_id] != event:
                return _report(valid=False, errors=[prefix + "conflicting duplicate event_id"])
            duplicates += 1
            continue
        run = runs.get(run_id)
        if run is None:
            if kind != "STARTED" or sequence != 1:
                return _report(valid=False, errors=[prefix + "run must begin with STARTED sequence 1"])
            runs[run_id] = {"agent_id": agent, "last_sequence": 1,
                            "status": "INCOMPLETE", "usage_units": 0,
                            "usage_events": 0}
            agents.setdefault(agent, 0)
        else:
            if agent != run["agent_id"]:
                return _report(valid=False, errors=[prefix + "agent_id changed for run"])
            if sequence != run["last_sequence"] + 1:
                return _report(valid=False, errors=[prefix + "sequence gap or conflicting retry"])
            if run["status"] != "INCOMPLETE":
                return _report(valid=False, errors=[prefix + "event after terminal status"])
            if kind == "STARTED":
                return _report(valid=False, errors=[prefix + "second STARTED event"])
            run["last_sequence"] = sequence
            if kind == "USAGE":
                run["usage_units"] += event["units"]
                run["usage_events"] += 1
                agents[agent] += event["units"]
            else:
                run["status"] = kind
        seen[event_id] = dict(event)
        applied += 1
    return _report(valid=True, runs=runs, agents=agents, applied=applied, repeated=duplicates)


def html_report(report: dict) -> str:
    """A script-free, escaped local report, not an online dashboard."""
    title = "AgentOps Replay — Synthetic Event Journal"
    rows = []
    for run_id, run in report["runs"].items():
        rows.append(
            "<tr><td>" + html.escape(run_id) + "</td><td>" +
            html.escape(run["agent_id"]) + "</td><td>" +
            html.escape(run["status"]) + "</td><td>" +
            str(run["usage_units"]) + "</td></tr>"
        )
    summary = ("PASS: fully reconciled" if report["fully_reconciled"]
               else "HOLD: incomplete or invalid")
    errors = ", ".join(report["errors"]) if report["errors"] else "None"
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; "
        "style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">"
        "<title>" + title + "</title>"
        "<style>body{font:1rem/1.5 system-ui,sans-serif;max-width:56rem;margin:2rem auto;"
        "padding:0 1rem;color:#172b32}table{width:100%;border-collapse:collapse}"
        "th,td{padding:.65rem;text-align:left;border-bottom:1px solid #bccbd1}"
        "th{background:#eaf1f2}strong{display:block;margin:1rem 0}</style></head><body>"
        "<main><h1>" + title + "</h1><p>Offline educational output; "
        "not evidence of real-world execution or provider billing.</p><strong>" +
        html.escape(summary) + "</strong><table><thead><tr><th>Run</th>"
        "<th>Agent</th><th>Recorded status</th><th>Supplied usage units</th></tr>"
        "</thead><tbody>" + "".join(rows) + "</tbody></table>"
        "<p>Duplicate receipts ignored: " + str(report["duplicates_ignored"]) + "</p>"
        "<p>Validation errors: " + html.escape(errors) + "</p></main></body></html>"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay supplied fictional AgentOps events")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", action="store_true")
    group.add_argument("--truncated-demo", action="store_true")
    group.add_argument("--input", type=Path)
    parser.add_argument("--html", type=Path, help="Write escaped offline report for valid input")
    args = parser.parse_args()
    try:
        data = (fictional_journal(truncated=args.truncated_demo)
                if args.demo or args.truncated_demo
                else parse_manifest(args.input.read_text(encoding="utf-8")))
        report = replay(data)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        report = _report(valid=False, errors=["input rejected: " + str(exc)])
    if args.html and report["valid_input"]:
        try:
            args.html.write_text(html_report(report), encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            report = _report(valid=False, errors=["report write failed: " + str(exc)])
    print(json.dumps(report, indent=2, sort_keys=True))
    return 2 if not report["valid_input"] else (0 if report["fully_reconciled"] else 1)


if __name__ == "__main__":
    raise SystemExit(main())

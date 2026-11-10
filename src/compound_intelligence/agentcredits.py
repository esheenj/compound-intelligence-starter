"""AgentCredits: deterministic synthetic credit accounting, not money or payments.

An event journal can be replayed without duplicate charges. No exchange,
provider billing, wallet access, database writes or network activity.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SCHEMA = "agentcredits.journal.v1"
REPORT = "agentcredits.replay.v1"
IDENT = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._:-]{0,99}\Z")


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key: " + key)
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("non-finite JSON number: " + value)


def fictional_journal() -> dict:
    return {"schema": SCHEMA, "events": [
        {"event_id": "g1", "account": "demo-team", "op": "grant", "amount": 100},
        {"event_id": "r1", "account": "demo-team", "op": "reserve", "request_id": "demo-run", "amount": 40},
        {"event_id": "r1", "account": "demo-team", "op": "reserve", "request_id": "demo-run", "amount": 40},
        {"event_id": "s1", "account": "demo-team", "op": "settle", "request_id": "demo-run", "amount": 25},
        {"event_id": "f1", "account": "demo-team", "op": "refund", "request_id": "demo-run", "amount": 5},
    ]}


def _valid_ident(value: object) -> bool:
    return type(value) is str and IDENT.fullmatch(value) is not None


def _fail(reason: str, index: int = 0) -> dict:
    return {
        "schema": REPORT,
        "valid": False,
        "events_applied": 0,
        "duplicates_ignored": 0,
        "accounts": {},
        "errors": [("event " + str(index) + ": " if index else "") + reason],
        "scope": "Synthetic non-monetary credits; no real charges or provider reconciliation.",
    }


def replay(journal: object) -> dict:
    if type(journal) is not dict or set(journal) != {"schema", "events"} or journal.get("schema") != SCHEMA:
        return _fail("invalid journal schema or fields")
    events = journal.get("events")
    if type(events) is not list or not (1 <= len(events) <= 10000):
        return _fail("events must contain 1 to 10000 records")
    seen: dict[str, dict] = {}
    accounts: dict[str, dict[str, int]] = {}
    requests: dict[tuple[str, str], dict] = {}
    duplicate_count = 0
    applied = 0
    for index, event in enumerate(events, 1):
        if type(event) is not dict:
            return _fail("event is not an object", index)
        op = event.get("op")
        required = {"event_id", "account", "op", "amount"}
        if op in {"reserve", "settle", "refund"}:
            required.add("request_id")
        if type(op) is not str or op not in {"grant", "reserve", "settle", "refund"} or set(event) != required:
            return _fail("unknown operation or fields", index)
        event_id, account, amount = event["event_id"], event["account"], event["amount"]
        if not _valid_ident(event_id) or not _valid_ident(account):
            return _fail("invalid event_id or account", index)
        if type(amount) is not int or amount < 0 or (op != "settle" and amount == 0):
            return _fail("amount must be an allowed non-negative integer", index)
        if op != "grant" and not _valid_ident(event["request_id"]):
            return _fail("invalid request_id", index)
        if event_id in seen:
            if seen[event_id] != event:
                return _fail("conflicting duplicate event_id", index)
            duplicate_count += 1
            continue
        state = accounts.setdefault(account, {"available": 0, "held": 0, "spent": 0})
        key = (account, event["request_id"]) if op != "grant" else None
        if op == "grant":
            state["available"] += amount
        elif op == "reserve":
            if key in requests:
                return _fail("request_id already reserved", index)
            if amount > state["available"]:
                return _fail("insufficient available credits", index)
            state["available"] -= amount
            state["held"] += amount
            requests[key] = {"reserved": amount, "settled": None, "refunded": 0}
        elif op == "settle":
            reservation = requests.get(key)
            if reservation is None or reservation["settled"] is not None:
                return _fail("missing or already settled reservation", index)
            if amount > reservation["reserved"]:
                return _fail("settlement exceeds reservation", index)
            state["held"] -= reservation["reserved"]
            state["available"] += reservation["reserved"] - amount
            state["spent"] += amount
            reservation["settled"] = amount
        else:
            reservation = requests.get(key)
            if reservation is None or reservation["settled"] is None:
                return _fail("refund requires a settled request", index)
            if amount > reservation["settled"] - reservation["refunded"]:
                return _fail("refund exceeds unrefunded settlement", index)
            state["spent"] -= amount
            state["available"] += amount
            reservation["refunded"] += amount
        seen[event_id] = dict(event)
        applied += 1
    return {
        "schema": REPORT,
        "valid": True,
        "events_applied": applied,
        "duplicates_ignored": duplicate_count,
        "accounts": {key: accounts[key] for key in sorted(accounts)},
        "errors": [],
        "scope": "Synthetic non-monetary credits; no real charges or provider reconciliation.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline, idempotent synthetic AI credit ledger")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", action="store_true")
    group.add_argument("--input", type=Path)
    args = parser.parse_args()
    try:
        journal = fictional_journal() if args.demo else json.loads(args.input.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)
        report = replay(journal)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        report = _fail("input rejected: " + str(exc))
        print(json.dumps(report, indent=2, sort_keys=True))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

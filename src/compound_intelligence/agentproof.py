"""AgentProof: offline receipt structure and payload-integrity verification.

This cannot establish that an AI claim, producer identity, or action is truthful.
No network, exchange, agent execution, signature verification, or secrets.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
from pathlib import Path

MANIFEST_SCHEMA = "agentproof.receipts.v1"
REPORT_SCHEMA = "agentproof.validation.v1"
ID_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._:-]{0,99}\Z")
SHA_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
FIELDS = {"sequence", "event_id", "status", "claimed_producer", "payload", "payload_sha256"}
STATES = {"CREATED", "ACCEPTED", "COMPLETED", "REJECTED"}


def canonical_bytes(value: object) -> bytes:
    """Deterministic UTF-8 JSON encoding; rejects NaN and infinity."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def payload_digest(payload: object) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    output = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("duplicate JSON object key: " + key)
        output[key] = value
    return output


def _reject_constant(value: str) -> None:
    raise ValueError("non-finite JSON number: " + value)


def parse_manifest(text: str) -> object:
    return json.loads(text, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)


def fictional_manifest() -> dict:
    samples = [
        ("example-1", "CREATED", {"task": "fictional-document-check"}),
        ("example-2", "ACCEPTED", {"test": "synthetic-input", "passed": True}),
        ("example-3", "COMPLETED", {"receipt": "demo-only", "count": 2}),
    ]
    events = []
    for sequence, (event_id, status, payload) in enumerate(samples, start=1):
        events.append({
            "sequence": sequence,
            "event_id": event_id,
            "status": status,
            "claimed_producer": "fictional-agent",
            "payload": payload,
            "payload_sha256": payload_digest(payload),
        })
    return {"schema": MANIFEST_SCHEMA, "events": events}


def verify_manifest(manifest: object) -> dict:
    errors: list[str] = []
    events_checked = 0
    if type(manifest) is not dict:
        errors.append("manifest must be an object")
        return _report(errors, events_checked)
    if set(manifest) != {"schema", "events"}:
        errors.append("manifest fields must be schema and events")
    if manifest.get("schema") != MANIFEST_SCHEMA:
        errors.append("unsupported manifest schema")
    events = manifest.get("events")
    if type(events) is not list or not (1 <= len(events) <= 10000):
        errors.append("events must contain 1 to 10000 records")
        return _report(errors, events_checked)
    seen: set[str] = set()
    for index, event in enumerate(events, start=1):
        events_checked += 1
        prefix = "event " + str(index) + ": "
        if type(event) is not dict:
            errors.append(prefix + "expected an object")
            continue
        if set(event) != FIELDS:
            errors.append(prefix + "missing or unexpected fields")
        if type(event.get("sequence")) is not int or event.get("sequence") != index:
            errors.append(prefix + "non-contiguous sequence")
        event_id = event.get("event_id")
        if type(event_id) is not str or ID_PATTERN.fullmatch(event_id) is None:
            errors.append(prefix + "invalid event_id")
        elif event_id in seen:
            errors.append(prefix + "duplicate event_id")
        else:
            seen.add(event_id)
        if event.get("status") not in STATES:
            errors.append(prefix + "invalid status")
        producer = event.get("claimed_producer")
        if type(producer) is not str or ID_PATTERN.fullmatch(producer) is None:
            errors.append(prefix + "invalid or missing claimed_producer")
        payload = event.get("payload")
        digest = event.get("payload_sha256")
        if type(payload) is not dict:
            errors.append(prefix + "payload must be an object")
        if type(digest) is not str or SHA_PATTERN.fullmatch(digest) is None:
            errors.append(prefix + "invalid payload_sha256")
        if type(payload) is dict and type(digest) is str and SHA_PATTERN.fullmatch(digest):
            try:
                if not hmac.compare_digest(payload_digest(payload), digest):
                    errors.append(prefix + "payload digest mismatch")
            except (TypeError, ValueError):
                errors.append(prefix + "payload contains invalid JSON values")
    return _report(errors, events_checked)


def _report(errors: list[str], checked: int) -> dict:
    return {
        "schema": REPORT_SCHEMA,
        "integrity_valid": not errors,
        "events_checked": checked,
        "errors": errors,
        "scope": "Structural and payload-hash checks only; no proof of truth, authorization or producer identity.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline fictional AI receipt verifier")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", action="store_true", help="Validate built-in fictional receipts")
    group.add_argument("--input", type=Path, help="Read a JSON manifest locally")
    args = parser.parse_args()
    try:
        manifest = fictional_manifest() if args.demo else parse_manifest(args.input.read_text(encoding="utf-8"))
        report = verify_manifest(manifest)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        report = _report(["input rejected: " + str(exc)], 0)
        print(json.dumps(report, sort_keys=True, indent=2))
        return 2
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["integrity_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Offline agent identity claim consistency, scope and replay diagnostics.

A matching registry claim or SHA-256 checksum does NOT authenticate an agent.
No cryptographic signatures, private keys, real endpoints, execution or trust
issuer are used. All data in the public fixture is fictional.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path

from .agentproof import canonical_bytes, parse_manifest

SCHEMA = "agent-trust-claims.v1"
REPORT = "agent-trust-review.v1"
IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,79}\Z")
ORIGIN = re.compile(r"https://[a-z0-9][a-z0-9.-]{0,140}(/[a-zA-Z0-9._/-]{0,80})?\Z")
DIGEST = re.compile(r"[a-f0-9]{64}\Z")
MAX_BYTES = 65536
MAX_AGENTS = 50
MAX_CLAIMS = 150


def _exact(value: object, keys: set[str], where: str) -> dict:
    if type(value) is not dict or set(value) != keys:
        raise ValueError(where + ": invalid fields")
    return value


def _id(value: object, where: str) -> str:
    if type(value) is not str or not IDENT.fullmatch(value):
        raise ValueError(where + ": invalid identifier")
    return value


def _origin(value: object) -> str:
    if type(value) is not str or not ORIGIN.fullmatch(value):
        raise ValueError("invalid fictional HTTPS origin")
    return value


def _hash(value: object) -> str:
    if type(value) is not str or not DIGEST.fullmatch(value):
        raise ValueError("digest must be 64 lowercase hexadecimal characters")
    return value


def _tick(value: object) -> int:
    if type(value) is not int or not 0 <= value <= 2_000_000_000:
        raise ValueError("tick must be an integer from 0 to 2000000000")
    return value


def _rev(value: object) -> int:
    if type(value) is not int or not 1 <= value <= 999999:
        raise ValueError("registry revision must be a positive bounded integer")
    return value


def _array(value: object, low: int, high: int, label: str) -> list:
    if type(value) is not list or not low <= len(value) <= high:
        raise ValueError(label + ": invalid count")
    return value


CLAIM_FIELDS = {"claim_id", "agent_id", "origin", "key_fingerprint",
                "capability", "registry_revision", "nonce", "issued_tick",
                "expires_tick", "proof_claim", "payload_sha256"}


def claim_digest(value: dict) -> str:
    """Checksum of canonical public fields, not a proof of private key control."""
    return hashlib.sha256(canonical_bytes({k: v for k, v in value.items()
                                           if k != "payload_sha256"})).hexdigest()


def validate(document: object) -> tuple[dict[str, dict], list[dict], int]:
    _exact(document, {"schema", "evaluation_tick", "registry", "claims"}, "document")
    if document["schema"] != SCHEMA:
        raise ValueError("unsupported agent-trust schema")
    if len(canonical_bytes(document)) > MAX_BYTES:
        raise ValueError("document exceeds 64 KiB")
    now = _tick(document["evaluation_tick"])
    registry = {}
    for row in _array(document["registry"], 1, MAX_AGENTS, "registry"):
        _exact(row, {"agent_id", "origin", "key_fingerprint", "revision",
                     "state", "capabilities"}, "registry entry")
        aid = _id(row["agent_id"], "registry agent")
        if aid in registry:
            raise ValueError("duplicate registry agent")
        _origin(row["origin"])
        _hash(row["key_fingerprint"])
        _rev(row["revision"])
        if type(row["state"]) is not str or row["state"] not in {"ACTIVE", "REVOKED"}:
            raise ValueError("invalid registry state")
        capabilities = [_id(x, "registered capability") for x in
                        _array(row["capabilities"], 1, 16, "registered capabilities")]
        if len(set(capabilities)) != len(capabilities):
            raise ValueError("duplicate registered capability")
        registry[aid] = row
    claims = _array(document["claims"], 1, MAX_CLAIMS, "claims")
    seen = set()
    for row in claims:
        _exact(row, CLAIM_FIELDS, "claim")
        cid = _id(row["claim_id"], "claim_id")
        if cid in seen:
            raise ValueError("duplicate claim ID")
        seen.add(cid)
        _id(row["agent_id"], "claimed agent")
        _origin(row["origin"])
        _hash(row["key_fingerprint"])
        _id(row["capability"], "claimed capability")
        _rev(row["registry_revision"])
        _id(row["nonce"], "nonce")
        issued, expiry = _tick(row["issued_tick"]), _tick(row["expires_tick"])
        if expiry < issued:
            raise ValueError("claim expiry precedes issue tick")
        if type(row["proof_claim"]) is not str or row["proof_claim"] not in {"ABSENT", "SELF_REPORTED_SIGNED"}:
            raise ValueError("invalid proof declaration")
        _hash(row["payload_sha256"])
    return registry, claims, now


def inspect(document: object) -> dict:
    registry, claims, now = validate(document)
    counts = Counter((x["agent_id"], x["nonce"]) for x in claims)
    records = []
    for row in claims:
        reg = registry.get(row["agent_id"])
        problems = set()
        if reg is None:
            problems.add("UNKNOWN_AGENT")
        else:
            if reg["state"] == "REVOKED":
                problems.add("REVOKED_REGISTRATION")
            if row["origin"] != reg["origin"]:
                problems.add("ORIGIN_MISMATCH")
            if row["key_fingerprint"] != reg["key_fingerprint"]:
                problems.add("KEY_FINGERPRINT_MISMATCH")
            if row["registry_revision"] != reg["revision"]:
                problems.add("STALE_REGISTRY_REVISION")
            if row["capability"] not in reg["capabilities"]:
                problems.add("CAPABILITY_NOT_DECLARED")
        if counts[(row["agent_id"], row["nonce"])] > 1:
            problems.add("REPLAYED_NONCE")
        if row["issued_tick"] > now:
            problems.add("NOT_YET_VALID")
        if row["expires_tick"] < now:
            problems.add("EXPIRED_CLAIM")
        checksum_matches = (row["payload_sha256"] == claim_digest(row))
        if not checksum_matches:
            problems.add("CHECKSUM_MISMATCH")
        # Deliberately do not infer identity from an asserted signature label.
        gate = "HOLD" if problems else "CLAIM_MATCH_ONLY"
        records.append({
            "claim_id": row["claim_id"], "agent_id": row["agent_id"],
            "capability": row["capability"], "gate": gate, "reasons": sorted(problems),
            "registration_found": reg is not None,
            "registration_state": reg["state"] if reg is not None else None,
            "claimed_proof": row["proof_claim"],
            "cryptographic_signature_verified": False,
            "checksum_matches": checksum_matches,
            "identity_authenticated": False, "execution_authority": "NONE",
        })
    records.sort(key=lambda x: x["claim_id"])
    held = sum(x["gate"] == "HOLD" for x in records)
    return {
        "schema": REPORT, "status": "DIAGNOSTIC_ONLY_NO_IDENTITY_AUTHENTICATION",
        "origin": "SYNTHETIC_OR_CALLER_SUPPLIED",
        "input_sha256": hashlib.sha256(canonical_bytes(document)).hexdigest(),
        "claims_checked": len(records), "held": held,
        "claim_matches_only": len(records) - held,
        "records": records, "identity_authenticated": False,
        "execution_authority": "NONE",
        "scope": ("Comparing caller-supplied registry and identity claims is NOT real "
                  "authentication. SHA-256 proves only that these supplied bytes match "
                  "a supplied checksum, not key possession or signature validity. "
                  "Revocation, origin, capability and tick states are fictional or "
                  "caller-declared; real issuer registries and trust roots are absent."),
    }


def fixture() -> dict:
    a = {"agent_id": "fictional-a", "origin": "https://example.invalid/agent-a",
         "key_fingerprint": "a" * 64, "revision": 2, "state": "ACTIVE",
         "capabilities": ["summarize", "search"]}
    revoked = {"agent_id": "fictional-revoked", "origin": "https://example.invalid/revoked",
               "key_fingerprint": "b" * 64, "revision": 3, "state": "REVOKED",
               "capabilities": ["summarize"]}
    def make(cid: str, agent: dict = a, **changes: object) -> dict:
        row = {"claim_id": cid, "agent_id": agent["agent_id"], "origin": agent["origin"],
               "key_fingerprint": agent["key_fingerprint"],
               "capability": "summarize", "registry_revision": agent["revision"],
               "nonce": cid, "issued_tick": 90, "expires_tick": 110,
               "proof_claim": "SELF_REPORTED_SIGNED"}
        row.update(changes)
        row["payload_sha256"] = claim_digest(row)
        return row

    claims = [
        make("matching-claim"),
        make("revoked-agent", revoked),
        make("unknown-agent", agent_id="unregistered"),
        make("wrong-origin", origin="https://elsewhere.invalid/agent"),
        make("wrong-key", key_fingerprint="c" * 64),
        make("capability-escalation", capability="payments"),
        make("stale-registry", registry_revision=1),
        make("nonce-replay-first", nonce="reused-challenge"),
        make("nonce-replay-second", nonce="reused-challenge"),
        make("expired", issued_tick=10, expires_tick=20),
        make("checksum-tamper"),
    ]
    claims[-1]["capability"] = "search"  # do NOT recompute its old checksum
    return {"schema": SCHEMA, "evaluation_tick": 100,
            "registry": [a, revoked], "claims": claims}


def render_html(result: dict) -> str:
    lines = []
    for rec in result["records"]:
        values = [rec["claim_id"], rec["agent_id"], rec["gate"],
                  ", ".join(rec["reasons"]) or "no declared mismatch",
                  "yes" if rec["checksum_matches"] else "no", "NO"]
        lines.append("<tr>" + "".join("<td>" + html.escape(str(x), quote=True) +
                                      "</td>" for x in values) + "</tr>")
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
            'style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
            '<title>Agent Trust Claim Diagnostics</title><style>'
            'body{font:1rem/1.55 system-ui,sans-serif;max-width:70rem;margin:2rem auto;'
            'padding:0 1rem}.scroll{overflow-x:auto}table{width:100%;'
            'border-collapse:collapse}td,th{border-bottom:1px solid #888;'
            'padding:.6rem;text-align:left}</style></head><body><main>'
            '<h1>Fictional Agent Trust Claim Diagnostics</h1>'
            '<p>No identity is authenticated, no signatures are verified and '
            'no action is authorized. Source metadata is caller-supplied.</p>'
            '<div class="scroll"><table><caption>Claim consistency</caption>'
            '<thead><tr><th>Claim</th><th>Declared agent</th><th>Gate</th>'
            '<th>Reason</th><th>Checksum matches</th><th>Identity proven</th>'
            '</tr></thead><tbody>' + "".join(lines) + '</tbody></table></div>'
            '</main></body></html>')


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    inputs = p.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--demo", action="store_true")
    inputs.add_argument("--input", type=Path)
    p.add_argument("--html", type=Path)
    args = p.parse_args()
    try:
        if args.demo:
            data = fixture()
        else:
            if args.input.stat().st_size > MAX_BYTES:
                raise ValueError("document exceeds 64 KiB")
            data = parse_manifest(args.input.read_text(encoding="utf-8"))
        result = inspect(data)
        if args.html:
            args.html.write_text(render_html(result), encoding="utf-8")
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        print(json.dumps({"schema": REPORT, "status": "REJECTED",
                          "error": type(exc).__name__ + ": " + str(exc)[:120]}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

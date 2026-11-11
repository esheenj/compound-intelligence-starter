"""Falsifiable offline checkpoint preservation probe, using entirely supplied text.

This is an exact-field/evidence-status comparator, not semantic similarity,
AI inference, training, authenticated provenance or execution authority.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path

from .agentproof import parse_manifest
from .engine import canonical

SCHEMA = "context-preservation.v1"
REPORT = "context-preservation-report.v1"
IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,79}\Z")
MAX_DOCUMENT_BYTES = 65536
MAX_FACTS = 100
MAX_CANDIDATES = 10
EVIDENCE = {"DECLARED_VERIFIED", "HYPOTHESIS"}
IMPORTANCE = {"CRITICAL", "SUPPORTING"}


def _sha(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _exact(value: object, keys: set[str], label: str) -> dict:
    if type(value) is not dict or set(value) != keys:
        raise ValueError(label + ": invalid fields")
    return value


def _name(value: object, label: str) -> str:
    if type(value) is not str or IDENT.fullmatch(value) is None:
        raise ValueError(label + ": invalid identifier")
    return value


def _value(value: object) -> str:
    if type(value) is not str or not 1 <= len(value) <= 240 or not value.strip() or "\x00" in value:
        raise ValueError("fact value must be 1-240 printable characters")
    # Reject surrogate code points even though canonical JSON could escape them.
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ValueError("invalid Unicode in fact value") from exc
    return value


def _version(value: object) -> int:
    if type(value) is not int or not 1 <= value <= 999999:
        raise ValueError("source version must be an integer from 1 to 999999")
    return value


def _bounded(value: object, limit: int, label: str) -> list:
    if type(value) is not list or not 1 <= len(value) <= limit:
        raise ValueError(label + ": invalid count")
    return value


def validate(document: object) -> tuple[dict, dict[str, dict], list[tuple[str, dict[str, dict]]]]:
    _exact(document, {"schema", "source", "candidates"}, "document")
    if document["schema"] != SCHEMA:
        raise ValueError("unsupported context-preservation schema")
    if len(canonical(document).encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise ValueError("document exceeds 64 KiB")
    source = _exact(document["source"], {"source_id", "version", "facts"}, "source")
    _name(source["source_id"], "source_id")
    _version(source["version"])
    facts = {}
    for entry in _bounded(source["facts"], MAX_FACTS, "facts"):
        _exact(entry, {"fact_id", "value", "source_ref", "importance", "evidence_status"}, "fact")
        fid = _name(entry["fact_id"], "fact_id")
        if fid in facts:
            raise ValueError("duplicate source fact ID")
        _value(entry["value"])
        _name(entry["source_ref"], "source_ref")
        if type(entry["importance"]) is not str or entry["importance"] not in IMPORTANCE:
            raise ValueError("invalid importance")
        if type(entry["evidence_status"]) is not str or entry["evidence_status"] not in EVIDENCE:
            raise ValueError("invalid evidence status")
        facts[fid] = entry
    candidates = []
    seen = set()
    for candidate in _bounded(document["candidates"], MAX_CANDIDATES, "candidates"):
        _exact(candidate, {"candidate_id", "entries"}, "candidate")
        cid = _name(candidate["candidate_id"], "candidate_id")
        if cid in seen:
            raise ValueError("duplicate candidate ID")
        seen.add(cid)
        entries = {}
        for entry in _bounded(candidate["entries"], MAX_FACTS, "entries"):
            _exact(entry, {"fact_id", "value", "source_ref", "source_version",
                           "evidence_status"}, "checkpoint entry")
            fid = _name(entry["fact_id"], "checkpoint fact_id")
            if fid in entries:
                raise ValueError("duplicate checkpoint fact ID")
            _value(entry["value"])
            _name(entry["source_ref"], "checkpoint source_ref")
            _version(entry["source_version"])
            if type(entry["evidence_status"]) is not str or entry["evidence_status"] not in EVIDENCE:
                raise ValueError("invalid checkpoint evidence status")
            entries[fid] = entry
        candidates.append((cid, entries))
    return source, facts, candidates


def _diagnose(fact: dict, entry: dict | None, version: int) -> str:
    if entry is None:
        return "MISSING"
    if entry["source_version"] != version:
        return "STALE_VERSION"
    if entry["value"] != fact["value"]:
        return "CONTRADICTED_VALUE"
    if entry["source_ref"] != fact["source_ref"]:
        return "PROVENANCE_DRIFT"
    if entry["evidence_status"] != fact["evidence_status"]:
        return "EVIDENCE_STATUS_DRIFT"
    return "RETAINED"


def evaluate(document: object) -> dict:
    """Compare candidate handovers to a reference held outside each checkpoint.

    No status/identity can be self-attested by a candidate. An exact match
    measures text retention, never truth, generalization or model performance.
    """
    source, facts, candidates = validate(document)
    total_critical = sum(f["importance"] == "CRITICAL" for f in facts.values())
    baseline_bytes = len(canonical(source["facts"]).encode("utf-8"))
    results = []
    for cid, entries in candidates:
        observations = []
        counts = {x: 0 for x in ("RETAINED", "MISSING", "STALE_VERSION",
                                  "CONTRADICTED_VALUE", "PROVENANCE_DRIFT",
                                  "EVIDENCE_STATUS_DRIFT", "UNSUPPORTED")}
        critical_retained = 0
        for fid in sorted(facts):
            fact = facts[fid]
            status = _diagnose(fact, entries.get(fid), source["version"])
            counts[status] += 1
            if status == "RETAINED" and fact["importance"] == "CRITICAL":
                critical_retained += 1
            observations.append({"fact_id": fid, "importance": fact["importance"],
                                 "evidence_status": fact["evidence_status"], "outcome": status})
        for fid in sorted(set(entries) - set(facts)):
            counts["UNSUPPORTED"] += 1
            observations.append({"fact_id": fid, "importance": "UNKNOWN",
                                 "evidence_status": "UNSUPPORTED", "outcome": "UNSUPPORTED"})
        unsafe = sum(counts[key] for key in ("STALE_VERSION", "CONTRADICTED_VALUE",
                      "PROVENANCE_DRIFT", "EVIDENCE_STATUS_DRIFT", "UNSUPPORTED"))
        complete_critical = critical_retained == total_critical
        state = ("HOLD" if unsafe or not complete_critical else
                 "PASS_LOSSLESS" if counts["MISSING"] == 0 else "PASS_CRITICAL_ONLY")
        payload_bytes = len(canonical([entries[k] for k in sorted(entries)]).encode("utf-8"))
        results.append({
            "candidate_id": cid, "state": state,
            "source_fact_count": len(facts), "critical_total": total_critical,
            "critical_retained": critical_retained,
            "counts": counts,
            "checkpoint_bytes": payload_bytes,
            "source_facts_bytes": baseline_bytes,
            "source_minus_checkpoint_bytes": baseline_bytes - payload_bytes,
            "observations": observations,
        })
    results.sort(key=lambda x: x["candidate_id"])
    return {
        "schema": REPORT, "source_id": source["source_id"], "source_version": source["version"],
        "source_sha256": _sha(source), "input_sha256": _sha(document),
        "origin": "SYNTHETIC_OR_CALLER_SUPPLIED",
        "status": "BENCHMARKED_NOT_PROMOTED", "candidates": results,
        "scope": ("Exact synthetic fact, declared-provenance and evidence-status retention only. "
                  "No real source authentication, semantic understanding, model inference, "
                  "learning, token count, identity attestation or execution authority."),
    }


def fixture() -> dict:
    facts = [
        ("execution", "execution_authority=NONE", "synthetic:gate", "CRITICAL", "DECLARED_VERIFIED"),
        ("spend", "additional_recurring_spend=R0", "synthetic:budget", "CRITICAL", "DECLARED_VERIFIED"),
        ("source", "public_source_revision=fixture-v2", "synthetic:source", "CRITICAL", "DECLARED_VERIFIED"),
        ("safety", "exchange_order_writes=DISABLED", "synthetic:order-boundary", "CRITICAL", "DECLARED_VERIFIED"),
        ("product", "public_tool=offline_demo_only", "synthetic:product", "SUPPORTING", "DECLARED_VERIFIED"),
        ("next", "next_step=independent_browser_acceptance", "synthetic:check", "SUPPORTING", "DECLARED_VERIFIED"),
        ("growth", "offline_usage_may_grow", "synthetic:hypothesis", "SUPPORTING", "HYPOTHESIS"),
    ]
    source = {"source_id": "fictional-public-project", "version": 2,
              "facts": [{"fact_id": fid, "value": value, "source_ref": ref,
                         "importance": importance, "evidence_status": status}
                        for fid, value, ref, importance, status in facts]}

    def carry(ids: list[str]) -> list[dict]:
        by_id = {fact["fact_id"]: fact for fact in source["facts"]}
        return [{"fact_id": key, "value": by_id[key]["value"],
                 "source_ref": by_id[key]["source_ref"],
                 "source_version": source["version"],
                 "evidence_status": by_id[key]["evidence_status"]} for key in ids]

    good = carry([x[0] for x in facts])
    brief = carry(["execution", "product", "next"])
    drifted = carry([x[0] for x in facts])
    for entry in drifted:
        if entry["fact_id"] == "spend":
            entry["source_version"] = 1
        if entry["fact_id"] == "safety":
            entry["value"] = "exchange_order_writes=ENABLED"
        if entry["fact_id"] == "growth":
            entry["evidence_status"] = "DECLARED_VERIFIED"
    drifted.append({"fact_id": "invented-capability", "value": "can_execute_trades",
                    "source_ref": "synthetic:untrusted", "source_version": 2,
                    "evidence_status": "DECLARED_VERIFIED"})
    return {"schema": SCHEMA, "source": source,
            "candidates": [
                {"candidate_id": "brief-chat", "entries": brief},
                {"candidate_id": "evidence-checkpoint", "entries": good},
                {"candidate_id": "unsafe-drift", "entries": drifted},
            ]}


def render_html(report: dict) -> str:
    """Script-free, escaped offline report; no remote resources or active HTML."""
    rows = []
    for candidate in report["candidates"]:
        values = [candidate["candidate_id"], candidate["state"],
                  str(candidate["critical_retained"]) + "/" + str(candidate["critical_total"]),
                  candidate["counts"]["MISSING"], candidate["counts"]["CONTRADICTED_VALUE"],
                  candidate["counts"]["STALE_VERSION"], candidate["counts"]["UNSUPPORTED"]]
        rows.append("<tr>" + "".join("<td>" + html.escape(str(v), quote=True) + "</td>"
                                     for v in values) + "</tr>")
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
            'style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
            '<title>Context Preservation Benchmark</title><style>'
            'body{font:1rem/1.55 system-ui,sans-serif;max-width:70rem;margin:2rem auto;padding:0 1rem}'
            'table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #888;'
            'padding:.65rem;text-align:left}.scroll{overflow-x:auto}</style></head><body><main>'
            '<h1>Fictional AI handover preservation check</h1>'
            '<p>Exact-field, source-version and evidence-label retention only. '
            'No AI inference, semantic equivalence, proof of truth or actual authority.</p>'
            '<div class="scroll"><table><caption>Candidate checkpoint diagnostics</caption>'
            '<thead><tr><th>Checkpoint</th><th>Gate</th><th>Critical retained</th>'
            '<th>Missing</th><th>Contradicted</th><th>Stale</th><th>Unsupported</th>'
            '</tr></thead><tbody>' + "".join(rows) +
            '</tbody></table></div></main></body></html>')


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline exact-field checkpoint loss benchmark")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", action="store_true")
    group.add_argument("--input", type=Path)
    parser.add_argument("--html", type=Path, help="optional script-free local report path")
    options = parser.parse_args()
    try:
        if options.demo:
            doc = fixture()
        else:
            if options.input.stat().st_size > MAX_DOCUMENT_BYTES:
                raise ValueError("input exceeds 64 KiB")
            doc = parse_manifest(options.input.read_text(encoding="utf-8"))
        result = evaluate(doc)
        if options.html:
            options.html.write_text(render_html(result), encoding="utf-8")
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": REPORT, "status": "REJECTED",
                          "error": type(exc).__name__ + ": " + str(exc)[:120]}))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

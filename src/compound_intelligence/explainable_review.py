"""Offline explanation/review triage from untrusted fictional evidence.

Neither source labels, supplied sample scores nor reviewer-state labels grant
execution authority. No model inference, external requests or automation.
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

SCHEMA = "explainable-review.fixtures.v1"
REPORT = "explainable-review.report.v1"
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,79}\Z")
MAX_BYTES = 65536
SOURCE_LIMIT = 100
DECISION_LIMIT = 50
STATUSES = {"DECLARED_VERIFIED", "HYPOTHESIS"}
IMPACTS = {"LOW", "HIGH"}
REVIEWS = {"PENDING", "RECORDED_APPROVE", "RECORDED_REJECT"}
CONFIDENCE = {"NONE", "SELF_REPORTED_SAMPLE"}


def _fields(value: object, expected: set[str], label: str) -> dict:
    if type(value) is not dict or set(value) != expected:
        raise ValueError(label + ": invalid fields")
    return value


def _id(value: object, label: str) -> str:
    if type(value) is not str or ID.fullmatch(value) is None:
        raise ValueError(label + ": invalid identifier")
    return value


def _text(value: object, label: str, maxlen: int = 240) -> str:
    if type(value) is not str or not 1 <= len(value) <= maxlen or not value.strip() or "\x00" in value:
        raise ValueError(label + ": invalid text")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(label + ": invalid Unicode") from exc
    return value


def _revision(value: object) -> int:
    if type(value) is not int or not 1 <= value <= 999999:
        raise ValueError("revision must be an integer from 1 to 999999")
    return value


def _list(value: object, low: int, high: int, label: str) -> list:
    if type(value) is not list or not low <= len(value) <= high:
        raise ValueError(label + ": invalid count")
    return value


def validate(doc: object) -> tuple[dict[str, dict], list[dict]]:
    _fields(doc, {"schema", "sources", "decisions"}, "document")
    if doc["schema"] != SCHEMA:
        raise ValueError("unsupported explainable review schema")
    if len(canonical(doc).encode("utf-8")) > MAX_BYTES:
        raise ValueError("document exceeds 64 KiB")
    sources = {}
    for source in _list(doc["sources"], 1, SOURCE_LIMIT, "sources"):
        _fields(source, {"source_id", "statement", "revision", "evidence_status"}, "source")
        sid = _id(source["source_id"], "source_id")
        if sid in sources:
            raise ValueError("duplicate source ID")
        _text(source["statement"], "source statement")
        _revision(source["revision"])
        if type(source["evidence_status"]) is not str or source["evidence_status"] not in STATUSES:
            raise ValueError("invalid declared evidence status")
        sources[sid] = source
    decisions = _list(doc["decisions"], 1, DECISION_LIMIT, "decisions")
    seen_decisions = set()
    for decision in decisions:
        _fields(decision, {"decision_id", "action", "impact", "support", "oppose",
                           "confidence", "review"}, "decision")
        did = _id(decision["decision_id"], "decision_id")
        if did in seen_decisions:
            raise ValueError("duplicate decision ID")
        seen_decisions.add(did)
        _text(decision["action"], "fictional proposed action")
        if type(decision["impact"]) is not str or decision["impact"] not in IMPACTS:
            raise ValueError("unsupported impact")
        if type(decision["review"]) is not str or decision["review"] not in REVIEWS:
            raise ValueError("invalid reviewer state")
        seen_refs = set()
        for label in ("support", "oppose"):
            for ref in _list(decision[label], 0, SOURCE_LIMIT, label):
                _fields(ref, {"source_id", "revision"}, label + " reference")
                sid = _id(ref["source_id"], label + " source ID")
                _revision(ref["revision"])
                if sid in seen_refs:
                    raise ValueError("duplicate or contradictory source reference")
                seen_refs.add(sid)
        confidence = _fields(decision["confidence"], {"method", "correct", "cases"}, "confidence")
        if type(confidence["method"]) is not str or confidence["method"] not in CONFIDENCE:
            raise ValueError("invalid confidence method")
        if confidence["method"] == "NONE":
            if confidence["correct"] is not None or confidence["cases"] is not None:
                raise ValueError("no-method confidence must not carry numerical results")
        else:
            n, k = confidence["cases"], confidence["correct"]
            if type(n) is not int or not 1 <= n <= 10000 or type(k) is not int or not 0 <= k <= n:
                raise ValueError("invalid self-reported sample counts")
    return sources, decisions


def inspect(doc: object) -> dict:
    sources, decisions = validate(doc)
    results = []
    for d in decisions:
        reasons = set()
        resolved = []
        if not d["support"]:
            reasons.add("NO_SUPPORT")
        if d["oppose"]:
            reasons.add("OPPOSING_EVIDENCE")
        for stance in ("support", "oppose"):
            for ref in d[stance]:
                sid = ref["source_id"]
                known = sources.get(sid)
                if known is None:
                    status = "UNKNOWN_SOURCE"
                    reasons.add("UNKNOWN_SOURCE")
                elif known["revision"] != ref["revision"]:
                    status = "STALE_REVISION"
                    reasons.add("STALE_REVISION")
                elif known["evidence_status"] != "DECLARED_VERIFIED":
                    status = "UNVERIFIED_SOURCE"
                    reasons.add("UNVERIFIED_SOURCE")
                else:
                    status = "DECLARED_VERIFIED_MATCH"
                resolved.append({
                    "source_id": sid, "stance": stance.upper(), "referenced_revision": ref["revision"],
                    "current_revision": known["revision"] if known is not None else None,
                    "evidence_status": known["evidence_status"] if known is not None else "UNKNOWN",
                    "statement": known["statement"] if known is not None else None,
                    "resolution": status,
                })
        if d["review"] == "RECORDED_REJECT":
            reasons.add("REVIEW_REJECTED")
        blockers = {"NO_SUPPORT", "OPPOSING_EVIDENCE", "UNKNOWN_SOURCE",
                    "STALE_REVISION", "UNVERIFIED_SOURCE", "REVIEW_REJECTED"}
        if reasons & blockers:
            gate = "HOLD"
        elif d["impact"] == "HIGH" or d["review"] == "PENDING" or d["confidence"]["method"] == "NONE":
            gate = "HUMAN_REVIEW_REQUIRED"
            if d["impact"] == "HIGH":
                reasons.add("HIGH_IMPACT")
            if d["review"] == "PENDING":
                reasons.add("REVIEW_PENDING")
            if d["confidence"]["method"] == "NONE":
                reasons.add("NO_CONFIDENCE_METHOD")
        else:
            gate = "REVIEW_RECORDED_NOT_AUTHORIZED"
        c = d["confidence"]
        results.append({
            "decision_id": d["decision_id"], "action": d["action"], "impact": d["impact"],
            "gate": gate, "reasons": sorted(reasons), "review_record": d["review"],
            "reported_confidence_method": c["method"],
            "self_reported_sample": ({"correct": c["correct"], "cases": c["cases"]}
                                      if c["method"] == "SELF_REPORTED_SAMPLE" else None),
            "evidence": sorted(resolved, key=lambda x: (x["source_id"], x["stance"])),
            "execution_authority": "NONE",
        })
    results.sort(key=lambda x: x["decision_id"])
    return {
        "schema": REPORT, "origin": "SYNTHETIC_OR_CALLER_SUPPLIED",
        "input_sha256": hashlib.sha256(canonical(doc).encode("utf-8")).hexdigest(),
        "status": "REVIEW_ONLY_NO_EXECUTION", "decisions_checked": len(results),
        "hold_count": sum(r["gate"] == "HOLD" for r in results),
        "human_review_count": sum(r["gate"] == "HUMAN_REVIEW_REQUIRED" for r in results),
        "recorded_review_count": sum(r["gate"] == "REVIEW_RECORDED_NOT_AUTHORIZED" for r in results),
        "execution_authority": "NONE", "results": results,
        "scope": ("Declarative, caller-supplied evidence labels and sample outcomes only. "
                  "No semantic entailment, calibrated probabilities, independently authenticated "
                  "sources, real human approval, model execution or operating authority."),
    }


def fixture() -> dict:
    return {
        "schema": SCHEMA,
        "sources": [
            {"source_id": "policy", "statement": "Fictional onboarding guide revision 2.",
             "revision": 2, "evidence_status": "DECLARED_VERIFIED"},
            {"source_id": "audit", "statement": "Fictional review checklist completed.",
             "revision": 1, "evidence_status": "DECLARED_VERIFIED"},
            {"source_id": "experiment", "statement": "Unproven optional workflow hypothesis.",
             "revision": 1, "evidence_status": "HYPOTHESIS"},
            {"source_id": "latency", "statement": "Fictional processing delay was observed.",
             "revision": 1, "evidence_status": "DECLARED_VERIFIED"},
        ],
        "decisions": [
            {"decision_id": "routine", "action": "Suggest a fictional onboarding checklist",
             "impact": "LOW", "support": [{"source_id": "policy", "revision": 2}], "oppose": [],
             "confidence": {"method": "SELF_REPORTED_SAMPLE", "correct": 8, "cases": 10},
             "review": "RECORDED_APPROVE"},
            {"decision_id": "high-impact", "action": "Suggest changing a fictional service policy",
             "impact": "HIGH", "support": [{"source_id": "audit", "revision": 1}], "oppose": [],
             "confidence": {"method": "SELF_REPORTED_SAMPLE", "correct": 9, "cases": 10},
             "review": "PENDING"},
            {"decision_id": "contradicted", "action": "Suggest fictional routing change",
             "impact": "LOW", "support": [{"source_id": "policy", "revision": 2}],
             "oppose": [{"source_id": "audit", "revision": 1}],
             "confidence": {"method": "SELF_REPORTED_SAMPLE", "correct": 5, "cases": 5},
             "review": "PENDING"},
            {"decision_id": "stale", "action": "Suggest outdated fictional instructions",
             "impact": "LOW", "support": [{"source_id": "policy", "revision": 1}], "oppose": [],
             "confidence": {"method": "SELF_REPORTED_SAMPLE", "correct": 5, "cases": 5},
             "review": "RECORDED_APPROVE"},
            {"decision_id": "unverified", "action": "Suggest untested fictional enhancement",
             "impact": "LOW", "support": [{"source_id": "experiment", "revision": 1}], "oppose": [],
             "confidence": {"method": "SELF_REPORTED_SAMPLE", "correct": 3, "cases": 3},
             "review": "RECORDED_APPROVE"},
            {"decision_id": "unscored", "action": "Consider a fictional follow-up",
             "impact": "LOW", "support": [{"source_id": "latency", "revision": 1}], "oppose": [],
             "confidence": {"method": "NONE", "correct": None, "cases": None},
             "review": "PENDING"},
        ],
    }


def render_html(report: dict) -> str:
    """Escaped, script-free local review report; no live authorization."""
    lines = []
    for d in report["results"]:
        values = [d["decision_id"], d["gate"], ", ".join(d["reasons"]) or "none",
                  d["reported_confidence_method"], d["review_record"]]
        lines.append("<tr>" + "".join("<td>" + html.escape(str(v), quote=True) + "</td>"
                                      for v in values) + "</tr>")
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
            'style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
            '<title>Explainable AI Decision Review</title><style>'
            'body{font:1rem/1.55 system-ui,sans-serif;max-width:72rem;margin:2rem auto;'
            'padding:0 1rem}.scroll{overflow-x:auto}table{width:100%;'
            'border-collapse:collapse}td,th{border-bottom:1px solid #888;'
            'padding:.6rem;text-align:left}</style></head><body><main>'
            '<h1>Fictional explainable decision review</h1>'
            '<p>User-supplied fictional evidence; review records are not authority. '
            'No live AI, human approval, independent truth verification or execution.</p>'
            '<div class="scroll"><table><caption>Explanation gates</caption><thead><tr>'
            '<th>Decision</th><th>Review status</th><th>Reasons</th>'
            '<th>Reported methodology</th><th>Human-review claim</th>'
            '</tr></thead><tbody>' + "".join(lines) + '</tbody></table></div>'
            '</main></body></html>')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--demo", action="store_true")
    g.add_argument("--input", type=Path)
    parser.add_argument("--html", type=Path)
    args = parser.parse_args()
    try:
        if args.demo:
            doc = fixture()
        else:
            if args.input.stat().st_size > MAX_BYTES:
                raise ValueError("input exceeds 64 KiB")
            doc = parse_manifest(args.input.read_text(encoding="utf-8"))
        result = inspect(doc)
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

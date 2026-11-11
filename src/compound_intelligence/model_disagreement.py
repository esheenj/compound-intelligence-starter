"""Offline multi-model disagreement and evidence triage over supplied answers.

Consensus is not truth. A caller-supplied reference is not independent proof.
No inference, network, model execution, training or agent authority occurs.
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

SCHEMA = "model-disagreement.fixtures.v1"
REPORT = "model-disagreement.review.v1"
IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,79}\Z")
MAX_BYTES = 65536
MAX_CASES = 40
MAX_MODELS = 8


def _exact(value: object, fields: set[str], where: str) -> dict:
    if type(value) is not dict or set(value) != fields:
        raise ValueError(where + ": invalid fields")
    return value


def _id(value: object, where: str) -> str:
    if type(value) is not str or IDENT.fullmatch(value) is None:
        raise ValueError(where + ": invalid identifier")
    return value


def _answer(value: object) -> str:
    if type(value) is not str or not 1 <= len(value) <= 160 or not value.strip() or "\x00" in value:
        raise ValueError("answer must be 1-160 nonblank characters")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("invalid Unicode in answer") from exc
    return value


def _list(value: object, minimum: int, maximum: int, where: str) -> list:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise ValueError(where + ": invalid item count")
    return value


def validate(doc: object) -> tuple[list[str], list[dict]]:
    _exact(doc, {"schema", "models", "cases"}, "document")
    if doc["schema"] != SCHEMA:
        raise ValueError("unsupported disagreement schema")
    if len(canonical(doc).encode("utf-8")) > MAX_BYTES:
        raise ValueError("document exceeds 64 KiB")
    models = [_id(x, "model") for x in _list(doc["models"], 2, MAX_MODELS, "models")]
    if len(set(models)) != len(models):
        raise ValueError("duplicate model ID")
    cases = _list(doc["cases"], 1, MAX_CASES, "cases")
    used = set()
    for item in cases:
        _exact(item, {"case_id", "critical", "reference", "responses"}, "case")
        cid = _id(item["case_id"], "case")
        if cid in used:
            raise ValueError("duplicate case ID")
        used.add(cid)
        if type(item["critical"]) is not bool:
            raise ValueError("case criticality must be boolean")
        if item["reference"] is not None:
            _answer(item["reference"])
        seen = set()
        for row in _list(item["responses"], 0, MAX_MODELS, "responses"):
            _exact(row, {"model_id", "status", "answer"}, "response")
            model = _id(row["model_id"], "response model")
            if model not in models or model in seen:
                raise ValueError("unknown or duplicate responding model")
            seen.add(model)
            if row["status"] == "ANSWER" and type(row["status"]) is str:
                _answer(row["answer"])
            elif row["status"] == "ABSTAIN" and type(row["status"]) is str:
                if row["answer"] is not None:
                    raise ValueError("abstention cannot include an answer")
            else:
                raise ValueError("unsupported response status")
    return models, cases


def inspect(doc: object) -> dict:
    models, cases = validate(doc)
    records = []
    for item in cases:
        present = {r["model_id"]: r for r in item["responses"]}
        missing = sorted(set(models) - set(present))
        abstained = sorted(r["model_id"] for r in item["responses"] if r["status"] == "ABSTAIN")
        groups: dict[str, list[str]] = {}
        for row in item["responses"]:
            if row["status"] == "ANSWER":
                groups.setdefault(row["answer"], []).append(row["model_id"])
        choices = [{"answer": key, "count": len(value), "model_ids": sorted(value)}
                   for key, value in sorted(groups.items())]
        ref = item["reference"]
        matched = (sum(group["count"] for group in choices if group["answer"] == ref)
                   if ref is not None else None)
        contradicted = (sum(group["count"] for group in choices if group["answer"] != ref)
                        if ref is not None else None)
        if not choices:
            state = "NO_ANSWERS"
        elif len(choices) > 1:
            state = "DISAGREEMENT"
        elif abstained or missing:
            state = "INCOMPLETE"
        elif ref is None:
            state = "UNVERIFIED_CONSENSUS"
        elif choices[0]["answer"] == ref:
            state = "MATCHES_SUPPLIED_REFERENCE"
        else:
            state = "CONTRADICTS_SUPPLIED_REFERENCE"
        # A purported reference is supplied by the caller, not verified by an authority.
        ready = state == "MATCHES_SUPPLIED_REFERENCE"
        records.append({
            "case_id": item["case_id"], "critical": item["critical"], "state": state,
            "triage": "REVIEW" if not ready else "REFERENCE_MATCH_ONLY",
            "reference_supplied": ref is not None,
            "models_expected": len(models), "answers_observed": sum(x["count"] for x in choices),
            "abstained_models": abstained, "missing_models": missing,
            "matching_reference": matched, "contradicting_reference": contradicted,
            "answer_groups": choices,
        })
    records.sort(key=lambda x: x["case_id"])
    review = sum(x["triage"] == "REVIEW" for x in records)
    critical_review = sum(x["critical"] and x["triage"] == "REVIEW" for x in records)
    return {
        "schema": REPORT, "origin": "SYNTHETIC_OR_CALLER_SUPPLIED",
        "input_sha256": hashlib.sha256(canonical(doc).encode("utf-8")).hexdigest(),
        "status": "REVIEW_REQUIRED" if review else "REFERENCE_MATCHES_ONLY",
        "model_count": len(models), "case_count": len(records),
        "review_cases": review, "critical_review_cases": critical_review,
        "records": records,
        "scope": ("Exact user-supplied answer agreement/abstention and comparison to an "
                  "untrusted supplied reference. No truth validation, semantic inference, "
                  "live model execution, causal intelligence uplift or authority."),
    }


def fixture() -> dict:
    model_ids = ["fictional-alpha", "fictional-beta", "fictional-gamma"]

    def rows(values):
        return [{"model_id": mid, "status": "ABSTAIN" if answer is None else "ANSWER",
                 "answer": answer} for mid, answer in zip(model_ids, values)]

    return {"schema": SCHEMA, "models": model_ids, "cases": [
        {"case_id": "unverified-consensus", "critical": False, "reference": None,
         "responses": rows(["route-a", "route-a", "route-a"])},
        {"case_id": "split-critical-decision", "critical": True, "reference": "deny",
         "responses": rows(["deny", "approve", "deny"])},
        {"case_id": "unanimous-wrong", "critical": True, "reference": "stop",
         "responses": rows(["run", "run", "run"])},
        {"case_id": "missing-and-abstained", "critical": False, "reference": None,
         "responses": rows(["pause", None])},
        {"case_id": "matches-supplied", "critical": True, "reference": "wait",
         "responses": rows(["wait", "wait", "wait"])},
    ]}


def render_html(result: dict) -> str:
    """Small script-free, HTML-escaped offline diagnostic table."""
    cells = []
    for row in result["records"]:
        items = [row["case_id"], row["state"], "yes" if row["critical"] else "no",
                 row["answers_observed"], len(row["missing_models"]),
                 len(row["abstained_models"]), row["matching_reference"]
                 if row["matching_reference"] is not None else "not supplied"]
        cells.append("<tr>" + "".join("<td>" + html.escape(str(x), quote=True) + "</td>"
                                       for x in items) + "</tr>")
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
            'style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
            '<title>Model Disagreement Lab</title><style>'
            'body{font:1rem/1.55 system-ui,sans-serif;margin:2rem auto;padding:0 1rem;'
            'max-width:72rem}table{border-collapse:collapse;width:100%}'
            'td,th{border-bottom:1px solid #888;padding:.6rem;text-align:left}'
            '.scroll{overflow-x:auto}</style></head><body><main>'
            '<h1>Fictional multi-model disagreement</h1>'
            '<p>Consensus is not truth. All answers and references are user-supplied '
            'fictional data. No live AI or decision execution.</p>'
            '<div class="scroll"><table><caption>Review states</caption><thead><tr>'
            '<th>Case</th><th>Finding</th><th>Critical</th><th>Answers</th>'
            '<th>Missing</th><th>Abstained</th><th>Reference matches</th>'
            '</tr></thead><tbody>' + "".join(cells) + '</tbody></table></div>'
            '</main></body></html>')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", action="store_true")
    group.add_argument("--input", type=Path)
    parser.add_argument("--html", type=Path, help="optional script-free report output")
    args = parser.parse_args()
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

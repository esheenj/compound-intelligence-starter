"""Claim–Evidence Mapper: offline literal excerpt matching, not fact-checking.

Checks *user-supplied* citations against *user-supplied* source excerpts.
Never fetches URLs, trusts claimed authors or establishes semantic truth.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .agentproof import parse_manifest

SCHEMA = "claim-evidence.fixtures.v1"
REPORT = "claim-evidence.review.v1"
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,99}\Z")
MAX_BYTES = 256_000


def fictional_claims(missing: bool = False) -> dict:
    return {
        "schema": SCHEMA,
        "sources": [
            {"source_id": "fictional-note", "excerpt": "The invented demo did not execute external jobs."},
            {"source_id": "fictional-receipt", "excerpt": "Exactly three fictional checks were recorded."},
        ],
        "claims": [
            {"claim_id": "claim-one", "text": "No external jobs were executed.",
             "quote": "did not execute external jobs",
             "cited_source_ids": ["fictional-note"]},
            {"claim_id": "claim-two", "text": "The synthetic fixture contains three checks.",
             "quote": "three fictional checks" if not missing else "four genuine checks",
             "cited_source_ids": ["fictional-receipt"]},
        ],
    }


def _invalid(reason: str) -> dict:
    return {
        "schema": REPORT, "valid_input": False,
        "all_literal_citations_found": False, "claims_checked": 0,
        "unresolved_claims": 0, "results": [], "errors": [reason],
        "scope": "Literal excerpt lookup on supplied text only. No truth, provenance, context or entailment verification.",
    }


def inspect_claims(document: object) -> dict:
    if type(document) is not dict or set(document) != {"schema", "sources", "claims"} or document.get("schema") != SCHEMA:
        return _invalid("unsupported document schema or fields")
    sources = document["sources"]
    claims = document["claims"]
    if type(sources) is not list or not (1 <= len(sources) <= 100):
        return _invalid("sources must have 1 to 100 entries")
    if type(claims) is not list or not (1 <= len(claims) <= 100):
        return _invalid("claims must have 1 to 100 entries")
    sources_by_id: dict[str, str] = {}
    for index, source in enumerate(sources, 1):
        if type(source) is not dict or set(source) != {"source_id", "excerpt"}:
            return _invalid(f"source {index}: invalid fields")
        source_id, excerpt = source["source_id"], source["excerpt"]
        if type(source_id) is not str or ID.fullmatch(source_id) is None or source_id in sources_by_id:
            return _invalid(f"source {index}: invalid or duplicate source ID")
        if type(excerpt) is not str or not 1 <= len(excerpt) <= 2000:
            return _invalid(f"source {index}: invalid excerpt length")
        sources_by_id[source_id] = excerpt
    results = []
    seen_claims: set[str] = set()
    for index, claim in enumerate(claims, 1):
        if type(claim) is not dict or set(claim) != {"claim_id", "text", "quote", "cited_source_ids"}:
            return _invalid(f"claim {index}: invalid fields")
        claim_id, text, quote, cited_ids = (
            claim["claim_id"], claim["text"], claim["quote"], claim["cited_source_ids"]
        )
        if type(claim_id) is not str or ID.fullmatch(claim_id) is None or claim_id in seen_claims:
            return _invalid(f"claim {index}: invalid or duplicate claim ID")
        seen_claims.add(claim_id)
        if type(text) is not str or not 2 <= len(text.strip()) <= 400:
            return _invalid(f"claim {index}: invalid claim text")
        if type(quote) is not str or len(quote) > 300:
            return _invalid(f"claim {index}: invalid quoted excerpt")
        if type(cited_ids) is not list or len(cited_ids) > 8 or any(
            type(s) is not str or ID.fullmatch(s) is None for s in cited_ids
        ) or len(set(cited_ids)) != len(cited_ids):
            return _invalid(f"claim {index}: invalid source references")
        unknown = sorted(source for source in cited_ids if source not in sources_by_id)
        missing = sorted(source for source in cited_ids if source in sources_by_id and quote and quote not in sources_by_id[source])
        matched = sorted(source for source in cited_ids if source in sources_by_id and quote and quote in sources_by_id[source])
        if not cited_ids:
            status = "NO_CITATION"
        elif unknown:
            status = "SOURCE_NOT_SUPPLIED"
        elif not quote.strip():
            status = "NO_TESTABLE_QUOTE"
        elif missing:
            status = "QUOTE_NOT_FOUND_IN_ALL_CITED_SOURCES"
        else:
            status = "ALL_QUOTES_FOUND_LITERAL_ONLY"
        results.append({
            "claim_id": claim_id, "status": status, "matched_source_ids": matched,
            "unmatched_source_ids": missing, "unknown_source_ids": unknown,
        })
    unresolved = sum(row["status"] != "ALL_QUOTES_FOUND_LITERAL_ONLY" for row in results)
    return {
        "schema": REPORT, "valid_input": True,
        "all_literal_citations_found": unresolved == 0,
        "claims_checked": len(results), "unresolved_claims": unresolved,
        "results": results, "errors": [],
        "scope": "Literal excerpt lookup on supplied text only. No truth, provenance, context or entailment verification.",
    }


def _input_document(path: Path) -> object:
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("oversized local fixture")
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError("oversized local fixture")
    return parse_manifest(raw.decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline fictional claim–excerpt matching")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--demo", action="store_true")
    mode.add_argument("--gap-demo", action="store_true")
    mode.add_argument("--input", type=Path)
    args = parser.parse_args()
    try:
        document = fictional_claims(missing=args.gap_demo) if args.demo or args.gap_demo else _input_document(args.input)
    except (OSError, UnicodeError, ValueError):
        print(json.dumps(_invalid("INPUT_REJECTED"), sort_keys=True, indent=2))
        return 2
    report = inspect_claims(document)
    print(json.dumps(report, sort_keys=True, indent=2))
    return 2 if not report["valid_input"] else 1 if not report["all_literal_citations_found"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

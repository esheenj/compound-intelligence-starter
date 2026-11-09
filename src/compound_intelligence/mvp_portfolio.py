"""Offline, read-only prioritization of fictional open-source MVP candidates.

This library produces review proposals, never build, merge or publication authority.
Only original synthetic examples belong in the public fixture.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

STATUSES = ("scaffold", "implemented", "source_published", "pages_deployed", "browser_verified")
FIELDS = {"id", "status", "value", "effort", "risk", "rights_reviewed", "tests_verified"}
SLUG = re.compile(r"[a-z][a-z0-9-]{2,47}\Z")
NEXT = {
    "scaffold": "Build one original offline vertical slice and a failing-input test",
    "implemented": "Verify exact-head tests, provenance, rights, and a clean public export",
    "source_published": "Verify release checks and prepare a static demo if appropriate",
    "pages_deployed": "Independently test live HTTPS, keyboard, narrow viewport and errors",
    "browser_verified": "Maintain regressions and collect attributed contributor feedback",
}


def _integer(value, minimum, maximum):
    return type(value) is int and minimum <= value <= maximum


def validate(payload):
    if type(payload) is not dict or set(payload) != {"version", "max_active", "candidates"}:
        raise ValueError("INVALID_ROOT")
    if type(payload["version"]) is not int or payload["version"] != 1:
        raise ValueError("UNSUPPORTED_VERSION")
    if not _integer(payload["max_active"], 1, 3):
        raise ValueError("INVALID_ACTIVE_LIMIT")
    candidates = payload["candidates"]
    if type(candidates) is not list or not 1 <= len(candidates) <= 100:
        raise ValueError("INVALID_CANDIDATES")
    seen = set()
    for candidate in candidates:
        if type(candidate) is not dict or set(candidate) != FIELDS:
            raise ValueError("INVALID_CANDIDATE_SHAPE")
        name = candidate["id"]
        if type(name) is not str or not SLUG.fullmatch(name) or name in seen:
            raise ValueError("INVALID_OR_DUPLICATE_ID")
        seen.add(name)
        if candidate["status"] not in STATUSES:
            raise ValueError("UNKNOWN_STATUS")
        for field in ("value", "effort", "risk"):
            if not _integer(candidate[field], 0, 5):
                raise ValueError("INVALID_SCORE")
        for field in ("rights_reviewed", "tests_verified"):
            if type(candidate[field]) is not bool:
                raise ValueError("INVALID_EVIDENCE_FLAG")
    return candidates


def plan(payload):
    candidates = validate(payload)
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    proposed = []
    for item in candidates:
        stage = STATUSES.index(item["status"])
        score = 3 * item["value"] - 2 * item["effort"] - item["risk"]
        reasons = []
        if not item["rights_reviewed"]:
            reasons.append("RIGHTS_NOT_REVIEWED")
        if not item["tests_verified"]:
            reasons.append("TESTS_NOT_VERIFIED")
        if item["status"] != "browser_verified":
            reasons.append("INDEPENDENT_BROWSER_VERIFICATION_MISSING")
        proposed.append({
            "id": item["id"],
            "claimed_status": item["status"],
            "priority_hint": score,
            "next_test": NEXT[item["status"]],
            "unverified_gates": reasons,
            "release_authorized": False,
            "execution_authorized": False,
            "_stage": stage,
        })
    proposed.sort(key=lambda x: (-x["_stage"], -x["priority_hint"], x["id"]))
    active = [x["id"] for x in proposed if x["claimed_status"] != "browser_verified"][:payload["max_active"]]
    for item in proposed:
        del item["_stage"]
    return {
        "schema": "esheen-public-mvp-wave-proposal-v1",
        "input_sha256": digest,
        "active_review_candidates": active,
        "candidate_count": len(proposed),
        "candidates": proposed,
        "evidence_source": "SELF_DECLARED_FIXTURE_ONLY",
        "external_execution": False,
        "publication_authority": "NONE",
        "results_verified": False,
    }


def load(path):
    p = Path(path)
    if p.is_symlink():
        raise ValueError("SYMLINK_FORBIDDEN")
    st = p.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_size > 65536:
        raise ValueError("INVALID_FILE")
    fd = os.open(p, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("FILE_TOO_LARGE")
    return json.loads(raw.decode("utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Propose bounded public MVP review waves from synthetic fixtures")
    parser.add_argument("--input", required=True)
    options = parser.parse_args(argv)
    try:
        result = plan(load(options.input))
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError):
        print(json.dumps({"schema": "esheen-public-mvp-wave-proposal-v1", "state": "REJECTED"}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

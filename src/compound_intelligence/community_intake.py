"""Read-only public GitHub feedback inventory: references and digests, no issue text.

This is evidence discovery for later human/Cortex review, not AI training, code
generation, contributor approval, continuous host execution or an MVP verdict.
Only the explicitly listed public repositories are queried.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

PUBLIC_REPOS = (
    "esheenj/compound-intelligence-starter",
    "esheenj/design-system-foundations-oss",
    "esheenj/mobile-first-flow-kit-oss",
    "esheenj/data-table-interactions-oss",
    "esheenj/flow-state-machine-oss",
    "esheenj/form-experience-kit-oss",
    "esheenj/visual-regression-starter-oss",
)
EXPANDED_PUBLIC_REPOS = PUBLIC_REPOS + (
    "esheenj/agent-capability-policy-lab",
    "esheenj/prompt-evaluation-harness-oss",
    "esheenj/eval-dataset-leakage-lab",
    "esheenj/rag-retrieval-eval-lab",
)
DATE = re.compile(r"^20[0-9]{2}-[01][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:[0-5][0-9]Z$")
MAX_BODY = 100_000
MAX_RESPONSE = 2_000_000


def summarize(repo: str, payload: list) -> dict:
    """Do not reproduce public issue text into reports; no inference is performed."""
    if repo not in EXPANDED_PUBLIC_REPOS or not isinstance(payload, list) or len(payload) > 40:
        raise ValueError("repository or issue payload outside allowed bounds")
    refs = []
    seen = set()
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("invalid issue")
        if item.get("pull_request") is not None:
            continue
        number, title = item.get("number"), item.get("title")
        body, updated = item.get("body") or "", item.get("updated_at")
        if type(number) is not int or number < 1 or number in seen:
            raise ValueError("invalid or duplicate issue number")
        if (not isinstance(title, str) or len(title) > 5000
                or not isinstance(body, str) or len(body) > MAX_BODY
                or not isinstance(updated, str) or not DATE.fullmatch(updated)):
            raise ValueError("invalid issue data")
        seen.add(number)
        refs.append({
            "source": f"https://github.com/{repo}/issues/{number}",
            "number": number,
            "updated_at": updated,
            "content_digest": hashlib.sha256((title + "\0" + body).encode("utf-8")).hexdigest(),
            "classification": "UNREVIEWED_PUBLIC_OBSERVATION",
        })
    refs.sort(key=lambda x: (x["updated_at"], x["number"]), reverse=True)
    return {"repository": repo, "issues": refs, "count": len(refs),
            "interpretation": "NONE", "safe_to_execute": False}


def fetch_public_issues(repo: str) -> list:
    if repo not in PUBLIC_REPOS:
        raise ValueError("unlisted repository")
    url = f"https://api.github.com/repos/{repo}/issues?state=open&per_page=30"
    request = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json",
                      "User-Agent": "compound-intelligence-starter-community-intake"})
    with urllib.request.urlopen(request, timeout=12) as response:
        raw = response.read(MAX_RESPONSE + 1)
    if len(raw) > MAX_RESPONSE:
        raise ValueError("remote response exceeds size bound")
    return json.loads(raw)


def report(payloads: dict, *, expanded_fixture: bool = False) -> dict:
    repos = EXPANDED_PUBLIC_REPOS if expanded_fixture else PUBLIC_REPOS
    if (not isinstance(payloads, dict) or not payloads or set(payloads) - set(repos)
            or (expanded_fixture and set(payloads) != set(repos))):
        raise ValueError("unknown or empty cohort")
    return {
        "schema": "public-feedback-inventory-v1",
        "source_access": "PUBLIC_READ_ONLY",
        "records": [summarize(repo, payloads[repo]) for repo in repos if repo in payloads],
        "contents_redacted": True,
        "intelligence_validated": False,
        "automated_code_changes": False,
        "model_training": False,
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Capture bounded public GitHub issue references")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true", help="Read only seven listed public GitHub repos")
    mode.add_argument("--fixture", help="Local synthetic JSON {repo: [issue, ...]}")
    p.add_argument("--expanded-fixture", action="store_true",
                   help="Require all eleven approved repositories in a local fixture")
    p.add_argument("--output", required=True, help="Local report JSON path")
    args = p.parse_args(argv)
    try:
        if args.live and args.expanded_fixture:
            raise ValueError("expanded scope is fixture-only")
        if args.live:
            payloads = {repo: fetch_public_issues(repo) for repo in PUBLIC_REPOS}
        else:
            source = Path(args.fixture)
            if not source.is_file() or source.stat().st_size > MAX_RESPONSE:
                raise ValueError("invalid or oversized fixture")
            payloads = json.loads(source.read_text(encoding="utf-8"))
        result = report(payloads, expanded_fixture=args.expanded_fixture)
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"state": "INVENTORIED", "path": str(destination),
                          "count": sum(row["count"] for row in result["records"]),
                          "intelligence_validated": False, "code_changes": False}))
        return 0
    except urllib.error.HTTPError as exc:
        # Do not log request URLs, response bodies or arbitrary response headers.
        status = exc.code if type(exc.code) is int and 100 <= exc.code <= 599 else None
        exhausted = exc.headers is not None and exc.headers.get("X-RateLimit-Remaining") == "0"
        reason = ("RATE_LIMITED" if status == 429 or (status == 403 and exhausted)
                  else "HTTP_REQUEST_REJECTED")
        print(json.dumps({"state": "FAILED", "error_type": "HTTPError",
                          "http_status": status, "reason": reason,
                          "partial_inventory_written": False}))
        return 2
    except (ValueError, OSError, UnicodeError, urllib.error.URLError,
            json.JSONDecodeError) as exc:
        print(json.dumps({"state": "FAILED", "error_type": type(exc).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

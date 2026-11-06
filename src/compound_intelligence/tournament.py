"""v0.3: replayable, bounded comparisons of independent model proposals.

Only a narrow integer-sum benchmark is supported. Models propose; a trusted
deterministic validator decides. No shell commands, browsing or code execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .engine import EvidenceStore, canonical

MAX_MODELS = 8
MAX_RESPONSE_BYTES = 16_384
DEFAULT_ENDPOINT = "http://127.0.0.1:11434"


def _identifier(task: dict, model: str) -> str:
    """Stable across restarts but distinct for different tasks and providers."""
    digest = hashlib.sha256(canonical({"task": task, "model": model}).encode()).hexdigest()[:24]
    return "model-" + digest


def _validate_task(values: list[int]) -> dict:
    if not isinstance(values, list) or not 1 <= len(values) <= 32:
        raise ValueError("provide 1 to 32 integers")
    if any(type(value) is not int or abs(value) > 1_000_000 for value in values):
        raise ValueError("integers must have absolute value <= 1000000")
    return {"kind": "sum", "values": values}


def _validate_models(models: list[str]) -> None:
    if not isinstance(models, list) or not 1 <= len(models) <= MAX_MODELS:
        raise ValueError("provide 1 to 8 models")
    if len(set(models)) != len(models):
        raise ValueError("model names must be unique")
    if any(not isinstance(m, str) or not re.fullmatch(r"[a-zA-Z0-9_.:/-]{1,128}", m) for m in models):
        raise ValueError("model names must use safe, non-empty identifiers")


def _local_endpoint(endpoint: str) -> str:
    parts = urlsplit(endpoint)
    if (parts.scheme != "http" or parts.hostname not in ("localhost", "127.0.0.1")
            or parts.username or parts.password or parts.path not in ("", "/")
            or parts.query or parts.fragment):
        raise ValueError("only local HTTP Ollama is supported")
    if parts.port is not None and not 1 <= parts.port <= 65535:
        raise ValueError("invalid local port")
    return endpoint.rstrip("/")


def ollama_proposal(model: str, task: dict, *, endpoint: str = DEFAULT_ENDPOINT,
                    timeout: float = 12) -> dict:
    """Untrusted Ollama text is parsed as a candidate, never as an instruction."""
    endpoint = _local_endpoint(endpoint)
    if not 0 < timeout <= 30:
        raise ValueError("timeout must be > 0 and <= 30 seconds")
    payload = json.dumps({
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_predict": 96},
        "prompt": (
            "Solve the following arithmetic task. Return ONLY a JSON object "
            'with an integer field "expected" and a short string "reason". '
            "Do not request tools. Task: " + canonical(task)
        ),
    }).encode()
    request = Request(endpoint + "/api/generate", data=payload, method="POST",
                      headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            return {"error": "RESPONSE_TOO_LARGE"}
        outer = json.loads(body)
        raw = outer.get("response")
        if not isinstance(raw, str) or len(raw) > 8000:
            return {"error": "INVALID_RESPONSE"}
        proposal = json.loads(raw)
        if not isinstance(proposal, dict) or type(proposal.get("expected")) is not int:
            return {"error": "INVALID_PROPOSAL"}
        if abs(proposal["expected"]) > 32_000_000:
            return {"error": "OUT_OF_BOUNDS"}
        reason = proposal.get("reason", "")
        return {"expected": proposal["expected"],
                "reason": reason[:200] if isinstance(reason, str) else ""}
    except (HTTPError, URLError, OSError, TimeoutError, ValueError,
            json.JSONDecodeError) as exc:
        return {"error": type(exc).__name__}


def fixture_proposal(model: str, task: dict) -> dict:
    """Offline deterministic multi-model demonstration, not actual inference."""
    if model == "fixture-correct":
        return {"expected": sum(task["values"]), "reason": "fixture reference"}
    if model == "fixture-incorrect":
        return {"expected": sum(task["values"]) + 1, "reason": "intentional error"}
    raise ValueError("unknown fixture model")


def compare(values: list[int], models: list[str], workspace: Path,
            proposer=None) -> dict:
    task = _validate_task(values)
    _validate_models(models)
    provider = proposer or ollama_proposal
    store = EvidenceStore(Path(workspace) / "experiments.sqlite3")
    results = []
    try:
        for model in models:
            experiment_id = _identifier(task, model)
            existing = store.get(experiment_id)
            if existing:
                # Existing identity is always read rather than running inference again.
                candidate = {"id": experiment_id, "kind": "sum",
                             "values": values, "expected": existing["experiment"]["expected"]}
                record, created = store.run(candidate)
                results.append({"model": model, "status": record["status"],
                                "expected": record["experiment"]["expected"],
                                "new": created, "reason": "reused evidence"})
                continue
            proposed = provider(model, task)
            if not isinstance(proposed, dict) or type(proposed.get("expected")) is not int:
                error = proposed.get("error", "INVALID_PROPOSAL") if isinstance(proposed, dict) else "INVALID_PROPOSAL"
                results.append({"model": model, "status": "NO_RESULT", "new": False,
                                "reason": str(error)[:80]})
                continue
            candidate = {"id": experiment_id, "kind": "sum", "values": values,
                         "expected": proposed["expected"]}
            advisory = {"provider": model, "reason": str(proposed.get("reason", ""))[:200],
                        "authority": "PROPOSAL_ONLY"}
            record, created = store.run(candidate, advisory)
            results.append({"model": model, "status": record["status"],
                            "expected": proposed["expected"], "new": created,
                            "reason": "independently validated"})
    finally:
        store.close()
    return {
        "task": task,
        "results": results,
        "verified": sum(x["status"] == "VERIFIED" for x in results),
        "rejected": sum(x["status"] == "REJECTED" for x in results),
        "no_result": sum(x["status"] == "NO_RESULT" for x in results),
        "note": "Arithmetic-only benchmark; verified means the stated integer sum is correct.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--values", type=int, nargs="+", default=[8, 13])
    parser.add_argument("--models", nargs="+", help="1-8 local Ollama model names")
    parser.add_argument("--fixture", action="store_true", help="offline simulated proposals")
    parser.add_argument("--workspace", type=Path, default=Path("local-data/v03"))
    args = parser.parse_args()
    if args.fixture and args.models:
        parser.error("choose --fixture or --models, not both")
    if not args.fixture and not args.models:
        parser.error("provide --fixture or --models MODEL [MODEL ...]")
    names = ["fixture-correct", "fixture-incorrect"] if args.fixture else args.models
    provider = fixture_proposal if args.fixture else None
    print(json.dumps(compare(args.values, names, args.workspace, proposer=provider), indent=2))


if __name__ == "__main__":
    main()

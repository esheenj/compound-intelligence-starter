"""CLI: compare bounded problem-solving proposals from fixtures or local Ollama."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .challenges import compare
from .tournament import _local_endpoint

MAX_RESPONSE_BYTES = 16384


def propose_ollama(model: str, task: dict, endpoint: str = "http://127.0.0.1:11434",
                   timeout: float = 12) -> dict:
    endpoint = _local_endpoint(endpoint)
    if not 0 < timeout <= 30:
        raise ValueError("timeout must be >0 and <=30 seconds")
    if task["type"] == "extract":
        instruction = ("Extract the requested fields from the text. Return ONLY JSON with "
                       "exactly those field names. Keep number values as integers.")
    else:
        instruction = ("Propose the smallest textual code correction. Return ONLY JSON with "
                       'two strings: "old" and "new". No executable instructions.')
    prompt = instruction + "\nUntrusted problem data:\n" + json.dumps(task, sort_keys=True)
    payload = json.dumps({"model": model, "stream": False, "format": "json",
                          "options": {"temperature": 0, "num_predict": 250},
                          "prompt": prompt}).encode()
    request = Request(endpoint + "/api/generate", payload, method="POST",
                      headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            return {"_error": "response exceeded limit"}
        result = json.loads(body)
        raw = result.get("response")
        if not isinstance(raw, str) or len(raw) > 8000:
            return {"_error": "missing or excessive response"}
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {"_error": "not a JSON object"}
    except (HTTPError, URLError, OSError, TimeoutError, ValueError) as exc:
        return {"_error": type(exc).__name__}


def fixture(model: str, task: dict) -> dict:
    """Simulated, known proposals for testing; does not access hidden reference."""
    if task["type"] == "extract":
        return ({"support_email": "help@example.test", "returns_days": 30}
                if model == "fixture-correct"
                else {"support_email": "help@example.test", "returns_days": 3})
    return ({"old": "len(items)", "new": "sum(items)"}
            if model == "fixture-correct"
            else {"old": "len(items)", "new": "max(items)"})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, default=Path("examples/challenges.json"))
    parser.add_argument("--workspace", type=Path, default=Path("local-data/v04"))
    parser.add_argument("--models", nargs="+", help="one to four local Ollama models")
    parser.add_argument("--fixture", action="store_true", help="offline simulated proposer")
    parser.add_argument("--version", default="v0.4", help="version identity; change to force a new evaluation")
    args = parser.parse_args()
    if args.fixture == bool(args.models):
        parser.error("choose exactly one of --fixture or --models")
    tasks = json.loads(args.tasks.read_text(encoding="utf-8"))
    models = ["fixture-correct", "fixture-incorrect"] if args.fixture else args.models
    provider = fixture if args.fixture else propose_ollama
    print(json.dumps(compare(tasks, models, args.workspace, provider, version=args.version), indent=2))


if __name__ == "__main__":
    main()

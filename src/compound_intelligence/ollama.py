"""Optional, explicitly requested Ollama research advisory; not a validator."""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

MAX_RESPONSE_BYTES = 32_768


def advisory(experiment: dict, *, model: str, endpoint: str = "http://127.0.0.1:11434", timeout: float = 8) -> dict:
    if not model or len(model) > 128:
        raise ValueError("provide an Ollama model name (max 128 characters)")
    parsed = urlsplit(endpoint)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.username or parsed.password or parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise ValueError("only a local HTTP Ollama endpoint is permitted")
    if not 0 < timeout <= 30:
        raise ValueError("timeout must be >0 and <=30 seconds")
    prompt = (
        "You are an independent reviewer. Identify weaknesses or counterexamples in this proposed "
        "arithmetic claim. Do not claim to have executed tools. Keep it under 80 words.\n"
        + json.dumps(experiment, sort_keys=True)
    )
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False, "options": {"num_predict": 120}}).encode()
    req = Request(endpoint.rstrip("/") + "/api/generate", payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("Ollama response exceeded size limit")
        body = json.loads(raw)
        message = body.get("response")
        if not isinstance(message, str):
            raise ValueError("Ollama response omitted text")
        return {"provider": "ollama", "model": model, "critique": message[:4000], "authority": "ADVISORY_ONLY"}
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"provider": "ollama", "model": model, "error": type(exc).__name__, "authority": "ADVISORY_ONLY"}

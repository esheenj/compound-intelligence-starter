"""Offline local-model resource fit planner from caller-supplied estimates.

No model loads, hardware probes, performance measurements or compatibility claims.
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

from .agentproof import parse_manifest

SCHEMA = "local-model-fit.v1"
REPORT = "local-model-fit-report.v1"
IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}\Z")


def fixture(*, constrained: bool = False) -> dict:
    return {
        "schema": SCHEMA,
        "device": {
            "ram_mib": 1024 if constrained else 3072,
            "reserved_ram_mib": 128 if constrained else 512,
            "free_storage_mib": 400 if constrained else 2048,
            "required_context_tokens": 4096,
        },
        "models": [
            {"model_id": "fictional-small-q4", "file_mib": 850,
             "estimated_runtime_ram_mib": 1750, "context_capacity_tokens": 8192},
            {"model_id": "fictional-large-q4", "file_mib": 2600,
             "estimated_runtime_ram_mib": 3100, "context_capacity_tokens": 32768},
        ],
    }


def _error(reason: str) -> dict:
    return {
        "schema": REPORT, "valid_input": False, "any_candidate_fits": False,
        "device": None, "candidates": [], "errors": [reason],
        "scope": "Supplied estimates only; no model loading, benchmarks or verified device compatibility.",
    }


def _integer(value: object, name: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(name + " outside permitted integer range")
    return value


def evaluate(document: object) -> dict:
    if type(document) is not dict or set(document) != {"schema", "device", "models"} or document.get("schema") != SCHEMA:
        return _error("invalid document schema or fields")
    device = document["device"]
    if type(device) is not dict or set(device) != {
        "ram_mib", "reserved_ram_mib", "free_storage_mib", "required_context_tokens"
    }:
        return _error("invalid device fields")
    try:
        ram = _integer(device["ram_mib"], "ram_mib", 1, 1000000)
        reserved = _integer(device["reserved_ram_mib"], "reserved_ram_mib", 0, 999999)
        disk = _integer(device["free_storage_mib"], "free_storage_mib", 0, 1000000)
        requested = _integer(device["required_context_tokens"], "required_context_tokens", 128, 1000000)
        if reserved >= ram:
            raise ValueError("reserved RAM must be less than total RAM")
    except ValueError as exc:
        return _error(str(exc))
    models = document["models"]
    if type(models) is not list or not 1 <= len(models) <= 100:
        return _error("models must contain 1 to 100 entries")
    seen = set()
    candidates = []
    for n, entry in enumerate(models, 1):
        prefix = "model " + str(n) + ": "
        if type(entry) is not dict or set(entry) != {
            "model_id", "file_mib", "estimated_runtime_ram_mib", "context_capacity_tokens"
        }:
            return _error(prefix + "invalid fields")
        mid = entry["model_id"]
        if type(mid) is not str or IDENT.fullmatch(mid) is None or mid in seen:
            return _error(prefix + "invalid or duplicate model_id")
        seen.add(mid)
        try:
            file_size = _integer(entry["file_mib"], "file_mib", 1, 1000000)
            runtime_ram = _integer(entry["estimated_runtime_ram_mib"], "estimated_runtime_ram_mib", 1, 1000000)
            max_context = _integer(entry["context_capacity_tokens"], "context_capacity_tokens", 128, 1000000)
        except ValueError as exc:
            return _error(prefix + str(exc))
        available_ram = ram - reserved
        ram_headroom = available_ram - runtime_ram
        storage_headroom = disk - file_size
        context_headroom = max_context - requested
        reasons = []
        if ram_headroom < 0:
            reasons.append("estimated_runtime_ram_exceeds_available_ram")
        if storage_headroom < 0:
            reasons.append("model_file_exceeds_free_storage")
        if context_headroom < 0:
            reasons.append("context_capacity_below_requirement")
        candidates.append({
            "model_id": mid, "meets_supplied_limits": not reasons,
            "estimated_ram_headroom_mib": ram_headroom,
            "storage_headroom_mib": storage_headroom,
            "context_headroom_tokens": context_headroom,
            "reasons": reasons,
        })
    # Compatible candidates are listed first, then in lexical order.
    candidates.sort(key=lambda x: (not x["meets_supplied_limits"], x["model_id"]))
    return {
        "schema": REPORT, "valid_input": True,
        "any_candidate_fits": any(x["meets_supplied_limits"] for x in candidates),
        "device": dict(device), "candidates": candidates, "errors": [],
        "scope": "Supplied estimates only; no model loading, benchmarks or verified device compatibility.",
    }


def render_html(report: dict) -> str:
    """Escape all content; create a script-free, offline comparison."""
    rows = []
    for item in report["candidates"]:
        fields = [
            item["model_id"],
            "Fits supplied limits" if item["meets_supplied_limits"] else "Does not fit",
            item["estimated_ram_headroom_mib"],
            item["storage_headroom_mib"],
            item["context_headroom_tokens"],
            ", ".join(item["reasons"]) if item["reasons"] else "None",
        ]
        rows.append("<tr>" + "".join(
            "<td>" + html.escape(str(field), quote=True) + "</td>" for field in fields
        ) + "</tr>")
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        'style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
        '<title>Local Model Fit Planner</title><style>'
        'body{font:1rem/1.5 system-ui,sans-serif;max-width:65rem;margin:2rem auto;padding:0 1rem}'
        'table{border-collapse:collapse;width:100%}th,td{padding:.6rem;text-align:left;'
        'border-bottom:1px solid #aaa}.scroll{overflow-x:auto}</style></head>'
        '<body><main><h1>Local model fit planner</h1>'
        '<p>Fictional device and model estimates only. No hardware/model compatibility is verified.</p>'
        '<div class="scroll"><table><caption>Resource headroom from supplied inputs</caption>'
        '<thead><tr><th>Model</th><th>Supplied fit</th><th>RAM MiB</th><th>Storage MiB</th>'
        '<th>Context tokens</th><th>Limitations</th></tr></thead><tbody>' +
        "".join(rows) + '</tbody></table></div></main></body></html>'
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline caller-supplied local AI model fit check")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--demo", action="store_true")
    group.add_argument("--constrained-demo", action="store_true")
    group.add_argument("--input", type=Path)
    parser.add_argument("--html", type=Path)
    args = parser.parse_args()
    try:
        data = fixture(constrained=args.constrained_demo) if args.demo or args.constrained_demo else \
               parse_manifest(args.input.read_text(encoding="utf-8"))
        report = evaluate(data)
        if args.html and report["valid_input"]:
            args.html.write_text(render_html(report), encoding="utf-8")
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        report = _error("input/output rejected: " + str(exc))
    print(json.dumps(report, sort_keys=True, indent=2))
    return 2 if not report["valid_input"] else (0 if report["any_candidate_fits"] else 1)


if __name__ == "__main__":
    raise SystemExit(main())

"""Offline synthetic AI model cost estimates. Never provider billing or model evaluation."""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import html
import json
import re
from pathlib import Path
from .agentproof import parse_manifest

SCHEMA = "model-cost-comparison.v1"
REPORT = "model-cost-report.v1"
IDENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,99}\Z")
PRICE = re.compile(r"(?:0|[1-9][0-9]{0,5})(?:\.[0-9]{1,6})?\Z")
MILLION = Decimal(1000000)
PRECISION = Decimal("0.000000000001")


def _money(value: object, name: str) -> Decimal:
    if type(value) is not str or PRICE.fullmatch(value) is None:
        raise ValueError(name + " must be a non-negative decimal string with at most six places")
    return Decimal(value)


def fixture(*, overrun: bool = False) -> dict:
    return {"schema": SCHEMA, "price_book_revision": "fictional-v1",
            "budget_usd": "0.000350" if overrun else "0.000400",
            "rates": [
                {"model_id": "sample-small", "input_usd_per_million": "0.20", "output_usd_per_million": "0.90"},
                {"model_id": "sample-large", "input_usd_per_million": "0.30", "output_usd_per_million": "0.80"},
            ],
            "events": [
                {"event_id": "small-1", "model_id": "sample-small", "input_tokens": 1000, "output_tokens": 200},
                {"event_id": "small-1", "model_id": "sample-small", "input_tokens": 1000, "output_tokens": 200},
                {"event_id": "large-1", "model_id": "sample-large", "input_tokens": 1000, "output_tokens": 200},
            ]}


def _error(why: str) -> dict:
    return {"schema": REPORT, "valid_input": False, "all_within_budget": False,
            "price_book_revision": None, "budget_usd": None, "events_applied": 0,
            "duplicates_ignored": 0, "models": [], "errors": [why],
            "scope": "Synthetic user-supplied prices and usage; not provider billing or model quality."}


def compare(document: object) -> dict:
    if (type(document) is not dict or
            set(document) != {"schema", "price_book_revision", "budget_usd", "rates", "events"} or
            document.get("schema") != SCHEMA):
        return _error("invalid schema or document fields")
    revision = document["price_book_revision"]
    if type(revision) is not str or IDENT.fullmatch(revision) is None:
        return _error("invalid price book revision")
    try:
        budget = _money(document["budget_usd"], "budget_usd")
    except (ValueError, InvalidOperation) as exc:
        return _error(str(exc))
    rates, events = document["rates"], document["events"]
    if type(rates) is not list or not 1 <= len(rates) <= 100:
        return _error("rates must have 1 to 100 models")
    if type(events) is not list or not 1 <= len(events) <= 10000:
        return _error("events must have 1 to 10000 rows")
    models = {}
    for i, row in enumerate(rates, 1):
        if type(row) is not dict or set(row) != {"model_id", "input_usd_per_million", "output_usd_per_million"}:
            return _error("rate " + str(i) + ": invalid fields")
        mid = row["model_id"]
        if type(mid) is not str or IDENT.fullmatch(mid) is None or mid in models:
            return _error("rate " + str(i) + ": invalid or duplicate model")
        try:
            inp = _money(row["input_usd_per_million"], "input price")
            out = _money(row["output_usd_per_million"], "output price")
        except (ValueError, InvalidOperation) as exc:
            return _error("rate " + str(i) + ": " + str(exc))
        models[mid] = {"in": inp, "out": out, "input": 0, "output": 0, "events": 0}
    seen = {}
    repeated = 0
    for i, event in enumerate(events, 1):
        prefix = "event " + str(i) + ": "
        if type(event) is not dict or set(event) != {"event_id", "model_id", "input_tokens", "output_tokens"}:
            return _error(prefix + "invalid fields")
        eid, mid = event["event_id"], event["model_id"]
        if type(eid) is not str or IDENT.fullmatch(eid) is None:
            return _error(prefix + "invalid event_id")
        if type(mid) is not str or mid not in models:
            return _error(prefix + "unknown model_id")
        for key in ("input_tokens", "output_tokens"):
            if type(event[key]) is not int or not 0 <= event[key] <= 1000000000:
                return _error(prefix + "invalid " + key)
        if event["input_tokens"] + event["output_tokens"] == 0:
            return _error(prefix + "zero token usage")
        if eid in seen:
            if event != seen[eid]:
                return _error(prefix + "conflicting duplicate event_id")
            repeated += 1
            continue
        state = models[mid]
        state["input"] += event["input_tokens"]
        state["output"] += event["output_tokens"]
        state["events"] += 1
        seen[eid] = dict(event)
    result = []
    for mid, row in models.items():
        cost = (Decimal(row["input"]) * row["in"] +
                Decimal(row["output"]) * row["out"]) / MILLION
        cost = cost.quantize(PRECISION)
        result.append({"model_id": mid, "input_tokens": row["input"],
                       "output_tokens": row["output"], "events": row["events"],
                       "estimated_usd": format(cost, ".12f"), "within_budget": cost <= budget})
    result.sort(key=lambda x: (Decimal(x["estimated_usd"]), x["model_id"]))
    return {"schema": REPORT, "valid_input": True,
            "all_within_budget": all(x["within_budget"] for x in result),
            "price_book_revision": revision, "budget_usd": format(budget, ".6f"),
            "events_applied": len(seen), "duplicates_ignored": repeated,
            "models": result, "errors": [],
            "scope": "Synthetic user-supplied prices and usage; not provider billing or model quality."}


def render_html(report: dict) -> str:
    """Escaped local-only HTML. No scripts, tracking or external assets."""
    parts = []
    for row in report["models"]:
        values = [row["model_id"], row["input_tokens"], row["output_tokens"],
                  row["estimated_usd"], "Within" if row["within_budget"] else "Over"]
        parts.append("<tr>" + "".join("<td>" + html.escape(str(v), quote=True) + "</td>"
                                      for v in values) + "</tr>")
    status = "PASS: all models within supplied budget" if report["all_within_budget"] else \
             "HOLD: at least one model exceeds supplied budget"
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
            'style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
            '<title>Offline Model Cost Comparator</title>'
            '<style>body{font:1rem/1.5 system-ui,sans-serif;max-width:52rem;margin:2rem auto;'
            'padding:0 1rem}table{width:100%;border-collapse:collapse}'
            'th,td{padding:.6rem;text-align:left;border-bottom:1px solid #aaa}'
            '.scroll{overflow-x:auto}</style></head><body><main>'
            '<h1>Model cost comparison</h1><p>Fictional user-supplied rates and tokens; '
            'not provider invoices or measured model quality.</p><strong>' +
            html.escape(status) + '</strong><div class="scroll"><table>'
            '<caption>USD estimates from supplied price-book revision</caption>'
            '<thead><tr><th>Model</th><th>Input tokens</th><th>Output tokens</th>'
            '<th>Estimated USD</th><th>Budget status</th></tr></thead><tbody>' +
            "".join(parts) + '</tbody></table></div><p>Price revision: ' +
            html.escape(report["price_book_revision"], quote=True) +
            '</p></main></body></html>')


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline synthetic model cost replay")
    opts = parser.add_mutually_exclusive_group(required=True)
    opts.add_argument("--demo", action="store_true")
    opts.add_argument("--overrun-demo", action="store_true")
    opts.add_argument("--input", type=Path)
    parser.add_argument("--html", type=Path, help="Local HTML report path")
    args = parser.parse_args()
    try:
        data = fixture(overrun=args.overrun_demo) if args.demo or args.overrun_demo else \
               parse_manifest(args.input.read_text(encoding="utf-8"))
        report = compare(data)
        if report["valid_input"] and args.html:
            args.html.write_text(render_html(report), encoding="utf-8")
    except (OSError, UnicodeError, ValueError, InvalidOperation, json.JSONDecodeError) as exc:
        report = _error("input/output rejected: " + str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 2 if not report["valid_input"] else (0 if report["all_within_budget"] else 1)


if __name__ == "__main__":
    raise SystemExit(main())

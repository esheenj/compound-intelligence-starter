"""Compare bounded benchmark snapshots without inventing continuous improvement.

Reports must have compatible dataset, mode, and model identities. A score
change describes these recorded outcomes; it never proves causal learning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from .benchmark import REPORT_SCHEMA
from .engine import canonical

MAX_REPORT_SIZE = 1_000_000


def read_report(path: Path) -> dict:
    path = Path(path)
    if path.stat().st_size > MAX_REPORT_SIZE:
        raise ValueError("benchmark report exceeds 1 MB")
    report = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("benchmark report must be a JSON object")
    validate_report(report)
    return report


def validate_report(report: dict) -> None:
    if report.get("schema") != REPORT_SCHEMA:
        raise ValueError("unknown report schema")
    if report.get("run_mode") not in ("SIMULATED_FIXTURE", "MODEL_PROPOSALS"):
        raise ValueError("unknown evidence origin")
    digest = report.get("dataset_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("missing dataset fingerprint")
    models = report.get("models")
    if not isinstance(models, list) or not 1 <= len(models) <= 4:
        raise ValueError("expected 1-4 model summaries")
    names = []
    for entry in models:
        if not isinstance(entry, dict) or not isinstance(entry.get("model"), str):
            raise ValueError("invalid model record")
        names.append(entry["model"])
        stats = entry.get("overall")
        if not isinstance(stats, dict):
            raise ValueError("invalid model statistics")
        attempt = stats.get("attempted")
        verified = stats.get("verified")
        rejected = stats.get("rejected")
        missing = stats.get("no_result")
        if any(type(v) is not int or v < 0 for v in (attempt, verified, rejected, missing)):
            raise ValueError("invalid result counts")
        if attempt != verified + rejected + missing or attempt <= 0:
            raise ValueError("inconsistent result counts")
        score = stats.get("verified_per_attempt")
        if type(score) not in (int, float) or abs(score - round(verified / attempt, 4)) > 0.000051:
            raise ValueError("inconsistent score")
    if len(set(names)) != len(names):
        raise ValueError("duplicate model identity")


def compare_reports(before: dict, after: dict) -> dict:
    validate_report(before)
    validate_report(after)
    if before["dataset_sha256"] != after["dataset_sha256"]:
        raise ValueError("different datasets; not comparable")
    if before["run_mode"] != after["run_mode"]:
        raise ValueError("fixture and real-model runs cannot be compared")
    old = {x["model"]: x["overall"] for x in before["models"]}
    new = {x["model"]: x["overall"] for x in after["models"]}
    if set(old) != set(new):
        raise ValueError("different model identities")
    changes = []
    for model in sorted(old):
        a, b = old[model], new[model]
        if a["attempted"] != b["attempted"]:
            raise ValueError("different attempt counts")
        delta = b["verified"] - a["verified"]
        changes.append({
            "model": model, "previous_verified": a["verified"],
            "current_verified": b["verified"], "attempted": b["attempted"],
            "change_in_verified": delta,
            "outcome": "MORE_VERIFIED" if delta > 0 else "FEWER_VERIFIED" if delta < 0 else "UNCHANGED",
        })
    return {
        "schema": "compound-progress-v1",
        "dataset_sha256": before["dataset_sha256"],
        "run_mode": before["run_mode"],
        "models": changes,
        "interpretation": (
            "Descriptive change on identical benchmark definitions only. "
            "This does not prove learning, generalization, or causation; rerun "
            "with independent tasks and real model provenance before claiming improvement."
        ),
    }


def receipt(report: dict, run_id: str) -> dict:
    validate_report(report)
    if not isinstance(run_id, str) or not run_id.isdigit() or len(run_id) > 20:
        raise ValueError("run id must be an opaque numeric execution identifier")
    return {
        "schema": "compound-cycle-receipt-v1",
        "run_id": run_id,
        "evidence_origin": report["run_mode"],
        "dataset_sha256": report["dataset_sha256"],
        "benchmark_sha256": hashlib.sha256(canonical(report).encode()).hexdigest(),
        "model_count": len(report["models"]),
        "task_count": report.get("task_count"),
        "status": "RECORDED_NOT_PROMOTED",
        "claim": "Snapshot only: no model training, promotion, or automatic code change",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    cycle = commands.add_parser("receipt")
    cycle.add_argument("--report", type=Path, required=True)
    cycle.add_argument("--run-id", required=True)
    cycle.add_argument("--output", type=Path, required=True)
    changes = commands.add_parser("compare")
    changes.add_argument("--before", type=Path, required=True)
    changes.add_argument("--after", type=Path, required=True)
    changes.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "receipt":
        result = receipt(read_report(args.report), args.run_id)
    else:
        result = compare_reports(read_report(args.before), read_report(args.after))
    output = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

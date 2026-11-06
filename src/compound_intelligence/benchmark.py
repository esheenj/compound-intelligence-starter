"""v0.5: reproducible exact-match benchmark reports, no code execution."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from .challenges import compare, validate_task
from .engine import canonical
from .problem_runner import fixture, propose_ollama

REPORT_SCHEMA = "compound-benchmark-v1"


def wilson_interval(passed: int, total: int, z: float = 1.96) -> list[float] | None:
    """95% Wilson score interval, descriptive only; never a model confidence claim."""
    if total <= 0:
        return None
    p = passed / total
    denominator = 1 + z * z / total
    midpoint = (p + z * z / (2 * total)) / denominator
    radius = (z / denominator) * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
    return [round(max(0, midpoint - radius), 4), round(min(1, midpoint + radius), 4)]


def metrics(rows: list[dict]) -> dict:
    """NO_RESULT counts against attempts; report conditional accuracy separately."""
    total = len(rows)
    verified = sum(row["status"] == "VERIFIED" for row in rows)
    rejected = sum(row["status"] == "REJECTED" for row in rows)
    missing = sum(row["status"] == "NO_RESULT" for row in rows)
    if verified + rejected + missing != total:
        raise ValueError("unknown evaluation status")
    answered = verified + rejected
    return {
        "attempted": total, "verified": verified, "rejected": rejected, "no_result": missing,
        "completion_rate": round(answered / total, 4) if total else None,
        "verified_per_attempt": round(verified / total, 4) if total else None,
        "exact_match_given_answer": round(verified / answered, 4) if answered else None,
        "verified_per_attempt_wilson95": wilson_interval(verified, total),
    }


def generate(tasks: list[dict], models: list[str], workspace: Path, proposer,
             *, version: str = "v0.5", fixture_mode: bool = False) -> dict:
    # compare preflights task count, model identifiers and individual task schema.
    result = compare(tasks, models, workspace, proposer, version=version)
    keyed = {task["id"]: task["type"] for task in tasks}
    groups = []
    for model in models:
        model_rows = [x for x in result["results"] if x["model"] == model]
        by_type = {
            kind: metrics([row for row in model_rows if keyed[row["task"]] == kind])
            for kind in sorted(set(keyed.values()))
        }
        groups.append({"model": model, "overall": metrics(model_rows), "by_task_type": by_type})
    payload = {
        "schema": REPORT_SCHEMA,
        "dataset_sha256": hashlib.sha256(canonical(tasks).encode()).hexdigest(),
        "task_count": len(tasks), "model_count": len(models),
        "experiment_version": version,
        "run_mode": "SIMULATED_FIXTURE" if fixture_mode else "MODEL_PROPOSALS",
        "models": groups,
        "results": result["results"],
        "limitations": (
            "This is an exact-reference benchmark on a tiny dataset. "
            "Static code patches are never executed. Wilson ranges are descriptive "
            "binomial intervals, not evidence of general model reliability. "
            "Fixture results are simulated; local model results are not independently audited."
        ),
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, default=Path("examples/challenges.json"))
    parser.add_argument("--workspace", type=Path, default=Path("local-data/v05"))
    parser.add_argument("--fixture", action="store_true", help="clearly labeled simulated benchmark")
    parser.add_argument("--models", nargs="+", help="up to 4 actual local Ollama models")
    parser.add_argument("--version", default="v0.5")
    parser.add_argument("--output", type=Path, help="optional JSON report output path")
    args = parser.parse_args()
    if args.fixture == bool(args.models):
        parser.error("choose exactly one of --fixture and --models")
    tasks = json.loads(args.tasks.read_text(encoding="utf-8"))
    names = ["fixture-correct", "fixture-incorrect"] if args.fixture else args.models
    outcome = generate(tasks, names, args.workspace,
                       fixture if args.fixture else propose_ollama,
                       version=args.version, fixture_mode=args.fixture)
    document = json.dumps(outcome, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(document + "\n", encoding="utf-8")
    print(document)


if __name__ == "__main__":
    main()

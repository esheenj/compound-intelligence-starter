"""v1.1 paired, bounded A/B evaluation of retrieved exemplars.

Baseline and assisted conditions use the same held-out tasks and model identity.
No answer reference is ever sent to a proposer. This is not model training.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from .challenges import evaluate, public_task, validate_task
from .engine import canonical
from .learning_loop import KnowledgeStore, offline_fixture
from .problem_runner import propose_ollama

MAX_TASKS = 10


def _digest(obj: object) -> str:
    return hashlib.sha256(canonical(obj).encode()).hexdigest()


def _outcome(task: dict, proposal: object) -> tuple[str, str]:
    if isinstance(proposal, dict) and set(proposal) == {"_error"}:
        return "NO_RESULT", str(proposal["_error"])[:100]
    result = evaluate(task, proposal)
    return result["status"], result["reason"]


def _invoke(proposer, model: str, prompt_task: dict, task: dict) -> dict:
    try:
        proposal = proposer(model, prompt_task)
        status, reason = _outcome(task, proposal)
    except (ValueError, TypeError, RuntimeError, OSError, TimeoutError) as exc:
        status, reason = "NO_RESULT", type(exc).__name__
    return {"status": status, "reason": reason}


def evaluate_pairs(seeds: list[dict], targets: list[dict], workspace: Path,
                   model: str, proposer, *, run_id: str,
                   max_examples: int = 3) -> dict:
    """Persist a receipt only after both arms for every task finish.

    If the process is interrupted before commit, requests may recur. No
    exactly-once external inference or causal improvement is claimed.
    """
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", run_id):
        raise ValueError("invalid run ID")
    if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,128}", model):
        raise ValueError("invalid model name")
    if (not isinstance(seeds, list) or not isinstance(targets, list) or
            not 1 <= len(seeds) <= MAX_TASKS or not 1 <= len(targets) <= MAX_TASKS):
        raise ValueError("provide 1-10 seed and 1-10 held-out tasks")
    if type(max_examples) is not int or not 0 <= max_examples <= 3:
        raise ValueError("max_examples must be 0-3")
    for task in seeds + targets:
        validate_task(task)
    ids = [task["id"] for task in seeds + targets]
    if len(set(ids)) != len(ids):
        raise ValueError("seed and target IDs must be unique")
    # Fixed dataset/arm identities make result recovery and comparisons auditable.
    spec = {"schema": "paired-v1", "seeds": seeds, "targets": targets,
            "model": model, "max_examples": max_examples}
    store = KnowledgeStore(Path(workspace) / "knowledge.sqlite3")
    try:
        prior = store.receipt(run_id, spec)
        if prior is not None:
            return {**prior, "reused_receipt": True}
        seeded = 0
        for seed in seeds:
            seed_prompt = public_task(seed)
            if proposer is offline_fixture:
                seed_prompt = {**seed_prompt, "verified_examples": [{"format": seed["type"]}]}
            proposed = proposer(model, seed_prompt)
            if isinstance(proposed, dict) and store.remember(seed, proposed):
                seeded += 1
        results = []
        for index, target in enumerate(targets):
            task_prompt = public_task(target)
            examples = store.relevant(target, max_examples)
            # Alternate arm ordering across tasks to expose simple order effects.
            order = ("baseline", "assisted") if index % 2 == 0 else ("assisted", "baseline")
            arms = {}
            for condition in order:
                prompt = dict(task_prompt)
                if condition == "assisted":
                    prompt["verified_examples"] = examples
                arms[condition] = _invoke(proposer, model, prompt, target)
            results.append({
                "task": target["id"], "baseline": arms["baseline"],
                "assisted": arms["assisted"], "invocation_order": list(order),
                "retrieved_ids": [e["source_id"] for e in examples],
                "retrieved_digests": [e["source_digest"] for e in examples],
            })
        baseline = sum(x["baseline"]["status"] == "VERIFIED" for x in results)
        assisted = sum(x["assisted"]["status"] == "VERIFIED" for x in results)
        gains = sum(x["baseline"]["status"] != "VERIFIED" and x["assisted"]["status"] == "VERIFIED" for x in results)
        losses = sum(x["baseline"]["status"] == "VERIFIED" and x["assisted"]["status"] != "VERIFIED" for x in results)
        output = {
            "schema": "compound-ab-evaluation-v1", "run_id": run_id,
            "model": model, "dataset_sha256": _digest({"seeds": seeds, "targets": targets}),
            "origin": "SIMULATED_FIXTURE" if proposer is offline_fixture else "LOCAL_MODEL_PROPOSALS",
            "task_count": len(targets), "new_verified_seeds": seeded,
            "baseline_verified": baseline, "assisted_verified": assisted,
            "paired_gains": gains, "paired_losses": losses,
            "net_verified_change": assisted - baseline,
            "results": results, "reused_receipt": False,
            "status": "RECORDED_NOT_PROMOTED",
            "interpretation": (
                "Descriptive paired outcomes only. A simulated fixture is not real model uplift; "
                "even real-model differences on small selected datasets do not prove causal "
                "improvement or generalization. No generated code was executed."
            ),
        }
        return store.commit(run_id, spec, output)
    finally:
        store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=Path, default=Path("examples/challenges.json"))
    parser.add_argument("--targets", type=Path, default=Path("examples/transfer_challenges.json"))
    parser.add_argument("--workspace", type=Path, default=Path("local-data/v11"))
    parser.add_argument("--run-id", default="ab-demo-001")
    parser.add_argument("--max-examples", type=int, default=3)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--fixture", action="store_true", help="scripted simulation, not model inference")
    group.add_argument("--model", help="locally installed Ollama model")
    options = parser.parse_args()
    seeds = json.loads(options.seeds.read_text(encoding="utf-8"))
    targets = json.loads(options.targets.read_text(encoding="utf-8"))
    if options.fixture:
        seeds = [x for x in seeds if x["type"] == "extract"]
    provider = offline_fixture if options.fixture else propose_ollama
    result = evaluate_pairs(
        seeds, targets, options.workspace,
        "fixture-transfer" if options.fixture else options.model,
        provider, run_id=options.run_id, max_examples=options.max_examples,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

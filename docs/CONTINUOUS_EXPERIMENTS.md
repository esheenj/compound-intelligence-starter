# Bounded recurring experiments — v0.9

The public repository's **existing** daily `Read-only public feedback intake` workflow also runs a tiny offline benchmark and stores a second, explicitly labeled artifact. The benchmark is an educational fixture and uses no paid model or private Esheen infrastructure.

## What actually runs

1. GitHub starts the existing scheduled workflow (or an owner triggers `workflow_dispatch`).
2. The workflow runs the unit-tested offline fixture benchmark in a fresh directory.
3. It generates a content-digested cycle receipt, marked `RECORDED_NOT_PROMOTED`.
4. The workflow uploads the report and receipt as short-retention artifacts.
5. The existing public-feedback read-only intake remains independent; no orders, deployments, repository writes, or unsandboxed code execution occur.

Each GitHub-hosted runner starts with a fresh filesystem. **No cross-run memory is implied** by the schedule. Download two artifact reports to compare them using the CLI:

```bash
python -m src.compound_intelligence.progress compare \
  --before path/to/older-benchmark.json \
  --after path/to/newer-benchmark.json \
  --output local-data/comparison.json
```

If the dataset fingerprint, origin, or model identities differ, comparison fails instead of announcing progress. If identical fixture experiments produce identical results, the outcome is **UNCHANGED**, not an improvement. No model is trained, no strategy is promoted, and a passing CI run is not evidence that real-model intelligence improved.

## Run locally

```bash
python -m src.compound_intelligence.benchmark --fixture \
  --workspace local-data/v09 \
  --output local-data/benchmark.json
python -m src.compound_intelligence.progress receipt \
  --report local-data/benchmark.json --run-id 123 \
  --output local-data/receipt.json
```

## Boundaries and cost

The existing schedule runs once daily. Artifact retention is two days; download artifacts before retention expires if you want longer history. It is subject to GitHub-hosted runner availability and repository settings, so an installed workflow does not guarantee future execution. The schedule is limited to the public educational repo, requires no external credentials, and keeps additional recurring infrastructure spend at R0. The default fixture benchmark is not a live local Ollama run.

For genuine continuous learning, the next step is an explicitly approved persistent evidence store and a model-enabled local worker with bounded resource limits, repeatable independent tests, and version-attested model identities.

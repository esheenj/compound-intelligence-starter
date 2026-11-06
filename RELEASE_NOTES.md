# Compound Intelligence Starter v1.1.0

**Release classification: complete educational/open-source MVP.**

A free, runnable framework for the pattern **Discover → Challenge → Test → Learn → Repeat**. It demonstrates how to preserve validated evidence, retrieve previously verified examples, compare different proposals, and measure baseline versus assisted outcomes on bounded tasks.

## Included

- Python 3.10+ standard-library implementation, MIT license and simple CLI demonstrations.
- Independent exact-match validators for typed information extraction and static text patches; **generated code is never executed**.
- SQLite-backed evidence, run receipts, bounded offline job queue, retry/recovery examples, and a read-only HTML evidence dashboard.
- Optional local Ollama proposals; the public CI exercises simulated offline fixtures rather than real models.
- Verified-example retrieval, paired baseline/assisted comparisons, descriptive benchmark reporting and reproducible task fixtures.
- Read-only public GitHub feedback index with bounded workflow artifacts and no repository write permission.
- Automated GitHub Actions tests for the supported Python versions.

## Try the MVP

```bash
python -m unittest discover -s tests -v
python -m src.compound_intelligence.learning_loop --fixture
python -m src.compound_intelligence.ab_evaluation --fixture
python -m src.compound_intelligence.scheduler enqueue --id final-demo
python -m src.compound_intelligence.scheduler tick
python -m src.compound_intelligence.dashboard --queue-db local-data/v06/queue.sqlite3 --output local-data/dashboard.html
```

The demonstrations store local evidence. The paired A/B fixture deliberately models an assisted gain; this **does not demonstrate real language-model learning or causal improvement**. Consult [v1.0](docs/V1.0.md), [v1.1](docs/V1.1.md), and [contributor extension guidance](docs/EXTENDING.md).

## Explicitly out of scope

- No always-on Cortex/Commander deployment, private configuration or infrastructure access.
- No autonomous source edits, test execution of generated code, unattended merges or trading authority.
- No proof of generalized intelligence, training, statistically defensible real-model uplift, or persistent scheduled model-learning cycles.
- No new recurring infrastructure costs required by the starter.

**Status:** v1.1.0 freezes this public MVP baseline; advanced capabilities should evolve in separate, permissioned projects.

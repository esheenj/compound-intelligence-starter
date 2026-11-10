# Open Intelligence — Wave 1 additional offline guards

This file documents two original educational utilities added under the public roadmap issue #40 / Wave 1 issue #41. These tools do not contact paid AI APIs, payment services, inference endpoints, customer data, private infrastructure or live agent executors.

## Prompt Regression Guard

At the repository root (Python 3.10+):

    python -m src.compound_intelligence.prompt_regression_guard --demo
    python -m src.compound_intelligence.prompt_regression_guard --regression-demo

The first example exits 0 and passes. The second deliberately exits **1** with a critical-case regression, even though the overall fixture average improves. Input is supplied scores only: schema prompt-regression.cases.v1 with identical baseline/candidate case IDs, immutable critical flags, and integer scores from 0 to 100. Exit 2 indicates malformed inputs.

This is not an autonomous model evaluator, factual claim checker or a measurement of actual prompt quality. Real usage must define how and when scores were gathered and guard against cherry-picked cases.

## Agent Budget Guard

    python -m src.compound_intelligence.agent_budget_guard --demo
    python -m src.compound_intelligence.agent_budget_guard --overrun-demo

The first example admits two original synthetic credit events (25 + 35), ignoring an identical duplicate, under a cap of 100. The second exceeds a cap of 50 and intentionally exits **1** with no admitted final accounting. Exit 2 indicates malformed input.

Input schema agentbudget.events.v1 contains synthetic integer credit limits per agent and an event list. This is an offline, in-memory deterministic policy demonstration. No live token usage, prices, actual subscription credits, concurrency transactions, payment reconciliation or real agent authorization.

## Checks and release scope

    python -m unittest discover -s tests -p 'test_*guard.py' -v

The actual repository CI runs all unit tests on Python 3.10 and 3.12 plus existing Chrome smoke tests. Release acceptance is exact-head green CI, source rights review, and no leaked private records. These new utilities are source-level add-ons within the existing public repo, **not independent packages or hosted web tools**. R0 added recurring cost.

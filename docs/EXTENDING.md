# Extending the starter safely

The public MVP uses intentionally **fixed, typed validators**. The extension point is source-level: contribute a narrowly scoped task schema and trusted validator with synthetic tests. There is no dynamic plugin loader or permission to execute third-party code.

1. Define a new bounded task type in `src/compound_intelligence/challenges.py:validate_task`. Reject oversized or malformed inputs and keep expected reference answers separate from model prompts.
2. Extend `public_task` to expose only task instructions, never `expected` reference data.
3. Extend `evaluate` with an independently checkable predicate and a meaningful failure reason. Do **not** call `eval`, `exec`, a subprocess or a model to decide truth.
4. Add synthetic examples and regression tests for success, counterexamples, malformed input, withheld reference data and replay.
5. If relevant, extend the opt-in prompt adapter in `problem_runner.py`. Its output remains a proposal, not verification authority.
6. Run `python -m unittest discover -s tests -v` and propose a narrow PR. Independent reviewer judgment is required before publishing a new capability.

For executable-code evaluation, a separate, independently reviewed sandbox project is required. This starter never runs untrusted proposed source.

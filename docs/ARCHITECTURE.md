# Architecture and expansion contracts

The first release separates five responsibilities: proposal, adversarial challenge, deterministic validation, evidence retention, and bounded continuation.

## Suggested future message contracts

- **Task envelope:** opaque task ID, owner, scope, budget, deadline, allowed capabilities, execution authority.
- **Research advisory:** evidence, uncertainty, competing hypotheses, source provenance; *never an execution authorization*.
- **Validation receipt:** test identity, input digest, assertion results, artifacts, runtime identity.
- **Knowledge record:** claim, outcome, provenance, timestamp, counterexamples, reviewer and promotion state.
- **Execution receipt:** requested action, admitted policy, result, immutable correlation ID and recovery instructions.

## Principles

1. New findings are not trusted simply because a model repeated or remembered them.
2. Proposals and executions have different permissions; external side effects must be explicitly approved or scoped.
3. Experiments are bounded by a finite iteration count, compute budget, and explicit stop conditions.
4. Failures are retained as evidence without automatically granting new capabilities.
5. Secrets and internal endpoints stay out of the public release.

## Demonstration limitations

The bundled ledger is local JSONL, without multi-writer locking or tamper-proof signing. The deterministic demo does not perform web retrieval, invoke LLMs, deploy code, or operate autonomously after the command exits. Treat it as a verified learning-loop *pattern*, not production-grade agent infrastructure.

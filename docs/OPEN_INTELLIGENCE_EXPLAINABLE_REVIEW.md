# Explainable AI Decision Review Lab — public fictional reference

A usable **offline explanation and review sandbox** for AI-inspired proposals. It shows evidence links, source versions, disagreements, self-reported evaluation samples, impact and fictional reviewer records. All data is invented or user supplied. This is **not** a real AI decision service, factual truth certification, human approval integration or permission to execute an action.

## Quickstart

Python 3.10+ with no dependencies and no network:

```sh
python -m src.compound_intelligence.explainable_review --demo
python -m src.compound_intelligence.explainable_review --demo --html /tmp/explainable-review.html
python -m unittest discover -s tests -p 'test_explainable_review.py' -v
```

Use `--input some-public-fixture.json` for your own **synthetic non-sensitive data**, capped at 64 KiB. Avoid real personal, client, workplace, financial, Cortex/Commander, SIGMA, credentials, private incident records and unreviewed logs. CLI exports JSON and optional script-free, HTML-escaped local review output. It never calls a model API or hosts a server.

## Evidence schema and gate semantics

Schema `explainable-review.fixtures.v1`:

- `sources`: 1–100 synthetic entries with unique `source_id`, `statement`, integer `revision` and `evidence_status` (`DECLARED_VERIFIED` or `HYPOTHESIS`).
- `decisions`: 1–50 hypothetical proposals with `decision_id`, `action`, `impact` (`LOW` or `HIGH`), `support` and `oppose` arrays of exact `{source_id,revision}` references, `review` (`PENDING`, `RECORDED_APPROVE`, or `RECORDED_REJECT`) and a `confidence` object.
- Confidence is either `{method:"NONE",correct:null,cases:null}` or `{method:"SELF_REPORTED_SAMPLE",correct:8,cases:10}`. **8/10 is merely a self-reported fictional sample, not an 80% probability of truth, calibrated confidence, or a prediction of success.**

**HOLD** means unresolved safety-critical explanation blockers: no supporting citation, opposing evidence, missing source, stale revision, source labeled a hypothesis, or simulated reviewer rejection.

**HUMAN_REVIEW_REQUIRED** means the references are structurally acceptable but the proposed decision is high-impact, its simulated review is pending, or the confidence methodology is absent.

**REVIEW_RECORDED_NOT_AUTHORIZED** means a low-impact hypothetical decision has matching declared references, no opposing sources, a supplied sample method and a fictional recorded approval. It **never** means an authorized execution; the report and every result explicitly specify `execution_authority: NONE`.

No labels in the source manifest are independently authenticated. The tool does not establish semantic entailment between evidence and proposed action, correctness, quality of reviewer identity, score calibration or real-world policy compliance. In particular, `DECLARED_VERIFIED` is just the supplied input's claim.

## Built-in examples

| Fictional decision | Gate | Reason |
| --- | --- | --- |
| `routine` | REVIEW_RECORDED_NOT_AUTHORIZED | Low impact, matched source revision, self-reported 8/10 sample and fictional review record |
| `high-impact` | HUMAN_REVIEW_REQUIRED | A 9/10 claimed sample does not bypass impact review |
| `contradicted` | HOLD | Opposing source reference |
| `stale` | HOLD | Claimed reference points to an old source revision |
| `unverified` | HOLD | Source is a hypothesis even if reviewer was marked approved |
| `unscored` | HUMAN_REVIEW_REQUIRED | No confidence methodology and review pending |

Adversarial tests reject duplicate IDs/JSON keys, invalid source labels, unknown/colliding references, invalid sample counts, malformed Unicode, oversized inputs and unexpected fields. Unknown source IDs and empty support **fail to HOLD**, never quietly become valid evidence. All diagnostics are deterministic with input SHA-256; no actual remote model or human reviewer is contacted.

Existing complementary tools are [Context Preservation](OPEN_INTELLIGENCE_CONTEXT_PRESERVATION.md) and [Model Disagreement](OPEN_INTELLIGENCE_MODEL_DISAGREEMENT.md). This slice focuses on **human-readable decision explanations**, not a new layer of infrastructure.

Public tracker: [Wave 3 #43](https://github.com/esheenj/compound-intelligence-starter/issues/43). All engineering is original/fictional and R0 additional recurring infrastructure cost.

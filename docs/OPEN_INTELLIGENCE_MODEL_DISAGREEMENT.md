# Model Disagreement Lab — original offline public experiment

The lab compares **user-supplied fictional outputs** of two to eight AI agents across up to forty example cases. It surfaces split answers, unanimous-but-wrong answers relative to a caller-supplied reference, absent responses, abstentions and consensus without a reference. It does **not** call, benchmark, train or judge actual models.

**The central failure mode:** three agents may all agree on an invented answer and still disagree with a supplied reference. Agreement is a *signal*, not validation or confidence calibration. A supplied reference may itself be wrong, unauthenticated or incomplete.

## Run locally

With Python 3.10+ from the public repository root:

```sh
python -m src.compound_intelligence.model_disagreement --demo
python -m src.compound_intelligence.model_disagreement --demo --html /tmp/model-disagreement.html
python -m unittest discover -s tests -p 'test_model_disagreement.py' -v
```

To use your own **sanitized non-sensitive** inputs, pass `--input /path/to/fictional.json`. Never commit real private LLM conversations, client data, prompt secrets, trading/exchange keys, owner grants, financial records or other control-plane material into a public repository. No third-party API or subscription is needed.

## Input contract

Schema `model-disagreement.fixtures.v1`: `models` array with two to eight unique model ID strings, and `cases` array with one to forty cases. Each case includes `case_id`, Boolean `critical`, optional string/null `reference` and a `responses` array. A response has `model_id`, `status` (either `ANSWER` or `ABSTAIN`), and `answer` (a nonblank string for ANSWER, null for ABSTAIN). Missing models remain **missing**, never silently synthesized or assumed to agree. No duplicate identifiers/fields are accepted; JSON input is capped at 64 KiB.

## Cases and outcomes

| Example case | Outcome | Interpretation |
| --- | --- | --- |
| `unverified-consensus` | UNVERIFIED_CONSENSUS | Every fictional model agrees but no reference exists; manual review |
| `split-critical-decision` | DISAGREEMENT | Two of three match a supplied reference; one contradicts it |
| `unanimous-wrong` | CONTRADICTS_SUPPLIED_REFERENCE | All three agree on an answer that conflicts with the supplied reference |
| `missing-and-abstained` | INCOMPLETE | One response, one abstention, one missing model |
| `matches-supplied` | MATCHES_SUPPLIED_REFERENCE | All three match a caller-supplied reference; *not* independent truth verification |

A case with zero substantive answers reports `NO_ANSWERS`. `REVIEW` flags unverified, incomplete, split or contradicting examples. `REFERENCE_MATCH_ONLY` denotes merely that all *supplied* answers match the *supplied* reference, not that the answer is true or that any live action is approved.

The report includes deterministic SHA-256 over its original input, per-case answer groups, model IDs, exact observations and missing/abstained counts, plus a script-free escaped HTML report. Repeated input gives identical output. Changing data yields a different digest. Tests cover malformed input, duplicate IDs, abstention/answer inconsistency, unknown models, HTML injection, invalid Unicode and the unanimous-wrong case.

## Reuse and limitations

This is distinct from the existing `context_preservation.py` (source/version retention), `ab_evaluation.py` (paired evaluated tasks) and `prompt_regression_guard.py` (supplied score regression). It is a **descriptive disagreement triage utility** without AI model calls, probability calibration, semantic comparison, reliable truth, independent producer attribution or policy enforcement.

To progress to genuine model evidence, independently qualify response collection, pin model/version/prompt/temperature and fixture rights, use held-out references, capture cost/latency, record uncertainty and compare to baseline on actual data. The presented fixture cannot justify automated financial actions or claims of generalized intelligence.

Wave 3 issue [#43](https://github.com/esheenj/compound-intelligence-starter/issues/43). Additional recurring spend **R0**.

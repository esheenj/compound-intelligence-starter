# Context Preservation Benchmark — evidence-grounded fictional handovers

A compact, **falsifiable and offline** example for assessing whether an AI conversation handover, compacted memory or worker checkpoint *preserves exact critical facts*, source identifiers, source versions and evidence classification. It directly addresses the risk that a confident-looking summary silently changes an assumption into a fact or invents execution authority.

This tool **does not call an AI**, compare semantic paraphrases, evaluate model comprehension, verify independent provenance, test real Cortex/Commander memory or imply that longer summaries are better. It complements—not replaces—the repository's existing `learning_loop.py` retrieval and `ab_evaluation.py` paired inference scaffold.

## Try it

From the public repository root with Python 3.10+ standard library:

    python -m src.compound_intelligence.context_preservation --demo
    python -m src.compound_intelligence.context_preservation --demo --html /tmp/context-preservation.html
    python -m unittest discover -s tests -p 'test_context_preservation.py' -v

The CLI accepts your own **non-sensitive, deliberately sanitized** local JSON with `--input path/to/fixture.json`. Do not upload private chats, API credentials, finance/trading execution secrets, customer data or corporate text to a public repository. No model or network connection is required, and the generated HTML report is local, script-free and escaped.

## Evaluation model

Input schema: `context-preservation.v1`, with one `source` and 1–10 `candidates` to compare. The source has `source_id`, integer `version`, and 1–100 synthetic `facts`. Each fact has a unique `fact_id`, string `value`, `source_ref`, `importance` (`CRITICAL` or `SUPPORTING`) and `evidence_status` (`DECLARED_VERIFIED` or `HYPOTHESIS`). Here *declared verified* is still just an untrusted statement from the input, not externally attested truth.

Every candidate has `candidate_id` and checkpoint `entries` with `fact_id`, `value`, `source_ref`, `source_version` and `evidence_status`. The evaluator holds the reference corpus separately from each candidate. It compares exact field values only:

- `RETAINED`: exact value, provenance reference, source version and evidence label match.
- `MISSING`: a reference fact was omitted.
- `STALE_VERSION`: a carried entry points to an older/different source version.
- `CONTRADICTED_VALUE`: a carried value contradicts the reference.
- `PROVENANCE_DRIFT`: a source reference changed.
- `EVIDENCE_STATUS_DRIFT`: a hypothesis was upgraded to a claim or the label was downgraded.
- `UNSUPPORTED`: the checkpoint contains a fact ID absent from the trusted reference set.

A checkpoint is **HOLD** when any critical fact is not exactly retained or any stale, contradictory, unsupported, provenance-drifted or evidence-drifted item exists. A checkpoint is **PASS_CRITICAL_ONLY** when all critical facts match and optional supporting facts are missing, but no unsafe drift occurs; **PASS_LOSSLESS** only when every reference fact is matched and no unsupported extra claims appear. This is a conservative local *text-preservation gate*, not permission to act on any fact.

The report includes deterministic SHA-256 digests of the source and input, per-fact outcomes and a byte-count comparison of canonical JSON source facts vs checkpoint entries. **Bytes are not tokenizer counts**. Input is capped at 64 KiB and bounded source/entry IDs, candidate counts and versions are rejected if malformed. Identical inputs yield identical reports; changed input cannot reuse the same digest.

## Built-in counterexamples

The fixture uses an invented public project where critical facts include disabled trading authority, zero extra recurring spend and a pinned fictional source revision. It includes three handovers:

| Candidate | Expected result | Why |
| --- | --- | --- |
| `brief-chat` | HOLD | Omits three out of four critical facts |
| `evidence-checkpoint` | PASS_LOSSLESS | Exactly carries all seven synthetic facts |
| `unsafe-drift` | HOLD | Has stale version, contradictory capability, hypothesis promotion and invented claim |

Negative tests also cover wrong evidence references, duplicate IDs, Boolean/invalid versions, oversized or unexpected fields, invalid Unicode, duplicate JSON keys and HTML escaping. Treat these as examples of engineering invariants, not measured AI compression accuracy.

## What still needs independent evaluation

To measure a **real** AI's handover quality, pin a licensed model, representative tasks, prompt/context budgets and a trustworthy, withheld reference set; capture repeat runs, exact outputs, token usage, task-quality metrics and error distributions. Run paired arms on the same held-out tasks using existing `ab_evaluation.py` patterns. A retention fixture cannot establish accuracy, reliability, transferable intelligence, semantic understanding, future cost savings or causal improvement.

Public/private boundary: original fixture uses no actual control-plane material, source histories, private SIGMA/Cortex/Commander configuration or finance/exchange order authority. The utility creates no background process, runner, scheduler or additional recurring spend (R0). Public roadmap [Wave 3 #43](https://github.com/esheenj/compound-intelligence-starter/issues/43).

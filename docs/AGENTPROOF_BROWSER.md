# AgentProof Receipt Verifier — public browser demonstration

**Purpose:** let a developer explore whether a user-supplied synthetic agent receipt manifest is *internally consistent*. This does not identify an agent, prove a claim or confer execution authority.

## How to try it

Open the public GitHub Pages directory and choose **AgentProof Receipt Verifier** (direct source path: site/agentproof.html). The fully static page has no account, backend, tracking, remote assets or paid model API.

1. Select **Verify supplied manifest**. Three fictional events have contiguous sequence numbers, unique IDs, claimed producer names and SHA-256 hashes computed from canonical JSON payloads.
2. **Simulate tampering** modifies a payload without changing the original digest. The result must be REJECTED with a digest mismatch.
3. **Duplicate event ID** must flag a replay identity collision. **Remove producer claim** must flag a missing field.
4. **Reset sample** must restore the original valid fixture.
5. Manually edit the JSON to explore unsupported inputs and negative cases. The browser declines duplicate object keys, floating-point JSON numbers, unsafe integers, malformed states and missing digest fields.

The browser uses built-in Web Crypto SHA-256 and TextEncoder for local digest calculations. The comparison uses a deterministic, sorted UTF-8 JSON canonicalization, matching the Python reference on the accepted subset. Browser sample limits are 100 events and 64 KiB; Python source accepts more events and has separate input/CLI checks. This is a deliberate small, auditable teaching slice, not a general untrusted cryptographic receipt service. No user data is transmitted or stored, and pasted information should still be synthetic.

**Crucial limit:** anyone can rewrite an unsigned manifest and recompute all digest hashes. Internally consistent hashes cannot establish who produced a manifest or whether a claimed action happened. A real identity-verification product must add independent signatures, certificate/key lifecycle, authenticated issuer enrolment, trustworthy event sources, replay safety and scoped authority. These facilities are NOT implemented in this public demo.

## Engineering and verification

- Reference Python source: src/compound_intelligence/agentproof.py
- Reference tests: tests/test_agentproof.py
- Public browser source: site/agentproof.html
- Stager: scripts/stage_showcase.py only publishes allowlisted source and produces SHA-256 artifact evidence.
- Browser QA: tests/browser_check_showcase.py validates positive/negative cases and responsive layouts using Chrome in CI.
- Public issue: https://github.com/esheenj/compound-intelligence-starter/issues/41

Source review, PR-head CI, merged-main CI, provider Pages deployment and independently observed external HTTPS behaviour are separate checkpoints. Never infer one from another. No external LLM inference, financial billing, real autonomous agent or private Cortex/Commander/SIGMA code; R0 additional recurring spend.

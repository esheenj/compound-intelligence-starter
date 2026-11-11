# Agent Trust & Identity Claims Lab — simulated public verification boundaries

This original Python utility is a **diagnostic identity-claim mismatch checker**, not a registry of real people or agents. It compares a fictional agent's claimed ID, HTTPS origin, key fingerprint, capability and registry revision with a caller-supplied registry; flags revoked registrations, expired observations, repeat challenge nonces and SHA-256 mismatches. It never asserts that a real agent is who it says it is.

## Try it

```sh
python -m src.compound_intelligence.agent_trust_claims --demo
python -m src.compound_intelligence.agent_trust_claims --demo --html /tmp/agent-trust.html
python -m unittest discover -s tests -p 'test_agent_trust_claims.py' -v
```

Pass `--input /path/to/your-fictional-fixture.json` to inspect your own synthetic public data. All data stays on the device; the CLI makes no requests. Never paste real agent private keys, signed enterprise handshakes, exchange credentials, customer records, employer IP, infrastructure authority, Cortex or SIGMA security material.

## Built-in negative tests

The **eleven** invented claims demonstrate one apparent match and ten holds. The checker detects: unknown agent, revoked registry entry, HTTPS origin mismatch, public key fingerprint mismatch, undeclared capability request, stale registry revision, **both sides** of a reused challenge nonce, expired claim and checksum tampering. Changing the evaluation tick also detects claims not yet valid.

Every case returns `identity_authenticated: false`, `cryptographic_signature_verified: false` and `execution_authority: "NONE"`, even where the checksum, declared fingerprint and registry record match. A self-asserted `SELF_REPORTED_SIGNED` label cannot establish possession of the corresponding private key. SHA-256 alone **cannot authenticate identity**: anyone can recompute a checksum over forged public data.

## Input contract

JSON schema `agent-trust-claims.v1`:

- `evaluation_tick` is an explicit, user-chosen nonnegative integer, **not** a trusted clock or live timestamp.
- `registry` includes 1–50 fictional entries with unique `agent_id`, HTTPS `origin`, 64-character lowercase hex `key_fingerprint`, positive integer `revision`, `state` (`ACTIVE`/`REVOKED`) and 1–16 declared `capabilities`.
- `claims` includes 1–150 observations with unique `claim_id`, `agent_id`, `origin`, `key_fingerprint`, requested `capability`, `registry_revision`, `nonce`, `issued_tick`, `expires_tick`, `proof_claim` (`ABSENT`/`SELF_REPORTED_SIGNED`) and `payload_sha256` as checksum of the other exact claim fields using sorted-keys compact UTF-8 JSON.
- No duplicate JSON object keys or duplicate IDs; input capped at 64 KiB. Nonces are scoped to the same declared agent in this *single* document, not a persistent replay database.

A matching claim reports `CLAIM_MATCH_ONLY` and a mismatching one `HOLD`. Neither is an authorized action.

## Path to actual trusted agent identity

Actual machine-to-machine verification needs **cryptographic challenge/response using independently rooted public keys**, a persistent nonce/replay database, trusted time and registry, key rotation and revocation, scoped permission checks and server-side enforcement. In a subsequent qualified product, verify Ed25519/P-256 signatures over canonical messages with trustworthy trust anchors, and issue short-lived capability tokens only from an authenticated issuer. **Do not** treat this offline exercise as a replacement for that real system.

This work complements [AgentProof receipt integrity](OPEN_INTELLIGENCE_WAVE1.md), [Model Disagreement](OPEN_INTELLIGENCE_MODEL_DISAGREEMENT.md) and [Explainable Decision Review](OPEN_INTELLIGENCE_EXPLAINABLE_REVIEW.md). It contains no private keys, real credentials, production endpoints or instructions to bypass controls. Additional recurring infrastructure spend R0. Public Wave 3 [issue #43](https://github.com/esheenj/compound-intelligence-starter/issues/43).

# Signed Agent Challenge — genuine local P-256 signature verification

This is an original dependency-free **Node.js ECDSA P-256 challenge/response verifier**, not a production agent identity or authorization service.

Source: src/agent_auth/challenge.mjs

Tests: node --test tests/test_agent_auth.mjs (Node.js 20+; no packages, network calls, or committed private keys).

Unlike the previous fictional claim-comparison lab, it uses **real P-256 ECDSA signatures with SHA-256**, verified against a **locally pre-enrolled public JWK**. Test keys are generated ephemerally at runtime. Public enrollment must come from an independently authorized source; this lab does not establish that trust.

## Protocol

1. Independently enroll a public P-256 JWK with agentId, unique keyId, verifier audience, bounded capability list, validity window and ACTIVE or REVOKED state. Private JWK fields are rejected.
2. The verifier issues a secure random 24-byte nonce with the pinned agent/key/audience/capability, issue and expiry times; TTL max 120 seconds. It records the challenge in an owner-controlled local issued ledger.
3. The agent signs a domain-separated UTF-8 message consisting of ESHEEN_AGENT_CHALLENGE_V1, a newline, and the JSON array containing the eight fields in fixed order. P-256 signatures are raw IEEE P1363 64-byte r||s, base64url encoded.
4. The verifier checks key enrollment, audience, capability, exact issued challenge, expiry and real signature. It atomically records nonce consumption in a local used ledger using exclusive file creation. This resists repeats across restarts on a trusted single-host filesystem.
5. Success reports SIGNATURE_VERIFIED_NOT_AUTHORIZED, signatureVerified true and nonceConsumed true. Always independentlyTrustedIdentity false and executionAuthority NONE.

No real action runs. No identity credentials or production keys are shipped. Key compromise, external enrollment provenance, key rotation, replay across multiple hosts, trusted clocks, API authentication/authorization, TLS, HTTP message signatures and secure provisioning are out of scope. In real deployments the ledger and enrollment directory and parent paths must be restricted to the verifier, and replay recording and the action must share a suitably atomic transaction boundary.

**Negative tests** cover invalid key, substituted private key, tampered scope/audience, forged self-issued nonce, expired/future challenge, revoked key, malformed signature, invalid JWK, replay across restart and simultaneous duplicate verification.

This is not an implementation of RFC 9421 HTTP Message Signatures. Its covered-message and replay approach follows general signature safety principles, but HTTP-specific semantics and independent trust-issuer enrollment are not provided. Details: https://www.rfc-editor.org/rfc/rfc9421.html

Follow-on: local browser Web Crypto demonstration with independently verified Pages acceptance. Tracking: https://github.com/esheenj/compound-intelligence-starter/issues/43 . Additional recurring infrastructure spend R0.

# Local public-key enrollment lifecycle

This offline Node example keeps a local, in-memory set of pinned public keys for the
existing signed challenge demo. It never generates, stores, or requests private keys.
Use ephemeral keys from the existing demo when learning.

1. Derive the expected SHA-256 fingerprint from a separately obtained trusted
   public key (DER SubjectPublicKeyInfo). Do not compute the expected value from
   the incoming enrollment request itself. Record the local reviewer and evidence
   reference, then call `enroll(input, unixSeconds)`.
2. Call `rotate(oldKeyId, replacement, unixSeconds)` after independently
   reviewing the new pin. The replacement must preserve agent and audience and
   cannot widen capabilities. Failed rotations leave the old entry unchanged.
3. Call `revoke(keyId, unixSeconds)` to retain a revoked entry. Rebuild the
   challenge verifier with `challengeEnrollments()` after every change. Old verifier
   instances retain their old snapshots; retire them before using a replacement.

The reviewer and evidence reference are caller-supplied provenance labels; they do not
authenticate anyone or prove real-world identity. The registry is in-memory, has no
trust-anchor discovery, persistence, concurrency guarantees across processes or
service authorization. Its revocation applies only to consumers of the new snapshot.
Keep production identity and authorization outside this teaching example.

Run `node --test tests/test_agent_auth.mjs` for positive and negative examples.

## Reject stale snapshots in one process

Call `registry.verifierFor(registry.versionedSnapshot(), {ledgerDir, now})` instead
of constructing a verifier directly. Each successful change advances the generation
once. A guarded verifier refuses to return results if its snapshot has become stale,
including a change during an awaited operation. Rebuild it from a fresh snapshot.
An interrupted operation may have already written a nonce receipt; request a fresh
challenge rather than retrying that nonce. Snapshots are local objects tied to one
registry instance; this does not protect other processes, restarts, persisted state,
or callers that use the original unguarded verifier directly.

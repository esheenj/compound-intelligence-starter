/** Local demonstration registry. Trust in the reviewer and pin is out of band. */
import {createHash, createPublicKey} from "node:crypto";
import {AgentChallengeVerifier} from "./challenge.mjs";

const id = value => typeof value === "string" &&
  /^[A-Za-z0-9][A-Za-z0-9._:/-]{0,79}$/.test(value);
const time = value => Number.isSafeInteger(value) && value >= 0 && value <= 2000000000;
const error = code => { throw new Error(code); };

export function publicKeyFingerprint(jwk) {
  if (!jwk || Object.keys(jwk).length !== 4 || jwk.kty !== "EC" ||
      jwk.crv !== "P-256" || !["x", "y"].every(k =>
        Object.hasOwn(jwk, k) && typeof jwk[k] === "string" &&
        /^[A-Za-z0-9_-]{43}$/.test(jwk[k]) &&
        Buffer.from(jwk[k], "base64url").toString("base64url") === jwk[k]) ||
      !Object.hasOwn(jwk, "kty") || !Object.hasOwn(jwk, "crv")) error("INVALID_PUBLIC_KEY");
  let key;
  try { key = createPublicKey({key: jwk, format: "jwk"}); }
  catch { error("INVALID_PUBLIC_KEY"); }
  return createHash("sha256").update(key.export({type: "spki", format: "der"})).digest("hex");
}

export class LocalEnrollmentRegistry {
  #rows = new Map();
  #fingerprints = new Set();
  #lastChange = 0;
  #generation = 0;
  #snapshots = new WeakSet();

  #prepare(input, at) {
    if (!input || !time(at) || at < this.#lastChange) error("INVALID_CHANGE_TIME");
    const {agentId, keyId, audience, capabilities, publicJwk, validUntil,
      reviewer, evidenceRef, expectedFingerprint} = input;
    if (![agentId, keyId, audience, reviewer, evidenceRef].every(id) ||
        !Array.isArray(capabilities) || capabilities.length < 1 || capabilities.length > 16 ||
        !Array.from(capabilities).every(id) || new Set(capabilities).size !== capabilities.length ||
        !time(validUntil) || validUntil <= at) error("INVALID_ENROLLMENT");
    if (this.#rows.size >= 100) error("REGISTRY_LIMIT");
    const fingerprint = publicKeyFingerprint(publicJwk);
    if (expectedFingerprint !== fingerprint) error("FINGERPRINT_MISMATCH");
    if (this.#rows.has(keyId) || this.#fingerprints.has(fingerprint)) error("KEY_ALREADY_USED");
    const enrollment = Object.freeze({agentId, keyId, audience,
      capabilities: Object.freeze([...capabilities]),
      publicJwk: Object.freeze({...publicJwk}), status: "ACTIVE", validFrom: at, validUntil});
    return Object.freeze({enrollment, fingerprint, reviewer, evidenceRef,
      independentlyTrustedIdentity: false, executionAuthority: "NONE"});
  }

  #insert(row, at) {
    this.#rows.set(row.enrollment.keyId, row);
    this.#fingerprints.add(row.fingerprint);
    this.#lastChange = at;
    return row;
  }

  enroll(input, at) {
    const row = this.#prepare(input, at);
    if ([...this.#rows.values()].some(({enrollment: e}) => e.status === "ACTIVE" &&
        e.agentId === row.enrollment.agentId && e.audience === row.enrollment.audience))
      error("ACTIVE_KEY_EXISTS");
    const result = this.#insert(row, at);
    this.#generation++;
    return result;
  }

  #active(keyId) {
    const row = this.#rows.get(keyId);
    if (!row || row.enrollment.status !== "ACTIVE") error("KEY_NOT_ACTIVE");
    return row;
  }

  #retire(row, at) {
    this.#rows.set(row.enrollment.keyId, Object.freeze({...row, revokedAt: at,
      enrollment: Object.freeze({...row.enrollment, status: "REVOKED"})}));
    this.#lastChange = at;
  }

  rotate(keyId, input, at) {
    const old = this.#active(keyId), next = this.#prepare(input, at);
    const a = old.enrollment, b = next.enrollment;
    if (at >= a.validUntil) error("KEY_EXPIRED");
    if (a.agentId !== b.agentId || a.audience !== b.audience ||
        b.capabilities.some(value => !a.capabilities.includes(value))) error("ROTATION_SCOPE_CHANGED");
    this.#retire(old, at);
    const result = this.#insert(next, at);
    this.#generation++;
    return result;
  }

  revoke(keyId, at) {
    if (!time(at) || at < this.#lastChange) error("INVALID_CHANGE_TIME");
    this.#retire(this.#active(keyId), at);
    this.#generation++;
  }

  versionedSnapshot() {
    const snapshot = Object.freeze({generation: this.#generation,
      enrollments: this.challengeEnrollments()});
    this.#snapshots.add(snapshot);
    return snapshot;
  }

  // Both checks matter: a registry update can occur while disk I/O is pending.
  verifierFor(snapshot, {ledgerDir, now}) {
    const assertCurrent = () => {
      if (!this.#snapshots.has(snapshot)) error("UNKNOWN_ENROLLMENT_SNAPSHOT");
      if (snapshot.generation !== this.#generation) error("STALE_ENROLLMENT_SNAPSHOT");
    };
    assertCurrent();
    const verifier = new AgentChallengeVerifier({ledgerDir, now, enrollments: snapshot.enrollments});
    const guarded = async operation => {
      assertCurrent();
      const result = await operation();
      assertCurrent();
      return result;
    };
    return Object.freeze({
      issue: request => guarded(() => verifier.issue(request)),
      verify: proof => guarded(() => verifier.verify(proof))
    });
  }

  snapshot() { return Object.freeze([...this.#rows.values()]); }
  challengeEnrollments() { return Object.freeze(this.snapshot().map(row => row.enrollment)); }
}

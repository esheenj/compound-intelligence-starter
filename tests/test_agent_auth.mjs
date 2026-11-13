import test from "node:test";
import assert from "node:assert/strict";
import {mkdtemp,rm,writeFile} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {createHash} from "node:crypto";
import {AgentChallengeVerifier,localDemoKeyPair,signForLocalDemo,
        validateChallenge,challengeMessage} from "../src/agent_auth/challenge.mjs";
const initial=1700000000;
const request={agentId:"synthetic-agent",keyId:"local-key-a",audience:"local-verifier",capability:"summarize"};
async function setup(t){
  const dir=await mkdtemp(join(tmpdir(),"esheen-agent-auth-"));
  t.after(()=>rm(dir,{recursive:true,force:true}));
  const key=localDemoKeyPair(),other=localDemoKeyPair();
  const enrollments=[{agentId:request.agentId,keyId:request.keyId,
    audience:request.audience,capabilities:["summarize","search"],status:"ACTIVE",
    publicJwk:key.publicJwk,validFrom:initial-100,validUntil:initial+600}];
  let now=initial;
  return {dir,key,other,enrollments,setNow:x=>now=x,
    verifier:()=>new AgentChallengeVerifier({ledgerDir:dir,enrollments,now:()=>now})};
}
test("genuine signature proves enrolled key access but no authorization",async t=>{
  const c=await setup(t),v=c.verifier(),challenge=await v.issue(request);
  const signatureBase64Url=signForLocalDemo(c.key.privateKey,challenge);
  const r=await v.verify({challenge,signatureBase64Url});
  assert.equal(r.signatureVerified,true);
  assert.equal(r.nonceConsumed,true);
  assert.equal(r.independentlyTrustedIdentity,false);
  assert.equal(r.executionAuthority,"NONE");
  assert.equal(r.state,"SIGNATURE_VERIFIED_NOT_AUTHORIZED");
  await assert.rejects(v.verify({challenge,signatureBase64Url}),/CHALLENGE_REPLAY/);
});
test("replay remains blocked after verifier restart",async t=>{
  const c=await setup(t),v=c.verifier(),challenge=await v.issue(request),
        signatureBase64Url=signForLocalDemo(c.key.privateKey,challenge);
  await v.verify({challenge,signatureBase64Url});
  await assert.rejects(c.verifier().verify({challenge,signatureBase64Url}),/CHALLENGE_REPLAY/);
});
test("two concurrent requests with same nonce allow exactly one",async t=>{
  const c=await setup(t),v=c.verifier(),challenge=await v.issue(request),
        signatureBase64Url=signForLocalDemo(c.key.privateKey,challenge);
  const r=await Promise.allSettled([v.verify({challenge,signatureBase64Url}),
                                   v.verify({challenge,signatureBase64Url})]);
  assert.equal(r.filter(x=>x.status==="fulfilled").length,1);
  assert.match(String(r.find(x=>x.status==="rejected").reason),/CHALLENGE_REPLAY/);
});
test("wrong private key cannot sign for enrolled public key",async t=>{
  const c=await setup(t),v=c.verifier(),challenge=await v.issue(request);
  await assert.rejects(v.verify({challenge,
    signatureBase64Url:signForLocalDemo(c.other.privateKey,challenge)}),/INVALID_SIGNATURE/);
});
test("audience, scope and nonce binding reject altered issued challenge",async t=>{
  const c=await setup(t),v=c.verifier(),challenge=await v.issue(request);
  const signatureBase64Url=signForLocalDemo(c.key.privateKey,challenge);
  for(const change of [{capability:"search"},{audience:"evil-viewer"},{nonce:"A".repeat(32)}]){
    await assert.rejects(v.verify({challenge:{...challenge,...change},signatureBase64Url}),
      /ISSUED_CHALLENGE_MISMATCH|UNISSUED_CHALLENGE|ENROLLMENT_IDENTITY_AUDIENCE_MISMATCH/);
  }
  assert.equal((await v.verify({challenge,signatureBase64Url})).signatureVerified,true);
});
test("unregistered capability and unknown key fail at issue",async t=>{
  const c=await setup(t),v=c.verifier();
  await assert.rejects(v.issue({...request,capability:"payments"}),/CAPABILITY_NOT_ENROLLED/);
  await assert.rejects(v.issue({...request,keyId:"unknown"}),/UNKNOWN_ENROLLMENT_KEY/);
});
test("revoked enrolled key cannot issue or verify",async t=>{
  const c=await setup(t),v=c.verifier(),challenge=await v.issue(request);
  c.enrollments[0].status="REVOKED";
  await assert.rejects(c.verifier().issue(request),/REVOKED_ENROLLMENT/);
  await assert.rejects(c.verifier().verify({challenge,
    signatureBase64Url:signForLocalDemo(c.key.privateKey,challenge)}),/REVOKED_ENROLLMENT/);
});
test("expired and not-yet-valid challenges cannot pass",async t=>{
  const c=await setup(t),v=c.verifier(),challenge=await v.issue(request),
    signatureBase64Url=signForLocalDemo(c.key.privateKey,challenge);
  c.setNow(initial+61);
  await assert.rejects(v.verify({challenge,signatureBase64Url}),/CHALLENGE_EXPIRED/);
  c.setNow(initial-1);
  await assert.rejects(v.verify({challenge,signatureBase64Url}),/NOT_YET_VALID/);
});
test("self-issued valid signature without verifier's nonce receipt fails",async t=>{
  const c=await setup(t),v=c.verifier(),challenge={
    schema:"esheen-agent-challenge.v1",...request,
    nonce:"X".repeat(32),issuedAt:initial,expiresAt:initial+60};
  await assert.rejects(v.verify({challenge,
    signatureBase64Url:signForLocalDemo(c.key.privateKey,challenge)}),/UNISSUED_CHALLENGE/);
});
test("tampered durable challenge receipt fails",async t=>{
  const c=await setup(t),v=c.verifier(),challenge=await v.issue(request);
  const key=createHash("sha256").update(challenge.audience+"\0"+challenge.agentId+
                                      "\0"+challenge.keyId+"\0"+challenge.nonce).digest("hex");
  await writeFile(join(c.dir,"issued",key),JSON.stringify({...challenge,capability:"search"}));
  await assert.rejects(v.verify({challenge,
    signatureBase64Url:signForLocalDemo(c.key.privateKey,challenge)}),/ISSUED_CHALLENGE_MISMATCH/);
});
test("reject invalid/ambiguous signatures and secret JWK import",async t=>{
  const c=await setup(t),v=c.verifier(),challenge=await v.issue(request);
  await assert.rejects(v.verify({challenge,signatureBase64Url:"bad"}),/MALFORMED_SIGNATURE/);
  assert.throws(()=>new AgentChallengeVerifier({ledgerDir:c.dir,enrollments:[
    {...c.enrollments[0],publicJwk:{...c.key.publicJwk,d:"private"}}]}),/INVALID_PUBLIC_JWK/);
});
test("reject invalid TTL, unknown fields, bool timestamps and bad nonce",async t=>{
  const c=await setup(t),v=c.verifier();
  for(const ttlSeconds of [0,121,1.5])await assert.rejects(
    v.issue({...request,ttlSeconds}),/INVALID_ISSUE_REQUEST/);
  const challenge=await v.issue(request);
  for(const update of [{issuedAt:true},{expiresAt:challenge.issuedAt+121},
                       {nonce:"short"},{schema:"wrong"},{extra:"x"}]){
    assert.throws(()=>validateChallenge({...challenge,...update}),/INVALID_CHALLENGE/);
  }
  assert.ok(challengeMessage(challenge).toString().startsWith("ESHEEN_AGENT_CHALLENGE_V1\n"));
});

import {LocalEnrollmentRegistry, publicKeyFingerprint} from "../src/agent_auth/enrollment.mjs";
function candidate(key, keyId, capabilities = ["summarize"]) {
  return {...request, keyId, capabilities, publicJwk:key.publicJwk, validUntil:initial+600,
    reviewer:"fictional-reviewer", evidenceRef:"offline-example/pin",
    expectedFingerprint:publicKeyFingerprint(key.publicJwk)};
}
test("rotation rejects an outstanding old proof and accepts the new key without granting authority", async t=>{
  const c = await setup(t), registry = new LocalEnrollmentRegistry();
  registry.enroll(candidate(c.key, request.keyId, ["summarize", "search"]), initial);
  const before = new AgentChallengeVerifier({ledgerDir:c.dir, enrollments:registry.challengeEnrollments(),
    now:()=>initial});
  const old = await before.issue(request);
  const snapshot = registry.snapshot();
  registry.rotate(request.keyId, candidate(c.other, "local-key-b"), initial+1);
  assert.equal(snapshot[0].enrollment.status,"ACTIVE");
  const after = new AgentChallengeVerifier({ledgerDir:c.dir, enrollments:registry.challengeEnrollments(),
    now:()=>initial+1});
  await assert.rejects(after.verify({challenge:old,
    signatureBase64Url:signForLocalDemo(c.key.privateKey,old)}), /REVOKED_ENROLLMENT/);
  await assert.rejects(after.issue({...request,keyId:"local-key-b",capability:"search"}),
    /CAPABILITY_NOT_ENROLLED/);
  const next = await after.issue({...request,keyId:"local-key-b"});
  const proof = await after.verify({challenge:next,
    signatureBase64Url:signForLocalDemo(c.other.privateKey,next)});
  assert.equal(proof.executionAuthority,"NONE");
  registry.revoke("local-key-b",initial+2);
  assert.deepEqual(registry.snapshot().map(row=>row.enrollment.status),["REVOKED","REVOKED"]);
});
test("bad pins, key reuse and scope escalation leave enrollment unchanged",()=>{
  const registry = new LocalEnrollmentRegistry(), a=localDemoKeyPair(), b=localDemoKeyPair();
  const first=candidate(a,"a"), next=candidate(b,"b");
  assert.throws(()=>registry.enroll({...first,expectedFingerprint:"wrong"},initial),
    /FINGERPRINT_MISMATCH/);
  assert.deepEqual(registry.snapshot(),[]);
  registry.enroll(first,initial);
  assert.throws(()=>registry.rotate("a",candidate(a,"renamed"),initial+1), /KEY_ALREADY_USED/);
  assert.throws(()=>registry.rotate("a",{...next,capabilities:["summarize","delete"]},initial+1),
    /ROTATION_SCOPE_CHANGED/);
  assert.equal(registry.snapshot()[0].enrollment.status,"ACTIVE");
  assert.equal(registry.snapshot().length,1);
  assert.throws(()=>publicKeyFingerprint({...a.publicJwk,d:"private"}), /INVALID_PUBLIC_KEY/);
});

test("versioned verifier rejects stale and foreign snapshots and accepts the replacement", async t=>{
  const c=await setup(t), registry=new LocalEnrollmentRegistry();
  const opts={ledgerDir:c.dir, now:()=>initial+1};
  registry.enroll(candidate(c.key, request.keyId),initial);
  const first=registry.versionedSnapshot(), old=registry.verifierFor(first,opts);
  const challenge=await old.issue(request);
  assert.throws(()=>registry.rotate(request.keyId,{...candidate(c.other,"b"),
    expectedFingerprint:"wrong"},initial+1), /FINGERPRINT_MISMATCH/);
  assert.equal(registry.versionedSnapshot().generation,first.generation);
  registry.rotate(request.keyId,candidate(c.other,"b"),initial+1);
  const current=registry.versionedSnapshot();
  assert.equal(current.generation,first.generation+1);
  assert.throws(()=>registry.verifierFor(first,opts),/STALE_ENROLLMENT_SNAPSHOT/);
  assert.throws(()=>registry.verifierFor({...current},opts),/UNKNOWN_ENROLLMENT_SNAPSHOT/);
  await assert.rejects(old.verify({challenge,
    signatureBase64Url:signForLocalDemo(c.key.privateKey,challenge)}),/STALE_ENROLLMENT_SNAPSHOT/);
  const fresh=registry.verifierFor(current,opts), next=await fresh.issue({...request,keyId:"b"});
  assert.equal((await fresh.verify({challenge:next,
    signatureBase64Url:signForLocalDemo(c.other.privateKey,next)})).executionAuthority,"NONE");
  const pending=fresh.issue({...request,keyId:"b"});
  registry.revoke("b",initial+2);
  await assert.rejects(pending,/STALE_ENROLLMENT_SNAPSHOT/);
});

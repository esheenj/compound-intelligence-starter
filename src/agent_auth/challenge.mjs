/** Offline P-256 ECDSA challenge verification. No permission to act is granted. */
import {createHash,createPublicKey,randomBytes,verify as ecdsaVerify,
        generateKeyPairSync,sign as ecdsaSign} from "node:crypto";
import {mkdir,readFile,writeFile} from "node:fs/promises";
import {dirname,join} from "node:path";

export const SCHEMA="esheen-agent-challenge.v1";
const ID=/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,79}$/;
const NONCE=/^[A-Za-z0-9_-]{32}$/;
const SIG=/^[A-Za-z0-9_-]{86}$/;
const FIELDS=["schema","audience","agentId","keyId","capability","nonce","issuedAt","expiresAt"];
const only=(v,k)=>v!==null&&typeof v==="object"&&!Array.isArray(v)&&
  Object.keys(v).length===k.length&&k.every(x=>Object.hasOwn(v,x));
const ident=x=>typeof x==="string"&&ID.test(x);
const time=x=>Number.isSafeInteger(x)&&x>=0&&x<=2000000000;
const fail=x=>{throw Error(x);};
const sha=x=>createHash("sha256").update(x).digest("hex");
const keyOf=c=>sha(c.audience+"\0"+c.agentId+"\0"+c.keyId+"\0"+c.nonce);

export function validateChallenge(c){
  if(!only(c,FIELDS)||c.schema!==SCHEMA||
     !ident(c.audience)||!ident(c.agentId)||!ident(c.keyId)||!ident(c.capability)||
     typeof c.nonce!=="string"||!NONCE.test(c.nonce)||
     !time(c.issuedAt)||!time(c.expiresAt)||
     c.expiresAt<=c.issuedAt||c.expiresAt-c.issuedAt>120)fail("INVALID_CHALLENGE");
  return c;
}
export function challengeMessage(c){
  validateChallenge(c);
  return Buffer.from("ESHEEN_AGENT_CHALLENGE_V1\n"+
    JSON.stringify(FIELDS.map(k=>c[k])),"utf8");
}
function enrollmentKey(e){
  if(!only(e,["agentId","keyId","audience","capabilities","status",
              "publicJwk","validFrom","validUntil"])||
     !ident(e.agentId)||!ident(e.keyId)||!ident(e.audience)||
     !Array.isArray(e.capabilities)||e.capabilities.length<1||e.capabilities.length>16||
     !e.capabilities.every(ident)||new Set(e.capabilities).size!==e.capabilities.length||
     !["ACTIVE","REVOKED"].includes(e.status)||
     !time(e.validFrom)||!time(e.validUntil)||e.validUntil<=e.validFrom)
       fail("INVALID_ENROLLMENT");
  const jwk=e.publicJwk;
  if(!only(jwk,["kty","crv","x","y"])||jwk.kty!=="EC"||jwk.crv!=="P-256"||
     typeof jwk.x!=="string"||typeof jwk.y!=="string"||
     !/^[A-Za-z0-9_-]{43}$/.test(jwk.x)||!/^[A-Za-z0-9_-]{43}$/.test(jwk.y))
       fail("INVALID_PUBLIC_JWK");
  let key;
  try{key=createPublicKey({key:jwk,format:"jwk"});}
  catch{fail("INVALID_PUBLIC_JWK");}
  if(key.asymmetricKeyType!=="ec"||
     key.asymmetricKeyDetails?.namedCurve!=="prime256v1")fail("WRONG_KEY_CURVE");
  return key;
}
function sigBytes(s){
  if(typeof s!=="string"||!SIG.test(s))fail("MALFORMED_SIGNATURE");
  const b=Buffer.from(s,"base64url");
  if(b.length!==64||b.toString("base64url")!==s)fail("MALFORMED_SIGNATURE");
  return b;
}
export class AgentChallengeVerifier{
  constructor({ledgerDir,enrollments,now=()=>Math.floor(Date.now()/1000)}){
    if(typeof ledgerDir!=="string"||!ledgerDir.startsWith("/")||
       ledgerDir.length>1024||typeof now!=="function"||
       !Array.isArray(enrollments)||!enrollments.length||enrollments.length>100)
       fail("INVALID_VERIFIER_CONFIGURATION");
    this.ledgerDir=ledgerDir;
    this.now=now;
    this.enrollments=new Map();
    this.keys=new Map();
    for(const e of enrollments){
      const key=enrollmentKey(e);
      if(this.keys.has(e.keyId))fail("DUPLICATE_ENROLLMENT_KEY_ID");
      this.keys.set(e.keyId,key);
      this.enrollments.set(e.keyId,Object.freeze({
        ...e,capabilities:Object.freeze([...e.capabilities]),
        publicJwk:Object.freeze({...e.publicJwk})
      }));
    }
  }
  registered(c,now){
    const e=this.enrollments.get(c.keyId);
    if(!e)fail("UNKNOWN_ENROLLMENT_KEY");
    if(e.status!=="ACTIVE")fail("REVOKED_ENROLLMENT");
    if(e.agentId!==c.agentId||e.audience!==c.audience)
       fail("ENROLLMENT_IDENTITY_AUDIENCE_MISMATCH");
    if(!e.capabilities.includes(c.capability))fail("CAPABILITY_NOT_ENROLLED");
    if(now<e.validFrom||now>e.validUntil||
       c.issuedAt<e.validFrom||c.expiresAt>e.validUntil)
       fail("ENROLLMENT_NOT_VALID");
  }
  async issue({agentId,keyId,capability,audience,ttlSeconds=60}){
    if(!ident(agentId)||!ident(keyId)||!ident(capability)||!ident(audience)||
       !Number.isSafeInteger(ttlSeconds)||ttlSeconds<1||ttlSeconds>120)
       fail("INVALID_ISSUE_REQUEST");
    const n=this.now();
    if(!time(n))fail("INVALID_VERIFIER_CLOCK");
    const c={schema:SCHEMA,audience,agentId,keyId,capability,
      nonce:randomBytes(24).toString("base64url"),issuedAt:n,expiresAt:n+ttlSeconds};
    validateChallenge(c);
    this.registered(c,n);
    const path=join(this.ledgerDir,"issued",keyOf(c));
    await mkdir(dirname(path),{recursive:true,mode:0o700});
    await writeFile(path,JSON.stringify(c),{flag:"wx",mode:0o600});
    return Object.freeze(c);
  }
  async verify({challenge,signatureBase64Url}){
    validateChallenge(challenge);
    const now=this.now();
    if(!time(now))fail("INVALID_VERIFIER_CLOCK");
    if(now<challenge.issuedAt)fail("NOT_YET_VALID");
    if(now>challenge.expiresAt)fail("CHALLENGE_EXPIRED");
    this.registered(challenge,now);
    const sig=sigBytes(signatureBase64Url);
    let original;
    try{original=JSON.parse(await readFile(join(this.ledgerDir,"issued",keyOf(challenge)),"utf8"));}
    catch{fail("UNISSUED_CHALLENGE");}
    if(!only(original,FIELDS)||
       !challengeMessage(original).equals(challengeMessage(challenge)))
       fail("ISSUED_CHALLENGE_MISMATCH");
    let valid=false;
    try{valid=ecdsaVerify("sha256",challengeMessage(challenge),
       {key:this.keys.get(challenge.keyId),dsaEncoding:"ieee-p1363"},sig);}
    catch{fail("SIGNATURE_VERIFICATION_ERROR");}
    if(!valid)fail("INVALID_SIGNATURE");
    const used=join(this.ledgerDir,"used",keyOf(challenge));
    await mkdir(dirname(used),{recursive:true,mode:0o700});
    try{await writeFile(used,"consumed\n",{flag:"wx",mode:0o600});}
    catch(e){if(e?.code==="EEXIST")fail("CHALLENGE_REPLAY");throw e;}
    return Object.freeze({schema:"esheen-agent-signed-proof-result.v1",
      state:"SIGNATURE_VERIFIED_NOT_AUTHORIZED",
      agentId:challenge.agentId,keyId:challenge.keyId,capability:challenge.capability,
      audience:challenge.audience,signatureVerified:true,nonceConsumed:true,
      independentlyTrustedIdentity:false,executionAuthority:"NONE"});
  }
}
/** Test/demo only. Never enroll this ephemeral key into real service authority. */
export function localDemoKeyPair(){
  const {privateKey,publicKey}=generateKeyPairSync("ec",{namedCurve:"prime256v1"});
  return {privateKey,publicJwk:publicKey.export({format:"jwk"})};
}
export function signForLocalDemo(privateKey,challenge){
  return ecdsaSign("sha256",challengeMessage(challenge),
    {key:privateKey,dsaEncoding:"ieee-p1363"}).toString("base64url");
}

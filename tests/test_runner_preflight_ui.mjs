import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import { TextEncoder } from "node:util";

const root = resolve(fileURLToPath(new URL("../", import.meta.url)));
const page = readFileSync(join(root, "site/runner-preflight.html"), "utf8");
const scripts = [...page.matchAll(/<script>([\s\S]*?)<\/script>/g)];
assert.equal(scripts.length, 1, "exactly one inline script and no external modules");
const context = vm.createContext({ TextEncoder });
vm.runInContext(scripts[0][1], context);

const browser = (raw) => JSON.parse(JSON.stringify(
  vm.runInContext("evaluate(parseInput("+JSON.stringify(raw)+"))", context)
));
const fixture = (name) => readFileSync(join(root, "experiments/runner_preflight/fixtures/"+name+".json"), "utf8");
const binary = process.env.RUNNER_PREFLIGHT_BINARY
  ? resolve(root, process.env.RUNNER_PREFLIGHT_BINARY)
  : null;
function rust(raw) {
  if (!binary) return null;
  const dir = mkdtempSync(join(tmpdir(), "runner-preflight-parity-"));
  try {
    const file = join(dir, "inventory.json");
    writeFileSync(file, raw);
    const result = spawnSync(binary, ["inspect", "--input", file, "--format", "json"], {encoding:"utf8", timeout:8000});
    if(result.error) throw result.error;
    return {status:result.status, report:result.stdout.trim()? JSON.parse(result.stdout):null};
  } finally {
    rmSync(dir,{force:true,recursive:true});
  }
}
test("offline safety and accessible sample interface", () => {
  assert.match(page,/connect-src 'none'/);
  assert.match(page,/default-src 'none'/);
  assert.doesNotMatch(page, /<script\s+src=|innerHTML|XMLHttpRequest|fetch\s*\(/i);
  assert.match(page, /<textarea id="inventory"/);
  assert.match(page, /role="status" aria-live="polite"/);
  for(const name of ["ready","warn","hold","evaluate"])assert.match(page,new RegExp('id="'+name+'"'));
  assert.match(page, /not Rust compiled to WebAssembly/);
});
for(const [name,status,exit] of [
  ["ready-x64","READY",0],
  ["warn-disk","WARN",1],
  ["hold-arch","HOLD",2],
]) {
  test(name+" matches expected status and compiled Rust when provided", () => {
    const raw=fixture(name),report=browser(raw);
    assert.equal(report.schema,"runner-preflight-result-v1");
    assert.equal(report.status,status);
    assert.ok(Array.isArray(report.findings));
    if(binary){
      const actual=rust(raw);
      assert.equal(actual.status,exit);
      assert.deepEqual(report,actual.report);
    }
  });
}
test("declared missing labels, tools and targets match Rust finding order",()=>{
  const example=JSON.parse(fixture("ready-x64"));
  example.job.required_labels=["gpu","ubuntu-24.04","gpu"];
  example.job.required_tools=["docker","cargo","docker"];
  example.job.rust_target="wasm32-unknown-unknown";
  example.job.min_memory_mb=10000;
  const raw=JSON.stringify(example),report=browser(raw);
  assert.equal(report.status,"HOLD");
  assert.deepEqual(report.findings.map(f=>f.code),[
    "LABEL_MISSING","MEMORY_INSUFFICIENT","TOOL_MISSING","RUST_TARGET_MISSING"
  ]);
  if(binary){const actual=rust(raw);assert.equal(actual.status,2);assert.deepEqual(report,actual.report);}
});
test("invalid fields, unsafe tokens and excessive UTF8 size are rejected",()=>{
  const raw=JSON.parse(fixture("ready-x64"));
  raw.runner.unexpected="sensitive";
  assert.throws(()=>browser(JSON.stringify(raw)),/Unknown input field/);
  delete raw.runner.unexpected;
  raw.runner.labels.push("malicious\nlabel");
  assert.throws(()=>browser(JSON.stringify(raw)),/Invalid or oversized/);
  raw.runner.labels.pop();
  raw.runner.disk_free_mb=-1;
  assert.throws(()=>browser(JSON.stringify(raw)),/Resource quantity/);
  assert.throws(()=>browser("X".repeat(65537)),/exceeds 64 KiB/);
});
test("browser scenario helpers stay consistent with fixture statuses",()=>{
  for(const [name,status] of [["ready","READY"],["warn","WARN"],["hold","HOLD"]]){
    const raw=vm.runInContext('JSON.stringify(scenario("'+name+'"))',context);
    assert.equal(browser(raw).status,status);
  }
});

# Runner Preflight

Offline, read-only CI runner requirement matching with deterministic JSON reports.

Runner Preflight evaluates a **supplied** inventory against a declared job specification. It **does not** inspect a host automatically, register CI runners, diagnose GitHub scheduling or billing, install software, access credentials, or repair a server. It does not grant financial or agent execution authority.

## Quick start

Install Rust 1.100.0 with Cargo on Linux x86-64 or ARM64. From the extracted repository root:

```sh
cd rust
cargo fmt --all -- --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
cargo run --locked -- inspect --input ../fixtures/ready-x64.json --format json
```

Expected report status: `READY`. Other supplied synthetic fixtures produce `WARN` or `HOLD`. An incompatible inventory is a diagnostic finding, not permission to change the machine.

## Optional: observe your own Linux runner

The accompanying **Python 3 standard-library** observer reads a deliberately small set of current host facts locally, then generates input for the Rust evaluator. This is a complementary Python/Rust workflow, not a replacement for the Rust engine and **not present in the original v0.1.0 release**.

Run these commands from the extracted standalone source root on your **own authorized Linux x86-64 machine** (choose `job-linux-arm64.json` on ARM64):

```sh
python3 scripts/collect_linux_runner.py --job fixtures/job-linux-x64.json --workspace . > observed.json
cd rust
cargo run --locked -- inspect --input ../observed.json --format json
```

The observer takes a job-only `runner-preflight-job-v1` JSON file and records Linux OS/architecture, free disk for the **specified workspace filesystem**, `/proc/meminfo` `MemAvailable` and presence of only the **requested executable names** on PATH. It reads files and metadata only: **no network, credentials, SSH, privileged commands, installs, subprocesses or filesystem mutations**. It writes its manifest to stdout, so redirect it to a local file only if you want to keep it.

The result is **not attested**. A tool name being present does not prove its version or functional readiness; OS resource values are point-in-time estimates in MiB and capped at the CLI's 1,000,000-unit input bound. Labels and installed Rust targets are intentionally left empty because they cannot be independently verified through this small observer. Jobs requiring those claims receive HOLD unless separately verified and supplied using another provenance-aware workflow. No output includes IP addresses, usernames, hostnames, environment variables, executable paths or secrets.

An invalid or symlinked job input (64 KiB maximum), unsupported host or unavailable Linux observation exits 3. The collector is intentionally Linux-only and never repairs CI runner registrations, scheduling, billing, disk capacity or software.

## Contract

The input JSON (maximum 64 KiB, regular file only, no symlinks) has `schema: "runner-preflight-input-v1"`, plus:

- `runner`: `os`, `arch`, `labels`, `disk_free_mb`, `memory_free_mb`, `tools`, and `rust_targets`
- `job`: `os`, `arch`, `required_labels`, `min_disk_mb`, `min_memory_mb`, `required_tools`, and optional `rust_target`

`os` is `linux`, `macos`, or `windows`. `arch` is `x86_64` or `aarch64`. Tool and target comparisons match exact identifiers; they do not discover installed versions. The output uses `runner-preflight-result-v1`, a status and generic machine-readable findings.

| Exit code | Meaning |
|---|---|
| 0 | READY: declared requirements matched |
| 1 | WARN: requirements matched, low resource headroom |
| 2 | HOLD: one or more requirements missing |
| 3 | Invalid input or CLI usage |

## Independent source and verification

This release-ready source tree was assembled from the explicitly allowlisted, original, **public** files in [Compound Intelligence Starter](https://github.com/esheenj/compound-intelligence-starter/tree/main/experiments/runner_preflight). The export contains no history, unrelated source, private instructions or account credentials. See `SOURCE_PROVENANCE.json` for the exact parent source commit and hashes of each included file. `rust/Cargo.lock` is committed. The included `.github/workflows/ci.yml` independently tests x86-64 and ARM64 and checks dependency advisories, licenses and sources.

MIT licensed (see `LICENSE`). Do not advertise an executable as signed, audited for all vulnerabilities, verified as running on Oracle, or commercially supported merely because source tests pass. The source archive can be imported into a new, functionally named GitHub repository after normal repository creation and final release checks.

No added recurring infrastructure spend or paid dependency is required.

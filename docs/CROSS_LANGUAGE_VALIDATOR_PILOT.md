# Python + Rust: first cross-language validation pilot

**Scope:** source-only, dependency-free experiment with original synthetic data. Not deployed, and not part of a private execution gateway.

## Purpose

Compare two language implementations of a single deterministic input-format contract before deciding whether a systems language adds value to an AI-assisted engineering platform.

Each program reads UTF-8 lines from standard input and emits one `VALID` or `INVALID` line per input. A row contains exactly three tab-separated fields: `record-id<TAB>status<TAB>digest-text`.

- ID: 1 to 64 ASCII alphanumeric / `_` / `-` characters
- Status: `ACCEPTED`, `REJECTED`, or `INCONCLUSIVE`
- Digest text: exactly 64 *lowercase* ASCII hex characters
- Entire encoded row: 512 bytes maximum, with no extra fields or implicit normalization

**Important:** Checking digest *shape* does not verify a hash, content authenticity, a signature, authorization or execution permissions. This intentionally cannot validate real operational receipts or grant access.

## Reproduce

```bash
python experiments/receipt_validator/python_validator.py < examples/receipt_validator_cases.tsv
cargo run --quiet --manifest-path experiments/receipt_validator/rust/Cargo.toml < examples/receipt_validator_cases.tsv
python -m unittest tests/test_receipt_validator_experiment.py -v
cargo test --manifest-path experiments/receipt_validator/rust/Cargo.toml
```

The Python reference needs Python 3.10+. The Rust program uses the standard library with Rust 1.70+. There are **no third-party dependencies**, no network access at runtime and no new services. The Rust parity test skips without Cargo locally; a dedicated CI job requires the Rust compiler.

## Measure, then choose

After correctness passes: measure a warmed, compiled Rust binary versus Python with identical fixed streams (100,000+ synthetic records) on the **same CPU** and architecture. Record warmup and process-start overhead separately; report median and p95 times, rows/second, peak RSS, compiler/runtime versions, fixture hash, source SHA and actual error counts. Run repeated trials and compare distributions. A process-start microbenchmark is not proof of algorithm superiority.

Adopt Rust for a shared function only if correctness, real workload benefit, portable packaging, and maintenance justify it. Prefer Python for low-volume orchestration and AI experiments. Only share a component across projects once two independent permitted consumers need it.

Potential follow-ups: deterministic fuzz cases, a reproducible benchmark harness, ARM64 testing, Go implementation, and optional PyO3 interoperability. No live Commander, trading or project permission changes are part of this experiment.

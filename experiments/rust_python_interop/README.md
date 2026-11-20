# Rust/Python interoperability qualification — public synthetic research

This **isolated original experiment** checks a bounded PyO3/Rust function against a
pure Python reference and the *existing* offline Engineering Issue Challenger.
It is not a universal Python-to-Rust translator, independent product repository,
published PyPI package, privileged Commander worker or Oracle deployment.

## Tested contract

`classify_ids(["a", "a", "A", "a-b", ""])` returns `(2, 1, 2)`.

- Valid identifiers contain 1–64 UTF-8 bytes of ASCII lowercase letters, digits,
  underscore or hyphen; the first valid occurrence is accepted, repeats are duplicates.
- All other strings count as rejected; non-strings and invalid containers raise `TypeError`.
- Python lists and tuples are accepted, with maximum 200,000 entries and
  8,000,000 UTF-8 bytes. Oversized inputs raise `ValueError`.
- The extension iterates bounded Python values without first cloning the entire
  untrusted container into a native vector.

## Reproduction (Rust 1.100.0, Python 3.10+)

From `experiments/rust_python_interop/`:

```sh
cargo fmt --all -- --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
python -m pip install "maturin==1.16.0"
maturin build --release --out dist --interpreter python --compatibility off
python -m pip install --no-index --find-links dist rust-id-interop-pilot
python -m unittest discover -s tests -v
python consumer_probe.py --engine python --issues 12 --iterations 200
python consumer_probe.py --engine rust --issues 12 --iterations 200
python benchmark.py --size 50000 --trials 7
```

The build wheel is **host-specific** and intended for CI import verification, not a
portable manylinux, Windows or macOS distribution. Nothing is uploaded to PyPI.

## Dependency security

The first dependency audit correctly rejected PyO3 0.27.2 due to
`RUSTSEC-2026-0176` and `RUSTSEC-2026-0177`. The experiment has since upgraded to
**PyO3 0.29.0** with its exact Cargo dependency lock and a reviewed narrow
`deny.toml` SPDX license allowlist. Advisories are **not** suppressed. The
repository CI uses the same pinned `cargo-deny` action as the existing
Runner Preflight project; release status depends on actual exact-head checks.

The Cargo.lock was generated independently on Linux x64 and ARM64 and
matched byte-for-byte, SHA-256
`4790e47cb2a01e5b6d2475afa6614701b839072edf4d65fe16bc6d0e0c59fcd1`.
It is now committed; CI must use `--locked` and reject edits.

## Real consumer fit

The existing Engineering Issue Challenger remains authoritative in Python.
`consumer_probe.py` calls its unchanged `validate()` and `plan()` on the
published fictional fixture expanded to 12 issues/24 hypotheses, then performs
an optional Rust identifier classification. It proves deterministic parity,
preserves scope and independently rejects input the broader native classifier
would otherwise accept.

The prior v0.27.2 full-consumer CI measurements were approximately
1.06 ms per call on x64 and 1.20 ms on ARM64 for both paths. The native
supplement did **not** produce a material application-level speedup and
used slightly more peak resident memory. Keep Python as this consumer's
implementation. Those measurements are one-run synthetic observations and are
not automatically reusable with the upgraded dependency.

## Evidence and limits

CI matrix: Linux x64 Python 3.10 and 3.12, Linux ARM64 Python 3.12.
Negative, boundary, parity and opt-in consumer tests are included. A benchmark
only measures synthetic ID classification and does not include native wheel
installation overhead, external workloads or production throughput.

Source, compilation, audit, package portability, publication, deployment and
real developer adoption are separate gates. Do not promote this experimental
module to production or publish a new product until its actual consumer value,
rights and complete release criteria justify that move.

No private control-plane or SIGMA trading sources; no network calls, host
administration, financial mutation, scheduling or additional recurring cost.

# Rust/Python parity qualification — private-product prerequisite, public research only

This **isolated, original educational experiment** tests whether a Rust function packaged with
PyO3/maturin has the same behavior as a pure Python reference. It does not create a new repo,
convert arbitrary Python code, modify Oracle/Commander/Cortex, or publish a package.

## Contract

`classify_ids(["a", "a", "A", "a-b", ""])` returns `(2, 1, 2)`.

- Valid identifiers: 1–64 bytes of ASCII lowercase letters, digits, underscore or hyphen.
- First valid occurrence counts as accepted; later occurrences count as duplicates.
- Other string values count as rejected; invalid member types raise `TypeError`.
- Lists/tuples are accepted. Maximum 200,000 entries and 8,000,000 UTF-8 bytes.
- Oversized batches raise `ValueError`. Counts, not timings, are compared.

## Qualification (requires Rust 1.100, Python 3.10+ and maturin)

From this directory:

```sh
cargo fmt --all -- --check
cargo clippy --all-targets -- -D warnings
cargo test
python -m pip install "maturin>=1.9,<2"
maturin build --release --out dist --interpreter python --compatibility off
python -m pip install --no-index --find-links dist rust-id-interop-pilot
python -m unittest discover -s tests -v
```

The `--compatibility off` wheel is **host-specific test evidence**, not a portable manylinux
release. Before release, commit the generated `Cargo.lock`, repeat exact-head `--locked`
checks, perform dependency/license audit and test actual supported wheel targets. Do not
publish to PyPI or claim a production speedup from this experiment.

## Evidence boundaries

The Python baseline was initially checked locally with six pure-Python unit tests.
Native compilation, wheel import and parity are unverified until actual architecture-specific
CI succeeds. This experiment is a capability prerequisite, not one of the proposed 30
developer-magnet products. Added recurring infrastructure spend R0.

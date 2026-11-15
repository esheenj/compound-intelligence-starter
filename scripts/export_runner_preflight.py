"""Deterministic, allowlisted clean export of the public Runner Preflight Rust utility.

Only source paths explicitly named below enter the artifact. No git history,
private repository files, credentials, remote hosts or deployment actions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "runner-preflight"
SOURCE_FILES = {
    "LICENSE": "LICENSE",
    "experiments/runner_preflight/README_STANDALONE.md": "README.md",
    "experiments/runner_preflight/standalone-ci.template.yml": ".github/workflows/ci.yml",
    "experiments/runner_preflight/fixtures/ready-x64.json": "fixtures/ready-x64.json",
    "experiments/runner_preflight/fixtures/hold-arch.json": "fixtures/hold-arch.json",
    "experiments/runner_preflight/fixtures/warn-disk.json": "fixtures/warn-disk.json",
    "experiments/runner_preflight/fixtures/job-linux-x64.json": "fixtures/job-linux-x64.json",
    "experiments/runner_preflight/fixtures/job-linux-arm64.json": "fixtures/job-linux-arm64.json",
    "scripts/collect_linux_runner.py": "scripts/collect_linux_runner.py",
    "tests/test_runner_preflight_collector.py": "tests/test_runner_preflight_collector.py",
    "experiments/runner_preflight/rust/Cargo.toml": "rust/Cargo.toml",
    "experiments/runner_preflight/rust/Cargo.lock": "rust/Cargo.lock",
    "experiments/runner_preflight/rust/rust-toolchain.toml": "rust/rust-toolchain.toml",
    "experiments/runner_preflight/rust/deny.toml": "rust/deny.toml",
    "experiments/runner_preflight/rust/src/main.rs": "rust/src/main.rs",
}
MAX_FILE_BYTES = 2_000_000
FIXED_DATE = (2020, 1, 1, 0, 0, 0)


def read_allowed(path: Path) -> bytes:
    """Read one regular source file, never a symlink, directory or oversized file."""
    info = path.lstat()
    if not path.is_file() or path.is_symlink() or info.st_size > MAX_FILE_BYTES:
        raise ValueError(f"Rejected nonregular/oversized source: {path.name}")
    data = path.read_bytes()
    if len(data) != info.st_size or len(data) > MAX_FILE_BYTES:
        raise ValueError(f"Unstable or oversized source: {path.name}")
    return data


def manifest_for(items: dict[str, bytes], revision: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("A complete 40-character lowercase Git commit is required")
    files = [
        {
            "path": target,
            "bytes": len(items[target]),
            "sha256": hashlib.sha256(items[target]).hexdigest(),
        }
        for target in sorted(items)
    ]
    provenance = {
        "schema": "runner-preflight-clean-export-v1",
        "source_repository": "esheenj/compound-intelligence-starter",
        "source_commit": revision,
        "scope": "Public standalone source snapshot; no private project content or git history",
        "files": files,
    }
    return (json.dumps(provenance, sort_keys=True, indent=2) + "\n").encode("utf-8")


def export_bundle(out_dir: Path, revision: str, root: Path = REPO) -> tuple[Path, str]:
    """Return the deterministic ZIP path and SHA-256 digest."""
    items: dict[str, bytes] = {}
    for source, target in sorted(SOURCE_FILES.items()):
        if target in items or target.startswith("/") or ".." in Path(target).parts:
            raise ValueError("Invalid or duplicate export target")
        items[target] = read_allowed(root / source)
    items["SOURCE_PROVENANCE.json"] = manifest_for(items, revision)
    out_dir.mkdir(parents=True, exist_ok=True)
    destination = out_dir / (PACKAGE_NAME + "-source.zip")
    with zipfile.ZipFile(destination, "w") as zf:
        for target in sorted(items):
            zi = zipfile.ZipInfo(f"{PACKAGE_NAME}/{target}", FIXED_DATE)
            zi.create_system = 3
            zi.external_attr = 0o100644 << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zi, items[target], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    (out_dir / (destination.name + ".sha256")).write_text(
        f"{digest}  {destination.name}\n", encoding="ascii"
    )
    return destination, digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    opts = parser.parse_args()
    archive, digest = export_bundle(opts.output, opts.source_revision)
    print(f"{archive} sha256={digest}")


if __name__ == "__main__":
    main()

"""Opt-in, read-only Linux inventory for the Runner Preflight Rust CLI.

Requires a declared job file. Observes OS, architecture, free resources and
presence of requested tool *names*. Does not access GitHub, the network,
credentials, private CI labels, process details or versioned tool identities.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import stat
import sys
from pathlib import Path
from typing import Callable

SCHEMA = "runner-preflight-job-v1"
OUTPUT_SCHEMA = "runner-preflight-input-v1"
MAX_BYTES = 65_536
MAX_RESOURCE = 1_000_000
TOKEN = re.compile(r"[A-Za-z0-9_.+/\-]{1,64}\Z")
BINARY = re.compile(r"[A-Za-z0-9_.+\-]{1,64}\Z")
JOB_REQUIRED = {"os", "arch", "min_disk_mb", "min_memory_mb"}
JOB_OPTIONAL = {"required_labels", "required_tools", "rust_target"}
VALID_OS = {"linux", "macos", "windows"}
VALID_ARCH = {"x86_64", "aarch64"}


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    obj: dict = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("Duplicate JSON key")
        obj[key] = value
    return obj


def _reject_constant(_: str) -> None:
    raise ValueError("Nonfinite JSON number")


def _tokens(values: object, pattern: re.Pattern) -> list[str]:
    if not isinstance(values, list) or len(values) > 64:
        raise ValueError("Expected a bounded token list")
    if any(not isinstance(v, str) or not pattern.fullmatch(v) for v in values):
        raise ValueError("Invalid token")
    return values


def validate_job(document: object) -> dict:
    if not isinstance(document, dict) or set(document) != {"schema", "job"}:
        raise ValueError("Unknown or missing job document field")
    if document["schema"] != SCHEMA:
        raise ValueError("Unsupported job schema")
    job = document["job"]
    if not isinstance(job, dict) or not JOB_REQUIRED.issubset(job):
        raise ValueError("Missing job requirements")
    if set(job) - JOB_REQUIRED - JOB_OPTIONAL:
        raise ValueError("Unexpected job requirement")
    if job["os"] not in VALID_OS or job["arch"] not in VALID_ARCH:
        raise ValueError("Unsupported OS or architecture")
    for key in ("min_disk_mb", "min_memory_mb"):
        value = job[key]
        if type(value) is not int or not 0 <= value <= MAX_RESOURCE:
            raise ValueError("Invalid resource threshold")
    _tokens(job.get("required_labels", []), TOKEN)
    # Only simple executable names are probed through PATH, never arguments,
    # relative/absolute paths, host commands or a shell.
    _tokens(job.get("required_tools", []), BINARY)
    target = job.get("rust_target")
    if target is not None and (
        not isinstance(target, str) or not TOKEN.fullmatch(target)
    ):
        raise ValueError("Invalid Rust target")
    return job


def read_job(path: Path) -> dict:
    """Reject symlinks/oversized files, including a symlink swap at open."""
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if not hasattr(os, "O_NOFOLLOW"):
        raise ValueError("No symlink-safe file open on this platform")
    descriptor = os.open(path, flags | os.O_NOFOLLOW)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise ValueError("Job file must be regular and at most 64 KiB")
        data = os.read(descriptor, MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("Job file exceeds 64 KiB")
    finally:
        os.close(descriptor)
    document = json.loads(
        data.decode("utf-8", errors="strict"),
        object_pairs_hook=_pairs,
        parse_constant=_reject_constant,
    )
    return validate_job(document)


def mem_available_kib(text: str) -> int:
    match = re.search(r"^MemAvailable:\s*(\d+)\s+kB$", text, re.MULTILINE)
    if match is None:
        raise ValueError("MemAvailable is not reported")
    value = int(match.group(1))
    if value < 0:
        raise ValueError("Invalid memory observation")
    return value


def collect(
    job: dict,
    *,
    system: str,
    machine: str,
    free_disk_bytes: int,
    free_memory_kib: int,
    which: Callable[[str], str | None],
) -> dict:
    """Pure projection: no host identification, credential or label collection."""
    if system != "Linux":
        raise ValueError("Only Linux is supported for local observations")
    arch = {"x86_64": "x86_64", "amd64": "x86_64",
            "aarch64": "aarch64", "arm64": "aarch64"}.get(machine.lower())
    if not arch:
        raise ValueError("Unknown local architecture")
    if type(free_disk_bytes) is not int or free_disk_bytes < 0:
        raise ValueError("Invalid disk observation")
    if type(free_memory_kib) is not int or free_memory_kib < 0:
        raise ValueError("Invalid memory observation")
    names = sorted(set(job.get("required_tools", [])))
    # Python's shutil.which verifies executable name availability only.
    # It does not run any tool or claim a version/capability.
    tools = [name for name in names if which(name) is not None]
    disk_mb = min(MAX_RESOURCE, free_disk_bytes // (1024 * 1024))
    memory_mb = min(MAX_RESOURCE, free_memory_kib // 1024)
    return {
        "schema": OUTPUT_SCHEMA,
        "runner": {
            "os": "linux",
            "arch": arch,
            "labels": [],  # Runner labels cannot be authenticated locally.
            "disk_free_mb": disk_mb,
            "memory_free_mb": memory_mb,
            "tools": tools,
            "rust_targets": [],  # Target installation is not verified.
        },
        "job": job,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path("."),
                        help="Existing directory whose filesystem free space is observed")
    args = parser.parse_args(argv)
    try:
        if platform.system() != "Linux":
            raise ValueError("Linux-only")
        job = read_job(args.job)
        if not args.workspace.is_dir():
            raise ValueError("Workspace is not a directory")
        available = mem_available_kib(
            Path("/proc/meminfo").read_text(encoding="ascii", errors="strict")
        )
        disk_bytes = shutil.disk_usage(args.workspace).free
        manifest = collect(
            job, system=platform.system(), machine=platform.machine(),
            free_disk_bytes=disk_bytes, free_memory_kib=available,
            which=shutil.which,
        )
    except (OSError, ValueError, UnicodeError, TypeError):
        # Generic stderr; no directory names or host-specific details leaked.
        print("runner-preflight-observer: invalid job or unavailable Linux observation",
              file=sys.stderr)
        return 3
    print(json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

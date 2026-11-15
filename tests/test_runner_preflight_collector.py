"""Deterministic contracts for the opt-in, no-network Linux host observer."""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.collect_linux_runner import (
    MAX_BYTES,
    collect,
    main,
    mem_available_kib,
    read_job,
    validate_job,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "experiments/runner_preflight/fixtures"
if not FIXTURES.is_dir():
    FIXTURES = ROOT / "fixtures"  # The allowlisted standalone source ZIP layout.
X64 = FIXTURES / "job-linux-x64.json"
ARM64 = FIXTURES / "job-linux-arm64.json"


def document(arch: str = "x86_64") -> dict:
    return {
        "schema": "runner-preflight-job-v1",
        "job": {
            "os": "linux", "arch": arch, "required_labels": [],
            "min_disk_mb": 1, "min_memory_mb": 1,
            "required_tools": ["git", "python3"], "rust_target": None,
        },
    }


class CollectorTests(unittest.TestCase):
    def test_shipped_fixtures_are_valid_and_allowlisted(self):
        self.assertEqual(read_job(X64), document()["job"])
        self.assertEqual(read_job(ARM64), document("aarch64")["job"])

    def test_pure_x64_projection_observes_only_declared_tools_and_counts(self):
        job = validate_job(document())
        actual = collect(
            job, system="Linux", machine="x86_64",
            free_disk_bytes=8 * 1024**3, free_memory_kib=4 * 1024**2,
            which=lambda name: "/sample/" + name if name == "python3" else None,
        )
        self.assertEqual(actual["schema"], "runner-preflight-input-v1")
        self.assertEqual(actual["runner"], {
            "os": "linux", "arch": "x86_64", "labels": [],
            "disk_free_mb": 8192, "memory_free_mb": 4096,
            "tools": ["python3"], "rust_targets": [],
        })
        self.assertEqual(actual["job"], job)
        self.assertNotIn("/sample", json.dumps(actual))
        self.assertNotIn("PATH", json.dumps(actual))

    def test_arm64_projection_never_invents_labels_targets_or_versions(self):
        doc = document("aarch64")
        doc["job"]["required_labels"] = ["gpu", "custom"]
        doc["job"]["rust_target"] = "aarch64-unknown-linux-gnu"
        actual = collect(
            validate_job(doc), system="Linux", machine="arm64",
            free_disk_bytes=16 * 1024**3, free_memory_kib=6000,
            which=lambda _: "/binary",
        )
        self.assertEqual(actual["runner"]["arch"], "aarch64")
        self.assertEqual(actual["runner"]["labels"], [])
        self.assertEqual(actual["runner"]["rust_targets"], [])
        self.assertEqual(actual["runner"]["tools"], ["git", "python3"])

    def test_bounded_thresholds_and_tokens_reject_invalid_input(self):
        for value in (-1, True, 1000001, 1.3, "1"):
            doc = document()
            doc["job"]["min_disk_mb"] = value
            with self.assertRaises(ValueError):
                validate_job(doc)
        for label in ("bad\nlabel", "", "x" * 65):
            doc = document()
            doc["job"]["required_labels"] = [label]
            with self.assertRaises(ValueError):
                validate_job(doc)
        for name in ("../secrets", "/usr/bin/python3", "node --help"):
            doc = document()
            doc["job"]["required_tools"] = [name]
            with self.assertRaises(ValueError):
                validate_job(doc)
        doc = document()
        doc["job"]["extra"] = "ignored?"
        with self.assertRaises(ValueError):
            validate_job(doc)

    def test_symlinks_duplicate_keys_nan_and_oversize_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / "job.json"
            p.write_text('{"schema":"runner-preflight-job-v1","schema":"x","job":{}}')
            with self.assertRaises(ValueError):
                read_job(p)
            p.write_text('{"schema":"runner-preflight-job-v1","job":{"os":"linux","arch":"x86_64","min_disk_mb":NaN,"min_memory_mb":1}}')
            with self.assertRaises(ValueError):
                read_job(p)
            p.write_bytes(b" " * (MAX_BYTES + 1))
            with self.assertRaises(ValueError):
                read_job(p)
            p.write_text(json.dumps(document()))
            link = root / "symlink.json"
            try:
                link.symlink_to(p)
            except (OSError, NotImplementedError):
                self.skipTest("Symlinks disabled by runner")
            with self.assertRaises(OSError):
                read_job(link)
            with self.assertRaises(ValueError):
                read_job(root)

    def test_missing_host_observations_are_rejected(self):
        job = validate_job(document())
        with self.assertRaises(ValueError):
            collect(job, system="Windows", machine="x86_64",
                    free_disk_bytes=10000, free_memory_kib=10000,
                    which=lambda _: None)
        with self.assertRaises(ValueError):
            collect(job, system="Linux", machine="mips",
                    free_disk_bytes=10000, free_memory_kib=10000,
                    which=lambda _: None)
        with self.assertRaises(ValueError):
            mem_available_kib("MemTotal: 123 kB")
        self.assertEqual(mem_available_kib("MemAvailable:       4096 kB\n"), 4096)

    @unittest.skipUnless(os.name == "posix" and Path("/proc/meminfo").is_file(),
                         "requires Linux /proc for actual read-only observation")
    def test_cli_observes_local_linux_without_network_or_private_identifiers(self):
        import platform
        if platform.machine().lower() not in {"x86_64", "amd64", "aarch64", "arm64"}:
            self.skipTest("Unsupported test architecture")
        src = ARM64 if platform.machine().lower() in {"aarch64", "arm64"} else X64
        with tempfile.TemporaryDirectory() as tmp:
            job_path = Path(tmp) / "job.json"
            job_path.write_bytes(src.read_bytes())
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = main(["--job", str(job_path), "--workspace", tmp])
            self.assertEqual(result, 0)
            manifest = json.loads(output.getvalue())
            self.assertEqual(manifest["schema"], "runner-preflight-input-v1")
            self.assertEqual(manifest["runner"]["os"], "linux")
            self.assertEqual(manifest["runner"]["labels"], [])
            self.assertEqual(manifest["runner"]["rust_targets"], [])
            self.assertIn("python3", manifest["runner"]["tools"])
            self.assertNotIn(tmp, output.getvalue())
            self.assertNotIn("home", manifest["runner"])


if __name__ == "__main__":
    unittest.main()

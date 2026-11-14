"""Clean source-export contract tests; Python standard library only."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.export_runner_preflight import (
    PACKAGE_NAME,
    REPO,
    SOURCE_FILES,
    export_bundle,
    manifest_for,
    read_allowed,
)

REVISION = "0123456789abcdef" * 2 + "01234567"


class RunnerPreflightExportTests(unittest.TestCase):
    def test_two_clean_exports_are_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            first, first_sha = export_bundle(Path(temp) / "first", REVISION)
            second, second_sha = export_bundle(Path(temp) / "second", REVISION)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first_sha, second_sha)
            self.assertEqual(first_sha, hashlib.sha256(first.read_bytes()).hexdigest())
            self.assertEqual(
                (first.parent / (first.name + ".sha256")).read_text(encoding="ascii"),
                f"{first_sha}  {first.name}\n",
            )

    def test_only_explicit_public_assets_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            archive, _ = export_bundle(Path(temp), REVISION)
            with zipfile.ZipFile(archive) as zf:
                self.assertIsNone(zf.testzip())
                names = zf.namelist()
                self.assertEqual(names, sorted(names))
                expected = {f"{PACKAGE_NAME}/{target}" for target in SOURCE_FILES.values()}
                expected.add(f"{PACKAGE_NAME}/SOURCE_PROVENANCE.json")
                self.assertEqual(set(names), expected)
                for source, target in SOURCE_FILES.items():
                    self.assertEqual(
                        zf.read(f"{PACKAGE_NAME}/{target}"),
                        (REPO / source).read_bytes(),
                    )
                manifest = json.loads(zf.read(f"{PACKAGE_NAME}/SOURCE_PROVENANCE.json"))
                self.assertEqual(manifest["source_commit"], REVISION)
                self.assertEqual(manifest["schema"], "runner-preflight-clean-export-v1")
                self.assertEqual({f["path"] for f in manifest["files"]}, set(SOURCE_FILES.values()))
                for record in manifest["files"]:
                    content = zf.read(f"{PACKAGE_NAME}/{record['path']}")
                    self.assertEqual(record["bytes"], len(content))
                    self.assertEqual(record["sha256"], hashlib.sha256(content).hexdigest())
                self.assertIn("working-directory: rust", zf.read(f"{PACKAGE_NAME}/.github/workflows/ci.yml").decode())

    def test_reject_incomplete_revision(self) -> None:
        with self.assertRaises(ValueError):
            manifest_for({"README.md": b"hello"}, "not-a-real-commit")

    def test_reject_symlinks_and_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / "data.txt"
            file.write_text("normal", encoding="utf-8")
            self.assertEqual(read_allowed(file), b"normal")
            with self.assertRaises(ValueError):
                read_allowed(root)
            link = root / "link.txt"
            try:
                link.symlink_to(file)
            except (OSError, NotImplementedError):
                self.skipTest("OS does not permit test symlinks")
            with self.assertRaises(ValueError):
                read_allowed(link)


if __name__ == "__main__":
    unittest.main()

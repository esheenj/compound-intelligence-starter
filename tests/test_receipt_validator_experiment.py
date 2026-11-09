"""Cross-language pilot: positive and negative cases plus optional Rust parity."""
from __future__ import annotations

import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from experiments.receipt_validator.python_validator import validate_line

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "receipt_validator_cases.tsv"
MANIFEST = ROOT / "experiments" / "receipt_validator" / "rust" / "Cargo.toml"
EXPECTED = ["VALID", "VALID", "VALID"] + ["INVALID"] * 7


class ReceiptValidatorExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = FIXTURE.read_text(encoding="utf-8").splitlines()

    def test_reference_contract(self) -> None:
        self.assertEqual(len(self.records), 10)
        self.assertEqual(["VALID" if validate_line(s) else "INVALID" for s in self.records], EXPECTED)
        self.assertFalse(validate_line("x" * 513))
        self.assertFalse(validate_line("é\tACCEPTED\t" + "0" * 64))

    def test_python_cli(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "experiments" / "receipt_validator" / "python_validator.py")],
            input=FIXTURE.read_text(encoding="utf-8"), capture_output=True, text=True, check=True,
        )
        self.assertEqual(result.stdout.splitlines(), EXPECTED)

    @unittest.skipUnless(shutil.which("cargo"), "Rust toolchain unavailable locally; CI parity check required")
    def test_python_rust_parity(self) -> None:
        subprocess.run(["cargo", "build", "--quiet", "--manifest-path", str(MANIFEST)], check=True, timeout=120)
        binary = MANIFEST.parent / "target" / "debug" / "receipt-validator-pilot"
        result = subprocess.run([str(binary)], input=FIXTURE.read_text(encoding="utf-8"), capture_output=True, text=True, check=True, timeout=15)
        self.assertEqual(result.stdout.splitlines(), EXPECTED)


if __name__ == "__main__":
    unittest.main()

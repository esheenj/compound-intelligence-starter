import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.compound_intelligence.engine import EvidenceStore, bounded_run, validate
from src.compound_intelligence.ollama import advisory
from src.compound_intelligence.runner import EXAMPLES


class EngineTests(unittest.TestCase):
    def test_expected_and_counterexample(self):
        self.assertTrue(validate(EXAMPLES[0])["accepted"])
        self.assertEqual(validate(EXAMPLES[1])["counterexample"], {"expected": 7, "actual": 8})

    def test_bool_not_integer_and_unsupported_kind(self):
        with self.assertRaises(ValueError):
            validate({"kind": "sum", "values": [True], "expected": 1})
        with self.assertRaises(ValueError):
            validate({"kind": "shell", "values": [1], "expected": 1})

    def test_transactional_recovery_and_evidence_reuse(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "memory.sqlite3"
            first = bounded_run(path, EXAMPLES, advisor=lambda e: {"review": e["id"]})
            self.assertEqual(first["new"], 3)
            called = []
            second = bounded_run(path, EXAMPLES, advisor=lambda e: called.append(e))
            self.assertEqual(second["new"], 0)
            self.assertFalse(called)
            store = EvidenceStore(path)
            self.assertEqual(len(store.list()), 3)
            self.assertEqual(store.get(EXAMPLES[1]["id"])["status"], "REJECTED")
            store.close()

    def test_conflicting_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with EvidenceStoreContext(Path(d) / "evidence.db") as store:
                store.run(EXAMPLES[0])
                with self.assertRaisesRegex(ValueError, "different inputs"):
                    store.run({**EXAMPLES[0], "expected": 900})

    def test_iteration_limit(self):
        with tempfile.TemporaryDirectory() as d:
            result = bounded_run(Path(d) / "x.db", EXAMPLES, limit=1)
            self.assertEqual(result["processed"], 1)
        with self.assertRaises(ValueError):
            bounded_run(Path("unused.db"), EXAMPLES, limit=101)

    def test_invalid_model_endpoint_rejected_before_network(self):
        with self.assertRaises(ValueError):
            advisory(EXAMPLES[0], model="test", endpoint="https://example.com")

    @patch("src.compound_intelligence.ollama.urlopen")
    def test_ollama_advisory_is_not_validation(self, urlopen):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"response":"Try a counterexample."}'
        urlopen.return_value = response
        result = advisory(EXAMPLES[0], model="tiny")
        self.assertEqual(result["authority"], "ADVISORY_ONLY")
        self.assertEqual(result["critique"], "Try a counterexample.")


class EvidenceStoreContext:
    def __init__(self, path):
        self.store = EvidenceStore(path)
    def __enter__(self):
        return self.store
    def __exit__(self, *args):
        self.store.close()


if __name__ == "__main__":
    unittest.main()

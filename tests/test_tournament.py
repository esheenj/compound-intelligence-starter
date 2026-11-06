import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.compound_intelligence.tournament import (
    compare, fixture_proposal, ollama_proposal, _local_endpoint,
)


class TournamentTests(unittest.TestCase):
    def test_fixture_compares_two_proposals(self):
        with tempfile.TemporaryDirectory() as directory:
            result = compare([8, 13], ["fixture-correct", "fixture-incorrect"],
                             Path(directory), proposer=fixture_proposal)
            self.assertEqual([x["status"] for x in result["results"]], ["VERIFIED", "REJECTED"])
            self.assertEqual((result["verified"], result["rejected"]), (1, 1))

    def test_replay_skips_model_call(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            compare([2, 3], ["a"], root, proposer=lambda model, task: {"expected": 5})
            def forbidden(model, task):
                raise AssertionError("model called after evidence saved")
            result = compare([2, 3], ["a"], root, proposer=forbidden)
            self.assertFalse(result["results"][0]["new"])
            self.assertEqual(result["results"][0]["status"], "VERIFIED")

    def test_task_changes_make_distinct_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = lambda name, task: {"expected": sum(task["values"])}
            self.assertTrue(compare([2, 3], ["a"], root, proposer=model)["results"][0]["new"])
            self.assertTrue(compare([2, 4], ["a"], root, proposer=model)["results"][0]["new"])

    def test_model_errors_do_not_create_verified_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            result = compare([2, 3], ["missing"], Path(directory),
                             proposer=lambda name, task: {"error": "offline"})
            self.assertEqual(result["no_result"], 1)
            self.assertEqual(result["verified"], 0)

    def test_invalid_bounds_and_duplicate_models(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                compare([True], ["a"], Path(directory))
            with self.assertRaises(ValueError):
                compare([2], ["a", "a"], Path(directory))
            with self.assertRaises(ValueError):
                compare([2], ["a;" ], Path(directory))

    def test_local_endpoint_restriction(self):
        for url in ["http://example.org:11434", "https://localhost:11434",
                    "http://localhost:11434/something", "http://user@localhost:11434"]:
            with self.assertRaises(ValueError):
                _local_endpoint(url)

    @patch("src.compound_intelligence.tournament.urlopen")
    def test_ollama_json_is_only_proposal(self, opener):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"response": '{"expected":21,"reason":"addition"}'}).encode()
        opener.return_value = response
        proposed = ollama_proposal("test", {"kind": "sum", "values": [8, 13]})
        self.assertEqual(proposed["expected"], 21)
        self.assertEqual(proposed["reason"], "addition")

    @patch("src.compound_intelligence.tournament.urlopen")
    def test_invalid_ollama_result_not_accepted(self, opener):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"response":"{\"expected\":true}"}'
        opener.return_value = response
        self.assertEqual(ollama_proposal("test", {"kind": "sum", "values": [1]})["error"],
                         "INVALID_PROPOSAL")


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.compound_intelligence.challenges import compare, evaluate, public_task, fingerprint, ChallengeLedger
from src.compound_intelligence.problem_runner import fixture, propose_ollama

FIXTURES = json.loads((Path(__file__).resolve().parents[1] / "examples/challenges.json").read_text())


class ChallengeTests(unittest.TestCase):
    def test_fixture_validates_two_distinct_task_kinds(self):
        with tempfile.TemporaryDirectory() as directory:
            result = compare(FIXTURES, ["fixture-correct", "fixture-incorrect"], Path(directory), fixture)
            self.assertEqual((result["verified"], result["rejected"], result["new"]), (2, 2, 4))

    def test_replay_skips_all_model_calls_and_recovers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            compare(FIXTURES, ["fixture-correct"], root, fixture)
            def must_not_call(*args):
                raise AssertionError("unexpected repeated model call")
            outcome = compare(FIXTURES, ["fixture-correct"], root, must_not_call)
            self.assertEqual(outcome["new"], 0)
            self.assertEqual(outcome["verified"], 2)

    def test_reference_is_not_in_model_prompt(self):
        for task in FIXTURES:
            exposed = public_task(task)
            self.assertNotIn("expected", exposed)
            self.assertEqual(exposed["type"], task["type"])

    def test_bad_extract_typing_is_rejected(self):
        self.assertEqual(evaluate(FIXTURES[0],
                         {"support_email": "help@example.test", "returns_days": "30"})["status"], "REJECTED")

    def test_patch_must_be_unique_and_never_runs(self):
        self.assertEqual(evaluate(FIXTURES[1], {"old": "len(items)", "new": "sum(items)"})["status"], "VERIFIED")
        self.assertEqual(evaluate(FIXTURES[1], {"old": "return", "new": "run()",
                         "extra": "ignored"})["status"], "REJECTED")

    def test_conflicting_tasks_cannot_reuse_identity(self):
        changed = {**FIXTURES[0], "expected": {**FIXTURES[0]["expected"], "returns_days": 7}}
        self.assertNotEqual(fingerprint(FIXTURES[0], "x"), fingerprint(changed, "x"))

    def test_failures_are_recorded_not_upgraded(self):
        with tempfile.TemporaryDirectory() as directory:
            result = compare(FIXTURES[:1], ["offline"], Path(directory),
                             lambda *args: {"_error": "not available"})
            self.assertEqual(result["no_result"], 1)
            replay = compare(FIXTURES[:1], ["offline"], Path(directory),
                             lambda *args: {"support_email": "help@example.test", "returns_days": 30})
            self.assertEqual(replay["no_result"], 1)
            self.assertEqual(replay["new"], 0)

    def test_bounds_on_models_and_tasks(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                compare(FIXTURES, ["x"] * 5, Path(directory), fixture)
            with self.assertRaises(ValueError):
                compare([FIXTURES[0]] * 21, ["x"], Path(directory), fixture)
            with self.assertRaises(ValueError):
                compare(FIXTURES, ["bad model"], Path(directory), fixture)

    @patch("src.compound_intelligence.problem_runner.urlopen")
    def test_model_response_is_untrusted_proposal(self, opener):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "response": json.dumps({"support_email": "help@example.test", "returns_days": 30})
        }).encode()
        opener.return_value = response
        output = propose_ollama("example", public_task(FIXTURES[0]))
        self.assertEqual(output["returns_days"], 30)
        sent = opener.call_args[0][0].data.decode()
        self.assertNotIn('"expected"', sent)

    def test_only_local_model_endpoint(self):
        with self.assertRaises(ValueError):
            propose_ollama("example", public_task(FIXTURES[0]), endpoint="http://evil.test")

    def test_ledger_records_multiple_verified_and_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "challenges.sqlite3"
            compare(FIXTURES, ["fixture-correct", "fixture-incorrect"], Path(directory), fixture)
            ledger = ChallengeLedger(path)
            self.assertEqual(len(ledger.records()), 4)
            ledger.close()


if __name__ == "__main__":
    unittest.main()

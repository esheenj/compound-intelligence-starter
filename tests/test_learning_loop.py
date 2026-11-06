import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from src.compound_intelligence.learning_loop import KnowledgeStore, offline_fixture, run

ROOT = Path(__file__).resolve().parents[1]
SEED = [x for x in json.loads((ROOT / "examples/challenges.json").read_text()) if x["type"] == "extract"]
TARGETS = json.loads((ROOT / "examples/transfer_challenges.json").read_text())


class LearningLoopTests(unittest.TestCase):
    def test_fixture_uses_verified_example_for_new_task(self):
        with tempfile.TemporaryDirectory() as d:
            result = run(SEED, TARGETS, Path(d), "fixture-transfer", offline_fixture, run_id="r1")
            self.assertEqual(result["new_verified_exemplars"], 1)
            self.assertEqual(result["results"][0]["status"], "VERIFIED")
            self.assertEqual(result["results"][0]["retrieved_ids"], ["store-policy-extraction"])
            self.assertEqual(result["origin"], "SIMULATED_FIXTURE")

    def test_recovery_does_not_invoke_proposer_again(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run(SEED, TARGETS, root, "fixture-transfer", offline_fixture, run_id="r1")
            blocked = Mock(side_effect=AssertionError("should not invoke"))
            existing = run(SEED, TARGETS, root, "fixture-transfer", blocked, run_id="r1")
            self.assertTrue(existing["reused_receipt"])
            blocked.assert_not_called()

    def test_invalid_seed_not_promoted(self):
        bad = dict(SEED[0])
        bad["expected"] = {"support_email": "not-the-email", "returns_days": 900}
        with tempfile.TemporaryDirectory() as d:
            result = run([bad], TARGETS, Path(d), "fixture-transfer", offline_fixture, run_id="r2")
            self.assertEqual(result["new_verified_exemplars"], 0)
            self.assertEqual(result["results"][0]["status"], "NO_RESULT")

    def test_target_reference_never_reaches_proposer(self):
        with tempfile.TemporaryDirectory() as d:
            seen = []
            def proposer(model, task):
                seen.append(task)
                if task["id"] == SEED[0]["id"]:
                    return SEED[0]["expected"]
                return TARGETS[0]["expected"]
            result = run(SEED, TARGETS, Path(d), "mock-model", proposer, run_id="r3")
            self.assertEqual(result["results"][0]["status"], "VERIFIED")
            for item in seen:
                self.assertNotIn("expected", item)

    def test_no_same_identity_or_same_input_retrieval(self):
        with tempfile.TemporaryDirectory() as d:
            store = KnowledgeStore(Path(d) / "k.sqlite3")
            self.assertTrue(store.remember(SEED[0], SEED[0]["expected"]))
            self.assertEqual(store.relevant(SEED[0]), [])
            alt = {**SEED[0], "id": "different-id"}
            self.assertEqual(store.relevant(alt), [])
            store.close()

    def test_wrong_answer_is_never_remembered(self):
        with tempfile.TemporaryDirectory() as d:
            store = KnowledgeStore(Path(d) / "k.sqlite3")
            self.assertFalse(store.remember(SEED[0], {"support_email": "wrong", "returns_days": 10}))
            self.assertEqual(store.relevant(TARGETS[0]), [])
            store.close()

    def test_run_id_conflict_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run(SEED, TARGETS, root, "fixture-transfer", offline_fixture, run_id="same")
            changed = [{**TARGETS[0], "text": "Different text: returns within 2 days"}]
            with self.assertRaisesRegex(ValueError, "different inputs"):
                run(SEED, changed, root, "fixture-transfer", offline_fixture, run_id="same")

    def test_missing_retrieval_and_limits(self):
        with tempfile.TemporaryDirectory() as d:
            result = run(SEED, TARGETS, Path(d), "fixture-transfer", offline_fixture,
                         run_id="no-memory", limit=0)
            self.assertEqual(result["results"][0]["status"], "NO_RESULT")
        with self.assertRaises(ValueError):
            run(SEED, TARGETS, Path("unused"), "fixture-transfer", offline_fixture,
                run_id="x", limit=4)


if __name__ == "__main__":
    unittest.main()

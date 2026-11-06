import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from src.compound_intelligence.ab_evaluation import evaluate_pairs
from src.compound_intelligence.learning_loop import offline_fixture

ROOT = Path(__file__).resolve().parents[1]
SEEDS = [item for item in json.loads((ROOT / "examples/challenges.json").read_text())
         if item["type"] == "extract"]
TARGETS = json.loads((ROOT / "examples/transfer_challenges.json").read_text())


class ABTests(unittest.TestCase):
    def test_simulated_fixture_is_labeled_and_paired(self):
        with tempfile.TemporaryDirectory() as d:
            r = evaluate_pairs(SEEDS, TARGETS, Path(d), "fixture-transfer",
                               offline_fixture, run_id="ab-a")
            self.assertEqual(r["origin"], "SIMULATED_FIXTURE")
            self.assertEqual((r["baseline_verified"], r["assisted_verified"]), (0, 1))
            self.assertEqual((r["paired_gains"], r["paired_losses"]), (1, 0))
            self.assertEqual(r["results"][0]["retrieved_ids"], ["store-policy-extraction"])

    def test_repeated_receipt_skips_model_calls(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            evaluate_pairs(SEEDS, TARGETS, root, "mock", offline_fixture, run_id="ab")
            forbidden = Mock(side_effect=AssertionError("should not run"))
            result = evaluate_pairs(SEEDS, TARGETS, root, "mock", forbidden, run_id="ab")
            forbidden.assert_not_called()
            self.assertTrue(result["reused_receipt"])

    def test_baseline_prompt_never_contains_exemplars_and_reference_hidden(self):
        with tempfile.TemporaryDirectory() as d:
            seen = []
            def proposer(model, prompt):
                seen.append(prompt)
                if prompt["id"] == SEEDS[0]["id"]:
                    return SEEDS[0]["expected"]
                return TARGETS[0]["expected"]
            r = evaluate_pairs(SEEDS, TARGETS, Path(d), "mock", proposer, run_id="ab")
            self.assertEqual(r["baseline_verified"], 1)
            self.assertEqual(r["assisted_verified"], 1)
            self.assertEqual(r["net_verified_change"], 0)
            self.assertNotIn("verified_examples", seen[1])
            self.assertEqual(len(seen[2]["verified_examples"]), 1)
            self.assertTrue(all("expected" not in prompt for prompt in seen))

    def test_changed_spec_with_same_id_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            evaluate_pairs(SEEDS, TARGETS, root, "fixture-transfer", offline_fixture, run_id="same")
            altered = [{**TARGETS[0], "expected": {**TARGETS[0]["expected"], "returns_days": 31}}]
            with self.assertRaisesRegex(ValueError, "different inputs"):
                evaluate_pairs(SEEDS, altered, root, "fixture-transfer", offline_fixture, run_id="same")

    def test_seed_wrong_is_not_retrieved(self):
        with tempfile.TemporaryDirectory() as d:
            invalid_seed = [{**SEEDS[0], "expected": {"support_email": "bad", "returns_days": 30}}]
            r = evaluate_pairs(invalid_seed, TARGETS, Path(d), "fixture-transfer",
                               offline_fixture, run_id="badseed")
            self.assertEqual(r["new_verified_seeds"], 0)
            self.assertEqual(r["assisted_verified"], 0)
            self.assertEqual(r["results"][0]["retrieved_ids"], [])

    def test_arms_alternate_order(self):
        with tempfile.TemporaryDirectory() as d:
            extra = {**TARGETS[0], "id": "second-target",
                     "text": "New: office@another.example; returns in 16 days.",
                     "expected": {"support_email": "office@another.example", "returns_days": 16}}
            r = evaluate_pairs(SEEDS, TARGETS + [extra], Path(d),
                               "fixture-transfer", offline_fixture, run_id="two")
            self.assertEqual(r["results"][0]["invocation_order"], ["baseline", "assisted"])
            self.assertEqual(r["results"][1]["invocation_order"], ["assisted", "baseline"])

    def test_limits_and_unique_id_required(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                evaluate_pairs(SEEDS, TARGETS, Path(d), "fixture-transfer",
                               offline_fixture, run_id="x", max_examples=4)
            with self.assertRaises(ValueError):
                evaluate_pairs(SEEDS, TARGETS * 11, Path(d), "fixture-transfer",
                               offline_fixture, run_id="x")

    def test_no_evidence_not_promoted(self):
        with tempfile.TemporaryDirectory() as d:
            r = evaluate_pairs(SEEDS, TARGETS, Path(d), "mock",
                               lambda model, task: {"_error": "unavailable"}, run_id="none")
            self.assertEqual(r["baseline_verified"], 0)
            self.assertEqual(r["assisted_verified"], 0)
            self.assertEqual(r["new_verified_seeds"], 0)
            self.assertEqual(r["net_verified_change"], 0)


if __name__ == "__main__":
    unittest.main()

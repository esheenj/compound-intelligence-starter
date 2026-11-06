import tempfile
import unittest
from pathlib import Path

from src.compound_intelligence.scheduler import (
    CAPABILITY, MAX_ATTEMPTS, JobQueue, tick,
)


class QueueTests(unittest.TestCase):
    def test_enqueue_dedupe_and_capability_policy(self):
        with tempfile.TemporaryDirectory() as d:
            q = JobQueue(Path(d) / "queue.db")
            self.assertEqual(q.enqueue("demo")["state"], "PENDING")
            self.assertEqual(q.enqueue("demo")["state"], "PENDING")
            self.assertEqual(len(q.list()), 1)
            with self.assertRaises(ValueError):
                q.enqueue("demo", "shell")
            with self.assertRaises(ValueError):
                q.enqueue("../unsafe")
            q.close()

    def test_tick_executes_fixture_only_once(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            q = JobQueue(root / "queue.sqlite3")
            q.enqueue("job1")
            q.close()
            self.assertEqual(tick(root)[0]["state"], "DONE")
            self.assertEqual(tick(root), [])
            q = JobQueue(root / "queue.sqlite3")
            job = q.get("job1")
            self.assertEqual(job["attempts"], 1)
            self.assertEqual(job["result"]["run_mode"], "SIMULATED_FIXTURE")
            self.assertEqual(len(job["result"]["results"]), 4)
            q.close()

    def test_wrong_token_cannot_finish(self):
        with tempfile.TemporaryDirectory() as d:
            q = JobQueue(Path(d) / "queue.db")
            q.enqueue("demo")
            job_id, _, token = q.claim(now=1)
            self.assertFalse(q.finish(job_id, "other", result={"ok": True}))
            self.assertTrue(q.finish(job_id, token, result={"ok": True}))
            self.assertFalse(q.finish(job_id, token, result={"ok": False}))
            q.close()

    def test_lease_expiry_and_retry_then_failure(self):
        with tempfile.TemporaryDirectory() as d:
            q = JobQueue(Path(d) / "queue.db")
            q.enqueue("demo")
            first = q.claim(now=1)
            self.assertIsNone(q.claim(now=2))
            second = q.claim(now=100)
            self.assertNotEqual(first[2], second[2])
            self.assertFalse(q.finish(first[0], first[2], result={"late": True}))
            self.assertIsNone(q.claim(now=200))
            self.assertEqual(q.get("demo")["state"], "FAILED")
            self.assertEqual(q.get("demo")["attempts"], MAX_ATTEMPTS)
            q.close()

    def test_exception_requeues_then_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            q = JobQueue(root / "queue.sqlite3")
            q.enqueue("demo")
            q.close()
            def bad(*args):
                raise RuntimeError("failure")
            self.assertEqual(tick(root, executor=bad)[0]["state"], "PENDING")
            self.assertEqual(tick(root, executor=bad)[0]["state"], "FAILED")

    def test_bounded_tick(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            q = JobQueue(root / "queue.sqlite3")
            for i in range(7):
                q.enqueue("job-" + str(i))
            q.close()
            self.assertEqual(len(tick(root, max_jobs=5)), 5)
            self.assertEqual(len(tick(root, max_jobs=5)), 2)
        with self.assertRaises(ValueError):
            tick(Path("unused"), 6)

    def test_no_arbitrary_tool_execution(self):
        with tempfile.TemporaryDirectory() as d:
            q = JobQueue(Path(d) / "queue.db")
            with self.assertRaises(ValueError):
                q.enqueue("run-command", "execute_shell")
            q.close()


if __name__ == "__main__":
    unittest.main()

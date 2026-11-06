import sqlite3
import tempfile
import unittest
from pathlib import Path

from src.compound_intelligence.dashboard import build, render, snapshot
from src.compound_intelligence.scheduler import JobQueue, tick
from src.compound_intelligence.challenges import ChallengeLedger, compare
from src.compound_intelligence.problem_runner import fixture
import json

FIXTURES = json.loads((Path(__file__).resolve().parents[1] / "examples/challenges.json").read_text())


class DashboardTests(unittest.TestCase):
    def test_works_with_completed_queue_and_challenge_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue = JobQueue(root / "queue.sqlite3")
            queue.enqueue("example")
            queue.close()
            tick(root)
            compare(FIXTURES, ["fixture-correct"], root / "research", fixture)
            data = snapshot(root / "queue.sqlite3", root / "research/challenges.sqlite3")
            self.assertEqual(data["job_counts"]["DONE"], 1)
            self.assertEqual(len(data["jobs"]), 1)
            self.assertEqual(len(data["outcomes"]), 6)
            self.assertEqual(len(data["models"]), 3)
            report = build(root / "queue.sqlite3", root / "research/challenges.sqlite3",
                           root / "site" / "index.html")
            self.assertEqual(report["evaluations"], 6)
            content = (root / "site/index.html").read_text()
            self.assertIn("SIMULATED_FIXTURE", content)
            self.assertIn("UNKNOWN_PROVIDER", content)
            self.assertIn("Content-Security-Policy", content)

    def test_empty_and_missing_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue = JobQueue(root / "queue.sqlite3")
            queue.close()
            data = snapshot(root / "queue.sqlite3")
            self.assertEqual(data["outcomes"], [])
            self.assertIn("Compound Intelligence", render(data))
            with self.assertRaises(FileNotFoundError):
                snapshot(root / "missing.db")

    def test_xss_is_escaped_even_if_database_is_untrusted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue = JobQueue(root / "queue.sqlite3")
            queue.enqueue("safe-id")
            queue.close()
            connection = sqlite3.connect(root / "queue.sqlite3")
            connection.execute("UPDATE jobs SET error=?,capability=? WHERE id='safe-id'",
                               ('<script>alert("bad")</script>', '<img src=x onerror=alert(1)>'))
            connection.commit()
            connection.close()
            page = render(snapshot(root / "queue.sqlite3"))
            self.assertNotIn('<script>alert(', page)
            self.assertNotIn('<img src=x', page)
            self.assertIn("&lt;script&gt;", page)
            self.assertIn("&lt;img", page)

    def test_viewer_does_not_mutate_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            q = JobQueue(root / "queue.sqlite3")
            q.enqueue("job")
            q.close()
            before = (root / "queue.sqlite3").read_bytes()
            snapshot(root / "queue.sqlite3")
            self.assertEqual((root / "queue.sqlite3").read_bytes(), before)

    def test_refuses_oversized_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            q = JobQueue(root / "queue.sqlite3")
            q.close()
            conn = sqlite3.connect(root / "queue.sqlite3")
            conn.executemany("INSERT INTO jobs (id,spec_digest,capability,state) VALUES (?, 'x', 'fixture_benchmark', 'PENDING')",
                             [(f"j{i}",) for i in range(1001)])
            conn.commit()
            conn.close()
            with self.assertRaises(ValueError):
                snapshot(root / "queue.sqlite3")


if __name__ == "__main__":
    unittest.main()

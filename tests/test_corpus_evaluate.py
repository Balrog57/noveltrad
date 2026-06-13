import json
import subprocess
import sys
import unittest

from tests.corpus.evaluate import evaluate_all


class CorpusEvaluateTests(unittest.TestCase):
    def test_evaluate_all_returns_stable_offline_shape(self) -> None:
        report = evaluate_all()
        self.assertEqual(report["schema_version"], 1)
        self.assertTrue(report["offline"])
        self.assertGreaterEqual(report["summary"]["case_count"], 6)
        for case in report["cases"]:
            self.assertIn("case_id", case)
            self.assertIn("format", case)
            self.assertIn("metrics", case)
            self.assertIn("warnings", case)
            self.assertIn("duration_ms", case)
            self.assertEqual(case["tokens"], {"input": 0, "output": 0})
            self.assertEqual(case["estimated_cost_usd"], 0.0)

    def test_module_outputs_json(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "tests.corpus.evaluate"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        parsed = json.loads(proc.stdout)
        self.assertEqual(parsed["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()

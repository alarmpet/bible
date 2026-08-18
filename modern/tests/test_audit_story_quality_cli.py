from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).parents[2]
CLI = ROOT / "modern" / "scripts" / "audit_story_quality.py"
FIXTURES = ROOT / "modern" / "tests" / "fixtures"


class AuditStoryQualityCliTests(unittest.TestCase):
    def run_cli(self, fixture_name: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), "--text", str(FIXTURES / fixture_name)],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

    def test_clean_text_returns_zero_and_json_report(self) -> None:
        result = self.run_cli("clean_story.txt")

        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])

    def test_repeated_text_returns_two_and_block_code(self) -> None:
        result = self.run_cli("repeated_story.txt")

        self.assertEqual(2, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(
            any("FILLER_REPEAT_BLOCK" in item for item in report["blocks"])
        )


if __name__ == "__main__":
    unittest.main()

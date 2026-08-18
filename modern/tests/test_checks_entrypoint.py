from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).parents[2]


class ChecksEntrypointTests(unittest.TestCase):
    def test_direct_script_execution_runs_selftest(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "modern" / "checks.py")],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("checks.py selftest OK", result.stdout)


if __name__ == "__main__":
    unittest.main()

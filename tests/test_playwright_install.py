"""The install script falls back, and a hung download cannot run forever."""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "playwright-install" / "run.sh"


def _npx(log: Path, first: int, second: int) -> str:
    return textwrap.dedent(
        f"""\
        #!/bin/bash
        printf '%s\\n' "$*" >> "{log}"
        count="$(wc -l < "{log}")"
        if [ "$count" -eq 1 ]; then
          exit {first}
        fi
        exit {second}
        """
    )


class PlaywrightInstallTest(unittest.TestCase):
    def _run(self, first: int, second: int) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / "calls.txt"
            bindir = root / "bin"
            bindir.mkdir()
            npx = bindir / "npx"
            npx.write_text(_npx(log, first, second), encoding="utf-8")
            npx.chmod(npx.stat().st_mode | stat.S_IEXEC)
            completed = subprocess.run(
                ["bash", str(SCRIPT)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                env={
                    **os.environ,
                    "PATH": f"{bindir}:{os.environ.get('PATH', '')}",
                    "PLAYWRIGHT_BROWSERS": "chromium",
                    "PLAYWRIGHT_DIRECTORY": "",
                },
            )
            completed.calls = log.read_text(encoding="utf-8") if log.exists() else ""  # type: ignore[attr-defined]
            return completed

    def test_a_successful_install_does_not_retry(self) -> None:
        completed = self._run(0, 1)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.calls.count("\n"), 1)  # type: ignore[attr-defined]
        self.assertIn("--with-deps", completed.calls)  # type: ignore[attr-defined]

    def test_apt_failure_falls_back_to_the_browser_alone(self) -> None:
        completed = self._run(1, 0)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("continuing with the browser only", completed.stdout + completed.stderr)
        calls = completed.calls.splitlines()  # type: ignore[attr-defined]
        self.assertEqual(len(calls), 2)
        self.assertIn("--with-deps", calls[0])
        self.assertNotIn("--with-deps", calls[1])

    def test_both_attempts_failing_fails_the_action(self) -> None:
        completed = self._run(1, 1)
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(completed.calls.count("\n"), 2)  # type: ignore[attr-defined]

    def test_both_attempts_are_bounded(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertEqual(text.count("timeout --kill-after=20s 180"), 1)
        self.assertIn("run_install --with-deps", text)
        self.assertIn("run_install\n", text)


if __name__ == "__main__":
    unittest.main()

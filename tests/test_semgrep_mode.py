"""ci mode calls semgrep ci, and a command error is not an empty SARIF."""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "semgrep" / "scan.sh"


class SemgrepModeTest(unittest.TestCase):
    def _run(self, mode: str, status: int, write_sarif: bool) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bindir = root / "bin"
            bindir.mkdir()
            log = root / "argv.txt"
            semgrep = bindir / "semgrep"
            semgrep.write_text(
                textwrap.dedent(
                    f"""\
                    #!/bin/sh
                    printf '%s\\n' "$*" > "{log}"
                    output=""
                    for arg in "$@"; do
                      case "$arg" in
                        --output=*) output="${{arg#--output=}}" ;;
                        --sarif-output=*) output="${{arg#--sarif-output=}}" ;;
                      esac
                    done
                    if [ "{int(write_sarif)}" -eq 1 ] && [ -n "$output" ]; then
                      printf '%s\\n' '{{"version":"2.1.0","runs":[{{"results":[{{"message":"hit"}}]}}]}}' > "$output"
                    fi
                    exit {status}
                    """
                ),
                encoding="utf-8",
            )
            semgrep.chmod(semgrep.stat().st_mode | stat.S_IEXEC)
            completed = subprocess.run(
                ["sh", str(SCRIPT)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                env={
                    "PATH": f"{bindir}:{os.environ.get('PATH', '')}",
                    "SEMGREP_MODE": mode,
                    "SEMGREP_RULES": "p/python p/secrets",
                    "SEMGREP_EXCLUDE_RULES": "",
                    "SEMGREP_SOURCE": "fixtures",
                    "SEMGREP_OUTPUT": "semgrep-results.sarif",
                    "GITHUB_ACTION_PATH": str(ROOT / "semgrep"),
                },
            )
            completed.argv = log.read_text(encoding="utf-8") if log.exists() else ""  # type: ignore[attr-defined]
            completed.sarif = (root / "semgrep-results.sarif").read_text(encoding="utf-8") if (root / "semgrep-results.sarif").is_file() else ""  # type: ignore[attr-defined]
            return completed

    def test_ci_mode_does_not_pass_scan_flags(self) -> None:
        completed = self._run("ci", 0, True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("ci --sarif --output=semgrep-results.sarif", completed.argv)  # type: ignore[attr-defined]
        self.assertNotIn("--config", completed.argv)  # type: ignore[attr-defined]
        self.assertNotIn("fixtures", completed.argv)  # type: ignore[attr-defined]

    def test_scan_mode_passes_config_and_the_directory(self) -> None:
        completed = self._run("scan", 0, True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--config p/python --config p/secrets", completed.argv)  # type: ignore[attr-defined]
        self.assertTrue(completed.argv.endswith("fixtures\n") or completed.argv.rstrip().endswith("fixtures"))  # type: ignore[attr-defined]

    def test_a_command_error_is_not_an_empty_sarif(self) -> None:
        completed = self._run("ci", 2, False)
        self.assertEqual(completed.returncode, 2, completed.stderr)
        self.assertEqual(completed.sarif, "")  # type: ignore[attr-defined]
        self.assertIn("exited 2", completed.stderr)


if __name__ == "__main__":
    unittest.main()

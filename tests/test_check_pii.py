"""Normalization rules for the hashed personal-data check."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_pii.py"
_SPEC = importlib.util.spec_from_file_location("check_pii", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
check_pii = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_pii)


class CheckPiiTest(unittest.TestCase):
    def test_trailing_period_does_not_stick_to_name_tokens(self) -> None:
        candidates = check_pii._candidates("Hello Sam Rivera.")
        self.assertIn("sam rivera", candidates)
        self.assertIn("rivera", candidates)
        self.assertNotIn("sam rivera.", candidates)
        self.assertNotIn("rivera.", candidates)

    def test_email_trailing_period_is_stripped_from_tokens(self) -> None:
        candidates = check_pii._candidates("Write user@example.com.")
        self.assertIn("user@example.com", candidates)
        self.assertNotIn("user@example.com.", candidates)

    def test_interior_dots_stay_in_tokens(self) -> None:
        candidates = check_pii._candidates("See note.v2 today.")
        self.assertIn("note.v2", candidates)

    def test_handle_strips_at_sign_and_trailing_period(self) -> None:
        candidates = check_pii._candidates("Follow @Mei.C.")
        self.assertIn("mei.c", candidates)
        self.assertNotIn("@mei.c", candidates)
        self.assertNotIn("mei.c.", candidates)

    def test_scan_suffixes_cover_source_docs_and_styles(self) -> None:
        self.assertTrue(
            {
                ".py",
                ".ts",
                ".tsx",
                ".js",
                ".mjs",
                ".dart",
                ".sql",
                ".md",
                ".mdc",
                ".yml",
                ".yaml",
                ".sh",
                ".html",
                ".css",
            }
            <= check_pii.SCAN_SUFFIXES
        )
        # site.json in lx-software holds a published owner name. Adding .json
        # here would start failing that tree.
        self.assertNotIn(".json", check_pii.SCAN_SUFFIXES)

    def test_phone_digits_are_candidates_without_separators(self) -> None:
        candidates = check_pii._candidates("Call +852 5111 1111.")
        self.assertIn("85251111111", candidates)

    def test_matching_line_reports_the_line_not_the_value(self) -> None:
        denied = {check_pii._digest("sam rivera")}
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as handle:
            handle.write("Hello there.\nHello Sam Rivera.\n")
            path = Path(handle.name)
        try:
            # The line before a hit is included because consecutive lines are
            # scanned as one window.
            self.assertEqual(check_pii._matching_lines(path, denied), [1, 2])
        finally:
            path.unlink(missing_ok=True)

    def test_scan_reads_root_and_denylist_from_the_environment(self) -> None:
        import os

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "note.md").write_text("Meet fixturepii tokenalpha today.\n", encoding="utf-8")
            denylist = root / "denylist.sha256"
            denylist.write_text(check_pii._digest("fixturepii tokenalpha") + "\n", encoding="utf-8")
            previous_root = os.environ.get("PII_ROOT")
            previous_list = os.environ.get("PII_DENYLIST")
            os.environ["PII_ROOT"] = str(root)
            os.environ["PII_DENYLIST"] = "denylist.sha256"
            try:
                self.assertEqual(check_pii.main(), 1)
                denylist.write_text(check_pii._digest("absent fixture token") + "\n", encoding="utf-8")
                self.assertEqual(check_pii.main(), 0)
            finally:
                if previous_root is None:
                    os.environ.pop("PII_ROOT", None)
                else:
                    os.environ["PII_ROOT"] = previous_root
                if previous_list is None:
                    os.environ.pop("PII_DENYLIST", None)
                else:
                    os.environ["PII_DENYLIST"] = previous_list


    def _with_env(self, root: Path, denylist: str | None, organisation: Path | None):
        import os
        from contextlib import contextmanager

        @contextmanager
        def _context():
            previous_root = os.environ.get("PII_ROOT")
            previous_list = os.environ.get("PII_DENYLIST")
            globals_ = check_pii.main.__globals__
            previous_org = globals_["_organisation_path"]
            os.environ["PII_ROOT"] = str(root)
            if denylist is None:
                os.environ.pop("PII_DENYLIST", None)
            else:
                os.environ["PII_DENYLIST"] = denylist
            if organisation is not None:
                globals_["_organisation_path"] = lambda path=organisation: path
            try:
                yield
            finally:
                if previous_root is None:
                    os.environ.pop("PII_ROOT", None)
                else:
                    os.environ["PII_ROOT"] = previous_root
                if previous_list is None:
                    os.environ.pop("PII_DENYLIST", None)
                else:
                    os.environ["PII_DENYLIST"] = previous_list
                globals_["_organisation_path"] = previous_org

        return _context()

    def test_organisation_list_applies_when_the_caller_has_no_list(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            note = root / "note.md"
            note.write_text("Meet fixturepii tokenalpha today.\n", encoding="utf-8")
            organisation = root / "org.sha256"
            organisation.write_text(check_pii._digest("fixturepii tokenalpha") + "\n", encoding="utf-8")
            with self._with_env(root, None, organisation):
                self.assertEqual(check_pii.main(), 1)
            note.write_text("Nothing personal here.\n", encoding="utf-8")
            with self._with_env(root, None, organisation):
                self.assertEqual(check_pii.main(), 0)

    def test_organisation_list_applies_alongside_the_caller_list(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            note = root / "note.md"
            organisation = root / "org.sha256"
            organisation.write_text(check_pii._digest("org fixture token") + "\n", encoding="utf-8")
            caller = root / "caller.sha256"
            caller.write_text(check_pii._digest("caller fixture token") + "\n", encoding="utf-8")
            note.write_text("See caller fixture token today.\n", encoding="utf-8")
            with self._with_env(root, "caller.sha256", organisation):
                self.assertEqual(check_pii.main(), 1)
            note.write_text("See org fixture token today.\n", encoding="utf-8")
            with self._with_env(root, "caller.sha256", organisation):
                self.assertEqual(check_pii.main(), 1)
            note.write_text("Nothing personal here.\n", encoding="utf-8")
            with self._with_env(root, "caller.sha256", organisation):
                self.assertEqual(check_pii.main(), 0)

    def test_explicit_missing_denylist_fails(self) -> None:
        import io
        from contextlib import redirect_stderr

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "note.md").write_text("Nothing personal here.\n", encoding="utf-8")
            errors = io.StringIO()
            with self._with_env(root, "missing-denylist.sha256", None), redirect_stderr(errors):
                status = check_pii.main()
            self.assertEqual(status, 1)
            self.assertIn("missing denylist:", errors.getvalue())
            self.assertIn("missing-denylist.sha256", errors.getvalue())

    def test_missing_default_caller_list_is_optional(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "note.md").write_text("Nothing personal here.\n", encoding="utf-8")
            with self._with_env(root, "scripts/pii-denylist.sha256", None):
                self.assertEqual(check_pii.main(), 0)

    def test_empty_organisation_file_checks_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "note.md").write_text("Meet fixturepii tokenalpha today.\n", encoding="utf-8")
            organisation = root / "org.sha256"
            organisation.write_text("# no digests\n", encoding="utf-8")
            caller = root / "caller.sha256"
            caller.write_text(check_pii._digest("fixturepii tokenalpha") + "\n", encoding="utf-8")
            with self._with_env(root, "caller.sha256", organisation):
                self.assertEqual(check_pii.main(), 0)


if __name__ == "__main__":
    unittest.main()

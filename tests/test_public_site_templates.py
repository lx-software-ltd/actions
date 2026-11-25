"""Public-site templates keep a skipped release and the smoke URL runnable."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates" / "workflows"
ORIGIN = "${{ steps.resolve_public_site_config.outputs.staging_site_origin }}"


class PublicSiteTemplateTest(unittest.TestCase):
    def test_promote_checks_out_before_the_summary(self) -> None:
        text = (TEMPLATES / "promote-public-www.yml").read_text(encoding="utf-8")
        promote = text.split("\n  promote:\n", 1)[1]
        following = promote.split("- name: Checkout repository\n", 1)[1]
        self.assertFalse(following.splitlines()[0].strip().startswith("if:"))

    def test_smoke_url_is_the_resolve_step_output(self) -> None:
        for name in (
            "deploy-public-www-staging.yml",
            "smoke-public-www-staging.yml",
        ):
            text = (TEMPLATES / name).read_text(encoding="utf-8")
            self.assertIn(f"SMOKE_BASE_URL: {ORIGIN}", text)
            self.assertNotIn("vars.STAGING_SITE_ORIGIN ||", text)
            after = text.split(f"SMOKE_BASE_URL: {ORIGIN}\n", 1)[1]
            sample = after.split("# template:set\n", 1)[1].split("# template:end\n", 1)[0]
            self.assertIn("EXAMPLE_ENV:", sample)
            self.assertNotIn("SMOKE_", sample)

        build = (TEMPLATES / "deploy-public-www-staging.yml").read_text(encoding="utf-8")
        build = build.split("- name: Build public website\n", 1)[1]
        sample = build.split("# template:set\n", 1)[1].split("# template:end\n", 1)[0]
        self.assertIn("EXAMPLE_ENV:", sample)
        self.assertNotIn("NEXT_PUBLIC_", sample)

"""Shared Android jobs wait out Maven Central HTTP 429."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRADLE_OPTS = (
    "GRADLE_OPTS: -Dorg.gradle.internal.repository.max.tentatives=5 "
    "-Dorg.gradle.internal.repository.initial.backoff=5000"
)


class AndroidGradleRetryTest(unittest.TestCase):
    def test_debug_and_release_jobs_retry_maven_central(self) -> None:
        for relative in (
            "templates/workflows/test.yml",
            "templates/workflows/deploy-mobile.yml",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(GRADLE_OPTS, text, relative)

"""Pair B shared steps: export options, App Store key, keystore, Play check."""

from __future__ import annotations

import json
import os
import plistlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ios-export-options"))
sys.path.insert(0, str(ROOT / "appstore-api-key"))

import load_api_key  # noqa: E402
import write_export_options  # noqa: E402


class ExportOptionsTest(unittest.TestCase):
    def test_an_empty_profile_stays_automatic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_export_options.write_plist(Path(tmp), "TEAM", "com.example", "")
            data = plistlib.loads(path.read_bytes())
        self.assertEqual(data["signingStyle"], "automatic")
        self.assertNotIn("provisioningProfiles", data)
        self.assertEqual(data["method"], "app-store")

    def test_a_profile_selects_manual_signing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = write_export_options.write_plist(Path(tmp), "TEAM", "com.example", "App Store")
            data = plistlib.loads(path.read_bytes())
        self.assertEqual(data["provisioningProfiles"], {"com.example": "App Store"})

    def test_a_missing_team_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {"WORKING_DIRECTORY": tmp, "APPLE_TEAM_ID": "", "IOS_BUNDLE_ID": "com.example"}
            with mock.patch.dict(os.environ, env, clear=False):
                self.assertEqual(write_export_options.main(), 1)


class AppStoreKeyTest(unittest.TestCase):
    def test_json_wins_and_is_written_as_a_multiline_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "env"
            payload = json.dumps(
                {"issuer_id": "iss", "key_id": "key", "private_key": "line1\nline2"}
            )
            result = load_api_key.load(str(env_path), payload, "other", "", "")
            text = env_path.read_text(encoding="utf-8")
        self.assertEqual(result, "loaded")
        self.assertIn("APPSTORE_ISSUER_ID=iss\n", text)
        self.assertIn("APPSTORE_API_PRIVATE_KEY<<EOF\nline1\nline2\nEOF\n", text)
        self.assertNotIn("other", text)

    def test_every_empty_value_skips(self) -> None:
        self.assertEqual(load_api_key.load("/tmp/unused", "", "", "", ""), "skip")

    def test_incomplete_json_fails(self) -> None:
        with self.assertRaises(SystemExit):
            load_api_key.load("/tmp/unused", "{}", "", "", "")


class ShellStepTest(unittest.TestCase):
    def test_keystore_skip_and_decode(self) -> None:
        script = ROOT / "android-signing" / "install_keystore.sh"
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "WORKING_DIRECTORY": tmp,
                "ANDROID_KEYSTORE_BASE64": "",
                "ANDROID_KEYSTORE_PASSWORD": "",
                "ANDROID_KEY_PASSWORD": "",
                "ANDROID_KEY_ALIAS": "",
                "PATH": os.environ["PATH"],
            }
            skipped = subprocess.run(["sh", str(script)], check=False, env=env, capture_output=True, text=True)
            self.assertEqual(skipped.returncode, 0)
            self.assertIn("Skipping Android signing", skipped.stdout)
            env.update(
                {
                    "ANDROID_KEYSTORE_BASE64": "aGVsbG8=",
                    "ANDROID_KEYSTORE_PASSWORD": "pw",
                    "ANDROID_KEY_PASSWORD": "key",
                    "ANDROID_KEY_ALIAS": "alias",
                }
            )
            written = subprocess.run(["sh", str(script)], check=False, env=env, capture_output=True, text=True)
            self.assertEqual(written.returncode, 0)
            self.assertEqual((Path(tmp) / "android" / "app" / "keystore.p12").read_bytes(), b"hello")

    def test_play_check_requires_every_secret(self) -> None:
        script = ROOT / "play-prerequisites" / "check_play.sh"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out"
            env = {
                "GITHUB_OUTPUT": str(output),
                "GOOGLE_PLAY_SERVICE_ACCOUNT": "",
                "ANDROID_RELEASE_TRACK": "",
                "ANDROID_KEYSTORE_BASE64": "",
                "ANDROID_KEYSTORE_PASSWORD": "",
                "ANDROID_KEY_PASSWORD": "",
                "ANDROID_KEY_ALIAS": "",
                "PATH": os.environ["PATH"],
            }
            skipped = subprocess.run(["sh", str(script)], check=False, env=env, capture_output=True, text=True)
            self.assertEqual(skipped.returncode, 0)
            self.assertIn("should_upload=false", output.read_text(encoding="utf-8"))
            output.write_text("", encoding="utf-8")
            env.update(
                {
                    "GOOGLE_PLAY_SERVICE_ACCOUNT": "{}",
                    "ANDROID_RELEASE_TRACK": "internal",
                    "ANDROID_KEYSTORE_BASE64": "aGVsbG8=",
                    "ANDROID_KEYSTORE_PASSWORD": "pw",
                    "ANDROID_KEY_PASSWORD": "key",
                    "ANDROID_KEY_ALIAS": "alias",
                }
            )
            ready = subprocess.run(["sh", str(script)], check=False, env=env, capture_output=True, text=True)
            self.assertEqual(ready.returncode, 0)
            self.assertEqual(output.read_text(encoding="utf-8").strip(), "should_upload=true")

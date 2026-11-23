"""Load an App Store Connect API key into GITHUB_ENV.

A JSON payload wins. Otherwise the three separate values are used.
When every value is empty the step skips, which is what both pair B
workflows do. A partial key fails.
"""

from __future__ import annotations

import json
import os
import sys


def load(env_path: str, payload: str, issuer_id: str, key_id: str, private_key: str) -> str:
    if not payload and not (issuer_id and key_id and private_key):
        print("Skipping App Store Connect API key setup (missing secrets)")
        return "skip"
    if payload:
        data = json.loads(payload)
        issuer_id = str(data.get("issuer_id") or "")
        key_id = str(data.get("key_id") or "")
        private_key = str(data.get("private_key") or "")
    if not issuer_id or not key_id or not private_key:
        raise SystemExit("Missing App Store Connect API key inputs")
    with open(env_path, "a", encoding="utf-8") as handle:
        # The following step reads these names from the environment.
        # Both deploy-ios workflows already pass the key this way.
        handle.write(f"APPSTORE_ISSUER_ID={issuer_id}\n")  # codeql[py/clear-text-storage-of-sensitive-data]
        handle.write(f"APPSTORE_API_KEY_ID={key_id}\n")  # codeql[py/clear-text-storage-of-sensitive-data]
        handle.write("APPSTORE_API_PRIVATE_KEY<<EOF\n")
        handle.write(private_key.strip() + "\n")  # codeql[py/clear-text-storage-of-sensitive-data]
        handle.write("EOF\n")
    return "loaded"


def main() -> int:
    try:
        load(
            os.environ["GITHUB_ENV"],
            os.environ.get("APPSTORE_API_KEY_JSON", ""),
            os.environ.get("APPSTORE_ISSUER_ID", ""),
            os.environ.get("APPSTORE_API_KEY_ID", ""),
            os.environ.get("APPSTORE_API_PRIVATE_KEY", ""),
        )
    except (SystemExit, json.JSONDecodeError, OSError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

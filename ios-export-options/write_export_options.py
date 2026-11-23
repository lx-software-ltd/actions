"""Write ios/ExportOptions.plist for an App Store export.

The caller passes the team, bundle id, and optional profile. A profile
selects manual signing. An empty profile stays automatic, which is what
both pair B workflows do.
"""

from __future__ import annotations

import os
import plistlib
import sys
from pathlib import Path


def write_plist(working_directory: Path, team_id: str, bundle_id: str, profile_name: str) -> Path:
    if not team_id or not bundle_id:
        raise SystemExit("APPLE_TEAM_ID and IOS_BUNDLE_ID are required")
    data: dict[str, object] = {
        "method": "app-store",
        "teamID": team_id,
        "compileBitcode": False,
        "stripSwiftSymbols": True,
        "uploadSymbols": True,
        "uploadBitcode": False,
        "thinning": "<none>",
        "signingCertificate": "Apple Distribution",
    }
    if profile_name:
        data["signingStyle"] = "manual"
        data["provisioningProfiles"] = {bundle_id: profile_name}
    else:
        data["signingStyle"] = "automatic"
    output = working_directory / "ios" / "ExportOptions.plist"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(plistlib.dumps(data))
    return output


def main() -> int:
    try:
        write_plist(
            Path(os.environ.get("WORKING_DIRECTORY", "")),
            os.environ.get("APPLE_TEAM_ID", ""),
            os.environ.get("IOS_BUNDLE_ID", ""),
            os.environ.get("IOS_PROVISIONING_PROFILE", "").strip(),
        )
    except SystemExit as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

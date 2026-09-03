#!/usr/bin/env python3
"""Verify React dashboard scaffold and optional production build."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"

REQUIRED = [
    DASHBOARD / "package.json",
    DASHBOARD / "vite.config.ts",
    DASHBOARD / "src" / "App.tsx",
    DASHBOARD / "src" / "main.tsx",
    DASHBOARD / "src" / "api" / "client.ts",
    DASHBOARD / "src" / "pages" / "OverviewPage.tsx",
    DASHBOARD / "src" / "pages" / "ReviewsPage.tsx",
    DASHBOARD / "src" / "pages" / "PrivacyPage.tsx",
    DASHBOARD / "src" / "pages" / "AuditPage.tsx",
    DASHBOARD / "src" / "components" / "Layout.tsx",
]


def main() -> int:
    missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.exists()]
    if missing:
        print("Missing dashboard files:", ", ".join(missing), file=sys.stderr)
        return 1

    npm = shutil.which("npm")
    if not npm:
        print("npm not found; skipping build (scaffold check passed)")
        return 0

    node_modules = DASHBOARD / "node_modules"
    if not node_modules.exists():
        install = subprocess.run([npm, "install"], cwd=DASHBOARD, check=False)
        if install.returncode != 0:
            return install.returncode

    build = subprocess.run([npm, "run", "build"], cwd=DASHBOARD, check=False)
    if build.returncode != 0:
        return build.returncode

    dist = DASHBOARD / "dist" / "index.html"
    if not dist.exists():
        print("Build succeeded but dist/index.html missing", file=sys.stderr)
        return 1

    print("Dashboard verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

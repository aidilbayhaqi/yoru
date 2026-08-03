from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def json_version(path: Path) -> str:
    return str(json.loads(path.read_text(encoding="utf-8"))["version"])


def pyproject_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise ValueError(f"version not found in {path}")
    return match.group(1)


def python_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise ValueError(f"__version__ not found in {path}")
    return match.group(1)


def compose_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"APP_VERSION:\s*\$\{APP_VERSION:-([^}]+)\}", text)
    if not match:
        raise ValueError(f"APP_VERSION default not found in {path}")
    return match.group(1)


def main() -> int:
    release_path = ROOT / ".yoru-release.json"
    release = json.loads(release_path.read_text(encoding="utf-8-sig"))
    expected = str(release["version"])
    checks = {
        "root package": json_version(ROOT / "package.json"),
        "storefront package": json_version(ROOT / "apps/storefront/package.json"),
        "console package": json_version(ROOT / "apps/console/package.json"),
        "API package": pyproject_version(ROOT / "services/api/pyproject.toml"),
        "API runtime": python_version(
            ROOT / "services/api/src/yoru_api/__init__.py"
        ),
        "worker package": pyproject_version(ROOT / "services/worker/pyproject.toml"),
        "Docker Compose": compose_version(ROOT / "docker-compose.yml"),
    }

    failures = {name: value for name, value in checks.items() if value != expected}
    print(
        f"Yoru release {expected} · {release.get('release')} · "
        f"Alembic {release.get('alembic_head')}"
    )
    for name, value in checks.items():
        marker = "OK" if value == expected else "MISMATCH"
        print(f"[{marker}] {name}: {value}")

    if failures:
        print("Release consistency check failed.", file=sys.stderr)
        return 1
    print("Release consistency check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

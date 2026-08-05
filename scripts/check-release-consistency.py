from __future__ import annotations

import ast
import json
import re
import sys
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RELEASE_TRUTH_MARKER = "YORU_PRIORITY2_RELEASE_TRUTH_V1"
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


class ReleaseConsistencyError(RuntimeError):
    """Raised when a release source cannot be parsed safely."""


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ReleaseConsistencyError(f"expected JSON object in {path}")
    return value


def json_version(path: Path) -> str:
    value = read_json(path).get("version")
    if not isinstance(value, str) or not value:
        raise ReleaseConsistencyError(f"version not found in {path}")
    return value


def pyproject_version(path: Path) -> str:
    value = tomllib.loads(path.read_text(encoding="utf-8")).get("project", {}).get("version")
    if not isinstance(value, str) or not value:
        raise ReleaseConsistencyError(f"project.version not found in {path}")
    return value


def python_version(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        target_name: str | None = None
        value_node: ast.expr | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                target_name = target.id
                value_node = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
            value_node = node.value

        if target_name == "__version__" and value_node is not None:
            value = ast.literal_eval(value_node)
            if isinstance(value, str) and value:
                return value
    raise ReleaseConsistencyError(f"__version__ not found in {path}")


def compose_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"APP_VERSION:\s*\$\{APP_VERSION:-([^}]+)\}", text)
    if not match:
        raise ReleaseConsistencyError(f"APP_VERSION default not found in {path}")
    return match.group(1).strip()


def _assignment_literal(tree: ast.Module, name: str, path: Path) -> object:
    for node in tree.body:
        value_node: ast.expr | None = None
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                value_node = node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                value_node = node.value

        if value_node is not None:
            try:
                return ast.literal_eval(value_node)
            except (ValueError, TypeError) as exc:
                raise ReleaseConsistencyError(
                    f"{name} must be a literal in {path}"
                ) from exc
    raise ReleaseConsistencyError(f"{name} not found in {path}")


def _down_revisions(value: object, path: Path) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (tuple, list)) and all(isinstance(item, str) for item in value):
        return tuple(value)
    raise ReleaseConsistencyError(f"unsupported down_revision in {path}: {value!r}")


def alembic_heads(versions_dir: Path) -> tuple[str, ...]:
    revision_to_down: dict[str, tuple[str, ...]] = {}
    revision_to_path: dict[str, Path] = {}

    migration_paths = sorted(path for path in versions_dir.glob("*.py") if path.name != "__init__.py")
    if not migration_paths:
        raise ReleaseConsistencyError(f"no Alembic migrations found in {versions_dir}")

    for path in migration_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        revision = _assignment_literal(tree, "revision", path)
        down_revision = _assignment_literal(tree, "down_revision", path)
        if not isinstance(revision, str) or not revision:
            raise ReleaseConsistencyError(f"revision must be a non-empty string in {path}")
        if revision in revision_to_down:
            raise ReleaseConsistencyError(
                f"duplicate Alembic revision {revision!r}: "
                f"{revision_to_path[revision]} and {path}"
            )
        revision_to_down[revision] = _down_revisions(down_revision, path)
        revision_to_path[revision] = path

    referenced = {
        down_revision
        for down_revisions in revision_to_down.values()
        for down_revision in down_revisions
    }
    unknown = sorted(referenced - revision_to_down.keys())
    if unknown:
        raise ReleaseConsistencyError(
            f"Alembic down_revision references unknown revisions: {unknown!r}"
        )

    heads = tuple(sorted(revision_to_down.keys() - referenced))
    if not heads:
        raise ReleaseConsistencyError("Alembic graph has no head")
    return heads


def _render_list(values: Iterable[str]) -> str:
    return ", ".join(values) if values else "<none>"


def main() -> int:
    release_path = ROOT / ".yoru-release.json"
    release = read_json(release_path)
    expected = release.get("version")
    if not isinstance(expected, str) or not SEMVER_PATTERN.fullmatch(expected):
        raise ReleaseConsistencyError(
            f"release version must be valid SemVer in {release_path}: {expected!r}"
        )

    release_name = release.get("release")
    if not isinstance(release_name, str) or not release_name:
        raise ReleaseConsistencyError(f"release name missing in {release_path}")

    expected_alembic_head = release.get("alembic_head")
    if not isinstance(expected_alembic_head, str) or not expected_alembic_head:
        raise ReleaseConsistencyError(f"alembic_head missing in {release_path}")

    checks = {
        "root package": json_version(ROOT / "package.json"),
        "storefront package": json_version(ROOT / "apps/storefront/package.json"),
        "console package": json_version(ROOT / "apps/console/package.json"),
        "API package": pyproject_version(ROOT / "services/api/pyproject.toml"),
        "API runtime": python_version(ROOT / "services/api/src/yoru_api/__init__.py"),
        "worker package": pyproject_version(ROOT / "services/worker/pyproject.toml"),
        "worker runtime": python_version(
            ROOT / "services/worker/src/yoru_worker/__init__.py"
        ),
        "Docker Compose": compose_version(ROOT / "docker-compose.yml"),
    }
    version_failures = {name: value for name, value in checks.items() if value != expected}

    actual_heads = alembic_heads(ROOT / "services/api/alembic/versions")
    alembic_ok = actual_heads == (expected_alembic_head,)

    print(f"Yoru release {expected} · {release_name} · Alembic {expected_alembic_head}")
    for name, value in checks.items():
        marker = "OK" if value == expected else "MISMATCH"
        print(f"[{marker}] {name}: {value}")

    alembic_marker = "OK" if alembic_ok else "MISMATCH"
    print(f"[{alembic_marker}] Alembic heads: {_render_list(actual_heads)}")

    if version_failures or not alembic_ok:
        if version_failures:
            print(
                "Version mismatches: "
                + ", ".join(
                    f"{name}={value}" for name, value in sorted(version_failures.items())
                ),
                file=sys.stderr,
            )
        if not alembic_ok:
            print(
                f"Alembic head mismatch: expected {expected_alembic_head}, "
                f"actual {_render_list(actual_heads)}",
                file=sys.stderr,
            )
        print("Release consistency check failed.", file=sys.stderr)
        return 1

    print("Release consistency check passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ReleaseConsistencyError as exc:
        print(f"Release consistency check error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

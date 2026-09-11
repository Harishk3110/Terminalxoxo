"""Report eligible source lines by ownership, without line-count completion gates."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.count_25k_delta import (  # noqa: E402
    EXCLUDED_PARTS,
    EXTENSIONS,
    eligible_lines,
    git,
)

CATEGORIES = (
    "backend_domain",
    "frontend",
    "workers_agents_reporting",
    "migrations",
    "unit_tests",
    "integration_tests",
    "e2e_tests",
)


def category_for(path: str) -> str | None:
    parts = PurePosixPath(path.lower()).parts
    if not parts or PurePosixPath(parts[-1]).suffix not in EXTENSIONS:
        return None
    excluded = EXCLUDED_PARTS - {"reports"}
    if any(p in excluded or p.startswith((".next", ".venv")) for p in parts):
        return None
    if parts[0] in {"reports", "outputs"} or "public" in parts:
        return None
    name = parts[-1]
    if name.endswith((".d.ts", ".min.js", ".min.css")) or "generated" in name:
        return None
    if "tests" in parts or name.startswith("test_") or ".test." in name or ".spec." in name:
        if "e2e" in parts or "visual" in parts:
            return "e2e_tests"
        if {"sprint", "integration", "contract", "security"}.intersection(parts) or parts[:2] == (
            "services",
            "api",
        ):
            return "integration_tests"
        return "unit_tests"
    if parts[0] == "migrations":
        return "migrations"
    if parts[0] == "apps" or (parts[0] == "packages" and PurePosixPath(name).suffix != ".py"):
        return "frontend"
    if parts[:3] == ("services", "api", "app") or parts[0] == "packages":
        return "backend_domain"
    if parts[0] in {"services", "scripts", "infrastructure", "monitoring"}:
        return "workers_agents_reporting"
    return None


def inventory(root: Path) -> dict[str, object]:
    root = root.resolve()
    listing = git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    assert isinstance(listing, str)
    totals = {c: {"files": 0, "physical_lines": 0, "eligible_lines": 0} for c in CATEGORIES}
    files = []
    for relative in sorted(set(listing.split("\0")) - {""}):
        category = category_for(relative)
        target = root / relative
        if category is None or target.is_symlink() or not target.is_file():
            continue
        if not target.resolve().is_relative_to(root):
            raise ValueError("Source path escapes repository")
        raw = target.read_bytes()
        if b"\0" in raw:
            continue
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            continue
        count = len(eligible_lines(relative, content))
        if not count:
            continue
        group = totals[category]
        group["files"] += 1
        group["physical_lines"] += len(content.splitlines())
        group["eligible_lines"] += count
        files.append({"path": relative, "category": category, "eligible_lines": count})
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "commit": str(git(root, "rev-parse", "HEAD")).strip(),
        "dirty": bool(str(git(root, "status", "--porcelain")).strip()),
        "categories": totals,
        "eligible_total": sum(group["eligible_lines"] for group in totals.values()),
        "methodology": "Nonblank non-comment code, excluding Python docstrings, generated markers and artifacts. Mixed sprint suites conservatively classified as integration; not a functional test count or quality certification.",
        "files": files,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = inventory(args.root)
    if not args.json:
        result.pop("files")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

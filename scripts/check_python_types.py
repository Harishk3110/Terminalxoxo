"""Strictly check each Python distribution without conflating its package namespace."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRST_PARTY_ROOTS = {
    "services",
    "packages",
    "scripts",
    "tests",
    "infrastructure",
    "migrations",
    "typings",
}
DISTRIBUTIONS = (
    "services/api/app",
    "services/api/tests",
    "services/local-agent",
    "services/broker-agent",
    "services/worker-data",
    "services/worker-quant",
    "services/report-engine",
    "tests/sprint",
)


def inventory(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    files = {Path(os.fsdecode(name)) for name in result.stdout.split(b"\0") if name}
    return sorted(
        path
        for path in files
        if path.parts[0] in FIRST_PARTY_ROOTS
        and path.suffix in {".py", ".pyi"}
        and (root / path).is_file()
    )


def distribution(path: Path) -> str:
    for prefix in DISTRIBUTIONS:
        if path.is_relative_to(prefix):
            return prefix
    return "repository-tools"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "logs/python-types")
    parser.add_argument("--inventory-only", action="store_true")
    args = parser.parse_args()
    files = inventory(ROOT)
    if not files:
        raise RuntimeError("No first-party Python files found; refusing an empty type gate")
    groups: dict[str, list[Path]] = defaultdict(list)
    for path in files:
        groups[distribution(path)].append(path)
    output: Path = args.output
    output.mkdir(parents=True, exist_ok=True)
    receipts: list[dict[str, object]] = []
    failed = False
    for group, paths in sorted(groups.items()):
        command = [sys.executable, "-m", "mypy", "--strict", *map(str, paths)]
        if group in {"repository-tools", "tests/sprint", "services/api/tests"}:
            command.insert(4, "--explicit-package-bases")
        receipt: dict[str, object] = {
            "distribution": group,
            "files": [path.as_posix() for path in paths],
            "command": command,
            "status": "NOT_RUN",
        }
        if not args.inventory_only:
            # Runtime services have independent app/agent packages. API imports in
            # tests and compatibility launchers resolve to the API distribution.
            env = dict(os.environ)
            env["PYTHONHASHSEED"] = "0"
            env["MYPYPATH"] = os.pathsep.join((str(ROOT / "typings"), str(ROOT / "services/api")))
            print(f"Checking {group}: {len(paths)} files", flush=True)
            result = subprocess.run(
                command,
                cwd=ROOT,
                env=env,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
            log = output / f"{group.replace('/', '-')}.log"
            log.write_bytes(result.stdout)
            receipt.update(
                status="PASS" if result.returncode == 0 else "FAIL",
                exit_code=result.returncode,
                log=str(log.resolve()),
            )
            print(result.stdout.decode("utf-8", errors="replace"), end="", flush=True)
            failed |= result.returncode != 0
        receipts.append(receipt)
    manifest = {
        "observed_at": datetime.now(UTC).isoformat(),
        "source_files": len(files),
        "status": "NOT_RUN" if args.inventory_only else "FAIL" if failed else "PASS",
        "groups": receipts,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())

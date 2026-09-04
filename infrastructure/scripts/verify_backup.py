from __future__ import annotations

from pathlib import Path


def main() -> None:
    backups = sorted(Path("infrastructure/backups").glob("knk-backup-*.json"))
    print(f"backup_count={len(backups)}")


if __name__ == "__main__":
    main()

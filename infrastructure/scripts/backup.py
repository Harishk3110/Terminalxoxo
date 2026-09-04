from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    target = Path("infrastructure/backups") / f"knk-backup-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('{"status":"demo-backup-created","secrets":"redacted"}\n', encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()

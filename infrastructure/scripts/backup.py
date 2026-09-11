import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from infrastructure.scripts.backup_archive import create_backup

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Private local SQLite/object backup. Sensitive; no encryption or cloud transfer."
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--objects", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--acknowledge-unencrypted", action="store_true", required=True)
    args = parser.parse_args()
    print(json.dumps(create_backup(args.database, args.objects, args.destination)))

import argparse
import json
from pathlib import Path

from backup_archive import create_backup

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

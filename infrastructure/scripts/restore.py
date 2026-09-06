import argparse
import json
from pathlib import Path

from backup_archive import restore_backup

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Restore to a NEW isolated directory. Never overwrites the active workspace."
    )
    parser.add_argument("archive", type=Path)
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(restore_backup(args.archive, args.target)))

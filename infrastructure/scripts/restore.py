import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from infrastructure.scripts.backup_archive import restore_backup

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Restore to a NEW isolated directory. Never overwrites the active workspace."
    )
    parser.add_argument("archive", type=Path)
    parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(restore_backup(args.archive, args.target)))

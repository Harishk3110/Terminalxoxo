import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from infrastructure.scripts.backup_archive import verify_backup

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    result = verify_backup(args.archive)
    print(
        json.dumps(
            {
                "state": result["state"],
                "sha256": result["archive_hash"],
                "files": len(result["manifest"]["files"]),
                "tables": result["manifest"]["tables"],
            }
        )
    )

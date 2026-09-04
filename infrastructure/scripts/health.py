from __future__ import annotations

import json


def main() -> None:
    print(json.dumps({"api": "configured", "public_web": "configured", "terminal_web": "configured", "environment": "local-demo"}, indent=2))


if __name__ == "__main__":
    main()

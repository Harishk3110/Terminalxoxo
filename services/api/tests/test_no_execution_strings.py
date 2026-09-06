from pathlib import Path
import os


def test_application_source_has_no_forbidden_broker_action_methods():
    root = Path(__file__).resolve().parents[3]
    forbidden = [
        "place" + "Order",
        "cancel" + "Order",
        "req" + "Global" + "Cancel",
        "transmit" + "Order",
        "modify" + "Order",
        "submit" + "Order",
        "execute" + "Trade",
        "auto" + "Rebalance",
        "auto" + "Hedge",
        "Buy" + " button",
        "Sell" + " button",
        "Submit" + " order",
        "Transmit" + " order",
        "Cancel" + " broker order",
        "Live" + " execution toggle",
    ]
    scan_roots = [root / "apps", root / "packages", root / "services"]
    skipped_parts = {"node_modules", ".next", ".next-prod", ".next-build", "logs", "dist", "coverage", "__pycache__", "tests"}
    violations: list[str] = []
    for scan_root in scan_roots:
        for directory, dirs, files in os.walk(scan_root):
            dirs[:] = [name for name in dirs if name not in skipped_parts]
            for name in files:
                path = Path(directory) / name
                if path.suffix.lower() not in {".ts", ".tsx", ".py", ".js", ".mjs", ".json", ".md"}:
                    continue
                text = path.read_text(encoding="utf-8", errors="ignore")
                for pattern in forbidden:
                    if pattern in text:
                        violations.append(f"{path.relative_to(root)} contains {pattern}")
    assert not violations

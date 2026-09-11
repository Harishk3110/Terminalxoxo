"""Scan tracked and eligible new text files without printing credential values."""

import ast
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{30,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
)
CREDENTIAL_ASSIGNMENT = re.compile(
    r"^\s*([A-Z][A-Z0-9_]*(?:API_KEY|SECRET|TOKEN|PASSWORD|PRIVATE_KEY|ACCOUNT_ID)[A-Z0-9_]*)\s*=\s*(.*?)\s*$"
)
PROHIBITED = re.compile(
    r"(?:^|/)(?:node_modules|\.next[^/]*|\.vercel|coverage|test-results|logs|__pycache__)(?:/|$)|\.(?:db|sqlite3?|pyc|tsbuildinfo)$|(?:^|/)\.env(?:\..+)?$"
)
# Exact public fixtures only; never exempt a test file or an entire credential key.
PUBLIC_TEST_FIXTURES = {
    ("tests/sprint/test_provider_connections.py", "MARKET_DATA_API_KEY"): "server-secret",
}


def public_fixture(name: str, key: str, expression: str) -> bool:
    expected = PUBLIC_TEST_FIXTURES.get((name, key))
    if expected is None:
        return False
    try:
        value = ast.literal_eval(expression.removesuffix(","))
    except (SyntaxError, ValueError):
        return False
    return isinstance(value, str) and value == expected


def main() -> int:
    files = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
        )
        .decode()
        .split("\0")
    )
    findings = []
    scanned = 0
    for name in sorted(set(files) - {""}):
        path = ROOT / name
        if not path.is_file():
            continue
        if PROHIBITED.search(name) and path.name != ".env.example":
            findings.append(f"{name}: prohibited tracked artifact")
            continue
        content = path.read_bytes()
        if b"\0" in content:
            continue
        scanned += 1
        for line_no, line in enumerate(content.decode("utf-8", errors="replace").splitlines(), 1):
            if TOKEN.search(line):
                findings.append(f"{name}:{line_no}: possible credential or private key")
            assignment = CREDENTIAL_ASSIGNMENT.match(line)
            if (
                assignment
                and assignment[2].strip("\"'")
                and not public_fixture(name, assignment[1], assignment[2])
            ):
                findings.append(
                    f"{name}:{line_no}: nonempty credential assignment ({assignment[1]})"
                )
    for finding in findings:
        print(finding)
    print(f"Scanned {scanned} text files; {len(findings)} findings; values redacted")
    return int(bool(findings))


if __name__ == "__main__":
    raise SystemExit(main())

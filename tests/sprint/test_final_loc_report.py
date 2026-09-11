from pathlib import Path

import pytest

from scripts.loc_report import category_for, inventory
from tests.sprint.test_loc_counter import command


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("services/api/app/portfolio.py", "backend_domain"),
        ("packages/reports/render.py", "backend_domain"),
        ("services/report-engine/app/main.py", "workers_agents_reporting"),
        ("migrations/versions/0006.py", "migrations"),
        ("tests/unit/test_nav.py", "unit_tests"),
        ("tests/sprint/test_nav.py", "integration_tests"),
        ("tests/e2e/nav.spec.ts", "e2e_tests"),
        ("apps/terminal-web/tests/nav.test.ts", "unit_tests"),
        ("apps/terminal-web/app/page.tsx", "frontend"),
        ("reports/report.py", None),
        ("apps/terminal-web/.next-final/page.js", None),
        ("node_modules/lib/index.js", None),
        ("docs/sample.py", None),
        ("tests/fixtures/large.py", None),
        ("apps/terminal-web/client.generated.ts", None),
    ],
)
def test_final_categories(path: str, expected: str | None) -> None:
    assert category_for(path) == expected


def test_final_inventory_excludes_padding_and_marks_dirty(tmp_path: Path) -> None:
    command(tmp_path, "init")
    command(tmp_path, "config", "user.name", "LOC test")
    command(tmp_path, "config", "user.email", "loc@example.invalid")
    command(tmp_path, "commit", "--allow-empty", "-m", "Empty baseline")
    app = tmp_path / "services" / "api" / "app"
    app.mkdir(parents=True)
    (app / "nav.py").write_text('"""Documentation."""\n# comment\n\nnav = 100000\n')
    (app / "auto.py").write_text("# @generated\npadding = 999\n")
    result = inventory(tmp_path)
    assert result["eligible_total"] == 1
    assert result["dirty"] is True
    assert len(result["files"]) == 1

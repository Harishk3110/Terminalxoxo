import subprocess
from pathlib import Path

import pytest

from scripts.count_25k_delta import (
    GATES,
    SourceFile,
    baseline_sources,
    category_for,
    delta,
    eligible_lines,
    main,
    make_source,
    python_docstring_lines,
    totals,
    working_sources,
)


def source(path: str, text: str) -> SourceFile:
    result = make_source(path, text.encode())
    assert result is not None
    return result


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("services/api/app/ledger.py", "backend"),
        ("packages/performance/returns.py", "backend"),
        ("migrations/versions/0004_ledger.sql", "backend"),
        ("apps/terminal-web/components/positions.tsx", "frontend"),
        ("apps/terminal-web/app/portfolio.css", "frontend"),
        ("packages/search/src/index.ts", "frontend"),
        ("services/local-agent/watch.py", "workers_agents_reports_infrastructure"),
        ("services/api/scripts/seed.py", "workers_agents_reports_infrastructure"),
        ("scripts/check.ps1", "workers_agents_reports_infrastructure"),
        ("infrastructure/scripts/backup.sh", "workers_agents_reports_infrastructure"),
        ("services/api/tests/test_cash.py", "tests"),
        ("apps/terminal-web/tests/nav.test.tsx", "tests"),
        ("packages/search/src/search.spec.ts", "tests"),
        ("tests/e2e/terminal.spec.ts", "tests"),
    ],
)
def test_category_ownership(path: str, expected: str) -> None:
    assert category_for(path) == expected


@pytest.mark.parametrize(
    "path",
    [
        "docs/example.py",
        "services/api/app/data/fixture.py",
        "tests/fixtures/prices.py",
        "apps/terminal-web/.next/server/index.js",
        "services/api/__pycache__/file.py",
        "vendor/library/source.py",
        "apps/terminal-web/public/generated.js",
        "packages/api-client/generated/index.ts",
        "apps/terminal-web/lib/schema.generated.ts",
        "services/api/logs/replay.py",
        "node_modules/package/index.js",
        ".venv-sprint/lib/site-packages/a.py",
        "tests/screenshots/draw.ts",
        "reports/output.py",
        "dist/main.js",
        "apps/terminal-web/app/bundle.min.js",
        "apps/terminal-web/next-env.d.ts",
        "README.md",
        "pnpm-lock.yaml",
        "data/seed.csv",
        "knk_terminal.db",
        "unknown_root/file.py",
    ],
)
def test_nonqualifying_artifacts_never_count(path: str) -> None:
    assert category_for(path) is None


def test_docstrings_comments_and_structural_lines_are_excluded() -> None:
    text = "\n".join(
        [
            '"""Module purpose.',
            "More documentation.",
            '"""',
            "",
            "# Comment",
            "def cash() -> int:",
            '    """Function description."""',
            "    return 17",
            "",
        ]
    )
    assert python_docstring_lines(text) == {1, 2, 3, 7}
    assert eligible_lines("services/api/app/cash.py", text) == (
        "def cash() -> int:",
        "return 17",
    )


def test_nested_class_docstrings_are_excluded_without_removing_expressions() -> None:
    text = "\n".join(
        [
            "class Price:",
            '    """A price record."""',
            "    def label(self) -> str:",
            '        """Currency label."""',
            '        return "USD"',
        ]
    )
    assert python_docstring_lines(text) == {2, 4}
    assert len(eligible_lines("services/api/app/price.py", text)) == 3


def test_generated_marker_in_header_excludes_the_entire_module() -> None:
    assert (
        eligible_lines("apps/terminal-web/client.ts", "// @generated\nexport const id = 7;") == ()
    )
    assert eligible_lines("services/api/app/generated.py", "# Automatically generated\nx = 7") == ()


def test_generated_marker_in_runtime_data_is_not_a_header() -> None:
    lines = eligible_lines(
        "services/api/app/content.py", 'message = "@generated is not a header here"'
    )
    assert len(lines) == 1


def test_block_comments_and_urls_are_handled_separately() -> None:
    text = "\n".join(
        [
            "/* A comment",
            "continued */",
            'const url = "https://example.test";',
            "// A second comment",
            "/* one line */ const value = 19;",
            "{",
            "}",
        ]
    )
    assert eligible_lines("apps/terminal-web/view.ts", text) == (
        'const url = "https://example.test";',
        "const value = 19;",
    )


def test_sql_comments_do_not_remove_schema_constraints() -> None:
    text = "-- migration\nCREATE TABLE samples (\n id INT CHECK (id > 0)\n);"
    assert eligible_lines("migrations/0004.sql", text) == (
        "CREATE TABLE samples (",
        "id INT CHECK (id > 0)",
    )


def test_css_colors_are_not_mistaken_for_hash_comments() -> None:
    assert eligible_lines(
        "apps/terminal-web/app/style.css", "#portfolio {\ncolor: #111111;\n}"
    ) == (
        "#portfolio {",
        "color: #111111;",
    )


def test_baseline_and_relocated_content_earn_zero_credit() -> None:
    old = [source("services/api/app/old.py", "def total():\n    return 7\n")]
    current = [source("services/api/app/new.py", "def total():\n    return 7\n")]
    report = delta(old, current)
    assert report["total"] == 0
    assert report["line_gates_passed"] is False


def test_copying_baseline_code_does_not_inflate_the_delta() -> None:
    original = source("services/api/app/old.py", "def total():\n    return 7\n")
    copied = source("services/api/app/copy.py", "def total():\n    return 7\n")
    assert delta([original], [original, copied])["total"] == 0


def test_repeating_new_boilerplate_is_credited_only_once() -> None:
    a = source("services/api/app/a.py", "from decimal import Decimal\nvalue = Decimal('15')")
    b = source("services/api/app/b.py", "from decimal import Decimal\nvalue = Decimal('15')")
    assert delta([], [a, b])["total"] == 2


def test_pure_whitespace_and_comments_cannot_earn_credit() -> None:
    old = source("services/api/app/a.py", "value = 15\nreturn_value = value")
    new = source(
        "services/api/app/a.py", "# Explanation\n\nvalue    =   15\nreturn_value = value\n"
    )
    assert delta([old], [new])["total"] == 0


def test_a_real_behavior_change_is_assigned_to_its_owner() -> None:
    old = source("services/api/app/a.py", "value = 15")
    new = source("services/api/app/a.py", "value = 17\nresult = value * 2")
    report = delta([old], [new])
    assert report["total"] == 2
    assert report["categories"]["backend"]["added"] == 2
    assert report["categories"]["tests"]["added"] == 0


def test_deletions_never_create_negative_or_positive_credit() -> None:
    old = [source("services/api/app/a.py", "value = 15")]
    assert delta(old, [])["total"] == 0


def test_total_does_not_hide_a_failed_category_gate() -> None:
    module = source(
        "services/api/app/a.py", "\n".join(f"value_{index} = {index}" for index in range(25001))
    )
    report = delta([], [module])
    assert report["total"] == 25001
    assert report["categories"]["backend"]["passed"] is True
    assert report["line_gates_passed"] is False
    assert report["files"][0]["over_1200_lines"] is True


def test_all_four_independent_gates_are_required() -> None:
    modules = []
    paths = {
        "backend": "services/api/app/ledger.py",
        "frontend": "apps/terminal-web/view.ts",
        "workers_agents_reports_infrastructure": "scripts/health.py",
        "tests": "tests/test_ledger.py",
    }
    for category, minimum in GATES.items():
        text = "\n".join(f"{category}_{index} = {index}" for index in range(minimum))
        modules.append(source(paths[category], text))
    report = delta([], modules)
    assert report["total"] == 25000
    assert report["line_gates_passed"] is True
    assert report["semantic_review_required"] is True


def test_binary_and_bad_encoding_are_excluded() -> None:
    assert make_source("services/api/app/a.py", b"a\x00b") is None
    assert make_source("services/api/app/a.py", b"\xff\xfe") is None
    assert make_source("README.md", b"example") is None


def test_inventory_preserves_physical_and_eligible_counts() -> None:
    a = source("services/api/app/a.py", "# header\n\nvalue = 3\n")
    result = totals([a])
    assert result["backend"] == {"files": 1, "physical_lines": 3, "eligible_lines": 1}
    assert result["tests"]["files"] == 0


def command(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def test_counter_reads_commit_and_untracked_source_without_staging(tmp_path: Path) -> None:
    command(tmp_path, "init")
    command(tmp_path, "config", "user.name", "LOC test")
    command(tmp_path, "config", "user.email", "loc-test@example.invalid")
    app = tmp_path / "services" / "api" / "app"
    app.mkdir(parents=True)
    (app / "existing.py").write_text("opening = 70000\n", encoding="utf-8")
    command(tmp_path, "add", ".")
    command(tmp_path, "commit", "-m", "Baseline")
    baseline = command(tmp_path, "rev-parse", "HEAD")
    (app / "added.py").write_text("closing = opening + 150\n", encoding="utf-8")
    assert delta(baseline_sources(tmp_path, baseline), working_sources(tmp_path))["total"] == 1
    assert main(["--root", str(tmp_path), "--baseline", baseline, "--check"]) == 1
    assert main(["--root", str(tmp_path), "--baseline", baseline]) == 0
    assert "?? services/api/app/added.py" in command(tmp_path, "status", "--short")


def test_invalid_revision_is_rejected_before_git_object_access(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="2"):
        main(["--root", str(tmp_path), "--baseline", "HEAD~1; dangerous"])

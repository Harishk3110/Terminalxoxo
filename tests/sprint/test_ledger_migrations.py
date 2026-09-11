"""Migration lifecycle tests use temporary databases, never the user's ledger."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from app import models
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[2]
NEW_TABLES = {
    "transaction_revisions",
    "position_lots",
    "position_lot_matches",
    "capital_flows",
    "portfolio_income",
    "portfolio_fees",
    "portfolio_accruals",
    "portfolio_liabilities",
    "auth_totp_states",
}


def configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Config, str]:
    url = "sqlite:///" + (tmp_path / "migration.sqlite").as_posix()
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    return config, url


def test_baseline_revision_does_not_create_future_tables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, url = configuration(tmp_path, monkeypatch)
    command.upgrade(config, "0003_portfolio_operations")
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
        assert {"portfolios", "portfolio_transactions", "portfolio_valuation_runs"} <= tables
        assert not NEW_TABLES & tables
    finally:
        engine.dispose()


def test_fresh_head_schema_matches_orm_column_ownership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, url = configuration(tmp_path, monkeypatch)
    command.upgrade(config, "head")
    engine = create_engine(url)
    try:
        schema = inspect(engine)
        assert NEW_TABLES <= set(schema.get_table_names())
        for name in NEW_TABLES:
            actual = {column["name"] for column in schema.get_columns(name)}
            expected = {column.name for column in models.Base.metadata.tables[name].columns}
            assert actual == expected
        with engine.connect() as connection:
            assert (
                connection.scalar(text("SELECT version_num FROM alembic_version"))
                == ScriptDirectory.from_config(config).get_current_head()
            )
    finally:
        engine.dispose()


def test_upgrade_downgrade_upgrade_preserves_existing_portfolio_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, url = configuration(tmp_path, monkeypatch)
    command.upgrade(config, "0003_portfolio_operations")
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO portfolios (id, name, base_currency, reference_capital, is_default, created_at, updated_at) VALUES ('preserved', 'Existing user book', 'SGD', 70000, 0, '2026-01-01', '2026-01-01')"
                )
            )
        command.upgrade(config, "head")
        command.downgrade(config, "0003_portfolio_operations")
        assert not NEW_TABLES & set(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert (
                connection.scalar(
                    text("SELECT reference_capital FROM portfolios WHERE id='preserved'")
                )
                == 70000
            )
        command.upgrade(config, "head")
        assert NEW_TABLES <= set(inspect(engine).get_table_names())
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT COUNT(*) FROM portfolios")) == 1
    finally:
        engine.dispose()


def test_migration_declares_revision_uniqueness_checks_and_foreign_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, url = configuration(tmp_path, monkeypatch)
    command.upgrade(config, "head")
    engine = create_engine(url)
    try:
        schema = inspect(engine)
        uniques = schema.get_unique_constraints("transaction_revisions")
        assert any(item["column_names"] == ["transaction_id", "version"] for item in uniques)
        checks = {item["name"] for item in schema.get_check_constraints("transaction_revisions")}
        assert checks == {"ck_transaction_revision_version", "ck_transaction_revision_action"}
        references = {
            item["referred_table"] for item in schema.get_foreign_keys("transaction_revisions")
        }
        assert references == {"users", "portfolios", "portfolio_transactions"}
        indexes = {item["name"] for item in schema.get_indexes("position_lot_matches")}
        assert "ix_lot_match_run_instrument" in indexes
    finally:
        engine.dispose()


def test_database_rejects_invalid_revision_state_and_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, url = configuration(tmp_path, monkeypatch)
    command.upgrade(config, "head")
    engine = create_engine(url)
    statement = text(
        "INSERT INTO transaction_revisions (id, portfolio_id, transaction_id, version, action, reason, before, after, created_at, updated_at) VALUES (:id, 'book', 'txn', :version, :action, 'Correction', '{}', '{}', '2026-01-01', '2026-01-01')"
    )
    try:
        for identifier, version, action in (
            ("invalid-version", 1, "AMEND"),
            ("invalid-action", 2, "REPLACE"),
        ):
            with pytest.raises(IntegrityError), engine.begin() as connection:
                connection.execute(
                    statement, {"id": identifier, "version": version, "action": action}
                )
        with engine.begin() as connection:
            connection.execute(statement, {"id": "first", "version": 2, "action": "AMEND"})
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(statement, {"id": "second", "version": 2, "action": "VOID"})
    finally:
        engine.dispose()


def test_subledger_migration_matches_orm_constraints_types_and_references(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sqlalchemy import CheckConstraint

    config, url = configuration(tmp_path, monkeypatch)
    command.upgrade(config, "head")
    engine = create_engine(url)
    try:
        schema = inspect(engine)
        for table in (
            "capital_flows",
            "portfolio_income",
            "portfolio_fees",
            "portfolio_accruals",
            "portfolio_liabilities",
        ):
            definition = models.Base.metadata.tables[table]
            actual_checks = {
                row["name"]: " ".join(row["sqltext"].split())
                for row in schema.get_check_constraints(table)
            }
            expected_checks = {
                constraint.name: " ".join(str(constraint.sqltext).split())
                for constraint in definition.constraints
                if isinstance(constraint, CheckConstraint)
            }
            assert actual_checks == expected_checks
            columns = {row["name"]: row for row in schema.get_columns(table)}
            assert columns["native_amount"]["type"].precision == 38
            assert columns["native_amount"]["type"].scale == 16
            assert columns["native_amount"]["nullable"] is False
            assert columns["base_amount"]["nullable"] is True
            assert columns["payload"]["nullable"] is False
            assert {row["referred_table"] for row in schema.get_foreign_keys(table)} == {
                "portfolios",
                "portfolio_valuation_runs",
                "portfolio_accounts",
                "portfolio_transactions",
                "instruments",
                "portfolio_balance_adjustments",
            }
            assert any(
                row["column_names"] == ["valuation_run_id", "component_key"]
                for row in schema.get_unique_constraints(table)
            )
            assert any(
                row["column_names"] == ["portfolio_id", "effective_date"]
                for row in schema.get_indexes(table)
            )
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "override",
    [
        {"kind": "DIVIDEND"},
        {"native": -1},
        {"capitalized": 20},
        {"kind": "TAX", "capitalized": 1},
        {"fx": 0},
        {"base": None},
        {"transaction": None},
        {"adjustment": "balance"},
        {"settled": "2026-01-01"},
    ],
)
def test_migrated_fee_table_enforces_amount_source_and_valuation_contracts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    override: dict,
) -> None:
    config, url = configuration(tmp_path, monkeypatch)
    command.upgrade(config, "head")
    engine = create_engine(url)
    statement = text(
        "INSERT INTO portfolio_fees (id, portfolio_id, valuation_run_id, component_key, transaction_id, "
        "adjustment_id, kind, effective_date, settlement_date, currency, native_amount, fx_rate, base_amount, "
        "capitalized_native, capitalized_base, payload, created_at, updated_at) "
        "VALUES (:id, 'book', 'run', :id, :transaction, :adjustment, :kind, '2026-01-05', :settled, 'SGD', "
        ":native, :fx, :base, :capitalized, 0, '{}', '2026-01-05', '2026-01-05')"
    )
    params = {
        "id": "valid",
        "transaction": "transaction",
        "adjustment": None,
        "kind": "FEE",
        "settled": "2026-01-06",
        "native": 10,
        "fx": 1,
        "base": 10,
        "capitalized": 0,
    }
    try:
        # Foreign-key enforcement is covered by session tests; isolate each CHECK here.
        with engine.begin() as connection:
            connection.execute(statement, params)
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(statement, {**params, "id": "invalid", **override})
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT COUNT(*) FROM portfolio_fees")) == 1
    finally:
        engine.dispose()

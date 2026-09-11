"""Snapshot-consistent PostgreSQL dump and isolated, non-overwriting restoration."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import TupleRow
from sqlalchemy.engine import make_url

from infrastructure.scripts.managed_backup_contracts import ObjectReference, TableEvidence


@dataclass(frozen=True)
class Postgres:
    url: str = field(repr=False)
    tools_container: str | None = None

    def parameters(self, database: str | None = None) -> dict[str, str]:
        url = make_url(self.url)
        if url.get_backend_name() != "postgresql" or not url.database:
            raise ValueError("A PostgreSQL database URL is required")
        parameters = {
            "host": url.host or "localhost",
            "port": str(url.port or 5432),
            "dbname": database or url.database,
            "user": url.username or "",
            "password": url.password or "",
            "connect_timeout": "10",
        }
        for key, value in url.query.items():
            if key not in {"sslmode", "sslrootcert", "sslcert", "sslkey", "channel_binding"}:
                raise ValueError("Unsupported PostgreSQL connection option")
            if not isinstance(value, str):
                raise ValueError("Duplicate PostgreSQL connection option")
            parameters[key] = value
        return parameters

    def connect(self, database: str | None = None) -> psycopg.Connection[TupleRow]:
        return psycopg.connect(make_conninfo(**self.parameters(database)))

    def run(
        self,
        tool: str,
        arguments: list[str],
        *,
        database: str | None = None,
        source: BinaryIO | None = None,
        target: BinaryIO | None = None,
    ) -> None:
        if tool not in {"pg_dump", "pg_restore"}:
            raise ValueError("Unsupported PostgreSQL tool")
        parameters = self.parameters(database)
        if self.tools_container:
            parameters.update(host="127.0.0.1", port="5432")
        mapping = {"dbname": "PGDATABASE", **{key: "PG" + key.upper() for key in parameters}}
        mapping["dbname"] = "PGDATABASE"
        mapping["channel_binding"] = "PGCHANNELBINDING"
        environment = {mapping[key]: value for key, value in parameters.items()}
        command = [tool, *arguments]
        if self.tools_container:
            command = [
                "docker",
                "exec",
                "-i",
                *sum((["-e", key] for key in environment), []),
                self.tools_container,
                *command,
            ]
        # Passwords travel in the child environment, never command arguments or evidence.
        result = subprocess.run(
            command,
            env={**os.environ, **environment},
            stdin=source or subprocess.DEVNULL,
            stdout=target or subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=1800,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if result.returncode:
            raise RuntimeError(
                f"{tool} failed with exit code {result.returncode}; no restore success recorded"
            )
        if result.stderr:
            raise RuntimeError(
                f"{tool} emitted diagnostics; backup/restore requires a clean tool run"
            )

    def create_isolated_database(self, name: str) -> None:
        if not re.fullmatch(r"knk_restore_[a-f0-9]{32}", name):
            raise ValueError("Restore database must be a generated isolated name")
        if self.parameters()["dbname"] == name:
            raise ValueError("Active database cannot be a restore target")
        with self.connect("postgres") as connection:
            connection.autocommit = True
            # No DROP, IF NOT EXISTS, --clean or reconnect to the source database.
            connection.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0").format(sql.Identifier(name))
            )


def table_snapshot(connection: psycopg.Connection[TupleRow]) -> list[TableEvidence]:
    connection.execute("SET LOCAL TIME ZONE 'UTC'")
    connection.execute("SET LOCAL extra_float_digits = 3")
    names = connection.execute(
        "SELECT n.nspname, c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE c.relkind IN ('r', 'p') AND NOT c.relispartition "
        "AND n.nspname NOT IN ('pg_catalog', 'information_schema') "
        "AND n.nspname NOT LIKE 'pg_toast%' ORDER BY n.nspname, c.relname"
    ).fetchall()
    if not names:
        raise ValueError("Refusing to certify an empty PostgreSQL database")
    evidence = []
    for schema, table in names:
        if not isinstance(schema, str) or not isinstance(table, str):
            raise ValueError("Invalid database table inventory")
        query = sql.SQL(
            "SELECT row_data FROM (SELECT to_jsonb(t)::text AS row_data FROM {}.{} t) "
            'snapshot_rows ORDER BY row_data COLLATE "C"'
        ).format(sql.Identifier(schema), sql.Identifier(table))
        digest = hashlib.sha256()
        count = 0
        with connection.cursor(name="knk_backup_rows") as cursor:
            cursor.execute(query)
            for (row,) in cursor:
                if not isinstance(row, str):
                    raise ValueError("Invalid row serialization")
                digest.update(row.encode("utf-8") + b"\n")
                count += 1
        evidence.append(
            TableEvidence(
                schema_name=schema, table_name=table, rows=count, sha256=digest.hexdigest()
            )
        )
    return evidence


def object_references(connection: psycopg.Connection[TupleRow]) -> list[ObjectReference]:
    rows = connection.execute(
        "SELECT object_key, content_hash, size_bytes FROM raw_objects "
        "UNION ALL SELECT object_key, content_hash, size_bytes FROM uploaded_files "
        "UNION ALL SELECT object_key, content_hash, size_bytes FROM report_jobs "
        "WHERE object_key IS NOT NULL "
        "UNION ALL SELECT schema_json->>'curated_key', schema_json->>'curated_hash', NULL "
        "FROM dataset_versions WHERE schema_json->>'curated_key' IS NOT NULL "
        "UNION ALL SELECT result->'artifact'->>'object_key', "
        "result->'artifact'->>'content_hash', (result->'artifact'->>'size_bytes')::bigint "
        "FROM analysis_runs WHERE result->'artifact'->>'object_key' IS NOT NULL"
    ).fetchall()
    return [ObjectReference(key=key, sha256=digest, bytes=size) for key, digest, size in rows]


def dump_snapshot(
    postgres: Postgres, path: Path
) -> tuple[list[TableEvidence], list[str], list[ObjectReference]]:
    with postgres.connect() as connection:
        connection.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        row = connection.execute("SELECT pg_export_snapshot()").fetchone()
        if row is None or not isinstance(row[0], str):
            raise ValueError("PostgreSQL did not export a snapshot")
        snapshot = row[0]
        tables = table_snapshot(connection)
        references = object_references(connection)
        migrations = connection.execute(
            "SELECT version_num FROM alembic_version ORDER BY version_num"
        ).fetchall()
        versions = [str(row[0]) for row in migrations]
        if not versions:
            raise ValueError("Missing Alembic migration version")
        with path.open("xb") as output:
            os.chmod(path, 0o600)
            postgres.run(
                "pg_dump",
                ["--format=custom", "--no-owner", "--no-acl", "--snapshot=" + snapshot],
                target=output,
            )
        return tables, versions, references


def restore_database(
    postgres: Postgres, dump: Path, database: str, tables: list[TableEvidence]
) -> None:
    postgres.create_isolated_database(database)
    with dump.open("rb") as source:
        postgres.run(
            "pg_restore",
            [
                "--exit-on-error",
                "--single-transaction",
                "--no-owner",
                "--no-acl",
                "--dbname=" + database,
            ],
            database=database,
            source=source,
        )
    with postgres.connect(database) as connection:
        connection.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        if table_snapshot(connection) != tables:
            raise ValueError("Restored business-table contents differ from the source snapshot")

"""Outbound-only data-drop agent. Tokens are stored in the OS credential vault."""

import argparse
import getpass
import hashlib
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import TypedDict
from urllib.parse import quote, urlparse
from uuid import uuid4

import httpx
import keyring
from keyring.backend import KeyringBackend
from keyring.core import load_keyring

VERSION = "1.0.0"
SERVICE = "KnK Capital Data Drop"
FOLDERS = [
    "inbox/koyfin",
    "inbox/prices",
    "inbox/fundamentals",
    "inbox/macro",
    "inbox/portfolio",
    "inbox/positions",
    "inbox/transactions",
    "inbox/options",
    "inbox/custom",
    "processing",
    "review",
    "processed",
    "rejected",
    "quarantine",
    "logs",
]
TERMINAL_STATES = {"IMPORTED", "ARCHIVED", "DUPLICATE", "REJECTED", "QUARANTINED"}
SERVER_STATES = TERMINAL_STATES | {
    "DETECTED",
    "HASHING",
    "UPLOADING",
    "UPLOAD_FAILED",
    "STORED_RAW",
    "PREVIEWING",
    "SCHEMA_DETECTED",
    "MAPPING_REQUIRED",
    "MAPPED",
    "VALIDATING",
    "VALIDATED",
    "VALIDATED_WITH_WARNINGS",
    "VALIDATION_FAILED",
    "AWAITING_APPROVAL",
    "IMPORTING",
    "IMPORT_FAILED",
}


class FileStatus(TypedDict):
    id: str
    hash: str
    state: str


def file_status(value: object) -> FileStatus:
    if not isinstance(value, dict):
        raise ValueError("Invalid file acknowledgement")
    identifier, digest, state = value.get("id"), value.get("hash"), value.get("state")
    if (
        not isinstance(identifier, str)
        or not identifier
        or len(identifier) > 200
        or not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        or not isinstance(state, str)
        or state not in SERVER_STATES
    ):
        raise ValueError("Invalid file acknowledgement")
    return {"id": identifier, "hash": digest, "state": state}


def safe_path(root: Path, value: str | Path) -> Path:
    resolved = Path(value).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("Path escapes configured data-drop root")
    return resolved


def validate_endpoint(url: str, allow_local: bool) -> str:
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError:
        raise ValueError("Invalid API server origin") from None
    if (
        not parsed.hostname
        or port == 0
        or any(character.isspace() for character in url)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("API URL must be a server origin without credentials or path")
    if parsed.scheme != "https" and not (
        allow_local
        and parsed.scheme == "http"
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    ):
        raise ValueError("HTTPS required except explicitly enabled loopback development")
    return url.rstrip("/")


def credential_backend() -> KeyringBackend:
    if sys.platform == "win32":
        backend = load_keyring("keyring.backends.Windows.WinVaultKeyring")
    else:
        backend = keyring.get_keyring()
        if "fail" in type(backend).__module__ or "plaintext" in type(backend).__module__.lower():
            raise RuntimeError("Secure operating-system credential vault unavailable")
    return backend


class Agent:
    def __init__(self, root: Path, url: str, token: str) -> None:
        self.root, self.url = root.resolve(), url
        for folder in FOLDERS:
            safe_path(self.root, self.root / folder).mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / "logs" / "queue.sqlite3")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, hash TEXT NOT NULL, file_id TEXT, state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, retry_at REAL NOT NULL DEFAULT 0)"
        )
        if "archive_path" not in {row[1] for row in self.db.execute("PRAGMA table_info(files)")}:
            self.db.execute("ALTER TABLE files ADD COLUMN archive_path TEXT")
        self.db.commit()
        self.client = httpx.Client(
            base_url=url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
            follow_redirects=False,
        )
        self.observed: dict[str, tuple[int, int]] = {}
        self.errors = 0
        self.auto_upload = os.environ.get("KNK_DATA_DROP_AUTO_UPLOAD", "true").lower() == "true"
        self.archive_processed = (
            os.environ.get("KNK_DATA_DROP_ARCHIVE_PROCESSED", "true").lower() == "true"
        )
        logging.basicConfig(
            filename=self.root / "logs" / "agent.log",
            level=logging.INFO,
            format="%(asctime)s %(message)s",
        )

    def scan(self) -> None:
        for path in (self.root / "inbox").rglob("*"):
            if (
                path.is_symlink()
                or not path.is_file()
                or path.suffix.lower()
                not in {".csv", ".json", ".jsonl", ".xlsx", ".xls", ".parquet"}
            ):
                continue
            path = safe_path(self.root, path)
            stat = path.stat()
            stamp = (stat.st_size, stat.st_mtime_ns)
            prior = self.observed.get(str(path))
            self.observed[str(path)] = stamp
            if prior != stamp or not 0 < stat.st_size <= 25_000_000:
                continue
            row = self.db.execute("SELECT state FROM files WHERE path=?", (str(path),)).fetchone()
            if row:
                continue
            content = path.read_bytes()
            if (path.stat().st_size, path.stat().st_mtime_ns) != stamp:
                continue
            digest = hashlib.sha256(content).hexdigest()
            target = safe_path(self.root, self.root / "processing" / f"{digest[:12]}-{path.name}")
            if target.exists():
                if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                    self.errors += 1
                    continue
                # Keep both sources until server-side deduplication confirms identity.
                target = safe_path(
                    self.root, self.root / "processing" / f"{time.time_ns()}-{path.name}"
                )
            path.rename(target)
            self.db.execute(
                "INSERT INTO files(path,hash,state) VALUES(?,?,?)", (str(target), digest, "QUEUED")
            )
            self.db.commit()
        # Recover files moved immediately before an interrupted queue commit.
        for path in (self.root / "processing").glob("*"):
            if path.is_file() and not path.is_symlink():
                safe_path(self.root, path)
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                self.db.execute(
                    "INSERT OR IGNORE INTO files(path,hash,state) VALUES(?,?,?)",
                    (str(path), digest, "QUEUED"),
                )
        self.db.commit()

    def upload(self) -> None:
        rows = self.db.execute(
            "SELECT path,hash,attempts FROM files WHERE state='QUEUED' AND retry_at<=?",
            (time.time(),),
        ).fetchall()
        for filename, digest, attempts in rows:
            path = safe_path(self.root, filename)
            try:
                content = path.read_bytes()
                if hashlib.sha256(content).hexdigest() != digest:
                    raise ValueError("Queued file changed")
                original = path.name.split("-", 1)[1]
                response = self.client.post("/agent/v1/files", files={"file": (original, content)})
                response.raise_for_status()
                payload = file_status(response.json())
                if payload["hash"] != digest:
                    raise ValueError("Upload acknowledgement hash mismatch")
                if payload["state"] == "UPLOAD_FAILED":
                    raise ValueError("Server raw storage unavailable")
                self.db.execute(
                    "UPDATE files SET file_id=?,state=? WHERE path=?",
                    (payload["id"], payload["state"], filename),
                )
                if payload["state"] not in TERMINAL_STATES:
                    destination = safe_path(self.root, self.root / "review" / path.name)
                    if not destination.exists():
                        path.rename(destination)
                        self.db.execute(
                            "UPDATE files SET path=? WHERE path=?", (str(destination), filename)
                        )
                logging.info("upload acknowledged hash=%s state=%s", digest[:12], payload["state"])
            except (httpx.HTTPError, OSError, ValueError, KeyError):
                self.errors += 1
                self.db.execute(
                    "UPDATE files SET attempts=?,retry_at=? WHERE path=?",
                    (attempts + 1, time.time() + min(300, 2 ** min(attempts + 1, 8)), filename),
                )
                logging.warning("upload retry hash=%s attempt=%s", digest[:12], attempts + 1)
            self.db.commit()

    def _archive(self, item: FileStatus, filename: str, digest: str, planned: str | None) -> None:
        path = safe_path(self.root, filename)
        if item["hash"] != digest:
            raise ValueError("Remote file identity changed")
        if planned is None:
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError("Local file changed before archive")
            folder = (
                "quarantine"
                if item["state"] == "QUARANTINED"
                else "rejected"
                if item["state"] == "REJECTED"
                else datetime.now().strftime("processed/%Y/%m")
            )
            target = safe_path(self.root, self.root / folder / path.name)
            if target.exists():
                target = safe_path(self.root, target.with_name(f"{uuid4().hex}-{path.name}"))
            # Commit intent before the filesystem move. A restart can then find
            # either source or destination without guessing a new archive month.
            self.db.execute(
                "UPDATE files SET archive_path=?,state='ARCHIVE_PENDING' WHERE path=?",
                (str(target), filename),
            )
            self.db.commit()
        else:
            target = safe_path(self.root, planned)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError("Local file changed during archive")
            path.rename(target)
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError("Archived file integrity check failed")
        if item["state"] == "IMPORTED":
            response = self.client.post(f"/agent/v1/files/{quote(item['id'], safe='')}/archived")
            response.raise_for_status()
            acknowledgement: object = response.json()
            if not isinstance(acknowledgement, dict) or acknowledgement.get("status") != "ARCHIVED":
                raise ValueError("Invalid archive acknowledgement")
        self.db.execute(
            "UPDATE files SET path=?,state='LOCAL_ARCHIVED',archive_path=NULL,attempts=0,retry_at=0 WHERE path=?",
            (str(target), filename),
        )
        self.db.commit()

    def sync(self) -> None:
        pending = self.db.execute(
            "SELECT DISTINCT file_id FROM files WHERE file_id IS NOT NULL AND state!='LOCAL_ARCHIVED' AND retry_at<=? ORDER BY file_id",
            (time.time(),),
        ).fetchall()
        identifiers = [row[0] for row in pending]
        items: list[FileStatus] = []
        for start in range(0, len(identifiers), 100):
            batch = identifiers[start : start + 100]
            response = self.client.get(
                "/agent/v1/files", params=[("file_id", identifier) for identifier in batch]
            )
            response.raise_for_status()
            payload: object = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
                raise ValueError("Invalid remote file list")
            statuses = [file_status(value) for value in payload["items"]]
            returned = {item["id"] for item in statuses}
            if len(returned) != len(statuses) or not returned.issubset(batch):
                raise ValueError("Remote status list does not match queued file identities")
            for identifier in set(batch) - returned:
                for filename, digest, attempts in self.db.execute(
                    "SELECT path,hash,attempts FROM files WHERE file_id=? AND state!='LOCAL_ARCHIVED'",
                    (identifier,),
                ).fetchall():
                    self.errors += 1
                    self.db.execute(
                        "UPDATE files SET attempts=?,retry_at=? WHERE path=?",
                        (attempts + 1, time.time() + min(300, 2 ** min(attempts + 1, 8)), filename),
                    )
                    logging.warning(
                        "remote status missing; local file retained hash=%s", digest[:12]
                    )
            items.extend(statuses)
        for item in items:
            records = self.db.execute(
                "SELECT path,state,hash,archive_path,attempts,retry_at FROM files WHERE file_id=?",
                (item["id"],),
            ).fetchall()
            for filename, state, digest, planned, attempts, retry_at in records:
                if state == "LOCAL_ARCHIVED" or retry_at > time.time():
                    continue
                try:
                    if item["hash"] != digest:
                        raise ValueError("Remote file identity changed")
                    if item["state"] in TERMINAL_STATES:
                        if self.archive_processed:
                            self._archive(item, filename, digest, planned)
                    elif state != "ARCHIVE_PENDING":
                        self.db.execute(
                            "UPDATE files SET state=? WHERE path=?", (item["state"], filename)
                        )
                except (httpx.HTTPError, OSError, ValueError):
                    self.errors += 1
                    self.db.execute(
                        "UPDATE files SET attempts=?,retry_at=? WHERE path=?",
                        (attempts + 1, time.time() + min(300, 2 ** min(attempts + 1, 8)), filename),
                    )
                    logging.warning("archive retry hash=%s attempt=%s", digest[:12], attempts + 1)
                self.db.commit()
        self.db.commit()

    def tick(self) -> None:
        paused = (self.root / "PAUSE").exists()
        queued = self.db.execute("SELECT COUNT(*) FROM files WHERE state='QUEUED'").fetchone()[0]
        self.client.post(
            "/agent/v1/heartbeat",
            json={"paused": paused, "queued": queued, "errors": self.errors, "version": VERSION},
        ).raise_for_status()
        if not paused:
            self.scan()
            if self.auto_upload:
                self.upload()
            self.sync()

    def close(self) -> None:
        self.client.close()
        self.db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["pair", "run", "rescan", "pause", "resume"])
    parser.add_argument("--root", default=os.environ.get("KNK_DATA_DROP_ROOT"))
    parser.add_argument("--url", default=os.environ.get("KNK_TERMINAL_API", "https://localhost"))
    parser.add_argument("--allow-loopback-http", action="store_true")
    parser.add_argument("--name", default="KnK Local Data Agent")
    args = parser.parse_args()
    interval = float(os.environ.get("KNK_DATA_DROP_SCAN_INTERVAL_SECONDS", "5"))
    if not 1 <= interval <= 3600:
        parser.error("KNK_DATA_DROP_SCAN_INTERVAL_SECONDS must be between 1 and 3600")
    if os.environ.get("KNK_DATA_DROP_AUTO_IMPORT_APPROVED_SCHEMAS", "false").lower() != "false":
        parser.error("Automatic import is not enabled; each dataset version requires approval")
    if not args.root:
        parser.error("Set KNK_DATA_DROP_ROOT or --root")
    root = Path(args.root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    url = validate_endpoint(args.url, args.allow_loopback_http)
    if args.command in {"pause", "resume"}:
        path = root / "PAUSE"
        if args.command == "pause":
            path.touch()
        else:
            path.unlink(missing_ok=True)
        return
    backend = credential_backend()
    if args.command == "pair":
        code = getpass.getpass("One-time pairing code: ")
        with httpx.Client(base_url=url, timeout=30, follow_redirects=False) as client:
            response = client.post("/agent/v1/pair", json={"code": code, "name": args.name})
            response.raise_for_status()
            payload: object = response.json()
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("token"), str)
            or not payload["token"]
        ):
            raise ValueError("Invalid pairing acknowledgement")
        backend.set_password(SERVICE, url, payload["token"])
        print("Agent paired. Scoped token stored in the operating-system credential vault.")
        return
    token = backend.get_password(SERVICE, url)
    if not token:
        raise RuntimeError("Agent is not paired")
    agent = Agent(root, url, token)
    try:
        while True:
            try:
                agent.tick()
            except (httpx.HTTPError, OSError, ValueError):
                agent.errors += 1
                logging.warning("scan or synchronization failed; queued files retained")
            if args.command == "rescan":
                time.sleep(2)
                agent.tick()
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        agent.close()


if __name__ == "__main__":
    main()

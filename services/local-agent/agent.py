"""Outbound-only data-drop agent. Tokens are stored in the OS credential vault."""
import argparse
import getpass
import hashlib
import json
import logging
import os
from pathlib import Path
import sqlite3
import sys
import time
from datetime import datetime
from urllib.parse import urlparse

import httpx
import keyring

VERSION = "1.0.0"
SERVICE = "KnK Capital Data Drop"
FOLDERS = ["inbox/koyfin", "inbox/prices", "inbox/fundamentals", "inbox/macro", "inbox/portfolio", "inbox/custom", "processing", "review", "processed", "rejected", "logs"]


def safe_path(root, value):
    resolved = Path(value).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("Path escapes configured data-drop root")
    return resolved


def validate_endpoint(url, allow_local):
    parsed = urlparse(url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise ValueError("API URL must be a server origin without credentials or path")
    if parsed.scheme != "https" and not (allow_local and parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}):
        raise ValueError("HTTPS required except explicitly enabled loopback development")
    return url.rstrip("/")


def credential_backend():
    if sys.platform == "win32":
        from keyring.backends.Windows import WinVaultKeyring
        backend = WinVaultKeyring()
    else:
        backend = keyring.get_keyring()
        if "fail" in type(backend).__module__ or "plaintext" in type(backend).__module__.lower():
            raise RuntimeError("Secure operating-system credential vault unavailable")
    return backend


class Agent:
    def __init__(self, root, url, token):
        self.root, self.url = root.resolve(), url
        for folder in FOLDERS:
            safe_path(self.root, self.root / folder).mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / "logs" / "queue.sqlite3")
        self.db.execute("CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, hash TEXT NOT NULL, file_id TEXT, state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, retry_at REAL NOT NULL DEFAULT 0)")
        self.db.commit()
        self.client = httpx.Client(base_url=url, headers={"Authorization": f"Bearer {token}"}, timeout=30, follow_redirects=False)
        self.observed = {}
        self.errors = 0
        logging.basicConfig(filename=self.root / "logs" / "agent.log", level=logging.INFO, format="%(asctime)s %(message)s")

    def scan(self):
        for path in (self.root / "inbox").rglob("*"):
            if path.is_symlink() or not path.is_file() or path.suffix.lower() not in {".csv", ".json", ".xlsx"}:
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
                target = safe_path(self.root, self.root / "processing" / f"{time.time_ns()}-{path.name}")
            path.rename(target)
            self.db.execute("INSERT INTO files(path,hash,state) VALUES(?,?,?)", (str(target), digest, "QUEUED"))
            self.db.commit()
        # Recover files moved immediately before an interrupted queue commit.
        for path in (self.root / "processing").glob("*"):
            if path.is_file() and not path.is_symlink():
                safe_path(self.root, path)
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                self.db.execute("INSERT OR IGNORE INTO files(path,hash,state) VALUES(?,?,?)", (str(path), digest, "QUEUED"))
        self.db.commit()

    def upload(self):
        rows = self.db.execute("SELECT path,hash,attempts FROM files WHERE state='QUEUED' AND retry_at<=?", (time.time(),)).fetchall()
        for filename, digest, attempts in rows:
            path = safe_path(self.root, filename)
            try:
                content = path.read_bytes()
                if hashlib.sha256(content).hexdigest() != digest:
                    raise ValueError("Queued file changed")
                original = path.name.split("-", 1)[1]
                response = self.client.post("/agent/v1/files", files={"file": (original, content)})
                response.raise_for_status()
                payload = response.json()
                if payload["hash"] != digest:
                    raise ValueError("Upload acknowledgement hash mismatch")
                if payload["state"] == "UPLOAD_FAILED":
                    raise ValueError("Server raw storage unavailable")
                self.db.execute("UPDATE files SET file_id=?,state=? WHERE path=?", (payload["id"], payload["state"], filename))
                if payload["state"] not in {"IMPORTED", "ARCHIVED", "DUPLICATE", "REJECTED", "QUARANTINED"}:
                    destination = safe_path(self.root, self.root / "review" / path.name)
                    if not destination.exists():
                        path.rename(destination)
                        self.db.execute("UPDATE files SET path=? WHERE path=?", (str(destination), filename))
                logging.info("upload acknowledged hash=%s state=%s", digest[:12], payload["state"])
            except (httpx.HTTPError, OSError, ValueError, KeyError):
                self.errors += 1
                self.db.execute("UPDATE files SET attempts=?,retry_at=? WHERE path=?", (attempts + 1, time.time() + min(300, 2 ** min(attempts + 1, 8)), filename))
                logging.warning("upload retry hash=%s attempt=%s", digest[:12], attempts + 1)
            self.db.commit()

    def sync(self):
        response = self.client.get("/agent/v1/files")
        response.raise_for_status()
        for item in response.json()["items"]:
            record = self.db.execute("SELECT path,state FROM files WHERE file_id=?", (item["id"],)).fetchone()
            if not record:
                continue
            filename, state = record
            if state == "LOCAL_ARCHIVED":
                continue
            remote = item["state"]
            if remote in {"IMPORTED", "ARCHIVED", "DUPLICATE", "REJECTED", "QUARANTINED"}:
                path = safe_path(self.root, filename)
                folder = "rejected" if remote in {"REJECTED", "QUARANTINED"} else datetime.now().strftime("processed/%Y/%m")
                target = safe_path(self.root, self.root / folder / path.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                if path.exists() and not target.exists():
                    path.rename(target)
                elif path.exists():
                    target = safe_path(self.root, target.with_name(f"{time.time_ns()}-{target.name}"))
                    path.rename(target)
                if remote == "IMPORTED":
                    self.client.post(f"/agent/v1/files/{item['id']}/archived").raise_for_status()
                self.db.execute("UPDATE files SET path=?,state='LOCAL_ARCHIVED' WHERE file_id=?", (str(target), item["id"]))
            else:
                self.db.execute("UPDATE files SET state=? WHERE file_id=?", (remote, item["id"]))
        self.db.commit()

    def tick(self):
        paused = (self.root / "PAUSE").exists()
        queued = self.db.execute("SELECT COUNT(*) FROM files WHERE state='QUEUED'").fetchone()[0]
        self.client.post("/agent/v1/heartbeat", json={"paused": paused, "queued": queued, "errors": self.errors, "version": VERSION}).raise_for_status()
        if not paused:
            self.scan()
            self.upload()
            self.sync()

    def close(self):
        self.client.close()
        self.db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["pair", "run", "rescan", "pause", "resume"])
    parser.add_argument("--root", default=os.environ.get("KNK_DATA_DROP_ROOT"))
    parser.add_argument("--url", default=os.environ.get("KNK_TERMINAL_API", "https://localhost"))
    parser.add_argument("--allow-loopback-http", action="store_true")
    parser.add_argument("--name", default="KnK Local Data Agent")
    args = parser.parse_args()
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
            payload = response.json()
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
            except httpx.HTTPError:
                agent.errors += 1
                logging.warning("server unavailable; queued files retained")
            if args.command == "rescan":
                time.sleep(2)
                agent.tick()
                break
            time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        agent.close()


if __name__ == "__main__":
    main()

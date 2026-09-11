from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .config import get_settings

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None


@dataclass(frozen=True)
class StoredObject:
    object_key: str
    content_hash: str
    size_bytes: int


class ObjectStorage:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.local_root = Path(self.settings.object_storage_local_dir)
        self.local_root.mkdir(parents=True, exist_ok=True)
        self._s3 = None
        if boto3 and self.settings.object_storage_endpoint and self.settings.object_storage_access_key and self.settings.object_storage_secret_key:
            self._s3 = boto3.client(
                "s3",
                endpoint_url=self.settings.object_storage_endpoint,
                aws_access_key_id=self.settings.object_storage_access_key,
                aws_secret_access_key=self.settings.object_storage_secret_key,
                region_name="us-east-1",
            )

    def put_bytes(self, *, key: str, data: bytes, content_type: str) -> StoredObject:
        self._validate_key(key)
        digest = hashlib.sha256(data).hexdigest()
        if self._s3:
            self._s3.put_object(Bucket=self.settings.object_storage_bucket, Key=key, Body=data, ContentType=content_type)
            return StoredObject(object_key=key, content_hash=digest, size_bytes=len(data))
        target = self.local_root / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return StoredObject(object_key=key, content_hash=digest, size_bytes=len(data))

    def get_bytes(self, key: str) -> bytes:
        self._validate_key(key)
        if self._s3:
            response = self._s3.get_object(Bucket=self.settings.object_storage_bucket, Key=key)
            return response["Body"].read()
        return (self.local_root / key).read_bytes()

    def put_new_bytes(self, *, key: str, data: bytes, content_type: str) -> StoredObject:
        """Write once. Conditional creation prevents competing workers overwriting output."""
        self._validate_key(key)
        if self._s3:
            self._s3.put_object(Bucket=self.settings.object_storage_bucket, Key=key,
                                Body=data, ContentType=content_type, IfNoneMatch="*")
        else:
            target = self.local_root / key
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(data)
        return StoredObject(key, hashlib.sha256(data).hexdigest(), len(data))

    def local_path(self, key: str) -> Path | None:
        self._validate_key(key)
        if self._s3:
            return None
        path = self.local_root / key
        return path if path.exists() else None

    def _validate_key(self, key: str) -> None:
        target = (self.local_root / key).resolve()
        if not target.is_relative_to(self.local_root.resolve()) or ".." in key.replace("\\", "/").split("/"):
            raise ValueError("Invalid object key")

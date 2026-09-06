"""Private immutable research attachments, always downloaded rather than embedded."""

import hashlib
import io
import uuid
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, Request, Response, UploadFile
from sqlalchemy import select

from . import models
from .object_storage import ObjectStorage
from .portfolio_api import identity
from .portfolio_operations import audit
from .portfolio_resource_api import Database

router = APIRouter(prefix="/api/v1/attachments", tags=["private-research-attachments"])


def payload(row):
    return {
        "id": row.id,
        "filename": row.original_filename,
        "content_type": row.content_type,
        "size_bytes": row.size_bytes,
        "hash": row.content_hash,
        "created_at": row.created_at,
        "state": "UNSCANNED_ATTACHMENT",
    }


@router.get("")
def list_attachments(session: Database):
    return {
        "items": [
            payload(row)
            for row in session.scalars(
                select(models.UploadedFile)
                .where(models.UploadedFile.upload_state == "RESEARCH_ATTACHMENT")
                .order_by(models.UploadedFile.created_at.desc())
                .limit(250)
            ).all()
        ]
    }


@router.post("", status_code=201)
async def attach(request: Request, session: Database, file: Annotated[UploadFile, File()]):
    name = Path((file.filename or "").replace("\\", "/")).name
    suffix = Path(name).suffix.lower()
    if not name or len(name) > 260 or any(ord(c) < 32 for c in name):
        raise ValueError("Invalid attachment filename")
    data = await file.read(25_000_001)
    if not 0 < len(data) <= 25_000_000:
        raise ValueError("Attachment must be nonempty and at most 25 MB")
    if suffix == ".pdf":
        if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
            raise ValueError("Invalid PDF signature or trailer")
        mime = "application/pdf"
    elif suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        from PIL import Image

        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.width * image.height > 25_000_000:
                    raise ValueError("Image exceeds 25 million pixels")
                expected = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}[suffix]
                if image.format != expected:
                    raise ValueError("Image contents do not match extension")
                image.verify()
            mime = "image/" + ("jpeg" if suffix in {".jpg", ".jpeg"} else suffix[1:])
        except (OSError, Image.DecompressionBombError) as exc:
            raise ValueError("Image validation failed") from exc
    else:
        raise ValueError("Research attachments support PDF, PNG, JPG and WebP")
    digest = hashlib.sha256(data).hexdigest()
    existing = session.scalar(
        select(models.UploadedFile).where(
            models.UploadedFile.content_hash == digest,
            models.UploadedFile.upload_state == "RESEARCH_ATTACHMENT",
        )
    )
    if existing:
        return {**payload(existing), "duplicate": True}
    key = f"research-attachments/{uuid.uuid4()}/{digest}{suffix}"
    ObjectStorage().put_bytes(key=key, data=data, content_type=mime)
    row = models.UploadedFile(
        original_filename=name,
        content_type=mime,
        object_key=key,
        content_hash=digest,
        size_bytes=len(data),
        upload_state="RESEARCH_ATTACHMENT",
    )
    session.add(row)
    session.flush()
    audit(
        session,
        "RESEARCH_ATTACHMENT_STORED",
        "uploaded_file",
        row.id,
        {"hash": digest, "filename": name, "state": "UNSCANNED_ATTACHMENT"},
        identity(request, session),
    )
    return payload(row)


@router.get("/{attachment_id}/download")
def download(attachment_id: str, session: Database):
    row = session.get(models.UploadedFile, attachment_id)
    if row is None or row.upload_state != "RESEARCH_ATTACHMENT":
        raise ValueError("Research attachment not found")
    data = ObjectStorage().get_bytes(row.object_key)
    if hashlib.sha256(data).hexdigest() != row.content_hash:
        raise ValueError("Attachment integrity check failed")
    return Response(
        data,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(row.original_filename)}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
            "Content-Security-Policy": "sandbox",
        },
    )

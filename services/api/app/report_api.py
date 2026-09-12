import hashlib
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models
from .auth_api import current_user
from .database import get_session
from .object_storage import ObjectStorage
from .portfolio_operations import audit
from .price_sources import utc
from .report_contracts import (
    ANALYSIS_KINDS,
    CONTENT_TYPES,
    FORMATS,
    ReportRequest,
    ReportTemplates,
    canonical,
    digest,
)
from .report_jobs import enqueue, public_job
from .report_models import ReportJob
from .report_sources import capture

router = APIRouter(prefix="/api/v1/report-jobs", tags=["Private reports"])
Database = Annotated[Session, Depends(get_session)]


def owned(session: Session, request: Request, identifier: str) -> ReportJob:
    user, _ = current_user(request, session)
    job = session.scalar(
        select(ReportJob).where(ReportJob.id == identifier, ReportJob.user_id == user.id)
    )
    if job is None:
        raise HTTPException(404, "Report not found")
    return job


@router.get("/templates")
def templates(request: Request, session: Database) -> ReportTemplates:
    current_user(request, session)
    return {
        "items": [
            {"kind": kind, "formats": formats, "analysis_kinds": ANALYSIS_KINDS.get(kind, ())}
            for kind, formats in FORMATS.items()
        ]
    }


@router.get("")
def listing(request: Request, session: Database) -> dict[str, object]:
    user, _ = current_user(request, session)
    jobs = session.scalars(
        select(ReportJob)
        .where(ReportJob.user_id == user.id)
        .order_by(ReportJob.created_at.desc())
        .limit(100)
    ).all()
    return {"items": [public_job(job) for job in jobs]}


@router.post("", status_code=202)
def create(payload: ReportRequest, request: Request, session: Database) -> dict[str, object]:
    user, _ = current_user(request, session)
    # Serialize submissions for this user on PostgreSQL; report owners cannot flood the queue.
    session.scalar(select(models.User).where(models.User.id == user.id).with_for_update())
    active = (
        session.scalar(
            select(func.count())
            .select_from(ReportJob)
            .where(ReportJob.user_id == user.id, ReportJob.status.in_(["QUEUED", "RUNNING"]))
        )
        or 0
    )
    if active >= 4:
        raise HTTPException(429, "Four active reports already queued; wait for completion")
    try:
        snapshot = capture(session, payload)
        job = enqueue(session, user.id, snapshot, payload.format)
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc
    session.commit()
    return public_job(job)


@router.get("/{identifier}")
def detail(identifier: str, request: Request, session: Database) -> dict[str, object]:
    return public_job(owned(session, request, identifier))


@router.get("/{identifier}/source")
def source(identifier: str, request: Request, session: Database) -> Response:
    job = owned(session, request, identifier)
    if digest(job.snapshot) != job.snapshot_hash:
        raise HTTPException(409, "Report source integrity check failed")
    return Response(
        canonical(job.snapshot),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="knk-{job.kind}-{job.id}-source.json"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/{identifier}/download")
def download(identifier: str, request: Request, session: Database) -> Response:
    job = owned(session, request, identifier)
    if utc(job.expires_at) <= datetime.now(UTC):
        raise HTTPException(410, "Report retention period expired")
    if job.status != "SUCCEEDED" or not job.object_key:
        raise HTTPException(409, "Report is not ready")
    try:
        content = ObjectStorage().get_bytes(job.object_key)
    except Exception as exc:
        raise HTTPException(503, "Report storage is unavailable") from exc
    if hashlib.sha256(content).hexdigest() != job.content_hash or len(content) != job.size_bytes:
        raise HTTPException(409, "Report integrity check failed")
    audit(
        session,
        "REPORT_DOWNLOADED",
        "report_job",
        job.id,
        {"content_hash": job.content_hash},
        job.user_id,
    )
    session.commit()
    return Response(
        content,
        media_type=CONTENT_TYPES[job.format],
        headers={
            "Content-Disposition": f'attachment; filename="knk-{job.kind}-{job.id}.{job.format}"',
            "Cache-Control": "private, no-store",
        },
    )

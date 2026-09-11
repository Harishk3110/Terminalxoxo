"""SQL claim and private object persistence; no external render endpoint."""

import hashlib
import os
import socket
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .database import SessionLocal
from .object_storage import ObjectStorage
from .portfolio_operations import audit
from .price_sources import utc
from .report_contracts import CONTENT_TYPES, ReportSnapshot, canonical, digest
from .report_models import ReportJob
from .report_render import render


def enqueue(session: Session, user_id: str, snapshot: ReportSnapshot, format: str) -> ReportJob:
    payload = snapshot.model_dump(mode="json")
    if len(canonical(payload)) > 10_000_000:
        raise ValueError("Report source exceeds the 10 MB job limit")
    job = ReportJob(
        user_id=user_id,
        kind=snapshot.kind,
        format=format,
        snapshot=payload,
        snapshot_hash=digest(payload),
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    session.add(job)
    session.flush()
    audit(
        session,
        "REPORT_QUEUED",
        "report_job",
        job.id,
        {"snapshot_hash": job.snapshot_hash, "kind": job.kind, "format": format},
        user_id,
    )
    return job


def execute(identifier: str) -> bool:
    worker = f"report:{socket.gethostname()}:{os.getpid()}"
    with SessionLocal() as session:
        claimed = session.execute(
            update(ReportJob)
            .where(ReportJob.id == identifier, ReportJob.status == "QUEUED")
            .values(status="RUNNING", progress=0.1, started_at=datetime.now(UTC), worker_id=worker)
            .returning(ReportJob.id)
        ).scalar_one_or_none()
        session.commit()
        if claimed is None:
            return False
        job = session.get(ReportJob, identifier)
        if job is None:
            return False
        try:
            if digest(job.snapshot) != job.snapshot_hash:
                raise ValueError("Snapshot integrity mismatch")
            snapshot = ReportSnapshot.model_validate(job.snapshot)
            content = render(snapshot, job.format)
            if not content or len(content) > 50_000_000:
                raise ValueError("Rendered report is empty or exceeds 50 MB")
            key = f"private-reports/{job.user_id}/{job.id}/report.{job.format}"
            storage = ObjectStorage()
            stored = storage.put_new_bytes(
                key=key, data=content, content_type=CONTENT_TYPES[job.format]
            )
            if hashlib.sha256(storage.get_bytes(key)).hexdigest() != stored.content_hash:
                raise ValueError("Stored report integrity mismatch")
            published = session.execute(
                update(ReportJob)
                .where(
                    ReportJob.id == identifier,
                    ReportJob.status == "RUNNING",
                    ReportJob.worker_id == worker,
                )
                .values(
                    object_key=key,
                    content_hash=stored.content_hash,
                    size_bytes=stored.size_bytes,
                    status="SUCCEEDED",
                    progress=1,
                    finished_at=datetime.now(UTC),
                )
                .returning(ReportJob.id)
            ).scalar_one_or_none()
            if published is None:
                session.rollback()
                return False
            audit(
                session,
                "REPORT_SUCCEEDED",
                "report_job",
                job.id,
                {"content_hash": stored.content_hash, "size_bytes": stored.size_bytes},
                job.user_id,
            )
        except Exception as exc:
            session.rollback()
            job = session.get(ReportJob, identifier)
            if job is None or job.status != "RUNNING" or job.worker_id != worker:
                return False
            job.status, job.error_category = "FAILED", type(exc).__name__
            job.error_message = (
                "Report generation failed; source, renderer or storage validation did not pass"
            )
            audit(
                session,
                "REPORT_FAILED",
                "report_job",
                job.id,
                {"category": job.error_category},
                job.user_id,
            )
        job.finished_at = datetime.now(UTC)
        session.commit()
    return True


def run_once() -> None:
    with SessionLocal() as session:
        # A process crash never causes an unbounded retry or silently altered output.
        expired = session.scalars(
            select(ReportJob).where(
                ReportJob.status == "RUNNING",
                ReportJob.started_at < datetime.now(UTC) - timedelta(minutes=15),
            )
        ).all()
        for job in expired:
            job.status, job.error_category = "FAILED", "WorkerLeaseExpired"
            job.error_message = "Worker stopped before completion; submit a new report"
            job.finished_at = datetime.now(UTC)
            audit(
                session,
                "REPORT_FAILED",
                "report_job",
                job.id,
                {"category": job.error_category},
                job.user_id,
            )
        session.commit()
        identifier = session.scalar(
            select(ReportJob.id)
            .where(ReportJob.status == "QUEUED")
            .order_by(ReportJob.created_at)
            .limit(1)
        )
    if identifier:
        execute(identifier)


def public_job(job: ReportJob) -> dict[str, object]:
    downloadable = job.status == "SUCCEEDED" and utc(job.expires_at) > datetime.now(UTC)
    return {
        "id": job.id,
        "kind": job.kind,
        "format": job.format,
        "status": job.status,
        "progress": job.progress,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "expires_at": job.expires_at.isoformat(),
        "snapshot_hash": job.snapshot_hash,
        "content_hash": job.content_hash,
        "size_bytes": job.size_bytes,
        "worker_id": job.worker_id,
        "error_category": job.error_category,
        "error_message": job.error_message,
        "source": job.snapshot.get("source"),
        "quality": job.snapshot.get("quality"),
        "as_of": job.snapshot.get("data_as_of"),
        "references": job.snapshot.get("references"),
        "download_url": f"/api/v1/report-jobs/{job.id}/download" if downloadable else None,
        "source_url": f"/api/v1/report-jobs/{job.id}/source",
    }

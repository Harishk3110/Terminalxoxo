"""Owned report jobs, separate from the shared analytical-run listing."""

from datetime import datetime

from pydantic import JsonValue
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .schema import Base, IdMixin


class ReportJob(IdMixin, Base):
    __tablename__ = "report_jobs"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    format: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(24), default="QUEUED", index=True)
    progress: Mapped[float] = mapped_column(Float, default=0)
    snapshot: Mapped[dict[str, JsonValue]] = mapped_column(JSON)
    snapshot_hash: Mapped[str] = mapped_column(String(64))
    worker_id: Mapped[str | None] = mapped_column(String(120))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    error_category: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)
    object_key: Mapped[str | None] = mapped_column(String(500))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int | None] = mapped_column(Integer)

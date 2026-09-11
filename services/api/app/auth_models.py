"""Persistent enrollment challenges and atomically consumed authenticator steps."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from .schema import Base, TimestampMixin


class TotpState(TimestampMixin, Base):
    __tablename__ = "auth_totp_states"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    last_timecode: Mapped[int] = mapped_column(BigInteger, default=-1, nullable=False)
    pending_secret: Mapped[str | None] = mapped_column(Text)
    pending_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

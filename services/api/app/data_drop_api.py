"""File-drop UI and narrowly scoped outbound agent endpoints."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from . import models
from .database import get_session
from .data_drop import DataDropService, file_payload, transition
from .data_mapping import seed_profiles
from .portfolio_api import identity
from .portfolio_operations import audit
from .price_sources import utc

router = APIRouter()
SCOPES = ["files:upload", "files:status", "agent:heartbeat"]


def checked(call, session):
    try:
        return call()
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.get("/api/v1/data-drop/files")
def files(session: Session = Depends(get_session)):
    rows = session.scalars(select(models.ExternalFile).order_by(models.ExternalFile.created_at.desc()).limit(250)).all()
    return {"items": [file_payload(row) for row in rows]}


@router.get("/api/v1/data-drop/files/{file_id}")
def file_detail(file_id: str, session: Session = Depends(get_session)):
    return checked(lambda: file_payload(DataDropService(session).get(file_id)), session)


@router.post("/api/v1/data-drop/files")
async def upload(file: UploadFile = File(...), session: Session = Depends(get_session)):
    data = await file.read(25_000_001)
    return checked(lambda: DataDropService(session).receive(file.filename or "upload.csv", data), session)


@router.get("/api/v1/data-drop/profiles")
def profiles(session: Session = Depends(get_session)):
    seed_profiles(session)
    session.commit()
    return {"items": [{"id": r.id, "code": r.code, "version": r.version, "source": r.source, "dataset_type": r.dataset_type, "approved": r.approved, "rules": r.rules} for r in session.scalars(select(models.MappingProfile).order_by(models.MappingProfile.code, models.MappingProfile.version.desc())).all()]}


class MappingRequest(BaseModel):
    profile_id: str
    mapping: dict[str, str] | None = None
    defaults: dict = Field(default_factory=dict)
    symbol_resolution: str | None = None


@router.post("/api/v1/data-drop/files/{file_id}/validate")
def validate(file_id: str, payload: MappingRequest, request: Request, session: Session = Depends(get_session)):
    actor = identity(request, session)
    return checked(lambda: DataDropService(session).map_validate(file_id, payload.profile_id, payload.mapping, payload.defaults, payload.symbol_resolution, actor), session)


class ImportRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    licence: str = Field(min_length=1, max_length=2000)
    approve: bool = False
    portfolio: str = "KNK_MAIN"


@router.post("/api/v1/data-drop/files/{file_id}/import")
def import_file(file_id: str, payload: ImportRequest, request: Request, session: Session = Depends(get_session)):
    actor = identity(request, session)
    return checked(lambda: DataDropService(session).import_file(file_id, **payload.model_dump(), actor=actor), session)


class RejectRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


@router.post("/api/v1/data-drop/files/{file_id}/reject")
def reject(file_id: str, payload: RejectRequest, request: Request, session: Session = Depends(get_session)):
    row = DataDropService(session).get(file_id)
    checked(lambda: transition(row, "REJECTED", payload.reason), session)
    audit(session, "EXTERNAL_FILE_REJECTED", "external_file", row.id, {"reason": payload.reason}, identity(request, session))
    session.commit()
    return file_payload(row)


@router.get("/api/v1/data-drop/agents")
def agents(session: Session = Depends(get_session)):
    now = datetime.now(timezone.utc)
    return {"items": [{"id": r.id, "name": r.name, "scopes": r.scopes, "last_seen": r.last_seen.isoformat() if r.last_seen else None, "state": "REVOKED" if r.revoked_at else "ONLINE" if r.last_seen and now - utc(r.last_seen) < timedelta(seconds=90) else "OFFLINE", "status": r.status} for r in session.scalars(select(models.LocalAgent)).all()]}


@router.post("/api/v1/data-drop/agents/pair")
def pair(request: Request, broker: bool = False, session: Session = Depends(get_session)):
    actor = identity(request, session, admin=True)
    code = secrets.token_urlsafe(24)
    from .portfolio_seed import profile_for
    permissions = [*SCOPES, "broker:read-sync", "portfolio:" + profile_for(session).portfolio_id] if broker else SCOPES
    row = models.AgentPairing(code_hash=hashlib.sha256(code.encode()).hexdigest(), expires_at=datetime.now(timezone.utc) + timedelta(minutes=10), scopes=permissions)
    session.add(row)
    session.flush()
    audit(session, "AGENT_PAIRING_CREATED", "agent_pairing", row.id, {"scopes": permissions}, actor)
    session.commit()
    return {"code": code, "expires_at": row.expires_at.isoformat(), "scopes": permissions}


@router.post("/api/v1/data-drop/agents/{agent_id}/revoke")
def revoke(agent_id: str, request: Request, session: Session = Depends(get_session)):
    actor = identity(request, session, admin=True)
    row = session.get(models.LocalAgent, agent_id)
    if row is None:
        raise HTTPException(404, "Agent not found")
    row.revoked_at = datetime.now(timezone.utc)
    audit(session, "AGENT_REVOKED", "local_agent", row.id, {}, actor)
    session.commit()
    return {"status": "REVOKED"}


class ClaimRequest(BaseModel):
    code: str = Field(min_length=20, max_length=100)
    name: str = Field(min_length=1, max_length=160)


@router.post("/agent/v1/pair")
def claim(payload: ClaimRequest, session: Session = Depends(get_session)):
    now = datetime.now(timezone.utc)
    row = session.scalar(select(models.AgentPairing).where(models.AgentPairing.code_hash == hashlib.sha256(payload.code.encode()).hexdigest()))
    if row is None or row.claimed_at or utc(row.expires_at) <= now:
        raise HTTPException(403, "Pairing code is invalid or expired")
    changed = session.execute(update(models.AgentPairing).where(models.AgentPairing.id == row.id, models.AgentPairing.claimed_at.is_(None), models.AgentPairing.expires_at > now).values(claimed_at=now).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        session.rollback()
        raise HTTPException(409, "Pairing already claimed")
    token = secrets.token_urlsafe(48)
    agent = models.LocalAgent(name=payload.name, token_hash=hashlib.sha256(token.encode()).hexdigest(), scopes=row.scopes, status={})
    session.add(agent)
    session.commit()
    return {"agent_id": agent.id, "token": token, "scopes": agent.scopes}


def agent_auth(request: Request, session: Session = Depends(get_session)):
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Agent token required")
    digest = hashlib.sha256(auth[7:].encode()).hexdigest()
    agent = session.scalar(select(models.LocalAgent).where(models.LocalAgent.token_hash == digest, models.LocalAgent.revoked_at.is_(None)))
    if agent is None:
        raise HTTPException(401, "Invalid or revoked agent token")
    return agent


def scope(agent, permission):
    if permission not in agent.scopes:
        raise HTTPException(403, "Agent scope denied")


class HeartbeatRequest(BaseModel):
    paused: bool = False
    queued: int = Field(default=0, ge=0, le=1000000)
    errors: int = Field(default=0, ge=0, le=1000000)
    version: str = Field(default="1.0", max_length=30)


@router.post("/agent/v1/heartbeat")
def heartbeat(payload: HeartbeatRequest, agent=Depends(agent_auth), session: Session = Depends(get_session)):
    scope(agent, "agent:heartbeat")
    agent.last_seen, agent.status = datetime.now(timezone.utc), payload.model_dump()
    session.commit()
    return {"status": "OK", "server_time": agent.last_seen.isoformat()}


@router.post("/agent/v1/files")
async def agent_upload(file: UploadFile = File(...), agent=Depends(agent_auth), session: Session = Depends(get_session)):
    scope(agent, "files:upload")
    data = await file.read(25_000_001)
    return checked(lambda: DataDropService(session).receive(file.filename or "upload.csv", data, agent_id=agent.id), session)


@router.get("/agent/v1/files")
def agent_files(agent=Depends(agent_auth), session: Session = Depends(get_session)):
    scope(agent, "files:status")
    rows = session.scalars(select(models.ExternalFile).where(models.ExternalFile.agent_id == agent.id).order_by(models.ExternalFile.created_at.desc()).limit(500)).all()
    return {"items": [{"id": r.id, "hash": r.content_hash, "state": r.state, "duplicate_of": r.duplicate_of} for r in rows]}


@router.post("/agent/v1/files/{file_id}/archived")
def archived(file_id: str, agent=Depends(agent_auth), session: Session = Depends(get_session)):
    scope(agent, "files:status")
    row = DataDropService(session).get(file_id)
    if row.agent_id != agent.id:
        raise HTTPException(403, "File belongs to another agent")
    if row.state != "ARCHIVED":
        checked(lambda: transition(row, "ARCHIVED", "Local agent confirmed archive"), session)
        session.commit()
    return {"status": row.state}

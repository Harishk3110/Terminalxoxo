import io

import pytest
from app import models
from app.attachments_api import router
from app.config import get_settings
from app.database import get_session
from app.object_storage import ObjectStorage
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image


@pytest.fixture
def attachment_client(ledger_session, session_token, tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "object_storage_local_dir", str(tmp_path))
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: ledger_session
    with TestClient(app) as client:
        client.cookies.set("knk_session", session_token)
        yield client


def test_image_signature_download_privacy_hash_and_dedup(attachment_client, ledger_session):
    content = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(content, "PNG")
    data = content.getvalue()
    client = attachment_client
    saved = client.post("/api/v1/attachments", files={"file": ("koyfin-research.png", data)}).json()
    assert saved["state"] == "UNSCANNED_ATTACHMENT"
    duplicate = client.post("/api/v1/attachments", files={"file": ("other.png", data)}).json()
    assert duplicate["duplicate"] and duplicate["id"] == saved["id"]
    url = f"/api/v1/attachments/{saved['id']}/download"
    response = client.get(url)
    assert response.content == data
    assert response.headers["Content-Disposition"].startswith("attachment;")
    assert response.headers["Cache-Control"] == "no-store"
    row = ledger_session.get(models.UploadedFile, saved["id"])
    ObjectStorage().put_bytes(
        key=row.object_key, data=b"corrupt", content_type="application/octet-stream"
    )
    assert client.get(url).status_code == 422
    client.cookies.clear()
    assert client.get(url).status_code == 403


@pytest.mark.parametrize(
    "name,data",
    [("fake.png", b"no-image"), ("code.svg", b"<svg/>"), ("bad.pdf", b"%PDF-incomplete")],
)
def test_invalid_attachment_rejected(attachment_client, name, data):
    assert (
        attachment_client.post("/api/v1/attachments", files={"file": (name, data)}).status_code
        == 422
    )

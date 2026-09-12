"""Private, audited Pine research exports. Never executes orders."""

import hashlib
from typing import Annotated, Self

from fastapi import APIRouter, File, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from . import models
from .equity_api import save_analysis
from .object_storage import ObjectStorage
from .pine_research import PineSettings, compare_export, generate
from .pine_results import SavedPineTemplate
from .portfolio_api import identity
from .portfolio_resource_api import Database

router = APIRouter(prefix="/api/v1/pine", tags=["pine-research"])


class StoredTemplateSource(BaseModel):
    model_config = ConfigDict(strict=True)
    source_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    pine_source: str = Field(min_length=1)
    settings: PineSettings

    @model_validator(mode="after")
    def hash_matches(self) -> Self:
        if hashlib.sha256(self.pine_source.encode()).hexdigest() != self.source_hash:
            raise ValueError("Saved Pine source hash does not match its content")
        return self


@router.post("/generate", status_code=201)
def create_template(
    payload: PineSettings, request: Request, session: Database
) -> dict[str, JsonValue]:
    generated = generate(payload)
    result: SavedPineTemplate = {
        **generated,
        "pine_source": generated["source"],
        "source": "KnK Pine template generator",
    }
    return save_analysis(
        session,
        "pine",
        f"{payload.strategy} Pine v6",
        payload.model_dump(mode="json"),
        result,
        identity(request, session),
    )


@router.post("/{run_id}/compare", status_code=201)
async def compare(
    run_id: str, request: Request, session: Database, file: Annotated[UploadFile, File()]
) -> dict[str, JsonValue]:
    template = session.get(models.AnalysisRun, run_id)
    if not template or template.kind != "pine" or template.status != "SUCCEEDED":
        raise ValueError("Saved Pine template not found")
    settings = PineSettings.model_validate(template.parameters)
    evidence = StoredTemplateSource.model_validate(template.result)
    if settings != evidence.settings:
        raise ValueError("Saved Pine settings do not match source evidence")
    raw = await file.read(10_000_001)
    result = compare_export(raw, settings)
    storage = ObjectStorage()
    key = f"pine-comparisons/{result['source_hash']}.csv"
    storage.put_bytes(key=key, data=raw, content_type="text/csv")
    return save_analysis(
        session,
        "pine_compare",
        template.name + " comparison",
        {
            "template_id": run_id,
            "template_hash": evidence.source_hash,
            "raw_object_key": key,
            "settings": template.parameters,
        },
        result,
        identity(request, session),
    )

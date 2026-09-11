"""Private, audited Pine research exports. Never executes orders."""

from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile

from . import models
from .equity_api import save_analysis
from .object_storage import ObjectStorage
from .pine_research import PineSettings, compare_export, generate
from .portfolio_api import identity
from .portfolio_resource_api import Database

router = APIRouter(prefix="/api/v1/pine", tags=["pine-research"])


@router.post("/generate", status_code=201)
def create_template(payload: PineSettings, request: Request, session: Database):
    result = generate(payload)
    result["pine_source"] = result.pop("source")
    result["source"] = "KnK Pine template generator"
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
):
    template = session.get(models.AnalysisRun, run_id)
    if not template or template.kind != "pine" or template.status != "SUCCEEDED":
        raise ValueError("Saved Pine template not found")
    raw = await file.read(10_000_001)
    result = compare_export(raw, PineSettings(**template.parameters))
    storage = ObjectStorage()
    key = f"pine-comparisons/{result['source_hash']}.csv"
    storage.put_bytes(key=key, data=raw, content_type="text/csv")
    return save_analysis(
        session,
        "pine_compare",
        template.name + " comparison",
        {
            "template_id": run_id,
            "template_hash": template.result["source_hash"],
            "raw_object_key": key,
            "settings": template.parameters,
        },
        result,
        identity(request, session),
    )

"""Gestão de activação de modelos LLM (tabela llm_model_config)."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from pipeline.openrouter_models import (
    _ID_TO_ENTRY,
    api_models_payload,
)
from database.connection import get_db
from database.models import LlmModelConfig
from routers.auth import exigir_role

router = APIRouter(prefix="/api/admin/llm-models", tags=["Admin — LLM"])


class LlmModelToggleBody(BaseModel):
    enabled: bool


@router.get("", summary="Catálogo com estado enabled por modelo")
def listar_llm_models(
    db: Session = Depends(get_db),
    _usuario=Depends(exigir_role("super_admin", "admin")),
):
    return api_models_payload(db=db, only_enabled=False, include_enabled_flag=True)


@router.patch("/{model_id}", summary="Activar ou desactivar modelo")
def definir_llm_model(
    model_id: str,
    body: LlmModelToggleBody,
    db: Session = Depends(get_db),
    _usuario=Depends(exigir_role("super_admin", "admin")),
):
    if model_id not in _ID_TO_ENTRY:
        raise HTTPException(
            404,
            detail=f"model_id desconhecido: {model_id!r}. Catálogo: {list(_ID_TO_ENTRY)}",
        )
    row = db.query(LlmModelConfig).filter(LlmModelConfig.model_id == model_id).first()
    now = datetime.utcnow()
    if row:
        row.enabled = body.enabled
        row.updated_at = now
    else:
        db.add(
            LlmModelConfig(model_id=model_id, enabled=body.enabled, updated_at=now)
        )
    db.commit()

    return api_models_payload(db=db, only_enabled=False, include_enabled_flag=True)

"""Metadados e visão agregada do painel administrativo."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from admin.deps import get_usuario_admin
from pipeline.openrouter_models import api_models_payload
from pipeline.sequential_spec import pipeline_step_meta_labels
from database.connection import get_db
from database.models import (
    Cardapio,
    Contrato,
    Empresa,
    FichaTecnica,
    Ingrediente,
    JobAgente,
)
from services.knowledge_base import knowledge_stats

router = APIRouter(prefix="/api/admin/meta", tags=["Admin — Meta"])


@router.get("/pipeline-steps", summary="Lista os 7 passos do pipeline (read-only)")
def pipeline_steps(_usuario=Depends(get_usuario_admin)):
    return {"steps": pipeline_step_meta_labels(), "fonte": "crew/sequential_spec.py"}


@router.get("/dashboard", summary="Resumo operacional do painel admin")
def dashboard_meta(
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_admin),
):
    is_super = usuario.role == "super_admin"
    empresa_id = str(usuario.empresa_id) if getattr(usuario, "empresa_id", None) else None

    contratos_q = db.query(Contrato)
    ingredientes_q = db.query(Ingrediente)
    fichas_q = db.query(FichaTecnica)
    cardapios_q = db.query(Cardapio)
    jobs_q = db.query(JobAgente)

    if not is_super and empresa_id:
        contratos_q = contratos_q.filter(Contrato.empresa_id == empresa_id)
        ingredientes_q = ingredientes_q.filter(
            (Ingrediente.empresa_id == empresa_id) | (Ingrediente.empresa_id == None)
        )
        fichas_q = fichas_q.filter(FichaTecnica.empresa_id == empresa_id)
        cardapios_q = cardapios_q.filter(Cardapio.empresa_id == empresa_id)
        jobs_q = jobs_q.filter(JobAgente.empresa_id == empresa_id)

    total_empresas = db.query(func.count(Empresa.id)).scalar() if is_super else (1 if empresa_id else 0)
    llm_payload = api_models_payload(db=db, only_enabled=False, include_enabled_flag=True)
    models = llm_payload.get("models") or []
    enabled_models = sum(1 for model in models if model.get("enabled"))
    knowledge = knowledge_stats(db, empresa_id=empresa_id)

    return {
        "scope": "global" if is_super else "empresa",
        "empresa_id": empresa_id,
        "user": {
            "id": str(usuario.id),
            "nome": usuario.nome,
            "email": usuario.email,
            "role": usuario.role,
        },
        "counts": {
            "empresas": int(total_empresas or 0),
            "contratos": int(contratos_q.count() or 0),
            "ingredientes": int(ingredientes_q.count() or 0),
            "fichas": int(fichas_q.count() or 0),
            "cardapios": int(cardapios_q.count() or 0),
            "jobs": int(jobs_q.count() or 0),
            "jobs_ativos": int(jobs_q.filter(JobAgente.status.in_(("iniciando", "executando"))).count() or 0),
        },
        "llm": {
            "provider": llm_payload.get("provider"),
            "default": llm_payload.get("default"),
            "enabled_models": enabled_models,
            "total_models": len(models),
        },
        "knowledge": knowledge,
    }

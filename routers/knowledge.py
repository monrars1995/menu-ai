"""
Endpoints de base de conhecimento vetorial via Supabase/PostgreSQL.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.connection import get_db
from routers.auth_supabase import exigir_role, get_usuario_atual
from services.knowledge_base import (
    knowledge_stats,
    reindex_knowledge_base,
    semantic_search,
)

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Base"])


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    source_type: Optional[str] = Field(default=None)
    limit: int = Field(default=5, ge=1, le=12)
    empresa_id: Optional[str] = None


class KnowledgeReindexRequest(BaseModel):
    empresa_id: Optional[str] = None
    source_type: str = Field(default="all")


def _empresa_scope(usuario, empresa_id: Optional[str]) -> Optional[str]:
    if usuario.role == "super_admin":
        return str(empresa_id).strip() if empresa_id else None
    return str(usuario.empresa_id or "").strip() or None


@router.get("/stats", summary="Resumo da base vetorial")
def stats(
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    resolved_empresa_id = _empresa_scope(usuario, empresa_id)
    return knowledge_stats(db, empresa_id=resolved_empresa_id)


@router.post("/reindex", summary="Reindexar contratos, fichas e cardápios")
def reindex(
    body: KnowledgeReindexRequest,
    db: Session = Depends(get_db),
    usuario=Depends(exigir_role("super_admin", "admin", "nutricionista")),
):
    resolved_empresa_id = _empresa_scope(usuario, body.empresa_id)
    source_type = (body.source_type or "all").strip().lower()
    valid = {"all", "contrato", "ficha", "cardapio"}
    if source_type not in valid:
        raise HTTPException(status_code=400, detail="source_type inválido.")

    result = reindex_knowledge_base(
        db,
        empresa_id=resolved_empresa_id,
        source_type=source_type,
    )
    db.commit()
    return {
        "ok": True,
        "empresa_id": resolved_empresa_id,
        "source_type": source_type,
        "result": result,
    }


@router.post("/search", summary="Buscar contexto semântico")
def search(
    body: KnowledgeSearchRequest,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_atual),
):
    resolved_empresa_id = _empresa_scope(usuario, body.empresa_id)
    source_types = [body.source_type.strip().lower()] if body.source_type else []
    try:
        rows = semantic_search(
            db,
            query=body.query,
            empresa_id=resolved_empresa_id,
            source_types=source_types,
            limit=body.limit,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "empresa_id": resolved_empresa_id,
        "count": len(rows),
        "results": rows,
    }

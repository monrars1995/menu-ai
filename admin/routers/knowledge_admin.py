"""Admin de base vetorial e busca semântica."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from admin.deps import get_usuario_admin
from database.connection import get_db
from services.knowledge_base import knowledge_stats, reindex_knowledge_base, semantic_search

router = APIRouter(prefix="/api/admin/knowledge", tags=["Admin — Knowledge"])


class AdminKnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    source_type: Optional[str] = None
    empresa_id: Optional[str] = None
    limit: int = Field(default=5, ge=1, le=12)


class AdminKnowledgeReindexRequest(BaseModel):
    empresa_id: Optional[str] = None
    source_type: str = Field(default="all")


def _empresa_scope(usuario, empresa_id: Optional[str]) -> Optional[str]:
    if usuario.role == "super_admin":
        return str(empresa_id).strip() if empresa_id else None
    return str(usuario.empresa_id or "").strip() or None


@router.get("/stats", summary="Resumo da base vetorial no escopo admin")
def stats(
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_admin),
):
    return knowledge_stats(db, empresa_id=_empresa_scope(usuario, empresa_id))


@router.post("/reindex", summary="Reindexar corpus vetorial")
def reindex(
    body: AdminKnowledgeReindexRequest,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_admin),
):
    source_type = (body.source_type or "all").strip().lower()
    if source_type not in {"all", "contrato", "ficha", "cardapio"}:
        raise HTTPException(status_code=400, detail="source_type inválido.")
    resolved_empresa_id = _empresa_scope(usuario, body.empresa_id)
    result = reindex_knowledge_base(db, empresa_id=resolved_empresa_id, source_type=source_type)
    db.commit()
    return {
        "ok": True,
        "empresa_id": resolved_empresa_id,
        "source_type": source_type,
        "result": result,
    }


@router.post("/search", summary="Buscar trechos semanticamente similares")
def search(
    body: AdminKnowledgeSearchRequest,
    db: Session = Depends(get_db),
    usuario=Depends(get_usuario_admin),
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

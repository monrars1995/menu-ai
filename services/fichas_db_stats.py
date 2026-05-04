"""
Estatísticas de fichas técnicas e ingredientes no SQL (com cache em memória + TTL).
Substitui a leitura de base_receitas.xlsx em /api/info e no progresso de jobs.
"""
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

TTL_SECONDS = int(os.getenv("FICHAS_DB_STATS_TTL", "60"))

# (empresa_key, payload_without_cached_flag, time_ts) — empresa_key: "__all__" | uuid str
_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def _cache_key(empresa_id: Optional[str]) -> str:
    return "__all__" if not empresa_id else str(empresa_id).strip()


def clear_fichas_db_stats_cache() -> None:
    _cache.clear()


def _get_session() -> Optional[Session]:
    try:
        from database.connection import SessionLocal

        return SessionLocal()
    except Exception:
        return None


def get_fichas_db_stats(empresa_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Conta fichas técnicas ativas e, quando possível, ingredientes; agrega por categoria.

    * empresa_id=None: totais globais (todas as empresas) — útil para /api/info.
    * empresa_id=str: restringe contagens e categorias a essa empresa (progresso do job).
    """
    from database.models import FichaTecnica, Ingrediente

    ekey = _cache_key(empresa_id)
    now = time.time()
    if ekey in _cache:
        ts, payload = _cache[ekey]
        if (now - ts) < TTL_SECONDS and payload.get("ok"):
            return {**payload, "cached": True}

    db = _get_session()
    if not db:
        return {
            "ok": False,
            "error": "Sessão de banco indisponível",
            "total_fichas": 0,
            "total_ingredientes": 0,
            "categorias": {},
        }

    try:
        qf = db.query(FichaTecnica).filter(FichaTecnica.ativo == True)  # noqa: E712
        if empresa_id:
            qf = qf.filter(FichaTecnica.empresa_id == str(empresa_id))

        total_fichas = qf.count()

        rows: List[Tuple[Any, int]] = (
            db.query(FichaTecnica.categoria, func.count(FichaTecnica.id))
            .filter(FichaTecnica.ativo == True)  # noqa: E712
        )
        if empresa_id:
            rows = rows.filter(FichaTecnica.empresa_id == str(empresa_id))
        rows = rows.group_by(FichaTecnica.categoria).all()
        categorias: Dict[str, int] = {str(r[0]): int(r[1]) for r in rows if r[0]}

        qi = db.query(Ingrediente).filter(Ingrediente.ativo == True)  # noqa: E712
        if empresa_id:
            qi = qi.filter(
                (Ingrediente.empresa_id == str(empresa_id)) | (Ingrediente.empresa_id.is_(None))
            )
        total_ing = qi.count()

        out = {
            "ok": True,
            "total_fichas": int(total_fichas),
            "total_pratos": int(total_fichas),
            "total_ingredientes": int(total_ing),
            "categorias": dict(sorted(categorias.items(), key=lambda x: -x[1])),
            "cached": False,
        }
        _cache[ekey] = (now, {k: v for k, v in out.items() if k != "cached"})
        return out
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "total_fichas": 0,
            "total_pratos": 0,
            "total_ingredientes": 0,
            "categorias": {},
        }
    finally:
        db.close()


def format_fichas_mensagem(
    stats: Optional[Dict[str, Any]] = None,
    empresa_id: Optional[str] = None,
) -> str:
    """Mensagem curta para o progresso do job (DB)."""
    if not stats or not stats.get("ok"):
        stats = get_fichas_db_stats(empresa_id=empresa_id)
    n = int(stats.get("total_fichas", stats.get("total_pratos", 0) or 0))
    ing = int(stats.get("total_ingredientes", 0) or 0)
    return f"📊 Base em SQL: {n} ficha(s) técnica(s) ativa(s), {ing} ingrediente(s) (empresa alvo: {empresa_id or 'todas'})."

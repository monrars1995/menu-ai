"""
Helpers para sincronização resiliente da base de conhecimento.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Any, Callable


logger = logging.getLogger(__name__)


def sync_knowledge_safe(sync_fn: Callable[..., Any], *args, **kwargs) -> None:
    try:
        sync_fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao sincronizar base vetorial: %s", exc)


def should_sync_knowledge_on_generation() -> bool:
    raw = (os.getenv("MENUAI_SYNC_KNOWLEDGE_ON_GENERATION") or "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def sync_cardapio_document_async(cardapio_id: str) -> None:
    """Sincroniza cardápio na base vetorial em background, fora do caminho crítico."""
    if not cardapio_id or not should_sync_knowledge_on_generation():
        return

    def _worker(cid: str) -> None:
        try:
            from database.connection import SessionLocal
            from database.models import Cardapio
            from services.knowledge_base import sync_cardapio_document

            db = SessionLocal()
            try:
                cardapio = db.query(Cardapio).filter(Cardapio.id == cid).first()
                if not cardapio:
                    return
                sync_knowledge_safe(sync_cardapio_document, db, cardapio)
                db.commit()
            finally:
                db.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falha ao sincronizar cardápio em background (%s): %s", cid, exc)

    threading.Thread(
        target=_worker,
        args=(cardapio_id,),
        name=f"kb-sync-cardapio-{cardapio_id[:8]}",
        daemon=True,
    ).start()

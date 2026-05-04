"""
Helpers para sincronização resiliente da base de conhecimento.
"""
from __future__ import annotations

import logging
from typing import Any, Callable


logger = logging.getLogger(__name__)


def sync_knowledge_safe(sync_fn: Callable[..., Any], *args, **kwargs) -> None:
    try:
        sync_fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Falha ao sincronizar base vetorial: %s", exc)

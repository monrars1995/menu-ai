"""
Compatibilidade: importações antigas a `get_receitas_stats` / `format_pratos_mensagem`.
A fonte de verdade é o SQL (`services.fichas_db_stats`); o parâmetro `xlsx_path` é ignorado.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from services.fichas_db_stats import format_fichas_mensagem, get_fichas_db_stats


def get_receitas_stats(
    xlsx_path: Path,  # noqa: ARG001 — legado, ignorado
    sheet: str = "GRUPO DE PRATOS",  # noqa: ARG001
) -> Dict[str, Any]:
    return get_fichas_db_stats(empresa_id=None)


def format_pratos_mensagem(
    stats: Optional[Dict[str, Any]] = None,
    xlsx_path: Optional[Path] = None,  # noqa: ARG001
) -> str:
    return format_fichas_mensagem(stats, empresa_id=None)

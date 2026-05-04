"""
Catálogo OpenRouter (Menu.AI): ids estáveis API/UI → slug provider/model + string LiteLLM.

Slugs base: páginas oficiais OpenRouter.
Overrides opcionais via .env se o catálogo mudar.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Optional, Set

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Id interno usado em POST /api/gerar e na UI (valor default)
DEFAULT_LLM_MODEL_ID = "queen-3.6"

# Chaves de env para override do slug OpenRouter (provider/model, sem prefixo openrouter/)
_ENV_SLUG_QUEEN = "OPENROUTER_SLUG_QUEEN_36"
_ENV_SLUG_GLM = "OPENROUTER_SLUG_GLM_51"
_ENV_SLUG_KIMI = "OPENROUTER_SLUG_KIMI_K25"


@dataclass(frozen=True)
class OpenRouterModelEntry:
    id: str
    label: str
    slug_default: str  # provider/model
    description: str


_CATALOG: tuple[OpenRouterModelEntry, ...] = (
    OpenRouterModelEntry(
        id="queen-3.6",
        label="Queen 3.6 (Qwen3.6 Plus)",
        slug_default="qwen/qwen3.6-plus",
        description="Qwen3.6 Plus via OpenRouter; foco em coding, raciocínio e uso geral.",
    ),
    OpenRouterModelEntry(
        id="glm-5-1",
        label="GLM 5.1",
        slug_default="z-ai/glm-5.1",
        description="GLM 5.1 via OpenRouter; forte em tarefas long-horizon e automação de engenharia.",
    ),
    OpenRouterModelEntry(
        id="kimi-k2.5",
        label="Kimi K2.5",
        slug_default="moonshotai/kimi-k2.5",
        description="Kimi K2.5 via OpenRouter; multimodal e agentic, bom para coding e tool calling.",
    ),
)

_ID_TO_ENTRY: Dict[str, OpenRouterModelEntry] = {e.id: e for e in _CATALOG}


def allowed_llm_model_ids() -> List[str]:
    return [e.id for e in _CATALOG]


def get_catalog_entries() -> List[OpenRouterModelEntry]:
    return list(_CATALOG)


def entry_for_id(model_id: Optional[str]) -> OpenRouterModelEntry:
    mid = (model_id or "").strip() or effective_default_model_id()
    entry = _ID_TO_ENTRY.get(mid)
    if entry is None:
        raise ValueError(
            f"llm_model inválido: {mid!r}. Use um de: {allowed_llm_model_ids()}"
        )
    return entry


def _enabled_ids_from_db(db: "Session") -> Set[str]:
    """Ids do catálogo que estão activos na BD. Falha → todos activos."""
    try:
        from database.models import LlmModelConfig

        rows = db.query(LlmModelConfig).all()
        if not rows:
            return {e.id for e in _CATALOG}
        disabled = {r.model_id for r in rows if not r.enabled}
        return {e.id for e in _CATALOG if e.id not in disabled}
    except Exception:
        return {e.id for e in _CATALOG}


def _enabled_map_from_db(db: "Session") -> Dict[str, bool]:
    """model_id → enabled; entrada em falta no catálogo ignorada."""
    try:
        from database.models import LlmModelConfig

        rows = {r.model_id: r.enabled for r in db.query(LlmModelConfig).all()}
        return {e.id: rows.get(e.id, True) for e in _CATALOG}
    except Exception:
        return {e.id: True for e in _CATALOG}


def is_llm_model_enabled_in_db(db: "Session", model_id: str) -> bool:
    mid = (model_id or "").strip() or effective_default_model_id()
    return _enabled_map_from_db(db).get(mid, True)


def assert_llm_model_allowed_for_generation(db: "Session", model_id: Optional[str]) -> None:
    """Lança HTTPException 400 se o modelo estiver desactivado (com BD aplicada)."""
    from fastapi import HTTPException

    mid = (model_id or "").strip() or effective_default_model_id()
    if mid not in _ID_TO_ENTRY:
        return
    if not is_llm_model_enabled_in_db(db, mid):
        raise HTTPException(
            status_code=400,
            detail=f"Modelo LLM desactivado pelo administrador: {mid}",
        )


def _slug_for_entry(entry: OpenRouterModelEntry) -> str:
    if entry.id == "queen-3.6":
        return (os.getenv(_ENV_SLUG_QUEEN) or "").strip() or entry.slug_default
    if entry.id == "glm-5-1":
        return (os.getenv(_ENV_SLUG_GLM) or "").strip() or entry.slug_default
    if entry.id == "kimi-k2.5":
        return (os.getenv(_ENV_SLUG_KIMI) or "").strip() or entry.slug_default
    return entry.slug_default


def openrouter_slug_for_id(model_id: Optional[str]) -> str:
    """Resolve id interno → slug OpenRouter (provider/model)."""
    entry = entry_for_id(model_id)
    return _slug_for_entry(entry)


def litellm_model_string_for_id(model_id: Optional[str]) -> str:
    """Id interno → argumento `model` do LiteLLM (prefixo openrouter/)."""
    slug = openrouter_slug_for_id(model_id)
    return f"openrouter/{slug}"


def label_for_id(model_id: Optional[str]) -> str:
    return entry_for_id(model_id).label


def description_for_id(model_id: Optional[str]) -> str:
    return entry_for_id(model_id).description


def effective_default_model_id() -> str:
    """Default para POST/UI quando `llm_model` está ausente."""
    return (os.getenv("OPENROUTER_DEFAULT_MODEL") or "").strip() or DEFAULT_LLM_MODEL_ID


def effective_default_model_id_resolved(db: Optional["Session"]) -> str:
    """Default efectivo: primeiro id activo na BD se o default env estiver desactivado."""
    base = effective_default_model_id()
    if db is None:
        return base
    m = _enabled_map_from_db(db)
    if m.get(base, True):
        return base
    for e in _CATALOG:
        if m.get(e.id, True):
            return e.id
    return base


def api_models_payload(
    db: Optional["Session"] = None,
    *,
    only_enabled: bool = True,
    include_enabled_flag: bool = False,
) -> dict:
    """
    Resposta JSON para GET /api/llm-models (e admin).

    - only_enabled: quando há BD, lista só modelos activos (UI pública).
    - include_enabled_flag: inclui chave `enabled` por modelo (consola admin).
    """
    default_id = effective_default_model_id_resolved(db)

    if db is None:
        models = [
            {
                "id": e.id,
                "label": e.label,
                "slug": _slug_for_entry(e),
                "description": e.description,
            }
            for e in _CATALOG
        ]
        if include_enabled_flag:
            models = [{**m, "enabled": True} for m in models]
    else:
        emap = _enabled_map_from_db(db)
        models = []
        for e in _CATALOG:
            en = emap.get(e.id, True)
            if only_enabled and not en:
                continue
            item = {
                "id": e.id,
                "label": e.label,
                "slug": _slug_for_entry(e),
                "description": e.description,
            }
            if include_enabled_flag:
                item["enabled"] = en
            models.append(item)

    return {
        "provider": "openrouter",
        "default": default_id,
        "models": models,
    }

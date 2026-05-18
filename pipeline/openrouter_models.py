"""
Catálogo de Modelos LLM (Menu.AI).

Delega para o sistema em llm_providers.py e mantém compatibilidade
com imports legados do projeto.

Modelos suportados:
- openai-gpt-5.5
- gemini-3.1-pro-preview
- gemini-3-flash-preview
- gemini-3.1-flash-lite
- kimi-k2.6
- queen-3.6
- glm-5-1
- kimi-k2.5
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Dict, List, Optional, Set

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Importa do novo sistema
from pipeline.llm_providers import (
    _ID_TO_ENTRY,
    allowed_llm_model_ids as _allowed_ids,
    api_models_payload as _api_payload,
    get_default_model_id as _default_id,
    get_effective_default_model_id as _effective_default_id,
    get_generation_model_ids as _generation_ids,
    get_model_entry as _get_entry,
    get_model_label as _get_label,
    get_model_string as _get_string,
    get_review_model_ids as _review_ids,
    is_review_capable as _is_review_capable,
    resolve_model_config as _resolve_config,
)


# ============================================================
# COMPATIBILIDADE COM CÓDIGO LEGADO
# ============================================================

# Constante legada
DEFAULT_LLM_MODEL_ID = "openai-gpt-5.5"

# Variáveis de env para override (mantidas para compatibilidade)
_ENV_SLUG_QUEEN = "OPENROUTER_SLUG_QUEEN_36"
_ENV_SLUG_GLM = "OPENROUTER_SLUG_GLM_51"
_ENV_SLUG_KIMI = "OPENROUTER_SLUG_KIMI_K25"


# ============================================================
# FUNÇÕES DE COMPATIBILIDADE
# ============================================================

def allowed_llm_model_ids() -> List[str]:
    """IDs de modelos permitidos (provedores habilitados)."""
    return _allowed_ids()


def generation_llm_model_ids() -> List[str]:
    """IDs de modelos disponíveis para geração."""
    return _generation_ids()


def review_llm_model_ids() -> List[str]:
    """IDs de modelos disponíveis para revisão consultiva (somente OpenRouter)."""
    return _review_ids()


def effective_default_model_id() -> str:
    """Default para POST/UI quando `llm_model` está ausente."""
    return _effective_default_id()


def effective_default_model_id_resolved(db: Optional["Session"]) -> str:
    """Default efectivo: primeiro id activo na BD se o default env estiver desactivado."""
    base = effective_default_model_id()
    if db is None:
        return base
    
    try:
        from database.models import LlmModelConfig
        rows = {r.model_id: r.enabled for r in db.query(LlmModelConfig).all()}
        if rows.get(base, True):
            return base
        # Procura primeiro ativo
        for mid in allowed_llm_model_ids():
            if rows.get(mid, True):
                return mid
    except Exception:
        pass
    
    return base


def litellm_model_string_for_id(model_id: Optional[str]) -> str:
    """Id interno → argumento `model` do LiteLLM."""
    return _get_string(model_id)


def label_for_id(model_id: Optional[str]) -> str:
    """Label amigável do modelo."""
    return _get_label(model_id)


def description_for_id(model_id: Optional[str]) -> str:
    """Descrição do modelo."""
    return _get_entry(model_id).description


def entry_for_id(model_id: Optional[str]):
    """Retorna entrada do catálogo (compatibilidade)."""
    return _get_entry(model_id)


def openrouter_slug_for_id(model_id: Optional[str]) -> str:
    """Resolve id interno → slug OpenRouter (provider/model)."""
    entry = _get_entry(model_id)
    if entry.provider == "openrouter":
        # Remove prefixo "openrouter/"
        ms = entry.model_string
        if ms.startswith("openrouter/"):
            return ms[11:]
        return ms
    # Para outros provedores, retorna string do modelo
    return entry.model_string


# ============================================================
# CATÁLOGO (compatibilidade)
# ============================================================

class OpenRouterModelEntry:
    """Classe compatível com código legado."""
    def __init__(self, id: str, label: str, slug_default: str, description: str):
        self.id = id
        self.label = label
        self.slug_default = slug_default
        self.description = description


def get_catalog_entries() -> List[OpenRouterModelEntry]:
    """Retorna entradas do catálogo (formato legado)."""
    entries = []
    for mid in allowed_llm_model_ids():
        try:
            entry = _get_entry(mid)
            entries.append(OpenRouterModelEntry(
                id=entry.id,
                label=entry.label,
                slug_default=openrouter_slug_for_id(mid),
                description=entry.description,
            ))
        except Exception:
            continue
    return entries


# ============================================================
# VALIDAÇÃO DE BANCO
# ============================================================

def _enabled_ids_from_db(db: "Session") -> Set[str]:
    """Ids do catálogo que estão activos na BD. Falha → todos activos."""
    try:
        from database.models import LlmModelConfig
        rows = db.query(LlmModelConfig).all()
        if not rows:
            return set(allowed_llm_model_ids())
        disabled = {r.model_id for r in rows if not r.enabled}
        return {mid for mid in allowed_llm_model_ids() if mid not in disabled}
    except Exception:
        return set(allowed_llm_model_ids())


def _enabled_map_from_db(db: "Session") -> Dict[str, bool]:
    """model_id → enabled; entrada em falta no catálogo ignorada."""
    try:
        from database.models import LlmModelConfig
        rows = {r.model_id: r.enabled for r in db.query(LlmModelConfig).all()}
        return {mid: rows.get(mid, True) for mid in allowed_llm_model_ids()}
    except Exception:
        return {mid: True for mid in allowed_llm_model_ids()}


def is_llm_model_enabled_in_db(db: "Session", model_id: str) -> bool:
    mid = (model_id or "").strip() or effective_default_model_id()
    return _enabled_map_from_db(db).get(mid, True)


def assert_llm_model_allowed_for_generation(db: "Session", model_id: Optional[str]) -> None:
    """Lança HTTPException 400 se o modelo estiver desactivado."""
    from fastapi import HTTPException
    
    mid = (model_id or "").strip() or effective_default_model_id()
    if mid not in _ID_TO_ENTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Modelo LLM inválido: {mid}. Use um de: {list(_ID_TO_ENTRY.keys())}",
        )
    # Valida também disponibilidade do provedor/chave antes de enfileirar o job.
    # Sem isso, a falha só aparecia de forma tardia no worker assíncrono.
    try:
        _resolve_config(mid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not is_llm_model_enabled_in_db(db, mid):
        raise HTTPException(
            status_code=400,
            detail=f"Modelo LLM desactivado pelo administrador: {mid}",
        )


def assert_llm_model_allowed_for_review(db: "Session", model_id: Optional[str]) -> None:
    """Reviewer deve ser sempre OpenRouter e estar habilitado."""
    from fastapi import HTTPException

    mid = (model_id or "").strip()
    if not mid:
        return
    if mid not in _ID_TO_ENTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Modelo reviewer inválido: {mid}. Use um de: {list(_ID_TO_ENTRY.keys())}",
        )
    if not _is_review_capable(mid):
        raise HTTPException(
            status_code=400,
            detail=f"Modelo reviewer inválido para revisão consultiva: {mid}. Escolha um modelo OpenRouter habilitado.",
        )
    try:
        _resolve_config(mid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not is_llm_model_enabled_in_db(db, mid):
        raise HTTPException(
            status_code=400,
            detail=f"Modelo reviewer desactivado pelo administrador: {mid}",
        )


# ============================================================
# API PAYLOAD
# ============================================================

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
    
    # Usa o novo sistema
    payload = _api_payload()
    payload["default"] = default_id
    
    if db is None:
        models = payload.get("models", [])
        models = [{**m, "enabled": True} for m in models]
        payload["models"] = models
        payload["generation_models"] = [{**m, "enabled": True} for m in payload.get("generation_models", [])]
        payload["review_models"] = [{**m, "enabled": True} for m in payload.get("review_models", [])]
    else:
        emap = _enabled_map_from_db(db)
        models = []
        for m in payload.get("models", []):
            mid = m.get("id", "")
            en = emap.get(mid, True)
            if only_enabled and not en:
                continue
            item = dict(m)
            item["enabled"] = en
            models.append(item)
        payload["models"] = models
        generation_models = []
        for m in payload.get("generation_models", []):
            mid = m.get("id", "")
            en = emap.get(mid, True)
            if only_enabled and not en:
                continue
            item = dict(m)
            item["enabled"] = en
            generation_models.append(item)
        payload["generation_models"] = generation_models
        review_models = []
        for m in payload.get("review_models", []):
            mid = m.get("id", "")
            en = emap.get(mid, True)
            if only_enabled and not en:
                continue
            item = dict(m)
            item["enabled"] = en
            review_models.append(item)
        payload["review_models"] = review_models
    
    # Adiciona campos legados para compatibilidade
    payload["provider"] = "multi"
    
    return payload

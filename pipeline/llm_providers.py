"""
Menu.AI — Catálogo LLM centralizado em OpenRouter.

Modelos suportados:
- queen-3.6
- glm-5-1
- kimi-k2.5
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    default_model: str = ""
    models: List[str] = field(default_factory=list)
    extra_headers: Optional[Dict[str, str]] = None
    enabled: bool = True


@dataclass(frozen=True)
class ModelEntry:
    id: str
    label: str
    provider: str
    model_string: str
    description: str = ""
    is_default: bool = False


@dataclass
class ResolvedModelConfig:
    model_id: str
    model_label: str
    model_string: str
    provider: str
    api_key: Optional[str]
    api_base: Optional[str]
    extra_headers: Optional[Dict[str, str]] = None


OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"


def _openrouter_extra_headers() -> Dict[str, str]:
    headers: Dict[str, str] = {}
    ref = (os.getenv("OPENROUTER_HTTP_REFERER") or "").strip()
    title = (os.getenv("OPENROUTER_APP_TITLE") or os.getenv("MENUAI_APP_TITLE") or "Menu.AI").strip()
    if ref:
        headers["HTTP-Referer"] = ref
    if title:
        headers["X-OpenRouter-Title"] = title
    return headers


def _get_openrouter_config() -> ProviderConfig:
    api_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    headers = _openrouter_extra_headers()
    return ProviderConfig(
        name="openrouter",
        api_key=api_key or None,
        api_base=OPENROUTER_API_BASE,
        default_model="queen-3.6",
        models=["queen-3.6", "glm-5-1", "kimi-k2.5"],
        extra_headers=headers if headers else None,
        enabled=bool(api_key),
    )


_CATALOG: tuple[ModelEntry, ...] = (
    ModelEntry(
        id="queen-3.6",
        label="Queen 3.6",
        provider="openrouter",
        model_string="openrouter/qwen/qwen3.6-plus",
        description="Modelo principal via OpenRouter para geração de cardápio.",
        is_default=True,
    ),
    ModelEntry(
        id="glm-5-1",
        label="GLM 5.1",
        provider="openrouter",
        model_string="openrouter/z-ai/glm-5.1",
        description="Alternativa para raciocínio e custo via OpenRouter.",
    ),
    ModelEntry(
        id="kimi-k2.5",
        label="Kimi K2.5",
        provider="openrouter",
        model_string="openrouter/moonshotai/kimi-k2.5",
        description="Alternativa para tarefas longas e execução robusta via OpenRouter.",
    ),
)

_ID_TO_ENTRY: Dict[str, ModelEntry] = {e.id: e for e in _CATALOG}
_PROVIDER_CONFIGS: Dict[str, ProviderConfig] = {}


def _load_provider_configs() -> Dict[str, ProviderConfig]:
    global _PROVIDER_CONFIGS
    if not _PROVIDER_CONFIGS:
        _PROVIDER_CONFIGS = {"openrouter": _get_openrouter_config()}
    return _PROVIDER_CONFIGS


def get_provider_config(provider: str) -> Optional[ProviderConfig]:
    return _load_provider_configs().get(provider)


def get_all_providers() -> Dict[str, ProviderConfig]:
    return _load_provider_configs()


def get_enabled_providers() -> Dict[str, ProviderConfig]:
    return {k: v for k, v in _load_provider_configs().items() if v.enabled}


def get_default_provider() -> str:
    return "openrouter"


def get_default_model_id() -> str:
    # Prioriza variável nova; mantém compatibilidade com legado.
    env_default = (
        os.getenv("OPENROUTER_DEFAULT_MODEL")
        or os.getenv("DEFAULT_LLM_MODEL")
        or ""
    ).strip()
    if env_default in _ID_TO_ENTRY:
        return env_default
    return "queen-3.6"


def get_model_entry(model_id: Optional[str]) -> ModelEntry:
    mid = (model_id or "").strip() or get_default_model_id()
    entry = _ID_TO_ENTRY.get(mid)
    if entry is None:
        raise ValueError(
            f"Modelo LLM inválido: {mid!r}. "
            f"Use um de: {list(_ID_TO_ENTRY.keys())}"
        )
    return entry


def get_model_string(model_id: Optional[str]) -> str:
    return get_model_entry(model_id).model_string


def get_model_provider(model_id: Optional[str]) -> str:
    return get_model_entry(model_id).provider


def get_model_label(model_id: Optional[str]) -> str:
    return get_model_entry(model_id).label


def resolve_model_config(model_id: Optional[str]) -> ResolvedModelConfig:
    entry = get_model_entry(model_id)
    provider_cfg = get_provider_config(entry.provider)
    if not provider_cfg:
        raise ValueError(f"Provedor não configurado: {entry.provider}")
    if not provider_cfg.enabled:
        raise ValueError(
            "OPENROUTER_API_KEY não configurada. "
            "Defina a chave para habilitar a geração."
        )
    return ResolvedModelConfig(
        model_id=entry.id,
        model_label=entry.label,
        model_string=entry.model_string,
        provider=entry.provider,
        api_key=provider_cfg.api_key,
        api_base=provider_cfg.api_base,
        extra_headers=provider_cfg.extra_headers,
    )


_FALLBACK_CHAINS: Dict[str, List[str]] = {
    "queen-3.6": ["glm-5-1", "kimi-k2.5"],
    "glm-5-1": ["queen-3.6", "kimi-k2.5"],
    "kimi-k2.5": ["queen-3.6", "glm-5-1"],
}


def get_fallback_chain(model_id: Optional[str]) -> List[str]:
    mid = (model_id or "").strip() or get_default_model_id()
    return _FALLBACK_CHAINS.get(mid, [])


def api_models_payload() -> dict:
    providers = get_enabled_providers()
    default_id = get_default_model_id()
    models = []
    for entry in _CATALOG:
        if entry.provider not in providers:
            continue
        models.append(
            {
                "id": entry.id,
                "label": entry.label,
                "provider": entry.provider,
                "model_string": entry.model_string,
                "description": entry.description,
            }
        )
    return {
        "default": default_id,
        "default_provider": "openrouter",
        "providers": list(providers.keys()),
        "models": models,
    }


def allowed_llm_model_ids() -> List[str]:
    providers = get_enabled_providers()
    return [e.id for e in _CATALOG if e.provider in providers]


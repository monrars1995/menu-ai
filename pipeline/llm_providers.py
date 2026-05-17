"""
Menu.AI — catálogo LLM centralizado.

Provedores suportados:
- OpenAI
- Gemini
- OpenRouter
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
    missing_env_message: str = ""


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
DEFAULT_LLM_MODEL_ID = "openai-gpt-5.5"


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
        missing_env_message="OPENROUTER_API_KEY não configurada.",
    )


def _get_openai_config() -> ProviderConfig:
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    return ProviderConfig(
        name="openai",
        api_key=api_key or None,
        default_model="openai-gpt-5.5",
        models=["openai-gpt-5.5"],
        enabled=bool(api_key),
        missing_env_message="OPENAI_API_KEY não configurada.",
    )


def _get_gemini_config() -> ProviderConfig:
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    return ProviderConfig(
        name="gemini",
        api_key=api_key or None,
        default_model="gemini-3.1-pro-preview",
        models=["gemini-3.1-pro-preview", "gemini-3-flash-preview", "gemini-3.1-flash-lite"],
        enabled=bool(api_key),
        missing_env_message="GEMINI_API_KEY ou GOOGLE_API_KEY não configurada.",
    )


_CATALOG: tuple[ModelEntry, ...] = (
    ModelEntry(
        id="openai-gpt-5.5",
        label="GPT-5.5",
        provider="openai",
        model_string="openai/gpt-5.5",
        description="Modelo OpenAI principal para máxima qualidade de geração.",
        is_default=True,
    ),
    ModelEntry(
        id="gemini-3.1-pro-preview",
        label="Gemini 3.1 Pro Preview",
        provider="gemini",
        model_string="gemini/gemini-3.1-pro-preview",
        description="Modelo Gemini avançado em preview para raciocínio e tarefas complexas.",
    ),
    ModelEntry(
        id="gemini-3-flash-preview",
        label="Gemini 3 Flash Preview",
        provider="gemini",
        model_string="gemini/gemini-3-flash-preview",
        description="Modelo Gemini preview otimizado para velocidade e custo.",
    ),
    ModelEntry(
        id="gemini-3.1-flash-lite",
        label="Gemini 3.1 Flash-Lite",
        provider="gemini",
        model_string="gemini/gemini-3.1-flash-lite",
        description="Modelo Gemini estável de menor custo para tarefas leves.",
    ),
    ModelEntry(
        id="queen-3.6",
        label="Queen 3.6",
        provider="openrouter",
        model_string="openrouter/qwen/qwen3.6-plus",
        description="Modelo Qwen via OpenRouter para geração de cardápio.",
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
        _PROVIDER_CONFIGS = {
            "openai": _get_openai_config(),
            "gemini": _get_gemini_config(),
            "openrouter": _get_openrouter_config(),
        }
    return _PROVIDER_CONFIGS


def get_provider_config(provider: str) -> Optional[ProviderConfig]:
    return _load_provider_configs().get(provider)


def get_all_providers() -> Dict[str, ProviderConfig]:
    return _load_provider_configs()


def get_enabled_providers() -> Dict[str, ProviderConfig]:
    return {k: v for k, v in _load_provider_configs().items() if v.enabled}


def get_default_provider() -> str:
    return get_model_provider(get_default_model_id())


def get_default_model_id() -> str:
    # Prioriza variável nova; mantém compatibilidade com defaults legados.
    env_default = (
        os.getenv("MENUAI_DEFAULT_LLM_MODEL")
        or os.getenv("OPENROUTER_DEFAULT_MODEL")
        or os.getenv("DEFAULT_LLM_MODEL")
        or ""
    ).strip()
    if env_default in _ID_TO_ENTRY:
        return env_default
    return DEFAULT_LLM_MODEL_ID


def get_effective_default_model_id() -> str:
    """Default que está realmente disponível com as chaves configuradas."""
    configured = get_default_model_id()
    entry = _ID_TO_ENTRY.get(configured)
    providers = get_enabled_providers()
    if entry and entry.provider in providers:
        return configured
    for candidate in _CATALOG:
        if candidate.provider in providers:
            return candidate.id
    return configured


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
        raise ValueError(f"{provider_cfg.missing_env_message} Defina a chave para habilitar {entry.label}.")
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
    "openai-gpt-5.5": ["gemini-3.1-pro-preview", "queen-3.6", "gemini-3-flash-preview"],
    "gemini-3.1-pro-preview": ["openai-gpt-5.5", "queen-3.6", "gemini-3-flash-preview"],
    "gemini-3-flash-preview": ["openai-gpt-5.5", "gemini-3.1-pro-preview", "queen-3.6"],
    "gemini-3.1-flash-lite": ["gemini-3-flash-preview", "openai-gpt-5.5", "queen-3.6"],
    "queen-3.6": ["openai-gpt-5.5", "gemini-3.1-pro-preview", "glm-5-1"],
    "glm-5-1": ["openai-gpt-5.5", "queen-3.6", "gemini-3.1-pro-preview"],
    "kimi-k2.5": ["openai-gpt-5.5", "queen-3.6", "gemini-3.1-pro-preview"],
}


def get_fallback_chain(model_id: Optional[str]) -> List[str]:
    mid = (model_id or "").strip() or get_default_model_id()
    providers = get_enabled_providers()
    out: List[str] = []
    for candidate in _FALLBACK_CHAINS.get(mid, []):
        entry = _ID_TO_ENTRY.get(candidate)
        if entry and entry.provider in providers:
            out.append(candidate)
    return out


def api_models_payload() -> dict:
    providers = get_enabled_providers()
    default_id = get_effective_default_model_id()
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
        "default_provider": get_model_provider(default_id) if default_id in _ID_TO_ENTRY else "",
        "providers": list(providers.keys()),
        "models": models,
    }


def allowed_llm_model_ids() -> List[str]:
    providers = get_enabled_providers()
    return [e.id for e in _CATALOG if e.provider in providers]

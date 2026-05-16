"""
Menu.AI — Sistema de Múltiplos Provedores LLM

Suporta:
- OpenAI (nativo) — GPT-4.1, GPT-5.5, etc
- Google Gemini — gemini-2.5-pro, gemini-3.1, etc
- OpenRouter (via LiteLLM) — queen-3.6, glm-5-1, kimi-k2.5

OpenAI é o provedor PRIMÁRIO por padrão.
Gemini 3.1 é o FALLBACK padrão.
OpenRouter é mantido para compatibilidade.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass(frozen=True)
class ProviderConfig:
    """Configuração de um provedor LLM."""
    name: str  # openai, gemini, openrouter
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    default_model: str = ""
    models: List[str] = field(default_factory=list)
    extra_headers: Optional[Dict[str, str]] = None
    enabled: bool = True


@dataclass(frozen=True)
class ModelEntry:
    """Entrada no catálogo de modelos."""
    id: str  # ID interno (ex: gpt-4.1, gemini-3.1)
    label: str  # Label exibido na UI
    provider: str  # openai, gemini, openrouter
    model_string: str  # String passada ao LiteLLM/SDK
    description: str = ""
    is_default: bool = False


# ============================================================
# CONFIGURAÇÃO DOS PROVEDORES
# ============================================================

def _get_openai_config() -> ProviderConfig:
    """Configuração do provedor OpenAI (nativo)."""
    api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    return ProviderConfig(
        name="openai",
        api_key=api_key or None,
        api_base=(os.getenv("OPENAI_API_BASE") or "https://api.openai.com/v1").strip(),
        default_model="gpt-4.1",
        models=[
            "gpt-5.5",
            "gpt-5",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "gpt-4o",
            "gpt-4o-mini",
        ],
        enabled=bool(api_key),
    )


def _get_gemini_config() -> ProviderConfig:
    """Configuração do provedor Google Gemini."""
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    # Também aceita GOOGLE_API_KEY para compatibilidade
    if not api_key:
        api_key = (os.getenv("GOOGLE_API_KEY") or "").strip()
    
    return ProviderConfig(
        name="gemini",
        api_key=api_key or None,
        api_base=(os.getenv("GEMINI_API_BASE") or "https://generativelanguage.googleapis.com/v1beta").strip(),
        default_model="gemini-2.5-pro",
        models=[
            "gemini-3.1",
            "gemini-3.1-pro",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-pro",
            "gemini-2.0-flash",
        ],
        enabled=bool(api_key),
    )


def _get_openrouter_config() -> ProviderConfig:
    """Configuração do provedor OpenRouter (via LiteLLM)."""
    api_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    
    # Headers opcionais recomendados pela OpenRouter
    extra_headers: Dict[str, str] = {}
    ref = (os.getenv("OPENROUTER_HTTP_REFERER") or "").strip()
    title = (os.getenv("OPENROUTER_APP_TITLE") or os.getenv("MENUAI_APP_TITLE") or "Menu.AI").strip()
    if ref:
        extra_headers["HTTP-Referer"] = ref
    if title:
        extra_headers["X-OpenRouter-Title"] = title
    
    return ProviderConfig(
        name="openrouter",
        api_key=api_key or None,
        api_base="https://openrouter.ai/api/v1",
        default_model="queen-3.6",
        models=[
            "queen-3.6",
            "glm-5-1",
            "kimi-k2.5",
        ],
        extra_headers=extra_headers if extra_headers else None,
        enabled=bool(api_key),
    )


# ============================================================
# CATÁLOGO DE MODELOS
# ============================================================

_CATALOG: tuple[ModelEntry, ...] = (
    # OPENAI
    ModelEntry(
        id="gpt-5.5",
        label="GPT-5.5",
        provider="openai",
        model_string="gpt-5.5",
        description="Modelo mais avançado da OpenAI. Excelente para geração de cardápios complexos e multimodal.",
    ),
    ModelEntry(
        id="gpt-5",
        label="GPT-5",
        provider="openai",
        model_string="gpt-5",
        description="GPT-5 com raciocínio avançado. Bom para análise de contratos e regras de negócio.",
    ),
    ModelEntry(
        id="gpt-4.1",
        label="GPT-4.1",
        provider="openai",
        model_string="gpt-4.1",
        description="GPT-4.1 — equilíbrio entre qualidade e custo. Recomendado para produção.",
    ),
    ModelEntry(
        id="gpt-4.1-mini",
        label="GPT-4.1 Mini",
        provider="openai",
        model_string="gpt-4.1-mini",
        description="Versão mais rápida e econômica do GPT-4.1.",
    ),
    ModelEntry(
        id="gpt-4o",
        label="GPT-4o",
        provider="openai",
        model_string="gpt-4o",
        description="GPT-4o — modelo multimodal com bom custo-benefício.",
    ),
    ModelEntry(
        id="gpt-4o-mini",
        label="GPT-4o Mini",
        provider="openai",
        model_string="gpt-4o-mini",
        description="GPT-4o Mini — rápido e econômico para tarefas simples.",
    ),
    # GEMINI
    ModelEntry(
        id="gemini-3.1",
        label="Gemini 3.1",
        provider="gemini",
        model_string="gemini/gemini-3.1-pro-latest",
        description="Gemini 3.1 Pro — modelo mais avançado do Google. Fallback recomendado.",
    ),
    ModelEntry(
        id="gemini-3.1-pro",
        label="Gemini 3.1 Pro",
        provider="gemini",
        model_string="gemini/gemini-3.1-pro-latest",
        description="Gemini 3.1 Pro — versão completa com contexto longo.",
    ),
    ModelEntry(
        id="gemini-2.5-pro",
        label="Gemini 2.5 Pro",
        provider="gemini",
        model_string="gemini/gemini-2.5-pro-latest",
        description="Gemini 2.5 Pro — excelente para coding e reasoning.",
    ),
    ModelEntry(
        id="gemini-2.5-flash",
        label="Gemini 2.5 Flash",
        provider="gemini",
        model_string="gemini/gemini-2.5-flash-latest",
        description="Gemini 2.5 Flash — rápido e econômico.",
    ),
    # OPENROUTER (LEGACY)
    ModelEntry(
        id="queen-3.6",
        label="Queen 3.6 (OpenRouter)",
        provider="openrouter",
        model_string="openrouter/qwen/qwen3.6-plus",
        description="Qwen3.6 Plus via OpenRouter. Mantido para compatibilidade.",
    ),
    ModelEntry(
        id="glm-5-1",
        label="GLM 5.1 (OpenRouter)",
        provider="openrouter",
        model_string="openrouter/z-ai/glm-5.1",
        description="GLM 5.1 via OpenRouter. Mantido para compatibilidade.",
    ),
    ModelEntry(
        id="kimi-k2.5",
        label="Kimi K2.5 (OpenRouter)",
        provider="openrouter",
        model_string="openrouter/moonshotai/kimi-k2.5",
        description="Kimi K2.5 via OpenRouter. Mantido para compatibilidade.",
    ),
)

_ID_TO_ENTRY: Dict[str, ModelEntry] = {e.id: e for e in _CATALOG}
_PROVIDER_CONFIGS: Dict[str, ProviderConfig] = {}


def _load_provider_configs() -> Dict[str, ProviderConfig]:
    """Carrega configurações dos provedores."""
    global _PROVIDER_CONFIGS
    if not _PROVIDER_CONFIGS:
        _PROVIDER_CONFIGS = {
            "openai": _get_openai_config(),
            "gemini": _get_gemini_config(),
            "openrouter": _get_openrouter_config(),
        }
    return _PROVIDER_CONFIGS


def get_provider_config(provider: str) -> Optional[ProviderConfig]:
    """Retorna configuração de um provedor."""
    return _load_provider_configs().get(provider)


def get_all_providers() -> Dict[str, ProviderConfig]:
    """Retorna todos os provedores configurados."""
    return _load_provider_configs()


def get_enabled_providers() -> Dict[str, ProviderConfig]:
    """Retorna apenas provedores habilitados (têm API key)."""
    return {k: v for k, v in _load_provider_configs().items() if v.enabled}


def get_default_provider() -> str:
    """Retorna o provedor padrão (openai se disponível, senão gemini, senão openrouter)."""
    providers = get_enabled_providers()
    
    # Prioridade: OpenAI > Gemini > OpenRouter
    if "openai" in providers:
        return "openai"
    if "gemini" in providers:
        return "gemini"
    if "openrouter" in providers:
        return "openrouter"
    
    return "openrouter"  # fallback final


def get_default_model_id() -> str:
    """Retorna o ID do modelo padrão."""
    # Verifica env override
    env_default = (os.getenv("DEFAULT_LLM_MODEL") or "").strip()
    if env_default and env_default in _ID_TO_ENTRY:
        return env_default
    
    # Verifica provider padrão
    provider = get_default_provider()
    provider_config = get_provider_config(provider)
    if provider_config and provider_config.default_model:
        return provider_config.default_model
    
    return "gpt-4.1"


# ============================================================
# RESOLUÇÃO DE MODELOS
# ============================================================

def get_model_entry(model_id: Optional[str]) -> ModelEntry:
    """Retorna entrada do catálogo pelo ID."""
    mid = (model_id or "").strip() or get_default_model_id()
    entry = _ID_TO_ENTRY.get(mid)
    if entry is None:
        raise ValueError(
            f"Modelo LLM inválido: {mid!r}. "
            f"Use um de: {list(_ID_TO_ENTRY.keys())}"
        )
    return entry


def get_model_string(model_id: Optional[str]) -> str:
    """Retorna a string do modelo para LiteLLM/SDK."""
    return get_model_entry(model_id).model_string


def get_model_provider(model_id: Optional[str]) -> str:
    """Retorna o provedor de um modelo."""
    return get_model_entry(model_id).provider


def get_model_label(model_id: Optional[str]) -> str:
    """Retorna o label de um modelo."""
    return get_model_entry(model_id).label


def resolve_model_config(model_id: Optional[str]) -> "ResolvedModelConfig":
    """Resolve modelo completo: entry + provider config."""
    entry = get_model_entry(model_id)
    provider_cfg = get_provider_config(entry.provider)
    
    if not provider_cfg:
        raise ValueError(f"Provedor não configurado: {entry.provider}")
    
    if not provider_cfg.enabled:
        raise ValueError(
            f"Provedor {entry.provider} não habilitado. "
            f"Configure a API key no .env"
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


@dataclass
class ResolvedModelConfig:
    """Configuração resolvida de um modelo para chamada LLM."""
    model_id: str
    model_label: str
    model_string: str
    provider: str
    api_key: Optional[str]
    api_base: Optional[str]
    extra_headers: Optional[Dict[str, str]] = None


# ============================================================
# FALLBACK CHAINS
# ============================================================

# Cadeias de fallback: model_id → lista de model_ids de fallback
# Se o modelo primário falha, tenta o próximo na lista
_FALLBACK_CHAINS: Dict[str, List[str]] = {
    # OpenAI → Gemini fallback
    "gpt-5.5": ["gemini-3.1", "gpt-5", "gemini-2.5-pro"],
    "gpt-5": ["gemini-3.1", "gpt-4.1", "gemini-2.5-pro"],
    "gpt-4.1": ["gemini-3.1", "gpt-4o", "gemini-2.5-pro"],
    "gpt-4.1-mini": ["gemini-2.5-flash", "gpt-4o-mini", "gemini-2.5-pro"],
    "gpt-4o": ["gemini-2.5-pro", "gpt-4.1", "gemini-3.1"],
    "gpt-4o-mini": ["gemini-2.5-flash", "gpt-4.1-mini", "gemini-2.5-pro"],
    # Gemini → OpenAI fallback
    "gemini-3.1": ["gpt-4.1", "gemini-2.5-pro", "gpt-5"],
    "gemini-3.1-pro": ["gpt-4.1", "gemini-2.5-pro", "gpt-5"],
    "gemini-2.5-pro": ["gpt-4.1", "gemini-3.1", "gpt-5"],
    "gemini-2.5-flash": ["gpt-4.1-mini", "gemini-2.5-pro", "gpt-4o-mini"],
    # OpenRouter → OpenAI fallback
    "queen-3.6": ["gpt-4.1", "gemini-3.1", "glm-5-1"],
    "glm-5-1": ["gpt-4.1", "queen-3.6", "gemini-3.1"],
    "kimi-k2.5": ["gpt-4.1", "queen-3.6", "gemini-3.1"],
}


def get_fallback_chain(model_id: Optional[str]) -> List[str]:
    """Retorna a cadeia de fallback para um modelo."""
    mid = (model_id or "").strip() or get_default_model_id()
    return _FALLBACK_CHAINS.get(mid, [])


# ============================================================
# API PAYLOAD
# ============================================================

def api_models_payload() -> dict:
    """Resposta JSON para GET /api/llm-models."""
    providers = get_enabled_providers()
    default_id = get_default_model_id()
    
    models = []
    for entry in _CATALOG:
        # Só inclui se o provedor estiver habilitado
        if entry.provider not in providers:
            continue
        models.append({
            "id": entry.id,
            "label": entry.label,
            "provider": entry.provider,
            "model_string": entry.model_string,
            "description": entry.description,
        })
    
    return {
        "default": default_id,
        "default_provider": get_default_provider(),
        "providers": list(providers.keys()),
        "models": models,
    }


def allowed_llm_model_ids() -> List[str]:
    """Retorna IDs de modelos permitidos (provedores habilitados)."""
    providers = get_enabled_providers()
    return [e.id for e in _CATALOG if e.provider in providers]

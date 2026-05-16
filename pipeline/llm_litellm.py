"""
Configuração de modelo e credenciais para LiteLLM (compatibility layer).

Este módulo mantém compatibilidade com código legado,
mas delega para o novo sistema multi-provider em llm_providers.py.
"""
import os
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class LitellmModelConfig:
    model: str
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    extra_headers: Optional[Dict[str, str]] = None
    model_id: Optional[str] = None
    model_label: Optional[str] = None


OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"


def _openrouter_extra_headers() -> Dict[str, str]:
    """Headers opcionais recomendados pela OpenRouter para rankings/atribuição."""
    h: Dict[str, str] = {}
    ref = (os.getenv("OPENROUTER_HTTP_REFERER") or "").strip()
    title = (os.getenv("OPENROUTER_APP_TITLE") or os.getenv("MENUAI_APP_TITLE") or "Menu.AI").strip()
    if ref:
        h["HTTP-Referer"] = ref
    if title:
        h["X-OpenRouter-Title"] = title
    return h


def get_litellm_config(model_override: Optional[str] = None) -> LitellmModelConfig:
    """
    Resolve modelo e credenciais para LiteLLM.completion.
    
    Usa o novo sistema multi-provider (llm_providers.py).
    OpenAI é o provedor padrão quando disponível.
    
    model_override: id interno do catálogo (gpt-4.1, gemini-3.1, queen-3.6) ou None para default.
    """
    from pipeline.llm_providers import resolve_model_config, get_default_model_id

    resolved_id = (model_override or "").strip() or get_default_model_id()
    
    try:
        cfg = resolve_model_config(resolved_id)
    except ValueError as e:
        # Se não conseguir resolver, tenta OpenRouter como fallback
        or_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
        if or_key:
            from pipeline.openrouter_models import litellm_model_string_for_id, label_for_id
            m = litellm_model_string_for_id(resolved_id)
            xh = _openrouter_extra_headers()
            print(f"  🤖 LiteLLM (OpenRouter fallback): {resolved_id} -> {m}")
            return LitellmModelConfig(
                model=m,
                api_key=or_key,
                api_base=OPENROUTER_API_BASE,
                extra_headers=xh if xh else None,
                model_id=resolved_id,
                model_label=label_for_id(resolved_id),
            )
        raise EnvironmentError(
            f"\n❌ {e}\n"
            f"   Configure OPENAI_API_KEY, GEMINI_API_KEY ou OPENROUTER_API_KEY no .env.\n"
        )
    
    print(f"  🤖 LiteLLM ({cfg.provider}): {cfg.model_id} -> {cfg.model_string}")
    return LitellmModelConfig(
        model=cfg.model_string,
        api_key=cfg.api_key,
        api_base=cfg.api_base,
        extra_headers=cfg.extra_headers,
        model_id=cfg.model_id,
        model_label=cfg.model_label,
    )

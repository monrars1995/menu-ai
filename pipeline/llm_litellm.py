"""
Configuração de modelo e credenciais para LiteLLM.

OpenRouter é o provider único suportado para geração de cardápios.
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
    Resolve modelo e credenciais OpenRouter para LiteLLM.completion.

    model_override: id interno do catálogo (queen-3.6, glm-5-1, kimi-k2.5) ou None para default .env.
    """
    or_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    if not or_key:
        raise EnvironmentError(
            "\n❌ Configure OPENROUTER_API_KEY no .env para geração via OpenRouter.\n"
            "   IDs suportados: queen-3.6, glm-5-1, kimi-k2.5.\n"
            "   Base oficial: https://openrouter.ai/api/v1\n"
        )

    from pipeline.openrouter_models import effective_default_model_id, label_for_id, litellm_model_string_for_id

    resolved_id = (model_override or "").strip() or effective_default_model_id()
    m = litellm_model_string_for_id(resolved_id)
    xh = _openrouter_extra_headers()
    print(f"  🤖 LiteLLM (OpenRouter): {resolved_id} -> {m}")
    return LitellmModelConfig(
        model=m,
        api_key=or_key,
        api_base=OPENROUTER_API_BASE,
        extra_headers=xh if xh else None,
        model_id=resolved_id,
        model_label=label_for_id(resolved_id),
    )

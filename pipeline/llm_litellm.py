"""Configuração de modelo e credenciais para LiteLLM."""
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


def get_litellm_config(model_override: Optional[str] = None) -> LitellmModelConfig:
    """
    Resolve modelo e credenciais para LiteLLM.completion.
    
    Usa o catálogo centralizado em llm_providers.py.
    
    model_override: id interno do catálogo ou None para default.
    """
    from pipeline.llm_providers import resolve_model_config, get_default_model_id

    resolved_id = (model_override or "").strip() or get_default_model_id()
    
    try:
        cfg = resolve_model_config(resolved_id)
    except ValueError as e:
        raise EnvironmentError(
            f"\n❌ {e}\n"
            f"   Configure a chave do provedor no .env.\n"
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

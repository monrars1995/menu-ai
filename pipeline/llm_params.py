"""Utilitários de parâmetros para chamadas LiteLLM por provedor/modelo."""
from __future__ import annotations

from typing import Any, Dict, Optional


def _is_openai_gpt5(model_string: str) -> bool:
    m = (model_string or "").strip().lower()
    return m.startswith("openai/gpt-5") or m.startswith("gpt-5")


def attach_temperature_if_supported(
    kwargs: Dict[str, Any],
    *,
    model_string: str,
    provider: Optional[str],
    temperature: Optional[float],
) -> None:
    """
    Anexa `temperature` somente quando o modelo suporta ajuste explícito.

    OpenAI GPT-5.x atualmente exige temperatura padrão do provedor;
    enviar valor explícito pode causar BadRequest.
    """
    if temperature is None:
        return
    p = (provider or "").strip().lower()
    if p == "openai" and _is_openai_gpt5(model_string):
        return
    kwargs["temperature"] = temperature

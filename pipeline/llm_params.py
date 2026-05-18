"""Utilitários de parâmetros para chamadas LiteLLM por provedor/modelo."""
from __future__ import annotations

from typing import Any, Dict, Optional


def _is_openai_gpt5(model_string: str) -> bool:
    m = (model_string or "").strip().lower()
    return (
        m.startswith("openai/gpt-5")
        or m.startswith("gpt-5")
        or "/gpt-5" in m
        or "openai/gpt-5" in m
    )


def _is_moonshot_kimi_k26(model_string: str, provider: Optional[str]) -> bool:
    p = (provider or "").strip().lower()
    m = (model_string or "").strip().lower()
    return p == "moonshot" and "kimi-k2.6" in m


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

    Kimi K2.6 oficial usa temperatura fixa no endpoint da Moonshot;
    enviar valor explícito pode causar comportamento inválido.
    """
    if temperature is None:
        return
    p = (provider or "").strip().lower()
    if p == "openai" and _is_openai_gpt5(model_string):
        return
    if _is_moonshot_kimi_k26(model_string, provider):
        return
    kwargs["temperature"] = temperature

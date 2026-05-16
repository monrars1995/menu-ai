"""
Menu.AI — Model Router com Fallback Automático (Multi-Provider)

Camada de resiliência que tenta múltiplos modelos/providers em sequência.
Se o modelo primário falhar (timeout, rate limit, erro 5xx),
tenta automaticamente o próximo na cadeia de fallback (cross-provider).

Uso:
    from pipeline.model_router import ModelRouter
    router = ModelRouter(model_id="gpt-4.1", job_id="abc123")
    result = router.call(messages=..., tools=...)
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from litellm import completion
from litellm.exceptions import (
    AuthenticationError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)

logger = logging.getLogger("menuai.model_router")

# Erros que devem acionar fallback (transitórios)
_RETRIABLE_ERRORS = (
    Timeout,
    RateLimitError,
    ServiceUnavailableError,
    ConnectionError,
    TimeoutError,
)

# Erros fatais (não adianta tentar fallback)
_FATAL_ERRORS = (AuthenticationError,)

# Número máximo de tentativas (primário + fallbacks)
MAX_ATTEMPTS = 3


@dataclass
class ModelCallResult:
    """Resultado de uma chamada ao modelo."""
    response: Any = None
    model_used: str = ""
    model_id: str = ""
    provider_used: str = ""
    is_fallback: bool = False
    latency_ms: int = 0
    tokens_prompt: int = 0
    tokens_completion: int = 0
    tokens_total: int = 0
    cost_usd: float = 0.0
    success: bool = True
    error: Optional[str] = None
    error_type: Optional[str] = None
    attempts: int = 0


class ModelRouter:
    """
    Router de modelos LLM com fallback automático cross-provider e audit logging.

    Encapsula a lógica de:
    - Resolução de modelo (id interno → config completa via llm_providers)
    - Fallback automático entre provedores (OpenAI → Gemini → OpenRouter)
    - Registro de audit log para cada tentativa
    """

    def __init__(
        self,
        model_id: Optional[str] = None,
        job_id: Optional[str] = None,
        empresa_id: Optional[str] = None,
        step_label: Optional[str] = None,
        step_index: Optional[int] = None,
    ):
        from pipeline.llm_providers import get_default_model_id, get_fallback_chain

        self.model_id = (model_id or "").strip() or get_default_model_id()
        self.job_id = job_id
        self.empresa_id = empresa_id
        self.step_label = step_label
        self.step_index = step_index
        self._fallback_chain = get_fallback_chain(self.model_id)

    def _resolve_model_config(self, model_id: str):
        """Resolve configuração completa para um dado model_id."""
        from pipeline.llm_providers import resolve_model_config
        return resolve_model_config(model_id)

    def _extract_usage(self, response) -> dict:
        """Extrai métricas de uso do response."""
        usage = getattr(response, "usage", None)
        if not usage:
            return {"tokens_prompt": 0, "tokens_completion": 0, "tokens_total": 0}

        return {
            "tokens_prompt": getattr(usage, "prompt_tokens", 0) or 0,
            "tokens_completion": getattr(usage, "completion_tokens", 0) or 0,
            "tokens_total": getattr(usage, "total_tokens", 0) or 0,
        }

    def _classify_error(self, error: Exception) -> str:
        """Classifica o tipo de erro para audit log."""
        if isinstance(error, Timeout) or isinstance(error, TimeoutError):
            return "timeout"
        if isinstance(error, RateLimitError):
            return "rate_limit"
        if isinstance(error, AuthenticationError):
            return "auth"
        if isinstance(error, ServiceUnavailableError):
            return "service_unavailable"
        if isinstance(error, ConnectionError):
            return "connection"
        return "unknown"

    def _log_attempt(
        self,
        model_requested: str,
        model_used: str,
        provider_used: str,
        is_fallback: bool,
        latency_ms: int,
        success: bool,
        usage: dict,
        error: Optional[Exception] = None,
    ) -> None:
        """Registra a tentativa no audit log."""
        try:
            from services.audit_log import log_llm_call

            log_llm_call(
                job_id=self.job_id,
                empresa_id=self.empresa_id,
                model_requested=model_requested,
                model_used=model_used,
                provider=provider_used,
                is_fallback=is_fallback,
                step_label=self.step_label,
                step_index=self.step_index,
                latency_ms=latency_ms,
                tokens_prompt=usage.get("tokens_prompt"),
                tokens_completion=usage.get("tokens_completion"),
                tokens_total=usage.get("tokens_total"),
                success=success,
                error_type=self._classify_error(error) if error else None,
                error_message=str(error)[:2000] if error else None,
            )
        except Exception as log_err:
            logger.warning("Falha ao registrar audit: %s", log_err)

    def call(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        temperature: Optional[float] = None,
        extra_headers: Optional[dict] = None,
    ) -> ModelCallResult:
        """
        Faz a chamada ao modelo com fallback automático cross-provider.

        Retorna ModelCallResult com o response e metadados da chamada.
        """
        if temperature is None:
            temperature = float(os.getenv("LLM_TEMPERATURE", "0.7") or 0.7)

        # Lista de modelos a tentar: primário + fallbacks
        models_to_try = [self.model_id] + self._fallback_chain[:MAX_ATTEMPTS - 1]

        result = ModelCallResult()
        original_model = self.model_id

        for attempt_idx, mid in enumerate(models_to_try):
            is_fallback = attempt_idx > 0
            
            try:
                cfg = self._resolve_model_config(mid)
            except ValueError as e:
                logger.warning("Modelo %s não resolvido: %s", mid, e)
                continue

            kwargs: dict = {
                "model": cfg.model_string,
                "messages": messages,
                "temperature": temperature,
            }
            if cfg.api_key:
                kwargs["api_key"] = cfg.api_key
            if cfg.api_base:
                kwargs["api_base"] = cfg.api_base
            if extra_headers or getattr(cfg, "extra_headers", None):
                merged_headers = {}
                if getattr(cfg, "extra_headers", None):
                    merged_headers.update(cfg.extra_headers)
                if extra_headers:
                    merged_headers.update(extra_headers)
                if merged_headers:
                    kwargs["extra_headers"] = merged_headers
            if tools:
                kwargs["tools"] = tools

            start_ms = int(time.time() * 1000)

            try:
                resp = completion(**kwargs)
                elapsed_ms = int(time.time() * 1000) - start_ms
                usage = self._extract_usage(resp)

                if is_fallback:
                    logger.info(
                        "Fallback OK: %s → %s (provider=%s, latência %dms)",
                        original_model, mid, cfg.provider, elapsed_ms,
                    )

                self._log_attempt(
                    model_requested=original_model,
                    model_used=cfg.model_string,
                    provider_used=cfg.provider,
                    is_fallback=is_fallback,
                    latency_ms=elapsed_ms,
                    success=True,
                    usage=usage,
                )

                result.response = resp
                result.model_used = cfg.model_string
                result.model_id = cfg.model_id
                result.provider_used = cfg.provider
                result.is_fallback = is_fallback
                result.latency_ms = elapsed_ms
                result.tokens_prompt = usage["tokens_prompt"]
                result.tokens_completion = usage["tokens_completion"]
                result.tokens_total = usage["tokens_total"]
                result.success = True
                result.attempts = attempt_idx + 1
                return result

            except _FATAL_ERRORS as fatal:
                # Erro fatal: não tenta fallback
                elapsed_ms = int(time.time() * 1000) - start_ms
                logger.error("Erro fatal no modelo %s: %s", mid, fatal)
                self._log_attempt(
                    model_requested=original_model,
                    model_used=cfg.model_string,
                    provider_used=cfg.provider,
                    is_fallback=is_fallback,
                    latency_ms=elapsed_ms,
                    success=False,
                    usage={},
                    error=fatal,
                )
                result.success = False
                result.error = str(fatal)
                result.error_type = self._classify_error(fatal)
                result.attempts = attempt_idx + 1
                return result

            except _RETRIABLE_ERRORS as retriable:
                elapsed_ms = int(time.time() * 1000) - start_ms
                logger.warning(
                    "Erro transitório no modelo %s (provider=%s, tentativa %d/%d): %s — tentando fallback...",
                    mid, cfg.provider, attempt_idx + 1, len(models_to_try), retriable,
                )
                self._log_attempt(
                    model_requested=original_model,
                    model_used=cfg.model_string,
                    provider_used=cfg.provider,
                    is_fallback=is_fallback,
                    latency_ms=elapsed_ms,
                    success=False,
                    usage={},
                    error=retriable,
                )
                result.error = str(retriable)
                result.error_type = self._classify_error(retriable)
                continue  # tenta próximo modelo

            except Exception as generic:
                elapsed_ms = int(time.time() * 1000) - start_ms
                logger.error("Erro inesperado no modelo %s: %s", mid, generic)
                self._log_attempt(
                    model_requested=original_model,
                    model_used=cfg.model_string,
                    provider_used=cfg.provider,
                    is_fallback=is_fallback,
                    latency_ms=elapsed_ms,
                    success=False,
                    usage={},
                    error=generic,
                )
                result.error = str(generic)
                result.error_type = "unexpected"
                continue  # tenta próximo modelo

        # Todos os modelos falharam
        result.success = False
        result.attempts = len(models_to_try)
        logger.error(
            "Todos os modelos falharam para job=%s step=%s: %s",
            self.job_id, self.step_label, result.error,
        )
        return result

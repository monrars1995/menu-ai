"""
Menu.AI — Model Router com Fallback Automático.

Camada de resiliência que tenta múltiplos modelos/provedores em sequência.
Se o modelo primário falhar (timeout, rate limit, erro 5xx),
tenta automaticamente o próximo na cadeia de fallback.

Uso:
    from pipeline.model_router import ModelRouter
    router = ModelRouter(model_id="openai-gpt-5.5", job_id="abc123")
    result = router.call(messages=..., tools=...)
"""
from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from litellm import completion
from litellm.exceptions import (
    AuthenticationError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)
from pipeline.llm_params import attach_temperature_if_supported

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
_PROVIDER_BACKOFF_UNTIL: Dict[str, float] = {}


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
    Router de modelos LLM com fallback automático e audit logging.

    Encapsula a lógica de:
    - Resolução de modelo (id interno → config completa via llm_providers)
    - Fallback automático entre provedores/modelos disponíveis
    - Registro de audit log para cada tentativa
    """

    def __init__(
        self,
        model_id: Optional[str] = None,
        job_id: Optional[str] = None,
        empresa_id: Optional[str] = None,
        step_label: Optional[str] = None,
        step_index: Optional[int] = None,
        timeout_seconds: Optional[float] = None,
        max_attempts: Optional[int] = None,
        fallback_chain_override: Optional[List[str]] = None,
        on_attempt: Optional[Callable[[dict[str, Any]], None]] = None,
    ):
        from pipeline.llm_providers import get_effective_default_model_id, get_fallback_chain

        requested_model_id = (model_id or "").strip()
        self.model_id = requested_model_id or get_effective_default_model_id()
        self.job_id = job_id
        self.empresa_id = empresa_id
        self.step_label = step_label
        self.step_index = step_index
        env_timeout = (os.getenv("MENUAI_LLM_REQUEST_TIMEOUT_SECONDS") or "55").strip()
        try:
            parsed_timeout = float(env_timeout)
        except ValueError:
            parsed_timeout = 55.0
        self.timeout_seconds = timeout_seconds if timeout_seconds and timeout_seconds > 0 else parsed_timeout
        self.max_attempts = max(1, int(max_attempts or MAX_ATTEMPTS))
        if fallback_chain_override is not None:
            self._fallback_chain = [m for m in fallback_chain_override if m and m != self.model_id]
        else:
            self._fallback_chain = get_fallback_chain(
                self.model_id,
                respect_selection=bool(requested_model_id),
            )
        self.on_attempt = on_attempt

    def _structured_log(self, event: str, **fields: Any) -> None:
        payload = {
            "event": event,
            "job_id": self.job_id,
            "step_label": self.step_label,
            "step_index": self.step_index,
            **fields,
        }
        logger.info("model_router=%s", json.dumps(payload, ensure_ascii=False, default=str))

    def _provider_backoff_seconds(self, provider: str) -> float:
        key = f"MENUAI_LLM_{provider.upper()}_BACKOFF_SECONDS"
        raw = (os.getenv(key) or os.getenv("MENUAI_LLM_PROVIDER_BACKOFF_SECONDS") or "").strip()
        default_map = {
            "openrouter": 900.0,
            "gemini": 180.0,
            "moonshot": 120.0,
            "openai": 120.0,
        }
        default_value = default_map.get(provider, 120.0)
        if not raw:
            return default_value
        try:
            return max(30.0, float(raw))
        except ValueError:
            return default_value

    def _provider_is_backed_off(self, provider: str) -> tuple[bool, int]:
        until = float(_PROVIDER_BACKOFF_UNTIL.get(provider, 0.0) or 0.0)
        now = time.monotonic()
        if until > now:
            return True, int(until - now)
        return False, 0

    def _mark_provider_backoff(self, provider: str, seconds: float, reason: str) -> None:
        _PROVIDER_BACKOFF_UNTIL[provider] = time.monotonic() + max(30.0, seconds)
        self._structured_log(
            "provider_backoff_set",
            provider=provider,
            reason=reason,
            backoff_seconds=int(max(30.0, seconds)),
        )

    def _resolve_model_config(self, model_id: str):
        """Resolve configuração completa para um dado model_id."""
        from pipeline.llm_providers import resolve_model_config
        return resolve_model_config(model_id)

    def _completion_with_hard_timeout(
        self,
        call_kwargs: dict[str, Any],
        heartbeat_meta: Optional[dict[str, Any]] = None,
    ):
        """
        Executa completion com timeout duro local.

        Em alguns provedores o timeout do SDK pode não encerrar a chamada no tempo esperado.
        Este guard-rail evita bloqueio longo por tentativa.
        """
        hard_extra_raw = (os.getenv("MENUAI_LLM_HARD_TIMEOUT_EXTRA_SECONDS") or "8").strip()
        try:
            hard_extra = max(2.0, float(hard_extra_raw))
        except ValueError:
            hard_extra = 8.0

        heartbeat_raw = (os.getenv("MENUAI_LLM_HEARTBEAT_SECONDS") or "8").strip()
        try:
            heartbeat_seconds = max(3.0, float(heartbeat_raw))
        except ValueError:
            heartbeat_seconds = 8.0

        base_timeout = float(call_kwargs.get("timeout") or self.timeout_seconds or 55.0)
        hard_timeout = max(20.0, base_timeout + hard_extra)
        started_at = time.monotonic()
        result_queue: "queue.Queue[tuple[str, Any]]" = queue.Queue(maxsize=1)

        def _invoke_completion() -> None:
            try:
                result_queue.put(("result", completion(**call_kwargs)))
            except BaseException as exc:  # pragma: no cover - repasse direto
                result_queue.put(("error", exc))

        worker = threading.Thread(
            target=_invoke_completion,
            name="menuai-llm-call",
            daemon=True,
        )
        worker.start()
        try:
            while True:
                elapsed = time.monotonic() - started_at
                remaining = hard_timeout - elapsed
                if remaining <= 0:
                    raise TimeoutError(f"LLM hard-timeout excedido ({int(hard_timeout)}s)")

                wait_window = min(heartbeat_seconds, max(0.5, remaining))
                try:
                    event_type, payload = result_queue.get(timeout=wait_window)
                    if event_type == "error":
                        raise payload
                    return payload
                except queue.Empty as exc:
                    elapsed = time.monotonic() - started_at
                    if elapsed >= hard_timeout:
                        raise TimeoutError(f"LLM hard-timeout excedido ({int(hard_timeout)}s)") from exc
                    if self.on_attempt:
                        payload = {
                            "event": "attempt_heartbeat",
                            "elapsed_seconds": round(elapsed, 1),
                            "hard_timeout_seconds": int(hard_timeout),
                        }
                        if heartbeat_meta:
                            payload.update(heartbeat_meta)
                        try:
                            self.on_attempt(payload)
                        except Exception:
                            pass
        finally:
            # Worker é daemon; se a chamada subjacente ignorar timeout do SDK, não bloqueia o fluxo.
            pass

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
        models_to_try = [self.model_id] + self._fallback_chain[: self.max_attempts - 1]

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
            }
            provider_blocked, provider_retry_after = self._provider_is_backed_off(cfg.provider)
            if provider_blocked:
                msg = (
                    f"Provider {cfg.provider} em backoff por falhas recentes "
                    f"(retry em ~{provider_retry_after}s)."
                )
                self._structured_log(
                    "attempt_skipped_provider_backoff",
                    attempt=attempt_idx + 1,
                    model_id=mid,
                    provider=cfg.provider,
                    retry_after_seconds=provider_retry_after,
                )
                if self.on_attempt:
                    try:
                        self.on_attempt(
                            {
                                "event": "attempt_skipped",
                                "attempt": attempt_idx + 1,
                                "max_attempts": len(models_to_try),
                                "model_id": mid,
                                "model_string": cfg.model_string,
                                "provider": cfg.provider,
                                "fallback": is_fallback,
                                "reason": msg,
                            }
                        )
                    except Exception:
                        pass
                result.error = msg
                result.error_type = "provider_backoff"
                continue
            kwargs["timeout"] = float(self.timeout_seconds)
            kwargs["request_timeout"] = float(self.timeout_seconds)
            attach_temperature_if_supported(
                kwargs,
                model_string=cfg.model_string,
                provider=cfg.provider,
                temperature=temperature,
            )
            if cfg.api_key:
                kwargs["api_key"] = cfg.api_key
            if cfg.api_base:
                kwargs["api_base"] = cfg.api_base
            if getattr(cfg, "extra_body", None):
                kwargs["extra_body"] = dict(cfg.extra_body)
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
            self._structured_log(
                "attempt_started",
                attempt=attempt_idx + 1,
                max_attempts=len(models_to_try),
                model_id=mid,
                model_string=cfg.model_string,
                provider=cfg.provider,
                fallback=is_fallback,
                timeout_seconds=self.timeout_seconds,
            )
            if self.on_attempt:
                try:
                    self.on_attempt(
                        {
                            "event": "attempt_started",
                            "attempt": attempt_idx + 1,
                            "max_attempts": len(models_to_try),
                            "model_id": mid,
                            "model_string": cfg.model_string,
                            "provider": cfg.provider,
                            "fallback": is_fallback,
                            "timeout_seconds": self.timeout_seconds,
                        }
                    )
                except Exception:
                    pass

            try:
                attempt_meta = {
                    "attempt": attempt_idx + 1,
                    "max_attempts": len(models_to_try),
                    "model_id": mid,
                    "model_string": cfg.model_string,
                    "provider": cfg.provider,
                    "fallback": is_fallback,
                }
                try:
                    resp = self._completion_with_hard_timeout(kwargs, heartbeat_meta=attempt_meta)
                except Exception as temp_err:
                    # Alguns modelos (ex.: GPT-5.x) rejeitam temperatura explícita.
                    # Se isso ocorrer, tenta 1x sem temperatura no mesmo modelo antes do fallback.
                    if (
                        "temperature" in kwargs
                        and "unsupported value" in str(temp_err).lower()
                        and "temperature" in str(temp_err).lower()
                    ):
                        kwargs.pop("temperature", None)
                        try:
                            resp = self._completion_with_hard_timeout(kwargs, heartbeat_meta=attempt_meta)
                        except TypeError as timeout_kw_err:
                            if "request_timeout" in str(timeout_kw_err).lower():
                                kwargs.pop("request_timeout", None)
                                resp = self._completion_with_hard_timeout(kwargs, heartbeat_meta=attempt_meta)
                            else:
                                raise
                    else:
                        if isinstance(temp_err, TypeError) and "request_timeout" in str(temp_err).lower():
                            kwargs.pop("request_timeout", None)
                            resp = self._completion_with_hard_timeout(kwargs, heartbeat_meta=attempt_meta)
                        else:
                            raise
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
                self._structured_log(
                    "attempt_success",
                    attempt=attempt_idx + 1,
                    model_id=mid,
                    model_string=cfg.model_string,
                    provider=cfg.provider,
                    latency_ms=elapsed_ms,
                    tokens_total=usage.get("tokens_total", 0),
                    fallback=is_fallback,
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
                self._mark_provider_backoff(
                    cfg.provider,
                    self._provider_backoff_seconds(cfg.provider),
                    reason="fatal_auth_error",
                )
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
                self._structured_log(
                    "attempt_fatal_error",
                    attempt=attempt_idx + 1,
                    model_id=mid,
                    provider=cfg.provider,
                    latency_ms=elapsed_ms,
                    error_type=result.error_type,
                    error=result.error,
                )
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
                if isinstance(retriable, RateLimitError):
                    self._mark_provider_backoff(
                        cfg.provider,
                        self._provider_backoff_seconds(cfg.provider),
                        reason="rate_limit",
                    )
                elif isinstance(retriable, (Timeout, TimeoutError)):
                    self._mark_provider_backoff(
                        cfg.provider,
                        self._provider_backoff_seconds(cfg.provider),
                        reason="timeout",
                    )
                self._structured_log(
                    "attempt_retriable_error",
                    attempt=attempt_idx + 1,
                    model_id=mid,
                    provider=cfg.provider,
                    latency_ms=elapsed_ms,
                    error_type=result.error_type,
                    error=result.error,
                )
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
                self._structured_log(
                    "attempt_unexpected_error",
                    attempt=attempt_idx + 1,
                    model_id=mid,
                    provider=cfg.provider,
                    latency_ms=elapsed_ms,
                    error_type=result.error_type,
                    error=result.error,
                )
                continue  # tenta próximo modelo

        # Todos os modelos falharam
        result.success = False
        result.attempts = len(models_to_try)
        logger.error(
            "Todos os modelos falharam para job=%s step=%s: %s",
            self.job_id, self.step_label, result.error,
        )
        self._structured_log(
            "all_attempts_failed",
            attempts=result.attempts,
            error_type=result.error_type,
            error=result.error,
        )
        return result

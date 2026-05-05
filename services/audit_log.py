"""
Menu.AI — Audit Log para chamadas LLM

Registra cada tentativa de chamada (sucesso ou falha) no banco de dados.
Permite análise de latência, custos, taxa de erro e uso de fallback.
"""
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("menuai.audit")


def log_llm_call(
    *,
    job_id: Optional[str] = None,
    empresa_id: Optional[str] = None,
    model_requested: str,
    model_used: str,
    provider: Optional[str] = None,
    is_fallback: bool = False,
    step_label: Optional[str] = None,
    step_index: Optional[int] = None,
    latency_ms: Optional[int] = None,
    tokens_prompt: Optional[int] = None,
    tokens_completion: Optional[int] = None,
    tokens_total: Optional[int] = None,
    cost_usd: Optional[float] = None,
    success: bool = True,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    http_status: Optional[int] = None,
) -> None:
    """
    Registra uma chamada LLM no banco de dados.
    Falha silenciosamente se o banco não estiver disponível.
    """
    try:
        from database.connection import SessionLocal
        from database.models import LLMAuditLog

        db = SessionLocal()
        entry = LLMAuditLog(
            job_id=job_id,
            empresa_id=empresa_id,
            model_requested=model_requested,
            model_used=model_used,
            provider=provider,
            is_fallback=is_fallback,
            step_label=step_label,
            step_index=step_index,
            latency_ms=latency_ms,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            tokens_total=tokens_total,
            cost_usd=cost_usd,
            success=success,
            error_type=error_type,
            error_message=error_message[:2000] if error_message else None,
            http_status=http_status,
        )
        db.add(entry)
        db.commit()
        db.close()

        if not success:
            logger.warning(
                "LLM audit: FALHA model=%s step=%s error=%s",
                model_used, step_label, error_type,
            )
        else:
            logger.debug(
                "LLM audit: OK model=%s step=%s latency=%sms tokens=%s",
                model_used, step_label, latency_ms, tokens_total,
            )

    except Exception as e:
        # Nunca deve bloquear o pipeline
        logger.warning("Falha ao registrar audit log LLM: %s", e)

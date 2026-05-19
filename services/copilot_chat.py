"""
Menu.AI — Orquestração do copiloto operacional.

Camada fina entre a sessão de chat persistida e o registry tipado de tools.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from database.models import AgentSlotType, MensagemChat, RoleMensagem, SessaoChat
from pipeline.llm_providers import get_effective_default_model_id
from pipeline.model_router import ModelRouter
from services.agent_runtime import resolve_agent_for_slot
from services.copilot_tools import (
    CopilotContext,
    build_openai_tool_specs,
    execute_tool,
    fallback_route_from_text,
)

logger = logging.getLogger("menuai.copilot_chat")


def _safe_json_loads(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _normalize_tool_calls(message: Any) -> list[dict[str, Any]]:
    raw = getattr(message, "tool_calls", None)
    if not raw and isinstance(message, dict):
        raw = message.get("tool_calls")
    if not raw:
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if hasattr(item, "model_dump"):
            out.append(item.model_dump())
        elif isinstance(item, dict):
            out.append(item)
    return out


def _message_content(message: Any) -> str:
    value = getattr(message, "content", None)
    if value is None and isinstance(message, dict):
        value = message.get("content")
    if value is None:
        return ""
    return str(value).strip()


def _build_context(sessao: SessaoChat, usuario: Any, metadata_json: Optional[dict[str, Any]]) -> CopilotContext:
    session_ctx = dict(sessao.contexto_json or {})
    request_ctx = dict(metadata_json or {})
    merged = {**session_ctx, **request_ctx}
    empresa_id = str(
        merged.get("empresa_id")
        or getattr(usuario, "empresa_id", None)
        or getattr(getattr(sessao, "usuario", None), "empresa_id", None)
        or ""
    ).strip()
    if not empresa_id:
        raise ValueError("Sessão sem empresa no contexto.")
    return CopilotContext(
        usuario=usuario,
        empresa_id=empresa_id,
        page_context=str(merged.get("page_context") or "gerar"),
        sessao_id=sessao.id,
        contrato_id=(str(merged.get("contrato_id")).strip() if merged.get("contrato_id") else None),
        cardapio_id=(str(merged.get("cardapio_id")).strip() if merged.get("cardapio_id") else None),
        job_id=(str(merged.get("job_id")).strip() if merged.get("job_id") else sessao.job_id),
    )


def _build_system_prompt(ctx: CopilotContext, system_override: Optional[str] = None) -> str:
    base = (
        "Você é o copiloto operacional do Menu.AI. "
        "Seu trabalho é operar com precisão sobre ingredientes, fichas técnicas, contratos e cardápios. "
        "Use tools quando houver ação ou consulta objetiva. "
        "Não invente IDs, não assuma mudança destrutiva e não altere regras contratuais sem tool explícita. "
        "Quando faltarem campos para criação/edição, peça apenas o mínimo necessário. "
        "Mantenha respostas curtas, operacionais e orientadas a execução.\n\n"
        f"Contexto atual:\n"
        f"- page_context: {ctx.page_context}\n"
        f"- empresa_id: {ctx.empresa_id}\n"
        f"- contrato_id: {ctx.contrato_id or 'nenhum'}\n"
        f"- cardapio_id: {ctx.cardapio_id or 'nenhum'}\n"
        f"- job_id: {ctx.job_id or 'nenhum'}\n"
    )
    if system_override and system_override.strip():
        return f"{system_override.strip()}\n\n---\n\n{base}"
    return base


def _history_to_messages(rows: list[MensagemChat]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        role = str(row.role)
        payload: dict[str, Any] = {"role": role, "content": row.content or ""}
        if role == RoleMensagem.TOOL:
            if row.tool_call_id:
                payload["tool_call_id"] = row.tool_call_id
            payload["content"] = row.content or "{}"
        elif row.tool_calls:
            payload["tool_calls"] = row.tool_calls
        out.append(payload)
    return out


def _tool_call_from_result(tool_name: str, args: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": f"toolcall_{tool_name}",
            "type": "function",
            "function": {
                "name": tool_name,
                "arguments": json.dumps(args or {}, ensure_ascii=False),
            },
        }
    ]


def _resolve_chat_model(sessao: SessaoChat, metadata_json: Optional[dict[str, Any]]) -> str:
    request_model = str((metadata_json or {}).get("llm_model") or "").strip()
    if request_model:
        return request_model
    job_params = {}
    if sessao.job and isinstance(getattr(sessao.job, "parametros_json", None), dict):
        job_params = dict(sessao.job.parametros_json)
    return (
        str(job_params.get("llm_model") or "").strip()
        or str(job_params.get("generator_model_used") or "").strip()
        or get_effective_default_model_id()
    )


def run_copilot_turn(
    db: Session,
    sessao: SessaoChat,
    usuario: Any,
    user_content: str,
    metadata_json: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    ctx = _build_context(sessao, usuario, metadata_json)
    resolved_copilot_agent = resolve_agent_for_slot(db, AgentSlotType.COPILOT)
    model_id = resolved_copilot_agent.version.provider_model_id or _resolve_chat_model(sessao, metadata_json)
    tool_specs = build_openai_tool_specs(resolved_copilot_agent.allowed_tools)

    history = (
        db.query(MensagemChat)
        .filter(MensagemChat.sessao_id == sessao.id)
        .order_by(MensagemChat.created_at.desc())
        .limit(10)
        .all()
    )
    history.reverse()

    messages = [{"role": "system", "content": _build_system_prompt(ctx, resolved_copilot_agent.version.system_prompt)}]
    history_messages = _history_to_messages(history)
    messages.extend(history_messages)
    if not history_messages or history_messages[-1].get("role") != RoleMensagem.USER or str(history_messages[-1].get("content") or "") != user_content:
        messages.append({"role": "user", "content": user_content})

    llm_error: Optional[str] = None
    try:
        router = ModelRouter(
            model_id=model_id,
            job_id=ctx.job_id,
            empresa_id=ctx.empresa_id,
            step_label="chat_copilot",
            timeout_seconds=20,
            max_attempts=2,
        )
        llm_result = router.call(messages=messages, tools=tool_specs, temperature=0.2)
        if llm_result.success and llm_result.response and llm_result.response.choices:
            message = llm_result.response.choices[0].message
            tool_calls = _normalize_tool_calls(message)
            content = _message_content(message)
            if tool_calls:
                selected = tool_calls[0]
                fn = (selected or {}).get("function") or {}
                tool_name = str(fn.get("name") or "").strip()
                raw_args = _safe_json_loads(fn.get("arguments"))
                tool_result = execute_tool(
                    db,
                    ctx,
                    tool_name,
                    raw_args,
                    allowed_tool_names=resolved_copilot_agent.allowed_tools,
                )
                return {
                    "assistant_message": tool_result.assistant_message,
                    "tool_name": tool_result.tool_name,
                    "result": tool_result.result,
                    "tool_calls": tool_calls,
                    "metadata_json": {
                        "tool_name": tool_result.tool_name,
                        "tool_result": tool_result.result,
                        "model_id": model_id,
                        "copilot_agent_id": str(resolved_copilot_agent.profile.id),
                        "copilot_agent_version_id": str(resolved_copilot_agent.version.id),
                    },
                    "context_updates": tool_result.context_updates or {},
                }
            if content:
                return {
                    "assistant_message": content,
                    "tool_name": None,
                    "result": None,
                    "tool_calls": None,
                    "metadata_json": {
                        "model_id": model_id,
                        "copilot_agent_id": str(resolved_copilot_agent.profile.id),
                        "copilot_agent_version_id": str(resolved_copilot_agent.version.id),
                    },
                    "context_updates": {},
                }
    except Exception as exc:  # noqa: BLE001
        llm_error = str(exc)
        logger.warning("copilot_llm_failed sessao=%s erro=%s", sessao.id, exc)

    fallback_tool, fallback_args = fallback_route_from_text(
        user_content,
        ctx,
        allowed_tool_names=resolved_copilot_agent.allowed_tools,
    )
    if fallback_tool:
        tool_result = execute_tool(
            db,
            ctx,
            fallback_tool,
            fallback_args,
            allowed_tool_names=resolved_copilot_agent.allowed_tools,
        )
        return {
            "assistant_message": tool_result.assistant_message,
            "tool_name": tool_result.tool_name,
            "result": tool_result.result,
            "tool_calls": _tool_call_from_result(tool_result.tool_name, fallback_args),
            "metadata_json": {
                "tool_name": tool_result.tool_name,
                "tool_result": tool_result.result,
                "fallback_reason": llm_error,
                "copilot_agent_id": str(resolved_copilot_agent.profile.id),
                "copilot_agent_version_id": str(resolved_copilot_agent.version.id),
            },
            "context_updates": tool_result.context_updates or {},
        }

    guidance = (
        "Posso operar sobre contratos, cardápios, fichas técnicas e ingredientes. "
        "Exemplos: `listar contratos`, `buscar ingredientes de frango`, "
        "`aprovar este cardápio`, `exportar este cardápio em pdf`."
    )
    if llm_error:
        guidance += " O modelo principal do copiloto falhou neste turno e usei resposta determinística."
    return {
        "assistant_message": guidance,
        "tool_name": None,
        "result": None,
        "tool_calls": None,
        "metadata_json": {"fallback_reason": llm_error} if llm_error else {},
        "context_updates": {},
    }

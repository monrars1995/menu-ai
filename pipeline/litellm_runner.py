"""
Execução sequencial do pipeline de geração de cardápio via LiteLLM (sem CrewAI kickoff).
"""
from __future__ import annotations

import json
import os
import re
import unicodedata
from types import SimpleNamespace
from typing import Any, List, Optional

from litellm import completion

from pipeline.llm_litellm import get_litellm_config
from pipeline.llm_params import attach_temperature_if_supported
from pipeline.sequential_spec import build_steps

MAX_TOOL_TURNS = 32
MAX_PRIOR_LEN = 14000
OPENAI_TOOL_NAME_MAX_LEN = 64


def _sanitize_tool_name(name: str) -> str:
    """OpenAI exige nomes de tools em ^[a-zA-Z0-9_-]+$."""
    raw = unicodedata.normalize("NFKD", str(name or "tool"))
    ascii_name = raw.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", ascii_name).strip("_")
    cleaned = re.sub(r"_+", "_", cleaned)
    return (cleaned or "tool")[:OPENAI_TOOL_NAME_MAX_LEN]


def _openai_name(tool: Any) -> str:
    n = getattr(tool, "name", None) or ""
    if not n and hasattr(tool, "func") and getattr(tool, "func", None) is not None:
        n = getattr(tool.func, "__name__", "tool")
    return _sanitize_tool_name(str(n) or "tool")


def _to_openai_tools(tools: List[Any]) -> List[dict]:
    if not tools:
        return []
    try:
        from langchain_core.utils.function_calling import convert_to_openai_tool
    except ImportError:
        try:
            from langchain_core.utils.function_calling import (
                convert_to_openai_function as convert_to_openai_tool,
            )
        except ImportError as e:
            raise ImportError("Instale langchain-core: pip install langchain-core") from e
    out: List[dict] = []
    used_names: set[str] = set()
    for t in tools:
        if t is None:
            continue
        try:
            oa = convert_to_openai_tool(t)
            schema = oa if isinstance(oa, dict) and oa.get("type") == "function" else {"type": "function", "function": oa}
            fn = schema.get("function") or {}
            base = _sanitize_tool_name(fn.get("name") or _openai_name(t))
            name = base
            suffix = 2
            while name in used_names:
                tail = f"_{suffix}"
                name = f"{base[:OPENAI_TOOL_NAME_MAX_LEN - len(tail)]}{tail}"
                suffix += 1
            used_names.add(name)
            fn["name"] = name
            schema["function"] = fn
            out.append(schema)
        except Exception:
            continue
    return out


def _index_tools(tools: List[Any]) -> dict:
    m: dict = {}
    for t in tools:
        if t is None:
            continue
        original = getattr(t, "name", None) or ""
        aliases = {
            _openai_name(t),
            _sanitize_tool_name(original),
            str(original),
            str(original).replace(" ", "_"),
        }
        for a in aliases:
            if a:
                m[a] = t
                m[a.lower()] = t
    return m


def _invoke_one(tool: Any, args: dict) -> str:
    if not isinstance(args, dict):
        args = {}
    if hasattr(tool, "invoke"):
        return str(tool.invoke(args))
    if hasattr(tool, "_run"):
        return str(tool._run(**args))
    if hasattr(tool, "func"):
        return str(tool.func(**args))
    if hasattr(tool, "run"):
        return str(tool.run(**args))
    return str(tool)


def _normalize_tool_calls(choice) -> List[dict]:
    """Converte tool_calls de vários formatos (OpenAI, LiteLLM) para dicts idempotentes."""
    msg = choice.message
    tcalls = getattr(msg, "tool_calls", None) or (msg.get("tool_calls") if isinstance(msg, dict) else None)
    if not tcalls:
        return []
    out = []
    for tc in tcalls:
        if hasattr(tc, "id") and hasattr(tc, "function"):
            name = _sanitize_tool_name(tc.function.name)
            out.append(
                {
                    "id": getattr(tc, "id", "") or "",
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": tc.function.arguments or "{}",
                    },
                }
            )
        elif isinstance(tc, dict):
            fn = tc.get("function") or {}
            name = _sanitize_tool_name(fn.get("name", ""))
            out.append(
                {
                    "id": tc.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": fn.get("arguments", "{}")
                        if isinstance(fn.get("arguments"), str)
                        else json.dumps(fn.get("arguments", {})),
                    },
                }
            )
    return out


def _assistant_content(choice) -> Optional[str]:
    msg = choice.message
    c = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
    return c if c else None


def _run_with_tools(
    model: str,
    api_key: Optional[str],
    api_base: Optional[str],
    system: str,
    user: str,
    tools: List[Any],
    step_callback: Any,
    agent_name: str,
    extra_headers: Optional[dict] = None,
    *,
    model_router=None,  # Optional ModelRouter instance for fallback
) -> str:
    openai_tools = _to_openai_tools(tools)
    idx = _index_tools(tools)
    messages: List[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    for _ in range(MAX_TOOL_TURNS):
        if model_router is not None:
            # Usa ModelRouter com fallback automático
            result = model_router.call(
                messages=messages,
                tools=openai_tools if openai_tools else None,
                extra_headers=extra_headers,
            )
            if not result.success:
                raise RuntimeError(f"LLM falhou em {agent_name}: {result.error}")
            resp = result.response
        else:
            # Chamada direta (compatibilidade)
            kwargs: dict = {
                "model": model,
                "messages": messages,
            }
            req_temp = float(os.getenv("LLM_TEMPERATURE", "0.7") or 0.7)
            provider = model.split("/", 1)[0] if "/" in model else None
            attach_temperature_if_supported(
                kwargs,
                model_string=model,
                provider=provider,
                temperature=req_temp,
            )
            if api_key:
                kwargs["api_key"] = api_key
            if api_base:
                kwargs["api_base"] = api_base
            if extra_headers:
                kwargs["extra_headers"] = extra_headers
            if openai_tools:
                kwargs["tools"] = openai_tools
            try:
                resp = completion(**kwargs)
            except Exception as e:
                raise RuntimeError(f"LLM falhou em {agent_name}: {e!s}") from e

        if not resp.choices:
            return ""
        choice = resp.choices[0]
        tcalls = _normalize_tool_calls(choice)
        content = _assistant_content(choice)
        if not tcalls:
            return (content or "").strip()
        asst: dict = {
            "role": "assistant",
            "content": content,
            "tool_calls": tcalls,
        }
        if not content:
            asst["content"] = None
        elif step_callback:
            try:
                step_callback(content, agent_name=agent_name)
            except TypeError:
                try:
                    step_callback(content, **{"agent_name": agent_name})
                except Exception:
                    pass
        messages = list(messages)
        messages.append(asst)
        for tc in tcalls:
            fn = (tc or {}).get("function") or {}
            name = fn.get("name", "")
            raw = fn.get("arguments", "{}")
            if not isinstance(raw, str):
                raw = json.dumps(raw)
            tid = (tc or {}).get("id", "")
            if step_callback:
                try:
                    step_callback(f"(ferramenta) {name}", agent_name=agent_name)
                except TypeError:
                    try:
                        step_callback(f"(ferramenta) {name}", **{"agent_name": agent_name})
                    except Exception:
                        pass
            try:
                ajs = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                ajs = {}
            tinst = (
                idx.get(name)
                or idx.get(name.replace(" ", "_"))
            )
            if tinst is not None:
                try:
                    out = _invoke_one(tinst, ajs)
                except Exception as ex:
                    out = f"ERRO: {ex}"
            else:
                out = f"[ferramenta não encontrada: {name}]"
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tid or f"call_{name}",
                    "content": out[:120000],
                }
            )
    return "[FIM: limite de chamadas a ferramentas]"


def run_lite_pipeline(crew) -> str:
    """Executa 7 etapas com a mesma semântica de ferramentas e contexto de `build_steps`."""
    mo = getattr(crew, "llm_model_id", None)
    cfg = get_litellm_config(model_override=mo)
    crew._configurar_tools()
    steps = build_steps(crew)
    prior: List[str] = []
    last_out = ""
    start_index = 0
    if getattr(crew, "skip_contract_analysis", False) and getattr(crew.ctx, "regras_contrato", None):
        start_index = 1
        prior.append(
            "## Analista de Contratos e Regras de Negócio\n"
            "Regras do contrato já extraídas, revisadas e confirmadas antes da geração:\n"
            + json.dumps(crew.ctx.regras_contrato, ensure_ascii=False, indent=2)
        )

    # Tenta importar ModelRouter (fallback gracioso se falhar)
    _ModelRouter = None
    try:
        from pipeline.model_router import ModelRouter as _ModelRouter
    except Exception:
        pass

    for step_idx, st in enumerate(steps[start_index:], start=start_index):
        ctx = ""
        if prior:
            acc = "\n\n".join(prior)
            if len(acc) > MAX_PRIOR_LEN:
                acc = acc[: MAX_PRIOR_LEN - 3] + "..."
            ctx = f"\n\n## Contexto de etapas anteriores\n{acc}\n"
        u = st.user + ctx

        # Cria ModelRouter por etapa (com contexto de job/empresa/step)
        router = None
        if _ModelRouter is not None:
            try:
                router = _ModelRouter(
                    model_id=mo,
                    job_id=getattr(crew, "_job_id", None),
                    empresa_id=getattr(crew, "empresa_id", None),
                    step_label=st.label,
                    step_index=step_idx,
                )
            except Exception:
                pass

        out = _run_with_tools(
            cfg.model,
            cfg.api_key,
            cfg.api_base,
            st.system,
            u,
            st.tools,
            crew.step_callback,
            st.label,
            extra_headers=getattr(cfg, "extra_headers", None),
            model_router=router,
        )
        last_out = out
        prior.append(f"## {st.label}\n{out}")
        if crew.task_callback:
            try:
                crew.task_callback(
                    SimpleNamespace(
                        agent=st.label,
                        raw=out,
                    )
                )
            except Exception:
                pass
    crew.ctx.etapa_atual = "concluido"
    crew.ctx.cardapio_final = last_out
    return last_out


def run_lite_pipeline_step(
    orchestrator,
    step_index: int,
    tools: dict,
) -> str:
    """
    Executa UMA ÚNICA etapa do pipeline.
    Usado no fluxo human-in-the-loop para rodar apenas a análise de contrato.

    Args:
        orchestrator: MenuOrchestrator instance
        step_index: índice da etapa (0 = Analista de Contratos)
        tools: dicionário de ferramentas
    """
    mo = getattr(orchestrator, "llm_model_id", None)
    cfg = get_litellm_config(model_override=mo)
    steps = build_steps(orchestrator)

    if step_index >= len(steps):
        return "[ERRO] Índice de etapa inválido."

    st = steps[step_index]
    out = _run_with_tools(
        cfg.model,
        cfg.api_key,
        cfg.api_base,
        st.system,
        st.user,
        st.tools,
        orchestrator.step_callback,
        st.label,
        extra_headers=getattr(cfg, "extra_headers", None),
    )

    orchestrator.ctx.etapa_atual = st.label
    if orchestrator.task_callback:
        try:
            orchestrator.task_callback(
                SimpleNamespace(agent=st.label, raw=out)
            )
        except Exception:
            pass

    return out

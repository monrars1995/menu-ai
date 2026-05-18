"""
Execução em background do pipeline de cardápio (LiteLLM + ferramentas).
"""
from __future__ import annotations

import io
import json
import logging
import os
import queue
import re
import traceback
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

from services import job_state
from services.fichas_db_stats import format_fichas_mensagem, get_fichas_db_stats

logger = logging.getLogger("menuai.jobs")
WORKER_LAUNCH_STUCK_SECONDS = 30.0


def _iso_now() -> str:
    return datetime.utcnow().isoformat()


def _log_job_event(job_id: str, event: str, **fields) -> None:
    payload = {
        "event": event,
        "job_id": job_id,
        "timestamp": _iso_now(),
        **fields,
    }
    logger.info("job_event=%s", json.dumps(payload, ensure_ascii=False, default=str))


def _persist_job_snapshot(
    job_id: str,
    *,
    db_ok: bool,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    error: Optional[str] = None,
    parametros_patch: Optional[dict] = None,
) -> None:
    if not db_ok:
        return
    try:
        from database.connection import SessionLocal
        from database.models import JobAgente

        db = SessionLocal()
        try:
            row = db.query(JobAgente).filter(JobAgente.job_id == job_id).first()
            if not row:
                return
            if status is not None:
                row.status = status
            if progress is not None:
                row.progresso = progress
            if error is not None:
                row.erro = error
            if parametros_patch:
                payload = row.parametros_json if isinstance(row.parametros_json, dict) else {}
                row.parametros_json = {**payload, **parametros_patch}
            row.updated_at = datetime.utcnow()
            db.commit()
        finally:
            db.close()
    except Exception:
        logger.exception("persist_job_snapshot_failed job_id=%s", job_id)


def _mark_job_error(
    job_id: str,
    message: str,
    *,
    db_ok: bool,
    error_type: str,
    timeout_reason: Optional[str] = None,
    progress: Optional[int] = None,
    emit_queue: bool = False,
) -> dict:
    now_iso = _iso_now()
    now_ts = time.time()
    job = job_state.jobs.setdefault(
        job_id,
        {
            "status": "erro",
            "progress": progress or 0,
            "logs": [],
            "result": None,
            "error": message,
            "error_type": error_type,
            "timeout_reason": timeout_reason,
            "config": {},
            "started_at": now_iso,
            "last_update_at": now_iso,
            "started_ts": now_ts,
            "last_update_ts": now_ts,
            "current_step": "erro",
        },
    )
    job["status"] = "erro"
    job["error"] = message
    job["error_type"] = error_type
    job["timeout_reason"] = timeout_reason
    job["progress"] = progress if progress is not None else int(job.get("progress") or 0)
    job["current_step"] = "erro"
    job["last_update_at"] = now_iso
    job["last_update_ts"] = now_ts
    _persist_job_snapshot(
        job_id,
        db_ok=db_ok,
        status="erro",
        progress=job["progress"],
        error=message,
        parametros_patch={
            "error_type": error_type,
            "timeout_reason": timeout_reason,
        },
    )
    if emit_queue:
        q = job_state.job_queues.setdefault(job_id, queue.Queue())
        payload = {
            "type": "error",
            "message": message,
            "progress": job["progress"],
            "error_type": error_type,
            "timeout_reason": timeout_reason,
        }
        job.setdefault("logs", []).append(payload)
        q.put(payload)
    _log_job_event(
        job_id,
        "job_marked_error",
        error_type=error_type,
        timeout_reason=timeout_reason,
        progress=job["progress"],
        error=message,
    )
    return job


def reconcile_runtime_job_state(job_id: str, db_ok: bool) -> Optional[dict]:
    job = job_state.jobs.get(job_id)
    if not job:
        return None
    status = str(job.get("status") or "").strip().lower()
    if status not in {"iniciando", "executando"}:
        return job
    current_step = str(job.get("current_step") or "").strip().lower()
    now_ts = time.time()
    started_ts = float(job.get("started_ts") or now_ts)
    last_update_ts = float(job.get("last_update_ts") or started_ts)
    launch_stuck = (
        status == "iniciando"
        or current_step in {"agendando worker", "iniciando worker", "iniciando"}
    )
    if not launch_stuck:
        return job
    stale_seconds = now_ts - last_update_ts
    if stale_seconds < WORKER_LAUNCH_STUCK_SECONDS:
        return job
    message = (
        "A geração não iniciou corretamente no servidor. "
        "Tente novamente. Se persistir, troque o modelo ou reduza os dias."
    )
    return _mark_job_error(
        job_id,
        message,
        db_ok=db_ok,
        error_type="worker_launch_timeout",
        timeout_reason=f"no_worker_progress_for_{int(WORKER_LAUNCH_STUCK_SECONDS)}s",
        progress=int(job.get("progress") or 0),
        emit_queue=True,
    )


def _hydrate_job_from_db(job_id: str, db_ok: bool) -> bool:
    """Recria entrada em `job_state.jobs` a partir de JobAgente após restart."""
    if not db_ok:
        return False
    db = None
    try:
        from database.connection import SessionLocal
        from database.models import JobAgente

        db = SessionLocal()
        row = db.query(JobAgente).filter(JobAgente.job_id == job_id).first()
        if not row:
            return False
        import queue

        job_state.job_queues.setdefault(job_id, queue.Queue())
        logs = []
        if row.logs_json:
            try:
                logs = list(row.logs_json) if isinstance(row.logs_json, list) else []
            except Exception:
                logs = []
        status = row.status or "desconhecido"
        erro = row.erro
        progress = row.progresso or 0
        if status in {"iniciando", "executando", "aguardando_confirmacao"}:
            status = "erro"
            erro = erro or (
                "Esta geração foi interrompida por reinício/deploy do servidor. "
                "Inicie uma nova geração para continuar."
            )
            if row.status != "erro":
                row.status = "erro"
                row.erro = erro
                row.updated_at = datetime.utcnow()
                db.commit()
        started_at = row.iniciado_em.isoformat() if row.iniciado_em else None
        updated_at = row.updated_at.isoformat() if row.updated_at else _iso_now()
        params = row.parametros_json or {}
        timeout_budget_seconds = None
        if isinstance(params, dict):
            timeout_budget_seconds = params.get("timeout_budget_seconds")
            if timeout_budget_seconds is None:
                timeout_budget_seconds = params.get("budget_seconds")

        job_state.jobs[job_id] = {
            "status": status,
            "progress": progress,
            "logs": logs,
            "result": row.resultado_raw,
            "error": erro,
            "error_type": "job_interrupted_after_restart" if status == "erro" and row.status in {"iniciando", "executando", "aguardando_confirmacao"} else None,
            "timeout_reason": "deploy_or_restart_interruption" if status == "erro" and row.status in {"iniciando", "executando", "aguardando_confirmacao"} else None,
            "config": params,
            "empresa_id": str(row.empresa_id) if row.empresa_id else None,
            "started_at": started_at,
            "last_update_at": updated_at,
            "started_ts": row.iniciado_em.timestamp() if row.iniciado_em else time.time(),
            "last_update_ts": row.updated_at.timestamp() if row.updated_at else time.time(),
            "current_step": "hidratação",
            "timeout_budget_seconds": timeout_budget_seconds,
        }
        _log_job_event(
            job_id,
            "job_rehydrated",
            status=status,
            progress=progress,
            timeout_budget_seconds=timeout_budget_seconds,
        )
        return True
    except Exception:
        return False
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                pass


def get_job_or_restore(job_id: str, db_ok: bool) -> Optional[dict]:
    if job_id in job_state.jobs:
        return reconcile_runtime_job_state(job_id, db_ok)
    if _hydrate_job_from_db(job_id, db_ok):
        return reconcile_runtime_job_state(job_id, db_ok)
    return None


def launch_generation_job(
    job_id: str,
    dias: int,
    target_custo_total: float,
    target_custo_proteico: float,
    restricoes_usuario: str,
    refeicoes: Optional[List[str]],
    empresa_id: Optional[str],
    contrato_id: Optional[str],
    nome_cardapio: Optional[str],
    llm_model: Optional[str],
    generation_mode: Optional[str],
    *,
    upload_dir: Path,
    db_ok: bool,
    contrato_analise_confirmada: bool = False,
) -> threading.Thread:
    now_iso = _iso_now()
    now_ts = time.time()
    job = job_state.jobs.setdefault(
        job_id,
        {
            "status": "iniciando",
            "progress": 0,
            "logs": [],
            "result": None,
            "error": None,
            "config": {},
            "started_at": now_iso,
            "last_update_at": now_iso,
            "started_ts": now_ts,
            "last_update_ts": now_ts,
            "current_step": "iniciando",
        },
    )
    job.setdefault("logs", [])
    job.setdefault("config", {})
    job.setdefault("started_at", now_iso)
    job.setdefault("started_ts", now_ts)
    job["status"] = "executando"
    job["error"] = None
    job["error_type"] = None
    job["timeout_reason"] = None
    job["current_step"] = "agendando worker"
    job["last_update_at"] = now_iso
    job["last_update_ts"] = now_ts
    job_state.job_queues.setdefault(job_id, queue.Queue())
    _persist_job_snapshot(
        job_id,
        db_ok=db_ok,
        status="executando",
        progress=int(job.get("progress") or 0),
        error=None,
        parametros_patch={"launch_mode": "thread"},
    )
    _log_job_event(
        job_id,
        "job_launch_requested",
        generation_mode=generation_mode,
        llm_model=llm_model,
        empresa_id=empresa_id,
        contrato_id=contrato_id,
    )

    def _runner():
        _log_job_event(
            job_id,
            "job_thread_booted",
            thread_name=threading.current_thread().name,
        )
        try:
            executar_crew(
                job_id,
                dias,
                target_custo_total,
                target_custo_proteico,
                restricoes_usuario,
                refeicoes,
                empresa_id,
                contrato_id,
                nome_cardapio,
                llm_model,
                generation_mode,
                upload_dir=upload_dir,
                db_ok=db_ok,
                contrato_analise_confirmada=contrato_analise_confirmada,
            )
        except BaseException as exc:
            logger.exception("job_thread_crashed job_id=%s", job_id)
            _mark_job_error(
                job_id,
                f"Falha ao executar o worker de geração: {exc}",
                db_ok=db_ok,
                error_type="worker_thread_crash",
                timeout_reason="worker_thread_exception",
                progress=int((job_state.jobs.get(job_id) or {}).get("progress") or 0),
                emit_queue=True,
            )

    worker = threading.Thread(
        target=_runner,
        name=f"menuai-job-{job_id}",
        daemon=True,
    )
    try:
        worker.start()
    except Exception as exc:
        logger.exception("job_thread_start_failed job_id=%s", job_id)
        _mark_job_error(
            job_id,
            f"Falha ao iniciar o worker de geração: {exc}",
            db_ok=db_ok,
            error_type="worker_launch_failed",
            timeout_reason="worker_thread_start_failed",
            progress=int(job.get("progress") or 0),
            emit_queue=True,
        )
        raise
    return worker


def executar_crew(
    job_id: str,
    dias: int,
    target_custo_total: float,
    target_custo_proteico: float,
    restricoes_usuario: str,
    refeicoes: Optional[List[str]],
    empresa_id: Optional[str],
    contrato_id: Optional[str],
    nome_cardapio: Optional[str],
    llm_model: Optional[str],
    generation_mode: Optional[str],
    *,
    upload_dir: Path,
    db_ok: bool,
    contrato_analise_confirmada: bool = False,
):
    started_ts = time.time()
    q = job_state.job_queues[job_id]
    job = job_state.jobs.get(job_id)
    if job is None:
        job_state.jobs[job_id] = {
            "status": "iniciando",
            "progress": 0,
            "logs": [],
            "result": None,
            "error": None,
            "config": {},
            "started_at": _iso_now(),
            "last_update_at": _iso_now(),
            "started_ts": started_ts,
            "last_update_ts": started_ts,
            "current_step": "iniciando",
        }
    else:
        job.setdefault("started_at", _iso_now())
        job.setdefault("started_ts", started_ts)
        job.setdefault("last_update_at", _iso_now())
        job.setdefault("last_update_ts", started_ts)
        job.setdefault("current_step", "iniciando")

    AGENTES = [
        "Coordenador",
        "Analista de Contratos",
        "Gestor de Fichas Técnicas",
        "Nutricionista",
        "Analista Nutricional",
        "Controller Financeiro",
        "Agente de Compras",
        "Exportador",
    ]
    stuck_threshold_raw = (os.getenv("MENUAI_JOB_STUCK_SECONDS") or "90").strip()
    try:
        stuck_threshold_seconds = max(30.0, float(stuck_threshold_raw))
    except ValueError:
        stuck_threshold_seconds = 90.0
    generation_mode_effective = (generation_mode or os.getenv("MENUAI_GENERATION_MODE", "fast") or "fast").strip().lower()
    if generation_mode_effective == "fast":
        fast_attempt_timeout_raw = (os.getenv("MENUAI_FAST_LLM_ATTEMPT_TIMEOUT_SECONDS") or "45").strip()
        fast_max_attempts_raw = (os.getenv("MENUAI_FAST_LLM_MAX_ATTEMPTS") or "2").strip()
        try:
            fast_attempt_timeout = max(20.0, float(fast_attempt_timeout_raw))
        except ValueError:
            fast_attempt_timeout = 45.0
        try:
            fast_max_attempts = max(1, int(fast_max_attempts_raw))
        except ValueError:
            fast_max_attempts = 2
        # Evita falso positivo do watchdog durante chamadas LLM longas com fallback.
        stuck_threshold_seconds = max(
            stuck_threshold_seconds,
            (fast_attempt_timeout * fast_max_attempts) + 25.0,
        )

    watchdog_stop = threading.Event()

    def emit(type_: str, **kw):
        msg = {"type": type_, **kw}
        job_state.jobs[job_id]["logs"].append(msg)
        job_state.jobs[job_id]["last_update_at"] = _iso_now()
        job_state.jobs[job_id]["last_update_ts"] = time.time()
        q.put(msg)
        if type_ in {"done", "error"}:
            _log_job_event(
                job_id,
                f"job_{type_}",
                progress=job_state.jobs[job_id].get("progress"),
                step=job_state.jobs[job_id].get("current_step"),
                error_type=kw.get("error_type"),
                timeout_reason=kw.get("timeout_reason"),
            )

    def ensure_not_aborted():
        current = job_state.jobs.get(job_id) or {}
        if current.get("status") == "erro":
            raise RuntimeError(current.get("error") or "Job interrompido por timeout/watchdog.")

    def progress(pct: int, msg: str, agent: str = "Sistema", step_label: Optional[str] = None):
        ensure_not_aborted()
        job_state.jobs[job_id]["progress"] = pct
        job_state.jobs[job_id]["status"] = "executando"
        job_state.jobs[job_id]["current_step"] = step_label or msg
        job_state.jobs[job_id]["last_update_at"] = _iso_now()
        job_state.jobs[job_id]["last_update_ts"] = time.time()
        emit("log", agent=agent, message=msg, progress=pct)
        _log_job_event(
            job_id,
            "job_progress",
            step_label=step_label or msg,
            progress=pct,
            agent=agent,
            elapsed_ms=int((time.time() - started_ts) * 1000),
        )
        if db_ok:
            try:
                from database.connection import SessionLocal
                from database.models import JobAgente

                db = SessionLocal()
                job_db = db.query(JobAgente).filter(JobAgente.job_id == job_id).first()
                if job_db:
                    job_db.progresso = pct
                    job_db.status = "executando"
                    job_db.updated_at = datetime.utcnow()
                    db.commit()
                db.close()
            except Exception:
                pass

    def _watchdog_loop():
        while not watchdog_stop.wait(5):
            j = job_state.jobs.get(job_id)
            if not j:
                return
            if j.get("status") != "executando":
                continue
            last_update_ts = float(j.get("last_update_ts") or started_ts)
            stale_seconds = time.time() - last_update_ts
            if stale_seconds <= stuck_threshold_seconds:
                continue
            msg = (
                "Geração interrompida por falta de progresso do servidor. "
                "Tente novamente, troque o modelo ou reduza os dias."
            )
            j["status"] = "erro"
            j["error"] = msg
            j["error_type"] = "stuck_job_watchdog"
            j["timeout_reason"] = f"no_progress_for_{int(stuck_threshold_seconds)}s"
            j["last_update_at"] = _iso_now()
            j["last_update_ts"] = time.time()
            emit(
                "error",
                message=msg,
                error_type="stuck_job_watchdog",
                timeout_reason=j["timeout_reason"],
                progress=j.get("progress", 0),
            )
            _log_job_event(
                job_id,
                "watchdog_triggered",
                stale_seconds=round(stale_seconds, 2),
                threshold_seconds=stuck_threshold_seconds,
                progress=j.get("progress", 0),
            )
            if db_ok:
                try:
                    from database.connection import SessionLocal
                    from database.models import JobAgente

                    db_wd = SessionLocal()
                    job_db_wd = db_wd.query(JobAgente).filter(JobAgente.job_id == job_id).first()
                    if job_db_wd:
                        job_db_wd.status = "erro"
                        job_db_wd.erro = msg
                        job_db_wd.updated_at = datetime.utcnow()
                        db_wd.commit()
                    db_wd.close()
                except Exception:
                    pass
            return

    watchdog_thread = threading.Thread(
        target=_watchdog_loop,
        name=f"job-watchdog-{job_id}",
        daemon=True,
    )

    try:
        job_state.jobs[job_id]["status"] = "executando"
        job_state.jobs[job_id]["current_step"] = "iniciando worker"
        job_state.jobs[job_id]["last_update_at"] = _iso_now()
        job_state.jobs[job_id]["last_update_ts"] = time.time()
        _log_job_event(
            job_id,
            "job_worker_started",
            generation_mode=generation_mode_effective,
            llm_model=llm_model,
            contrato_id=contrato_id,
            empresa_id=empresa_id,
            stuck_threshold_seconds=stuck_threshold_seconds,
        )
        watchdog_thread.start()
        progress(5, "🚀 Iniciando enxame de agentes...", "Sistema", "inicialização do worker")

        contrato_path = None
        contrato_regras_db = None
        if db_ok and contrato_id:
            try:
                from database.connection import SessionLocal
                from database.models import Contrato

                db = SessionLocal()
                contrato_db = db.query(Contrato).filter(Contrato.id == contrato_id).first()
                if contrato_db and contrato_db.arquivo_path:
                    contrato_path = contrato_db.arquivo_path
                if contrato_db and contrato_db.regras_json:
                    contrato_regras_db = contrato_db.regras_json
                db.close()
            except Exception:
                pass

        if not contrato_path:
            for ext in (".pdf", ".xlsx", ".xls", ".docx", ".txt", ".md", ".rtf"):
                cand = upload_dir / f"contrato{ext}"
                if cand.exists():
                    contrato_path = str(cand)
                    break

        if contrato_path:
            progress(10, f"📄 Contrato carregado: {Path(contrato_path).name}", "Sistema", "carregando contrato")
        else:
            progress(10, "⚠️ Nenhum contrato — usando configurações padrão", "Sistema", "sem contrato")

        stats = get_fichas_db_stats(empresa_id=empresa_id) if db_ok else None
        progress(12, format_fichas_mensagem(stats, empresa_id=empresa_id), "Sistema", "carregando base de fichas")

        emit(
            "agents_ready",
            agents=AGENTES,
            config={
                "dias": dias,
                "target_custo_total": target_custo_total,
                "target_custo_proteico": target_custo_proteico,
                "refeicoes": refeicoes,
                "llm_model": llm_model,
                "generation_mode": generation_mode or os.getenv("MENUAI_GENERATION_MODE", "fast"),
            },
        )

        task_progress = [15]

        def on_task_complete(task_output):
            pct = min(task_progress[0] + 20, 92)
            task_progress[0] = pct
            agent_name = getattr(task_output, "agent", "Agente")
            raw = str(getattr(task_output, "raw", "") or "")
            preview = raw[:400].replace("\n", " ")
            progress(pct, f"✅ Concluído: {agent_name}", agent=str(agent_name))
            emit("task_complete", agent=str(agent_name), preview=preview, progress=pct)

        def on_step_complete(step, **kwargs):
            text = ""
            if hasattr(step, "thought") and step.thought:
                text = step.thought
            elif hasattr(step, "log") and step.log:
                text = step.log
            elif hasattr(step, "text") and step.text:
                text = step.text
            elif isinstance(step, tuple) and len(step) > 0 and hasattr(step[0], "log"):
                text = step[0].log
            else:
                text = str(step)
            if text:
                text = re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", text)
                preview = text[:500].replace("\n", " ").strip()
                if preview:
                    agent_name = kwargs.get("agent_name", "")
                    emit("agent_thought", thought=preview, agent=agent_name)

        progress(15, "🏁 Orquestrando agentes...", "Coordenador", "orquestração")

        from pipeline.orchestrator import MenuOrchestrator

        crew = MenuOrchestrator(
            contrato_path=contrato_path,
            dias=dias,
            target_custo_total=target_custo_total,
            target_custo_proteico=target_custo_proteico,
            restricoes_usuario=restricoes_usuario,
            refeicoes=refeicoes,
            empresa_id=empresa_id,
            contrato_id=contrato_id,
            task_callback=on_task_complete,
            step_callback=on_step_complete,
            db_disponivel=db_ok,
            llm_model_id=llm_model,
        )
        crew._job_id = job_id

        # ============================================================
        # Human-in-the-Loop: pausa para confirmação após contrato
        # ============================================================
        # Fase 1: Análise do contrato (se disponível)
        resumo_contrato = None
        analise_pre_confirmada = bool(contrato_analise_confirmada and contrato_regras_db)
        if contrato_regras_db:
            crew.ctx.regras_contrato = contrato_regras_db

        if analise_pre_confirmada:
            crew.skip_contract_analysis = True
            progress(20, "📋 Análise do contrato já confirmada. Usando regras extraídas.", "Analista de Contratos", "reutilizando análise confirmada")
            progress(40, "🏁 Contexto confirmado. Iniciando montagem do cardápio...", "Sistema", "preparando geração")
        elif contrato_path:
            try:
                progress(20, "📋 Analisando contrato...", "Analista de Contratos", "análise de contrato")
                resumo_contrato = crew.analisar_contrato_apenas()
                progress(35, "📋 Análise do contrato concluída. Aguardando confirmação.", "Sistema", "aguardando confirmação")
            except Exception as e_contrato:
                progress(20, f"⚠️ Erro na análise do contrato: {e_contrato}", "Sistema", "erro na análise")
                resumo_contrato = {"erro": str(e_contrato)}

        if resumo_contrato and contrato_path:
            # Muda status para aguardando confirmação
            job_state.jobs[job_id]["status"] = "aguardando_confirmacao"
            job_state.jobs[job_id]["resumo_contrato"] = resumo_contrato
            emit(
                "aguardando_confirmacao",
                message="Análise do contrato concluída. Aguardando confirmação do usuário.",
                resumo=resumo_contrato if isinstance(resumo_contrato, dict) else {"texto": str(resumo_contrato)[:2000]},
                progress=35,
            )

            # Atualiza DB
            if db_ok:
                try:
                    from database.connection import SessionLocal
                    from database.models import JobAgente
                    db_wait = SessionLocal()
                    job_db_wait = db_wait.query(JobAgente).filter(JobAgente.job_id == job_id).first()
                    if job_db_wait:
                        job_db_wait.status = "executando"
                        job_db_wait.progresso = 35
                        job_db_wait.updated_at = datetime.utcnow()
                        db_wait.commit()
                    db_wait.close()
                except Exception:
                    pass

            # Loop de espera (max 30 min)
            _wait_start = time.time()
            _MAX_WAIT_SECONDS = 30 * 60  # 30 minutos

            while job_state.jobs[job_id].get("status") == "aguardando_confirmacao":
                time.sleep(2)
                elapsed = time.time() - _wait_start
                if elapsed > _MAX_WAIT_SECONDS:
                    job_state.jobs[job_id]["status"] = "erro"
                    job_state.jobs[job_id]["error"] = "Timeout: confirmação não recebida em 30 minutos."
                    progress(0, "⏰ Timeout: confirmação não recebida.", "Sistema")
                    emit("error", message="Timeout aguardando confirmação do usuário.")
                    return

            # Aplica ajustes do usuário se fornecidos
            ajustes_usuario = job_state.jobs[job_id].get("ajustes_usuario", "")
            if ajustes_usuario:
                crew.aplicar_ajustes_usuario(ajustes_usuario)
                progress(38, f"📝 Ajustes do usuário aplicados.", "Sistema", "aplicando ajustes")

            progress(40, "🏁 Confirmação recebida! Continuando geração...", "Sistema", "retomando geração")

        mode = (generation_mode or os.getenv("MENUAI_GENERATION_MODE", "fast") or "fast").strip().lower()
        if mode not in {"fast", "full"}:
            mode = "fast"

        if mode == "fast":
            from services.fast_generation import run_fast_generation

            fast_result = run_fast_generation(
                job_id=job_id,
                dias=dias,
                target_custo_total=target_custo_total,
                target_custo_proteico=target_custo_proteico,
                restricoes_usuario=restricoes_usuario,
                refeicoes=refeicoes,
                empresa_id=empresa_id,
                contrato_id=contrato_id,
                nome_cardapio=nome_cardapio,
                llm_model=llm_model,
                regras_contrato=crew.ctx.regras_contrato or contrato_regras_db or {},
                started_ts=started_ts,
                progress=progress,
            )
            result = fast_result["markdown"]
            job_state.jobs[job_id]["status"] = "concluido"
            job_state.jobs[job_id]["result"] = result
            job_state.jobs[job_id]["progress"] = 100
            job_state.jobs[job_id]["current_step"] = "concluído"
            job_state.jobs[job_id]["last_update_at"] = _iso_now()
            job_state.jobs[job_id]["last_update_ts"] = time.time()
            emit(
                "log",
                agent="Sistema",
                message="🎉 Cardápio gerado com sucesso no modo rápido.",
                progress=100,
            )
            emit(
                "done",
                result=result,
                progress=100,
                cardapio_id=fast_result.get("cardapio_id"),
                duration_seconds=fast_result.get("duration_seconds"),
                attempts=fast_result.get("attempts"),
                model_used=fast_result.get("model_used"),
                provider=fast_result.get("provider_used"),
            )
            return

        result = str(crew.run())

        # Persistir regras extraídas do contrato no DB
        if db_ok and contrato_id and crew.ctx.regras_contrato:
            try:
                from database.connection import SessionLocal
                from database.models import Contrato

                db2 = SessionLocal()
                ctr = db2.query(Contrato).filter(Contrato.id == contrato_id).first()
                if ctr:
                    regras = crew.ctx.regras_contrato
                    ctr.regras_json = regras
                    ctr.gramaturas_json = regras.get("gramaturas", ctr.gramaturas_json)
                    ctr.incidencias_json = regras.get("incidencias", ctr.incidencias_json)
                    ctr.proibicoes_json = regras.get("proibicoes", ctr.proibicoes_json)
                    db2.commit()
                db2.close()
            except Exception:
                pass

        job_state.jobs[job_id]["status"] = "concluido"
        job_state.jobs[job_id]["result"] = result
        job_state.jobs[job_id]["progress"] = 100
        job_state.jobs[job_id]["current_step"] = "concluído"
        job_state.jobs[job_id]["last_update_at"] = _iso_now()
        job_state.jobs[job_id]["last_update_ts"] = time.time()

        progress(100, "🎉 Cardápio gerado com sucesso!", "Sistema", "concluído")
        emit("done", result=result, progress=100)

        if db_ok:
            try:
                from database.connection import SessionLocal
                from database.models import Cardapio, JobAgente
                from services.knowledge_hooks import sync_cardapio_document_async

                db = SessionLocal()
                job_db = db.query(JobAgente).filter(JobAgente.job_id == job_id).first()
                nome = nome_cardapio or f"Cardápio {dias} dias — {job_id}"
                cardapio_db = None
                if empresa_id:
                    cardapio_db = Cardapio(
                        empresa_id=empresa_id,
                        contrato_id=contrato_id,
                        nome=nome,
                        status="rascunho",
                        num_dias=dias,
                        resultado_raw=result,
                        job_id=job_id,
                        parametros_json={
                            "dias": dias,
                            "target_custo_total": target_custo_total,
                            "target_custo_proteico": target_custo_proteico,
                            "llm_model": llm_model,
                            "generation_mode": "full",
                            "duration_seconds": round(time.time() - started_ts, 2),
                        },
                        updated_at=datetime.utcnow(),
                    )
                    db.add(cardapio_db)
                    db.flush()
                if job_db:
                    job_db.status = "concluido"
                    job_db.progresso = 100
                    job_db.resultado_raw = result
                    if cardapio_db is not None:
                        job_db.cardapio_id = cardapio_db.id
                    job_db.concluido_em = datetime.utcnow()
                    job_db.updated_at = datetime.utcnow()
                db.commit()
                if cardapio_db is not None:
                    sync_cardapio_document_async(str(cardapio_db.id))
                db.close()
                if empresa_id:
                    print(f"✅ Cardápio e job salvos no banco (job_id={job_id})")
            except Exception as e:
                print(f"⚠️  Erro ao salvar no banco: {e}")

    except Exception as exc:
        err = str(exc)
        job_state.jobs[job_id]["status"] = "erro"
        job_state.jobs[job_id]["error"] = err
        err_type = getattr(exc, "error_type", None) or "generation_failed"
        timeout_reason = getattr(exc, "timeout_reason", None)
        job_state.jobs[job_id]["error_type"] = err_type
        job_state.jobs[job_id]["timeout_reason"] = timeout_reason
        job_state.jobs[job_id]["last_update_at"] = _iso_now()
        job_state.jobs[job_id]["last_update_ts"] = time.time()
        emit(
            "error",
            message=err,
            detail=traceback.format_exc(),
            error_type=err_type,
            timeout_reason=timeout_reason,
            progress=job_state.jobs[job_id].get("progress", 0),
        )
        _log_job_event(
            job_id,
            "job_failed",
            error_type=err_type,
            timeout_reason=timeout_reason,
            error=err,
            elapsed_ms=int((time.time() - started_ts) * 1000),
        )

        if db_ok:
            try:
                from database.connection import SessionLocal
                from database.models import JobAgente

                db = SessionLocal()
                job_db = db.query(JobAgente).filter(JobAgente.job_id == job_id).first()
                if job_db:
                    job_db.status = "erro"
                    job_db.erro = err
                    job_db.updated_at = datetime.utcnow()
                    db.commit()
                db.close()
            except Exception:
                pass
    finally:
        watchdog_stop.set()

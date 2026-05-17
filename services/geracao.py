"""
Execução em background do pipeline de cardápio (LiteLLM + ferramentas).
"""
from __future__ import annotations

import io
import json
import os
import re
import traceback
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

from services import job_state
from services.fichas_db_stats import format_fichas_mensagem, get_fichas_db_stats


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
        job_state.jobs[job_id] = {
            "status": status,
            "progress": progress,
            "logs": logs,
            "result": row.resultado_raw,
            "error": erro,
            "config": row.parametros_json or {},
            "empresa_id": str(row.empresa_id) if row.empresa_id else None,
        }
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
        return job_state.jobs[job_id]
    if _hydrate_job_from_db(job_id, db_ok):
        return job_state.jobs.get(job_id)
    return None


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

    def emit(type_: str, **kw):
        msg = {"type": type_, **kw}
        job_state.jobs[job_id]["logs"].append(msg)
        q.put(msg)

    def progress(pct: int, msg: str, agent: str = "Sistema"):
        job_state.jobs[job_id]["progress"] = pct
        emit("log", agent=agent, message=msg, progress=pct)
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

    try:
        job_state.jobs[job_id]["status"] = "executando"
        progress(5, "🚀 Iniciando enxame de agentes...")

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
            for ext in (".pdf", ".xlsx", ".xls"):
                cand = upload_dir / f"contrato{ext}"
                if cand.exists():
                    contrato_path = str(cand)
                    break

        if contrato_path:
            progress(10, f"📄 Contrato carregado: {Path(contrato_path).name}")
        else:
            progress(10, "⚠️ Nenhum contrato — usando configurações padrão")

        stats = get_fichas_db_stats(empresa_id=empresa_id) if db_ok else None
        progress(12, format_fichas_mensagem(stats, empresa_id=empresa_id))

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

        progress(15, "🏁 Orquestrando agentes...", "Coordenador")

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
            progress(20, "📋 Análise do contrato já confirmada. Usando regras extraídas.", "Analista de Contratos")
            progress(40, "🏁 Contexto confirmado. Iniciando montagem do cardápio...", "Sistema")
        elif contrato_path:
            try:
                progress(20, "📋 Analisando contrato...", "Analista de Contratos")
                resumo_contrato = crew.analisar_contrato_apenas()
                progress(35, "📋 Análise do contrato concluída. Aguardando confirmação.", "Sistema")
            except Exception as e_contrato:
                progress(20, f"⚠️ Erro na análise do contrato: {e_contrato}", "Sistema")
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
            import asyncio
            import time
            _wait_start = time.time()
            _MAX_WAIT_SECONDS = 30 * 60  # 30 minutos

            while job_state.jobs[job_id].get("status") == "aguardando_confirmacao":
                import time as _t
                _t.sleep(2)
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
                progress(38, f"📝 Ajustes do usuário aplicados.", "Sistema")

            progress(40, "🏁 Confirmação recebida! Continuando geração...", "Sistema")

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
            emit(
                "log",
                agent="Sistema",
                message="🎉 Cardápio gerado com sucesso no modo rápido.",
                progress=100,
            )
            emit("done", result=result, progress=100, cardapio_id=fast_result.get("cardapio_id"))
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

        progress(100, "🎉 Cardápio gerado com sucesso!")
        emit("done", result=result, progress=100)

        if db_ok:
            try:
                from database.connection import SessionLocal
                from database.models import Cardapio, JobAgente
                from services.knowledge_base import sync_cardapio_document
                from services.knowledge_hooks import sync_knowledge_safe

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
                if cardapio_db is not None:
                    sync_knowledge_safe(sync_cardapio_document, db, cardapio_db)
                db.commit()
                db.close()
                if empresa_id:
                    print(f"✅ Cardápio e job salvos no banco (job_id={job_id})")
            except Exception as e:
                print(f"⚠️  Erro ao salvar no banco: {e}")

    except Exception as exc:
        err = str(exc)
        job_state.jobs[job_id]["status"] = "erro"
        job_state.jobs[job_id]["error"] = err
        progress(0, f"❌ Erro: {err}")
        emit("error", message=err, detail=traceback.format_exc())

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

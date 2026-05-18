
"""
Menu.AI — Backend FastAPI v3.6.19
Pipeline LLM + ferramentas + Banco de Dados PostgreSQL/Supabase + Multi-Tenant
"""
import io
import asyncio
import json
import logging
import os
import queue
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

load_dotenv()

APP_VERSION = "3.6.22"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
_DEFAULT_SECRET = "menuai-secret-key-change-in-production-2026"
SECRET_KEY = os.getenv("SECRET_KEY", _DEFAULT_SECRET)
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
DEMO_GERAR_SEM_AUTH = os.getenv("DEMO_GERAR_SEM_AUTH", "false").lower() == "true"
ALLOW_OPEN_REGISTRO = os.getenv("ALLOW_OPEN_REGISTRO", "false").lower() == "true"
_ENV_DATABASE_URL = (os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL") or "").strip().lower()
_DEFAULT_CREATE_ALL = "true" if (DEBUG and _ENV_DATABASE_URL.startswith("sqlite")) else "false"
CREATE_ALL_ON_START = os.getenv("CREATE_ALL_ON_START", _DEFAULT_CREATE_ALL).lower() == "true"
# Empresa de demo/seed (mesmo UUID que seed_data.py) — usada só com DEBUG + DEMO_GERAR_SEM_AUTH sem JWT
DEFAULT_EMPRESA_ID = os.getenv("DEFAULT_EMPRESA_ID", "00000000-0000-0000-0000-000000000001").strip()

if not DEBUG and SECRET_KEY == _DEFAULT_SECRET:
    raise RuntimeError(
        "Defina SECRET_KEY no ambiente (valor forte) antes de subir fora de DEBUG."
    )

# ============================================================
# App FastAPI
# ============================================================
app = FastAPI(
    title="Menu.AI",
    version=APP_VERSION,
    description="Sistema inteligente de planejamento de cardápios para refeições coletivas.",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)
logger = logging.getLogger("menuai.app")


class _SkipHealthcheckAccessLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        return "/api/health" not in msg


logging.getLogger("uvicorn.access").addFilter(_SkipHealthcheckAccessLogFilter())
limiter = Limiter(key_func=get_remote_address, default_limits=[])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

cors_effective = CORS_ORIGINS if CORS_ORIGINS else (["*"] if DEBUG else ["http://localhost:8000", "http://127.0.0.1:8000"])
if not CORS_ORIGINS and not DEBUG:
    print("⚠️  CORS_ORIGINS vazio em produção — a usar origens locais. Defina CORS_ORIGINS no .env.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_effective,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Diretórios
# ============================================================
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
DATA_DIR = BASE_DIR / "data"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "uploads" / "contratos").mkdir(parents=True, exist_ok=True)

# ============================================================
# Banco de Dados — inicialização
# ============================================================
try:
    from database.connection import criar_tabelas, verificar_conexao, get_db
    from database.models import JobAgente, Cardapio, Usuario

    _db_ok = verificar_conexao()
    if _db_ok and CREATE_ALL_ON_START:
        try:
            criar_tabelas()
            print("✅ Banco conectado — tabelas verificadas (create_all; em produção prefira Alembic).")
        except Exception as ex:
            print(f"⚠️  criar_tabelas: {ex}")
    elif _db_ok:
        print("✅ Banco conectado — CREATE_ALL_ON_START=false (use `alembic upgrade head`).")
    else:
        print("⚠️  Banco de dados indisponível — rodando em modo sem banco.")
except Exception as e:
    print(f"⚠️  Módulo database inacessível: {e}")
    _db_ok = False

# ============================================================
# Routers
# ============================================================
import httpx
from routers.auth_supabase import router as auth_router, decodificar_token
# Legacy auth fallback (mantido para referência)
# from routers.auth import router as auth_router_legacy
from routers.empresas import router as empresas_router
from routers.contratos import router as contratos_router
from routers.ingredientes import router as ingredientes_router
from routers.fichas_tecnicas import router as fichas_router
from routers.cardapios import router as cardapios_router
from routers.knowledge import router as knowledge_router
from routers.chat import router as chat_router
from database.schemas import GerarCardapioRequest

# Admin routers (disponíveis no app principal para consumo pelo Next.js admin)
from admin.routers.meta import router as admin_meta_router
from admin.routers.llm_admin import router as admin_llm_router
from admin.routers.knowledge_admin import router as admin_knowledge_router

app.include_router(auth_router)
app.include_router(empresas_router)
app.include_router(contratos_router)
app.include_router(ingredientes_router)
app.include_router(fichas_router)
app.include_router(cardapios_router)
app.include_router(knowledge_router)
app.include_router(chat_router)
app.include_router(admin_meta_router)
app.include_router(admin_llm_router)
app.include_router(admin_knowledge_router)

# ============================================================
# Jobs (memória) — módulo partilhado
# ============================================================
from services import job_state

jobs = job_state.jobs
job_queues = job_state.job_queues

_bearer_ger = HTTPBearer(auto_error=False)

_SUPABASE_VALIDATION_URL = os.getenv("SUPABASE_URL", "")
_SUPABASE_SERVICE_ROLE = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


def _status_payload(job_id: str, job_data: dict) -> dict:
    started_at = job_data.get("started_at")
    last_update_at = job_data.get("last_update_at")
    started_ts = job_data.get("started_ts")
    elapsed_seconds = None
    if isinstance(started_ts, (int, float)):
        elapsed_seconds = max(0, int(time.time() - float(started_ts)))
    elif started_at:
        try:
            elapsed_seconds = max(0, int((datetime.utcnow() - datetime.fromisoformat(str(started_at))).total_seconds()))
        except Exception:
            elapsed_seconds = None

    config = job_data.get("config") if isinstance(job_data.get("config"), dict) else {}
    return {
        "job_id": job_id,
        "status": job_data.get("status"),
        "progress": job_data.get("progress", job_data.get("progresso", 0)),
        "error": job_data.get("error") or job_data.get("erro"),
        "error_type": job_data.get("error_type"),
        "timeout_reason": job_data.get("timeout_reason"),
        "result": job_data.get("result"),
        "last_update_at": last_update_at,
        "elapsed_seconds": elapsed_seconds,
        "current_step": job_data.get("current_step"),
        "timeout_budget_seconds": job_data.get("timeout_budget_seconds"),
        "config": config,
        "generator_model": job_data.get("generator_model") or config.get("generator_model_used"),
        "generator_provider": job_data.get("generator_provider") or config.get("generator_provider_used"),
        "review_model": job_data.get("review_model") or config.get("review_model_used"),
        "review_provider": job_data.get("review_provider") or config.get("review_provider_used"),
        "review_status": job_data.get("review_status") or config.get("review_status"),
        "review_summary": job_data.get("review_summary") or config.get("review_summary"),
        "review_warnings": job_data.get("review_warnings") or config.get("review_warnings") or [],
        "review_applied_fixes_count": job_data.get("review_applied_fixes_count") or config.get("review_applied_fixes_count") or 0,
        "degraded_generation": bool(job_data.get("degraded_generation") if job_data.get("degraded_generation") is not None else config.get("degraded_generation")),
    }


def _validate_token_remote(token: str) -> Optional[dict]:
    """Valida token via /auth/v1/user do Supabase (fallback sync)."""
    if not _SUPABASE_VALIDATION_URL or not _SUPABASE_SERVICE_ROLE:
        return None
    try:
        with httpx.Client(timeout=5.0) as client:
            res = client.get(
                f"{_SUPABASE_VALIDATION_URL}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": _SUPABASE_SERVICE_ROLE,
                },
            )
            if res.status_code == 200:
                data = res.json()
                return {"sub": data.get("id"), "email": data.get("email")}
    except Exception as e:
        print(f"⚠️  Remote token validation failed: {e}")
    return None


def _decode_token_with_fallback(token: str) -> Optional[dict]:
    """Tenta decodificar localmente, senão valida remotamente via Supabase."""
    payload = decodificar_token(token)
    if not payload:
        payload = _validate_token_remote(token)
    return payload


def get_usuario_geracao(
    request: Request,
    db: Session = Depends(get_db),
    cred: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_ger),
) -> Optional[Usuario]:
    raw = None
    if cred and cred.credentials:
        raw = cred.credentials
    if not raw:
        raw = request.query_params.get("access_token")
    if DEBUG and DEMO_GERAR_SEM_AUTH and not raw:
        return None
    if not raw:
        raise HTTPException(
            status_code=401,
            detail="Token não fornecido. Use: Authorization: Bearer <token> ou ?access_token= (ex.: EventSource).",
        )
    payload = _decode_token_with_fallback(raw)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
    u = (
        db.query(Usuario)
        .filter(Usuario.id == payload.get("sub"), Usuario.ativo == True)
        .first()
    )
    if not u:
        raise HTTPException(status_code=401, detail="Utilizador não encontrado ou inativo.")
    return u


def alinhar_empresa(
    request_empresa_id: Optional[str],
    usuario: Optional[Usuario],
) -> None:
    if not usuario:
        return
    if not request_empresa_id:
        return
    if getattr(usuario, "role", None) == "super_admin":
        return
    if str(getattr(usuario, "empresa_id", None) or "") != str(request_empresa_id):
        raise HTTPException(403, "empresa_id não corresponde ao utilizador autenticado.")


def _empresa_id_efetivo_gerar(
    body: GerarCardapioRequest,
    usuario: Optional[Usuario],
) -> Optional[str]:
    """preenche empresa a partir do JWT se o body não enviar (ferramentas SQL + persistência)."""
    if body.empresa_id and str(body.empresa_id).strip():
        return str(body.empresa_id).strip()
    if usuario is not None and getattr(usuario, "empresa_id", None) is not None:
        return str(usuario.empresa_id)
    if DEBUG and DEMO_GERAR_SEM_AUTH and usuario is None and DEFAULT_EMPRESA_ID:
        return DEFAULT_EMPRESA_ID
    return None


def _raw_access_token(
    request: Request,
    cred: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    if cred and cred.credentials:
        return cred.credentials
    q_token = request.query_params.get("access_token")
    return q_token.strip() if q_token else None


def _resolve_info_scope(
    request: Request,
    db: Session,
    cred: Optional[HTTPAuthorizationCredentials],
    empresa_id: Optional[str],
    scope: str,
) -> tuple[Optional[str], str, Optional[Usuario], Optional[str]]:
    raw = _raw_access_token(request, cred)
    if raw:
        payload = _decode_token_with_fallback(raw)
        if not payload:
            raise HTTPException(status_code=401, detail="Token inválido ou expirado.")
        usuario = (
            db.query(Usuario)
            .filter(Usuario.id == payload.get("sub"), Usuario.ativo == True)
            .first()
        )
        if not usuario:
            raise HTTPException(status_code=401, detail="Utilizador não encontrado ou inativo.")

        scope_normalized = (scope or "").strip().lower()
        requested_empresa = str(empresa_id).strip() if empresa_id else None
        if usuario.role == "super_admin":
            if scope_normalized == "global":
                return None, "global", usuario, None
            if requested_empresa:
                return requested_empresa, "empresa", usuario, requested_empresa
            if usuario.empresa_id:
                eid = str(usuario.empresa_id)
                return eid, "empresa", usuario, None
            return None, "indefinido", usuario, "Super admin sem empresa no contexto. Use ?scope=global ou informe empresa_id."

        eid = str(usuario.empresa_id or "").strip() or None
        if requested_empresa and requested_empresa != eid:
            raise HTTPException(status_code=403, detail="empresa_id não corresponde ao utilizador autenticado.")
        return eid, "empresa", usuario, None

    if DEBUG and DEMO_GERAR_SEM_AUTH and DEFAULT_EMPRESA_ID:
        return DEFAULT_EMPRESA_ID, "demo", None, None
    return None, "anonimo", None, "Contexto da empresa indisponível sem autenticação."


# ============================================================
# ROTAS PRINCIPAIS
# ============================================================

@app.get("/")
async def index():
    return {"message": "Menu.AI API", "version": APP_VERSION, "docs": "/api/docs"}


@app.get("/api/info")
async def info(
    request: Request,
    empresa_id: Optional[str] = None,
    scope: str = "empresa",
    db: Session = Depends(get_db),
    cred: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_ger),
):
    """Estatísticas de fichas técnicas (SQL) e estado do sistema (db + cache TTL)."""
    from services.fichas_db_stats import get_fichas_db_stats

    status_db = "conectado" if _db_ok else "desconectado"
    from database.connection import DB_PROVIDER
    body: dict = {
        "db_status": status_db,
        "versao": APP_VERSION,
        "base_dados": "sql",
        "db_provider": DB_PROVIDER,
    }
    if not _db_ok:
        return {
            **body,
            "error": "banco indisponível",
            "total_pratos": 0,
            "total_fichas": 0,
            "categorias": {},
        }
    resolved_empresa_id, resolved_scope, usuario, scope_error = _resolve_info_scope(
        request,
        db,
        cred,
        empresa_id,
        scope,
    )
    if scope_error:
        return {
            **body,
            "scope": resolved_scope,
            "empresa_id": resolved_empresa_id,
            "error": scope_error,
            "total_pratos": 0,
            "total_fichas": 0,
            "total_ingredientes": 0,
            "categorias": {},
        }

    st = get_fichas_db_stats(empresa_id=resolved_empresa_id)
    if st.get("ok"):
        return {
            **body,
            "scope": resolved_scope,
            "empresa_id": resolved_empresa_id,
            "usuario_id": str(usuario.id) if usuario else None,
            "total_pratos": st.get("total_pratos", st.get("total_fichas", 0)),
            "total_fichas": st.get("total_fichas", 0),
            "total_ingredientes": st.get("total_ingredientes", 0),
            "categorias": st.get("categorias", {}),
            "fichas_stats_cached": st.get("cached", False),
        }
    return {
        **body,
        "scope": resolved_scope,
        "empresa_id": resolved_empresa_id,
        "error": st.get("error", "falha ao consultar fichas"),
        "total_pratos": 0,
        "total_fichas": 0,
        "total_ingredientes": 0,
        "categorias": {},
    }


@app.get("/api/llm-models")
async def llm_models():
    """Modelos LLM disponíveis para geração (ids + rótulos)."""
    from pipeline.openrouter_models import api_models_payload

    if not _db_ok:
        return api_models_payload(db=None, only_enabled=True)
    from database.connection import SessionLocal

    db = SessionLocal()
    try:
        return api_models_payload(db=db, only_enabled=True)
    finally:
        db.close()


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "versao": APP_VERSION,
        "db_status": "conectado" if _db_ok else "desconectado",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ============================================================
# UPLOAD / GERAÇÃO
# ============================================================
from services.geracao import get_job_or_restore, launch_generation_job


@app.post("/api/upload-contrato")
@limiter.limit("20/minute")
async def upload_contrato(
    request: Request,
    file: UploadFile = File(...),
    usuario: Optional[Usuario] = Depends(get_usuario_geracao),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".pdf", ".xlsx", ".xls"):
        raise HTTPException(400, f"Formato '{ext}' não suportado. Use PDF ou Excel.")

    content = await file.read()
    dest = UPLOAD_DIR / f"contrato{ext}"
    dest.write_bytes(content)

    return {
        "success": True,
        "filename": file.filename,
        "tipo": ext[1:],
        "tamanho_kb": round(len(content) / 1024, 1),
        "path": dest.name,
    }


@app.post("/api/gerar")
@limiter.limit("10/minute")
async def gerar_cardapio(
    request: Request,
    body: GerarCardapioRequest,
    usuario: Optional[Usuario] = Depends(get_usuario_geracao),
):
    if body.empresa_id and str(body.empresa_id).strip():
        alinhar_empresa(str(body.empresa_id).strip(), usuario)

    eid = _empresa_id_efetivo_gerar(body, usuario)
    if _db_ok and not eid:
        raise HTTPException(
            status_code=400,
            detail="empresa_id em falta: inicie sessão (utilizador com empresa) ou defina DEFAULT_EMPRESA_ID no .env com DEBUG=true e DEMO_GERAR_SEM_AUTH=true.",
        )
    body_resolved = body.model_copy(update={"empresa_id": eid})

    if _db_ok:
        from pipeline.openrouter_models import (
            assert_llm_model_allowed_for_generation,
            assert_llm_model_allowed_for_review,
        )
        from database.connection import SessionLocal

        db_chk = SessionLocal()
        try:
            assert_llm_model_allowed_for_generation(db_chk, body_resolved.llm_model)
            assert_llm_model_allowed_for_review(db_chk, body_resolved.review_llm_model)
        finally:
            db_chk.close()

    job_id = str(uuid.uuid4())[:8]
    timeout_budget_raw = (os.getenv("MENUAI_FAST_BUDGET_SECONDS") or "300").strip()
    try:
        timeout_budget_seconds = max(60, int(float(timeout_budget_raw)))
    except ValueError:
        timeout_budget_seconds = 300
    now_iso = datetime.utcnow().isoformat()
    now_ts = time.time()
    payload_config = body_resolved.model_dump()
    payload_config["timeout_budget_seconds"] = timeout_budget_seconds
    job_state.jobs[job_id] = {
        "status": "iniciando",
        "progress": 0,
        "logs": [],
        "result": None,
        "error": None,
        "error_type": None,
        "timeout_reason": None,
        "config": payload_config,
        "started_at": now_iso,
        "last_update_at": now_iso,
        "started_ts": now_ts,
        "last_update_ts": now_ts,
        "current_step": "iniciando",
        "timeout_budget_seconds": timeout_budget_seconds,
    }
    job_state.job_queues[job_id] = queue.Queue()

    if _db_ok:
        try:
            from database.connection import SessionLocal
            from database.models import JobAgente as JA

            db = SessionLocal()
            job_db = JA(
                job_id=job_id,
                empresa_id=eid,
                status="iniciando",
                progresso=0,
                parametros_json=payload_config,
                iniciado_em=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                criado_por_id=(str(usuario.id) if usuario else None),
            )
            db.add(job_db)
            db.commit()
            db.close()
        except Exception as e:
            print(f"⚠️  Não foi possível persistir job: {e}")

    try:
        launch_generation_job(
            job_id,
            body_resolved.dias,
            body_resolved.target_custo_total,
            body_resolved.target_custo_proteico,
            body_resolved.restricoes_usuario,
            body_resolved.refeicoes,
            eid,
            body_resolved.contrato_id,
            body_resolved.nome_cardapio,
            body_resolved.llm_model,
            body_resolved.review_llm_model,
            body_resolved.review_enabled,
            body_resolved.review_strategy,
            body_resolved.generation_mode,
            upload_dir=UPLOAD_DIR,
            db_ok=_db_ok,
            contrato_analise_confirmada=body_resolved.contrato_analise_confirmada,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao iniciar o worker de geração: {exc}",
        ) from exc
    runtime_status = str((job_state.jobs.get(job_id) or {}).get("status") or "executando")
    logger.info(
        "generate_request_v3 job_id=%s status=%s mode=%s confirmed=%s model=%s contrato_id=%s empresa_id=%s",
        job_id,
        runtime_status,
        body_resolved.generation_mode,
        body_resolved.contrato_analise_confirmada,
        body_resolved.llm_model,
        body_resolved.contrato_id,
        eid,
    )
    return {"job_id": job_id, "status": runtime_status, "launch_mode": "thread"}


@app.post("/api/gerar/upload")
@limiter.limit("10/minute")
async def gerar_cardapio_com_upload(
    request: Request,
    file: UploadFile = File(...),
    dias: int = Form(..., ge=1, le=366),
    refeicoes: str = Form('["almoco","jantar"]'),
    target_custo_total: float = Form(10.00, ge=0),
    restricoes_usuario: str = Form(""),
    nome_cardapio: Optional[str] = Form(None),
    llm_model: Optional[str] = Form(None),
    review_llm_model: Optional[str] = Form(None),
    review_enabled: bool = Form(True),
    review_strategy: str = Form("consultive"),
    usuario: Optional[Usuario] = Depends(get_usuario_geracao),
):
    """Upload/cadastro de contrato para o fluxo assistido.

    - Deduplica por SHA256 do arquivo
    - Cria contrato automaticamente se novo
    - Regrava arquivo físico mesmo em contratos deduplicados (importante após restart/deploy)
    - Não dispara análise nem geração; o frontend confirma o upload antes da análise
    """
    import hashlib

    from services.contract_parser import SUPPORTED_CONTRACT_EXTENSIONS, analysis_looks_invalid

    # 1. Validar extensão
    ext = Path(file.filename or "").suffix.lower()
    if ext not in SUPPORTED_CONTRACT_EXTENSIONS:
        raise HTTPException(400, f"Formato '{ext}' não suportado. Use PDF, Excel, DOCX ou TXT.")

    # 2. Ler conteúdo e calcular hash
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    # 3. Resolver empresa_id
    eid = None
    if usuario is not None and getattr(usuario, "empresa_id", None) is not None:
        eid = str(usuario.empresa_id)
    if DEBUG and DEMO_GERAR_SEM_AUTH and usuario is None and DEFAULT_EMPRESA_ID:
        eid = DEFAULT_EMPRESA_ID
    if _db_ok and not eid:
        raise HTTPException(400, "empresa_id em falta: inicie sessão ou defina DEFAULT_EMPRESA_ID.")

    # 4. Buscar ou criar contrato
    novo_contrato = False
    contrato_id = None
    contrato_nome = Path(file.filename or "contrato").stem

    if _db_ok:
        from database.connection import SessionLocal
        from database.models import Contrato as ContratoModel
        from database.models import _uuid as model_uuid

        db = SessionLocal()
        try:
            contrato = (
                db.query(ContratoModel)
                .filter(
                    ContratoModel.arquivo_hash == file_hash,
                    ContratoModel.empresa_id == eid,
                    ContratoModel.ativo == True,
                )
                .first()
            )

            if contrato:
                contrato_id = contrato.id
                contrato_nome = contrato.nome
                novo_contrato = False
                upload_subdir = UPLOAD_DIR / "contratos"
                upload_subdir.mkdir(parents=True, exist_ok=True)
                dest = upload_subdir / f"{file_hash}{ext}"
                # Garante que o arquivo exista fisicamente mesmo após restart/deploy.
                dest.write_bytes(content)
                contrato.arquivo_path = str(dest)
                db.commit()
            else:
                contrato_id = str(model_uuid())
                upload_subdir = UPLOAD_DIR / "contratos"
                upload_subdir.mkdir(parents=True, exist_ok=True)
                dest = upload_subdir / f"{file_hash}{ext}"
                dest.write_bytes(content)

                contrato = ContratoModel(
                    id=contrato_id,
                    empresa_id=eid,
                    nome=contrato_nome,
                    arquivo_path=str(dest),
                    arquivo_hash=file_hash,
                )
                db.add(contrato)
                db.commit()
                db.refresh(contrato)
                novo_contrato = True

            try:
                from services.knowledge_base import sync_contrato_document
                from services.knowledge_hooks import sync_knowledge_safe

                sync_knowledge_safe(sync_contrato_document, db, contrato)
                db.commit()
            except Exception:
                pass

            analise_status = "analisado" if (contrato.regras_json and not analysis_looks_invalid(contrato.regras_json)) else "pendente"
        finally:
            db.close()
    else:
        # Sem DB — salva arquivo e usa hash como contrato_id
        upload_subdir = UPLOAD_DIR / "contratos"
        upload_subdir.mkdir(parents=True, exist_ok=True)
        dest = upload_subdir / f"{file_hash}{ext}"
        dest.write_bytes(content)
        contrato_id = file_hash[:16]
        novo_contrato = True
        analise_status = "pendente"

    return {
        "success": True,
        "upload_status": "concluido",
        "contrato_id": contrato_id,
        "contrato_nome": contrato_nome,
        "novo_contrato": novo_contrato,
        "analise_status": analise_status,
        "filename": file.filename,
        "tipo": ext[1:],
        "tamanho_kb": round(len(content) / 1024, 1),
        "review_llm_model": review_llm_model,
        "review_enabled": review_enabled,
        "review_strategy": review_strategy,
    }


@app.get("/api/stream/{job_id}")
@limiter.limit("60/minute")
async def stream_job(request: Request, job_id: str, usuario: Optional[Usuario] = Depends(get_usuario_geracao)):
    j = get_job_or_restore(job_id, _db_ok) if _db_ok else job_state.jobs.get(job_id)
    if not j and job_id not in job_state.job_queues:
        raise HTTPException(404, f"Job '{job_id}' não encontrado")
    if job_id not in job_state.job_queues:
        job_state.job_queues[job_id] = queue.Queue()
    if j and j.get("status") == "concluido" and j.get("result"):
        async def once():
            r = j.get("result", "")
            yield f"data: {json.dumps({'type': 'log', 'message': 'reidratação a partir do banco'})}\n\n"
            payload = {
                "type": "done",
                "result": r,
                "progress": 100,
                "generator_model": j.get("generator_model") or (j.get("config") or {}).get("generator_model_used"),
                "generator_provider": j.get("generator_provider") or (j.get("config") or {}).get("generator_provider_used"),
                "review_model": j.get("review_model") or (j.get("config") or {}).get("review_model_used"),
                "review_provider": j.get("review_provider") or (j.get("config") or {}).get("review_provider_used"),
                "review_status": j.get("review_status") or (j.get("config") or {}).get("review_status"),
                "review_summary": j.get("review_summary") or (j.get("config") or {}).get("review_summary"),
                "review_warnings": j.get("review_warnings") or (j.get("config") or {}).get("review_warnings") or [],
                "review_applied_fixes_count": j.get("review_applied_fixes_count") or (j.get("config") or {}).get("review_applied_fixes_count") or 0,
                "degraded_generation": bool(j.get("degraded_generation") if j.get("degraded_generation") is not None else (j.get("config") or {}).get("degraded_generation")),
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        return StreamingResponse(once(), media_type="text/event-stream")
    if j and j.get("status") == "erro":
        async def once_error():
            yield f"data: {json.dumps({'type': 'error', 'message': j.get('error') or 'Job em erro', 'progress': j.get('progress', 0), 'error_type': j.get('error_type'), 'timeout_reason': j.get('timeout_reason')}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            once_error(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    async def gen():
        q = job_state.job_queues[job_id]
        while True:
            try:
                msg = await asyncio.to_thread(q.get, True, 45)
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                if msg.get("type") in ("done", "error"):
                    break
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/status/{job_id}")
async def job_status(job_id: str, usuario: Optional[Usuario] = Depends(get_usuario_geracao)):
    j = get_job_or_restore(job_id, _db_ok) if _db_ok else job_state.jobs.get(job_id)
    if not j:
        raise HTTPException(404, f"Job '{job_id}' não encontrado")
    return _status_payload(job_id, j)


@app.get("/api/admin/jobs/recentes")
async def admin_recent_jobs(
    limit: int = 20,
    status: Optional[str] = None,
    usuario: Optional[Usuario] = Depends(get_usuario_geracao),
):
    if not _db_ok:
        return {"items": [], "total": 0}
    if not usuario or getattr(usuario, "role", None) != "super_admin":
        raise HTTPException(403, "Apenas super_admin pode consultar jobs recentes.")

    from database.connection import SessionLocal
    from database.models import JobAgente

    db = SessionLocal()
    try:
        query = db.query(JobAgente)
        if status:
            query = query.filter(JobAgente.status == status)
        rows = query.order_by(JobAgente.iniciado_em.desc()).limit(max(1, min(limit, 100))).all()
        items = []
        for row in rows:
            duration_seconds = None
            if row.iniciado_em:
                end = row.concluido_em or row.updated_at
                if end:
                    duration_seconds = max(0.0, (end - row.iniciado_em).total_seconds())
            params = row.parametros_json if isinstance(row.parametros_json, dict) else {}
            items.append(
                {
                    "job_id": row.job_id,
                    "status": row.status,
                    "progress": row.progresso,
                    "empresa_id": str(row.empresa_id) if row.empresa_id else None,
                    "started_at": row.iniciado_em.isoformat() if row.iniciado_em else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                    "concluded_at": row.concluido_em.isoformat() if row.concluido_em else None,
                    "duration_seconds": round(duration_seconds, 2) if duration_seconds is not None else None,
                    "llm_model": params.get("llm_model"),
                    "generation_mode": params.get("generation_mode"),
                    "attempts": params.get("attempts"),
                    "timeout_reason": params.get("timeout_reason"),
                    "error": row.erro,
                }
            )
        return {"items": items, "total": len(items)}
    finally:
        db.close()


# ============================================================
# Human-in-the-Loop: Confirmação do contrato
# ============================================================
from pydantic import BaseModel, Field


class ConfirmacaoBody(BaseModel):
    """Body para confirmação ou rejeição da análise do contrato."""
    confirmar: bool = Field(True, description="True para confirmar e continuar, False para cancelar")
    ajustes: Optional[str] = Field(None, description="Ajustes/observações textuais a incorporar na geração")


@app.post("/api/gerar/{job_id}/confirmar")
@limiter.limit("30/minute")
async def confirmar_geracao(
    request: Request,
    job_id: str,
    body: ConfirmacaoBody,
    usuario: Optional[Usuario] = Depends(get_usuario_geracao),
):
    """
    Confirma ou rejeita a análise do contrato no fluxo human-in-the-loop.

    - `confirmar: true` → a geração continua com o pipeline completo
    - `confirmar: false` → cancela o job
    - `ajustes` (opcional) → texto livre com observações que serão incorporadas à geração
    """
    from services.geracao import get_job_or_restore

    j = get_job_or_restore(job_id, _db_ok)
    if not j:
        raise HTTPException(404, f"Job '{job_id}' não encontrado")

    if j.get("status") != "aguardando_confirmacao":
        raise HTTPException(
            400,
            f"Job '{job_id}' não está aguardando confirmação (status atual: {j.get('status')})",
        )

    if not body.confirmar:
        j["status"] = "erro"
        j["error"] = "Geração cancelada pelo usuário após análise do contrato."
        return {
            "ok": True,
            "job_id": job_id,
            "status": "cancelado",
            "mensagem": "Geração cancelada. O job não será processado.",
        }

    # Aplica ajustes se fornecidos
    if body.ajustes:
        j["ajustes_usuario"] = body.ajustes

    # Retoma a execução — muda status para que o loop no worker desbloqueie
    j["status"] = "executando"
    j["last_update_at"] = datetime.utcnow().isoformat()
    j["last_update_ts"] = time.time()

    if _db_ok:
        try:
            from database.connection import SessionLocal
            from database.models import JobAgente

            db = SessionLocal()
            row = db.query(JobAgente).filter(JobAgente.job_id == job_id).first()
            if row:
                row.status = "executando"
                row.updated_at = datetime.utcnow()
                db.commit()
            db.close()
        except Exception:
            pass

    logger.info(
        "generate_confirm_v2 job_id=%s confirmed=%s ajustes=%s",
        job_id,
        body.confirmar,
        bool(body.ajustes),
    )

    return {
        "ok": True,
        "job_id": job_id,
        "status": "executando",
        "mensagem": "Confirmação recebida. A geração do cardápio foi retomada.",
        "ajustes_aplicados": bool(body.ajustes),
    }

@app.get("/api/download/{job_id}")
async def download(job_id: str, formato: str = "xlsx", usuario: Optional[Usuario] = Depends(get_usuario_geracao)):
    j = get_job_or_restore(job_id, _db_ok) if _db_ok else job_state.jobs.get(job_id)
    if not j or not j.get("result"):
        raise HTTPException(404, "Resultado não disponível")
    content = j["result"]
    if formato == "xlsx":
        df = _extrair_dataframe(content)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Cardápio", index=False)
            ws = writer.sheets["Cardápio"]
            for col in ws.columns:
                max_len = max(len(str(c.value or "")) for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="cardapio_{job_id}.xlsx"'},
        )
    return Response(
        content=content.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="cardapio_{job_id}.txt"'},
    )


def _extrair_dataframe(texto: str) -> pd.DataFrame:
    linhas = [l.strip() for l in texto.split("\n") if "|" in l]
    linhas = [l for l in linhas if not re.match(r"^\|[\s\-:|]+\|$", l)]
    rows, header = [], None
    for l in linhas:
        cells = [c.strip() for c in l.split("|") if c.strip()]
        if not cells:
            continue
        if header is None:
            header = cells
        elif len(cells) == len(header):
            rows.append(cells)
    if not header or not rows:
        return pd.DataFrame({"Cardápio": texto.split("\n")})
    return pd.DataFrame(rows, columns=header)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    print(f"\n🍽️  Menu.AI v{APP_VERSION} — http://localhost:{port}")
    print(f"📚 Documentação API: http://localhost:{port}/api/docs\n")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=DEBUG)

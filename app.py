
"""
Menu.AI — Backend FastAPI v3.2.7
Pipeline LLM + ferramentas + Banco de Dados PostgreSQL/Supabase + Multi-Tenant
"""
import io
import json
import os
import queue
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import uvicorn
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

load_dotenv()

APP_VERSION = "3.5.3"
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
from services.geracao import executar_crew, get_job_or_restore


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
    background_tasks: BackgroundTasks,
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
        from pipeline.openrouter_models import assert_llm_model_allowed_for_generation
        from database.connection import SessionLocal

        db_chk = SessionLocal()
        try:
            assert_llm_model_allowed_for_generation(db_chk, body_resolved.llm_model)
        finally:
            db_chk.close()

    job_id = str(uuid.uuid4())[:8]
    job_state.jobs[job_id] = {
        "status": "iniciando",
        "progress": 0,
        "logs": [],
        "result": None,
        "error": None,
        "config": body_resolved.model_dump(),
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
                parametros_json=body_resolved.model_dump(),
                iniciado_em=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                criado_por_id=(str(usuario.id) if usuario else None),
            )
            db.add(job_db)
            db.commit()
            db.close()
        except Exception as e:
            print(f"⚠️  Não foi possível persistir job: {e}")

    background_tasks.add_task(
        executar_crew,
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
        upload_dir=UPLOAD_DIR,
        db_ok=_db_ok,
    )
    return {"job_id": job_id, "status": "iniciando"}


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
    background_tasks: BackgroundTasks = None,
    usuario: Optional[Usuario] = Depends(get_usuario_geracao),
):
    """Upload de contrato + geração em uma única chamada.

    - Deduplica por SHA256 do arquivo
    - Cria contrato automaticamente se novo
    - Dispara pipeline de geração em background
    - Retorna job_id + contrato_id + analise
    """
    import hashlib
    import json as _json

    # 1. Validar extensão
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".pdf", ".xlsx", ".xls"):
        raise HTTPException(400, f"Formato '{ext}' não suportado. Use PDF ou Excel.")

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

    # 5. Parse refeicoes
    try:
        refeicoes_list = _json.loads(refeicoes) if isinstance(refeicoes, str) else refeicoes
    except Exception:
        refeicoes_list = ["almoco", "jantar"]

    # 6. Disparar pipeline de geração (mesma lógica do /api/gerar)
    gerar_body = GerarCardapioRequest(
        empresa_id=eid,
        contrato_id=contrato_id,
        dias=dias,
        target_custo_total=target_custo_total,
        target_custo_proteico=3.50,
        restricoes_usuario=restricoes_usuario or "",
        refeicoes=refeicoes_list,
        nome_cardapio=nome_cardapio,
        llm_model=llm_model,
    )

    if _db_ok:
        from pipeline.openrouter_models import assert_llm_model_allowed_for_generation
        from database.connection import SessionLocal

        db_chk = SessionLocal()
        try:
            assert_llm_model_allowed_for_generation(db_chk, gerar_body.llm_model)
        finally:
            db_chk.close()

    job_id = str(uuid.uuid4())[:8]
    job_state.jobs[job_id] = {
        "status": "iniciando",
        "progress": 0,
        "logs": [],
        "result": None,
        "error": None,
        "config": gerar_body.model_dump(),
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
                parametros_json=gerar_body.model_dump(),
                iniciado_em=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                criado_por_id=(str(usuario.id) if usuario else None),
            )
            db.add(job_db)
            db.commit()
            db.close()
        except Exception as e:
            print(f"⚠️  Não foi possível persistir job: {e}")

    background_tasks.add_task(
        executar_crew,
        job_id,
        gerar_body.dias,
        gerar_body.target_custo_total,
        gerar_body.target_custo_proteico,
        gerar_body.restricoes_usuario,
        gerar_body.refeicoes,
        eid,
        gerar_body.contrato_id,
        gerar_body.nome_cardapio,
        gerar_body.llm_model,
        upload_dir=UPLOAD_DIR,
        db_ok=_db_ok,
    )

    return {
        "job_id": job_id,
        "contrato_id": contrato_id,
        "contrato_nome": contrato_nome,
        "novo_contrato": novo_contrato,
        "analise": None,
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
            yield f"data: {json.dumps({'type': 'done', 'result': r, 'progress': 100})}\n\n"
        return StreamingResponse(once(), media_type="text/event-stream")

    async def gen():
        q = job_state.job_queues[job_id]
        while True:
            try:
                msg = q.get(timeout=45)
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                if msg.get("type") in ("done", "error"):
                    break
            except queue.Empty:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/status/{job_id}")
async def job_status(job_id: str, usuario: Optional[Usuario] = Depends(get_usuario_geracao)):
    j = get_job_or_restore(job_id, _db_ok) if _db_ok else job_state.jobs.get(job_id)
    if not j:
        raise HTTPException(404, f"Job '{job_id}' não encontrado")
    return j


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
    j = job_state.jobs.get(job_id)
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

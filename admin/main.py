"""
MENU-A — aplicação administrativa (segundo processo ASGI, porta distinta).

Monta os routers de domínio existentes com substituição de `get_usuario_atual`
por autenticação admin (JWT admin/super_admin ou X-Admin-Api-Key).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

load_dotenv()

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

from admin.deps import get_usuario_admin  # noqa: E402
from admin.routers.knowledge_admin import router as knowledge_admin_router  # noqa: E402
from admin.routers.llm_admin import router as llm_admin_router  # noqa: E402
from admin.routers.meta import router as meta_router  # noqa: E402
from pipeline.sequential_spec import pipeline_step_meta_labels  # noqa: E402
from database.connection import get_db, verificar_conexao  # noqa: E402
from routers.auth import get_usuario_atual, router as auth_router  # noqa: E402
from routers.cardapios import router as cardapios_router  # noqa: E402
from routers.contratos import router as contratos_router  # noqa: E402
from routers.empresas import router as empresas_router  # noqa: E402
from routers.fichas_tecnicas import router as fichas_router  # noqa: E402
from routers.ingredientes import router as ingredientes_router  # noqa: E402

APP_VERSION = "3.4.0"
ADMIN_DIR = Path(__file__).resolve().parent
ADMIN_STATIC_DIR = ADMIN_DIR / "static"


def _inject_admin_asset(request: Request) -> dict:
    """Garante URLs de estáticos corretas (proxy, root_path) com fallback."""

    def admin_asset(name: str) -> str:
        try:
            return str(request.url_for("admin_static", path=name))
        except Exception:
            base = str(request.base_url).rstrip("/")
            return f"{base}/static/{name}"

    return {"admin_asset": admin_asset}


templates = Jinja2Templates(
    directory=str(ADMIN_DIR / "templates"),
    context_processors=[_inject_admin_asset],
)

app = FastAPI(
    title="Menu.AI — Admin",
    version=APP_VERSION,
    description="Painel administrativo (mesmo banco de dados que o núcleo da aplicação).",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.dependency_overrides[get_usuario_atual] = get_usuario_admin

_cors = [o.strip() for o in os.getenv("ADMIN_CORS_ORIGINS", "").split(",") if o.strip()]
if not _cors:
    _cors = ["http://localhost:8001", "http://127.0.0.1:8001"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_db_ok = verificar_conexao()


def _jwt_dev_para_admin(db: Session) -> tuple[str | None, str | None]:
    """
    Em desenvolvimento: gera JWT válido para o primeiro admin/super_admin (ou e-mail em MENUAI_ADMIN_DEV_EMAIL).
    Só deve ser usado com DEBUG=true.
    """
    from database.models import Usuario
    from routers.auth import criar_token

    prefer = (os.getenv("MENUAI_ADMIN_DEV_EMAIL") or "").strip().lower()
    base = db.query(Usuario).filter(Usuario.ativo == True)
    if prefer:
        u = base.filter(Usuario.email == prefer).first()
        if u and u.role in ("super_admin", "admin"):
            return criar_token({"sub": str(u.id)}), u.email
    u = base.filter(Usuario.role == "super_admin").first()
    if not u:
        u = base.filter(Usuario.role == "admin").first()
    if not u:
        return None, None
    return criar_token({"sub": str(u.id)}), u.email


app.include_router(auth_router)
app.include_router(empresas_router)
app.include_router(contratos_router)
app.include_router(ingredientes_router)
app.include_router(fichas_router)
app.include_router(cardapios_router)
app.include_router(meta_router)
app.include_router(llm_admin_router)
app.include_router(knowledge_admin_router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "servico": "menu-a-admin",
        "versao": APP_VERSION,
        "db_status": "conectado" if _db_ok else "desconectado",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    ctx: dict = {
        "db_ok": _db_ok,
        "docs_url": "/api/docs",
        "debug": DEBUG,
        "dev_token": None,
        "dev_email": None,
        "admin_api_key_configured": bool((os.getenv("MENUAI_ADMIN_API_KEY") or "").strip()),
        "pipeline_steps": pipeline_step_meta_labels(),
    }
    if DEBUG and _db_ok:
        from database.connection import SessionLocal

        db = SessionLocal()
        try:
            try:
                tok, em = _jwt_dev_para_admin(db)
                ctx["dev_token"] = tok
                ctx["dev_email"] = em
            except Exception:
                logging.getLogger(__name__).exception(
                    "Falha ao gerar JWT de desenvolvimento para o painel admin"
                )
        finally:
            db.close()
    return templates.TemplateResponse(request, "dashboard.html", ctx)


@app.get("/api/admin/info")
def admin_info(db: Session = Depends(get_db), usuario=Depends(get_usuario_admin)):
    """Smoke interno: usuário efetivo da sessão admin."""
    return {
        "usuario_id": usuario.id,
        "email": usuario.email,
        "role": usuario.role,
        "empresa_id": usuario.empresa_id,
    }


# Montar estáticos por último (Starlette: evita rotas a “roubarem” /static).
app.mount(
    "/static",
    StaticFiles(directory=str(ADMIN_STATIC_DIR)),
    name="admin_static",
)

"""
Menu.AI — Conexão com banco de dados via SQLAlchemy
Suporta Supabase/PostgreSQL e SQLite como fallback técnico.
"""
import os
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

load_dotenv()

# Raiz do repositório (database/ -> parent parent)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _default_sqlite_url() -> str:
    """SQLite no ficheiro `menuai_test.db` na raiz do projecto (independente do CWD)."""
    p = (_PROJECT_ROOT / "menuai_test.db").resolve()
    return "sqlite:///" + p.as_posix()


def _normalize_sqlite_url(url: str) -> str:
    """Garante caminho absoluto para `sqlite:///` relativo a `./` ou ficheiro na raiz."""
    if not url.startswith("sqlite"):
        return url
    if not url.startswith("sqlite:///"):
        return url
    path_part = url[len("sqlite:///") :]
    if not path_part or path_part.startswith("//"):
        return url
    p = Path(path_part)
    if p.is_absolute():
        return "sqlite:///" + p.as_posix()
    return "sqlite:///" + (_PROJECT_ROOT / p).resolve().as_posix()


# ============================================================
# URL de conexão (alinhada com Alembic: mesmo default e regras)
# Prioridade: SUPABASE_DB_URL -> DATABASE_URL -> SQLite fallback
# ============================================================
_raw = (os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL") or "").strip()
if not _raw:
    DATABASE_URL = _default_sqlite_url()
else:
    DATABASE_URL = _normalize_sqlite_url(_raw) if _raw.startswith("sqlite") else _raw

# Compatibilidade com URLs do Heroku/Railway (postgres:// → postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

IS_SQLITE = DATABASE_URL.startswith("sqlite")
DB_PROVIDER = "supabase" if "supabase.co" in DATABASE_URL or "supabase.com" in DATABASE_URL else ("sqlite" if IS_SQLITE else "postgresql")

# ============================================================
# Engine SQLAlchemy — configuração por driver
# ============================================================
if IS_SQLITE:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # necessário para FastAPI (threads múltiplas)
        echo=os.getenv("DB_ECHO", "false").lower() == "true",
    )

    # Habilita WAL mode e foreign keys no SQLite
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

else:
    # PostgreSQL — pool completo
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        echo=os.getenv("DB_ECHO", "false").lower() == "true",
    )

# ============================================================
# Session Factory
# ============================================================
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ============================================================
# Base declarativa para os Models
# ============================================================
Base = declarative_base()


# ============================================================
# Dependency para FastAPI (injeção via Depends)
# ============================================================
def get_db() -> Generator[Session, None, None]:
    """
    Dependency que fornece uma sessão de banco por requisição.
    Garante fechamento automático mesmo em caso de erro.

    Uso nos routers:
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# Criação de tabelas (apenas desenvolvimento — produção: Alembic)
# ============================================================
def criar_tabelas():
    """
    Cria todas as tabelas no metadata da Base (útil em dev via CREATE_ALL_ON_START).

    **Produção:** use `alembic upgrade head` e mantenha `CREATE_ALL_ON_START=false` no .env
    (ou omita) para evitar *drift* entre `create_all` e a história de migrações.
    """
    from database import models  # noqa: F401 — registra os models na Base
    Base.metadata.create_all(bind=engine)
    print("✅ Tabelas criadas/verificadas no banco de dados.")


def verificar_conexao() -> bool:
    """Testa a conexão com o banco de dados."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ Falha na conexão com o banco: {e}")
        return False

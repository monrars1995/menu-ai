"""
Alembic env.py — Menu.AI
Configura as migrações para PostgreSQL via SQLAlchemy.
"""
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# ============================================================
# Adiciona o diretório raiz ao sys.path
# ============================================================
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Carrega variáveis de ambiente
load_dotenv(ROOT_DIR / ".env")

# ============================================================
# Importa os models e a mesma DATABASE_URL resolvida que a app
# ============================================================
from database.connection import Base, DATABASE_URL
import database.models  # noqa: F401 — necessário para registrar os models

# ============================================================
# Configuração do Alembic
# ============================================================
config = context.config

# Configura logging se o arquivo alembic.ini tiver seção [loggers]
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata dos models (usado para autogenerate)
target_metadata = Base.metadata

# ============================================================
# URL: mesma que `database.connection` (env + default SQLite na raiz do projecto)
# Para PostgreSQL local, defina DATABASE_URL no .env (ex.: setup.sh / Docker).
# ============================================================
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))


# ============================================================
# Funções de migração
# ============================================================

def run_migrations_offline() -> None:
    """
    Modo offline: gera SQL sem conexão real.
    Útil para revisar as migrações antes de aplicar.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,            # detecta mudanças de tipo
        compare_server_default=True,  # detecta mudanças de default
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Modo online: conecta ao banco e aplica as migrações.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


# ============================================================
# Execução
# ============================================================
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
